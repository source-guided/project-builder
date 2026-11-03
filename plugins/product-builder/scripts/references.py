#!/usr/bin/env python3
"""참조 메타데이터 조회와 원천 접근 경로를 기록한다. 원천 본문은 저장하지 않는다."""

import argparse
import hashlib
import json
from pathlib import Path
import uuid
import os
import tempfile
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
POLICY = (ROOT / "sources/governance/reference-routing.md").resolve()
FIELDS = {"id", "label", "kind", "access", "locator", "topics", "related_references"}


def read_index(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text())
    return validate_index(data)


def validate_index(data):
    if set(data) != {"format", "entries"} or data["format"] != 1 or not isinstance(data["entries"], list):
        raise ValueError("Invalid reference index format")
    ids = set()
    for item in data["entries"]:
        if not isinstance(item, dict):
            raise ValueError("Reference entries must be metadata objects")
        if set(item) - FIELDS or not {"id", "label", "kind", "access", "locator", "topics"} <= set(item):
            raise ValueError("References may contain navigation metadata only")
        if any(not isinstance(item[key], str) or not item[key] for key in ("id", "label", "kind", "access", "locator")):
            raise ValueError("Reference text fields must be nonempty strings")
        if len(item["label"]) > 240 or len(item["id"]) > 160:
            raise ValueError("Reference labels and identifiers must stay compact")
        if item["id"] in ids:
            raise ValueError("Duplicate reference id")
        ids.add(item["id"])
        if item["kind"] not in {"reference", "source"} or item["access"] not in {"file", "web", "connector"}:
            raise ValueError("Unsupported reference kind or access method")
        if item["access"] == "web":
            url = urlparse(item["locator"])
            if url.scheme not in {"https", "http"} or not url.netloc or url.username or url.password:
                raise ValueError("Web references require an absolute HTTP(S) location without credentials")
        for key in ("topics", "related_references"):
            if not isinstance(item.get(key, []), list) or not all(isinstance(value, str) for value in item.get(key, [])):
                raise ValueError("Reference topics and relationships must be string arrays")
    return data


def walk_references(index):
    pending = [Path(index).resolve()]
    visited = set()
    result = []
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        data = read_index(current)
        result.append({"index": str(current), "entries": data["entries"]})
        for item in data["entries"]:
            if item["kind"] == "reference" and item["access"] == "file":
                pending.append((current.parent / item["locator"]).resolve())
            pending.extend((current.parent / path).resolve() for path in item.get("related_references", []))
    return result


def events(trace):
    trace = Path(trace)
    if trace.is_symlink():
        raise ValueError("Trace must not be a symlink")
    return [json.loads(line) for line in trace.read_text().splitlines() if line.strip()] if trace.exists() else []


def append(trace, event):
    trace = Path(trace)
    events(trace)
    trace.parent.mkdir(parents=True, exist_ok=True)
    with trace.open("a") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def resolve(index, identifier, trace):
    index = Path(index).resolve()
    candidates = [entry for entry in read_index(index)["entries"] if entry["id"] == identifier]
    if not candidates:
        raise ValueError("Reference not found; register an observed location first")
    entry = candidates[0]
    location = str((index.parent / entry["locator"]).resolve()) if entry["access"] == "file" else entry["locator"]
    event = {"event": "reference", "receipt": str(uuid.uuid4()), "index": str(index), "id": identifier, "target_kind": entry["kind"], "access": entry["access"], "location": location, "governance": entry["access"] == "file" and location == str(POLICY)}
    append(trace, event)
    return {**event, "related_references": [str((index.parent / value).resolve()) for value in entry.get("related_references", [])]}


def audit_records(records, require_policy=False):
    previous = None
    policy_read = False
    consumed = set()
    reads = 0
    for event in records:
        if event.get("event") == "reference":
            previous = event
            continue
        if event.get("event") != "source" or previous is None or previous.get("event") != "reference":
            raise ValueError("A source access must immediately follow a reference")
        if event.get("receipt") != previous.get("receipt") or event["receipt"] in consumed:
            raise ValueError("Source access needs a fresh matching reference receipt")
        if previous["target_kind"] != "source" or event.get("location") != previous.get("location"):
            raise ValueError("Source does not match the resolved reference")
        if not policy_read:
            if not previous.get("governance") or event.get("status") != "read":
                raise ValueError("Read the governing routing source through its reference first")
            policy_read = True
        consumed.add(event["receipt"])
        reads += 1
        previous = event
    if require_policy and not policy_read:
        raise ValueError("A completed traversal must include the governing source")
    return {"valid": True, "source_accesses": reads, "policy_read": policy_read}


def record(trace, receipt, status="read", digest=None):
    history = events(trace)
    if not history or history[-1].get("event") != "reference" or history[-1].get("receipt") != receipt:
        raise ValueError("Resolve a reference immediately before every source access")
    event = {"event": "source", "receipt": receipt, "location": history[-1]["location"], "status": status}
    if digest:
        event["observed_sha256"] = digest
    audit_records([*history, event])
    append(trace, event)
    return event


def read_source(index, identifier, trace):
    resolved = resolve(index, identifier, trace)
    if resolved["target_kind"] != "source" or resolved["access"] != "file":
        raise ValueError("Use the appropriate source tool, then record its receipt")
    # 원천을 읽기 전에 경로 규칙을 검사한다.
    history = events(trace)
    audit_records([*history, {"event": "source", "receipt": resolved["receipt"], "location": resolved["location"], "status": "read"}])
    data = Path(resolved["location"]).read_bytes()
    text = data.decode("utf-8")
    record(trace, resolved["receipt"], digest=hashlib.sha256(data).hexdigest())
    return {"reference": resolved, "content": text}


def add(index, identifier, label, locator, access, topics):
    index = Path(index).resolve()
    data = read_index(index)
    if any(item["id"] == identifier for item in data["entries"]):
        raise ValueError("Reference already exists; do not silently replace its owner binding")
    if access == "file" and not (index.parent / locator).resolve().is_file():
        raise ValueError("Register only an observed existing file")
    data["entries"].append({"id": identifier, "label": label, "kind": "source", "access": access, "locator": locator, "topics": topics})
    validate_index(data)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=index.parent, delete=False, encoding="utf-8") as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        os.replace(temporary, index)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list"); listing.add_argument("--index", type=Path, required=True)
    walking = commands.add_parser("walk"); walking.add_argument("--index", type=Path, required=True)
    for name in ("resolve", "read"):
        command = commands.add_parser(name)
        command.add_argument("--index", type=Path, required=True)
        command.add_argument("--id", required=True)
        command.add_argument("--trace", type=Path, required=True)
    command = commands.add_parser("record")
    command.add_argument("--trace", type=Path, required=True); command.add_argument("--receipt", required=True)
    command.add_argument("--status", choices=("read", "unavailable", "reused-from-current-context"), default="read")
    command = commands.add_parser("audit"); command.add_argument("--trace", type=Path, required=True)
    command = commands.add_parser("add")
    command.add_argument("--index", type=Path, required=True); command.add_argument("--id", required=True)
    command.add_argument("--label", required=True); command.add_argument("--locator", required=True)
    command.add_argument("--access", choices=("file", "web", "connector"), required=True)
    command.add_argument("--topics", nargs="*", default=[])
    args = parser.parse_args()
    if args.command == "list": result = read_index(args.index)
    elif args.command == "walk": result = walk_references(args.index)
    elif args.command == "resolve": result = resolve(args.index, args.id, args.trace)
    elif args.command == "read": result = read_source(args.index, args.id, args.trace)
    elif args.command == "record": result = record(args.trace, args.receipt, args.status)
    elif args.command == "audit": result = audit_records(events(args.trace), require_policy=True)
    else:
        add(args.index, args.id, args.label, args.locator, args.access, args.topics)
        result = {"registered": args.id}
    print(json.dumps(result, ensure_ascii=False, indent=2))
