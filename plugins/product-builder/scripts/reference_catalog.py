"""무상태 참조 발견·주소 해석. 본문, 세션, 업무 정책을 소유하지 않는다."""

from collections import deque
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlparse

from reference_address import address, index_access, index_address, source_address


FIELDS = {"id", "label", "description", "kind", "access", "locator", "topics", "related_references"}


def validate_index(data):
    if not isinstance(data, dict) or set(data) != {"format", "entries"} or data["format"] != 1 or not isinstance(data["entries"], list):
        raise ValueError("Invalid reference index format")
    ids = set()
    for item in data["entries"]:
        if not isinstance(item, dict) or set(item) - FIELDS or not {"id", "label", "kind", "access", "locator", "topics"} <= set(item):
            raise ValueError("References may contain navigation metadata only")
        for key in ("id", "label", "kind", "access", "locator"):
            if not isinstance(item[key], str) or not item[key].strip():
                raise ValueError("Reference fields must be nonempty strings")
        if len(item["id"]) > 160 or len(item["label"]) > 240:
            raise ValueError("Reference identifiers and labels must stay compact")
        if "description" in item and (not isinstance(item["description"], str) or len(item["description"]) > 500):
            raise ValueError("Description must be a short discovery cue")
        if item["id"] in ids:
            raise ValueError("Duplicate reference id")
        ids.add(item["id"])
        if item["kind"] not in {"reference", "source"} or item["access"] not in {"file", "web", "connector"}:
            raise ValueError("Unsupported reference kind or access method")
        for key in ("topics", "related_references"):
            if not isinstance(item.get(key, []), list) or not all(isinstance(v, str) and v.strip() for v in item.get(key, [])):
                raise ValueError("Reference topics and relationships must be string arrays")
        locations = [item["locator"], *item.get("related_references", [])]
        for location in locations:
            parsed = urlparse(location)
            if parsed.username or parsed.password:
                raise ValueError("Reference addresses must not contain credentials")
        if item["access"] == "web":
            parsed = urlparse(item["locator"])
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("Web references require an absolute HTTP(S) address")
    return data


def binding_digest(reference):
    fields = {k: v for k, v in reference.items() if k != "index_digest"}
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


class Catalog:
    def __init__(self, reader, *, connector_reader=None):
        self.reader = reader
        self.connector_reader = connector_reader

    def read_index(self, index, *, access=None):
        access = access or index_access(index)
        location = index_address(index, access)
        if access == "connector":
            if self.connector_reader is None:
                raise ValueError("No host connector index adapter configured")
            observed = self.connector_reader(location)
        else:
            observed = self.reader(location)
        canonical = index_address(observed.get("address", location), access)
        return {"document": validate_index(observed["document"]), "digest": observed["digest"],
                "address": canonical, "access": access}

    def bind(self, index, item, digest, access):
        return {"reference": {"index": index, "id": item["id"], "access": access},
                "address": source_address(index, item["locator"], item["access"]), "kind": item["kind"], "access": item["access"],
                "label": item["label"], "description": item.get("description", ""), "topics": item["topics"],
                "related_references": [str(p) if access == "connector" else address(index, p) for p in item.get("related_references", [])],
                "index_digest": digest, "metadata": item}

    def resolve(self, index, identifier, *, access=None):
        observed = self.read_index(index, access=access)
        for item in observed["document"]["entries"]:
            if item["id"] == identifier:
                return self.bind(observed["address"], item, observed["digest"], observed["access"])
        raise ValueError(f"Reference not found: {identifier}")

    def walk(self, indexes, *, max_indexes=128):
        if max_indexes < 1:
            raise ValueError("max_indexes must be positive")
        pending = deque()
        errors = []
        for position, item in enumerate(indexes):
            try:
                index = item["index"] if isinstance(item, dict) else item
                access = item.get("access", index_access(index)) if isinstance(item, dict) else index_access(index)
                pending.append((index_address(index, access), access))
            except (ValueError, TypeError, KeyError) as error:
                errors.append({"index": None, "root_position":position,"type":type(error).__name__,"message":str(error)})
        visited, results = set(), []
        fetched = 0
        while pending and fetched < max_indexes:
            current, access = pending.popleft()
            if (current, access) in visited:
                continue
            visited.add((current, access)); fetched += 1
            try:
                observed = self.read_index(current, access=access)
            except (OSError, ValueError) as error:
                errors.append({"index": current, "access": access, "type": type(error).__name__, "message": str(error)})
                continue
            canonical = observed["address"]
            if canonical != current and (canonical,access) in visited:
                continue
            visited.add((canonical, access))
            results.append({"index": canonical, "access": access, "entries": observed["document"]["entries"], "digest": observed["digest"]})
            for item in observed["document"]["entries"]:
                try:
                    if item["kind"] == "reference":
                        target=source_address(canonical, item["locator"], item["access"])
                        pending.append((index_address(target,item["access"]), item["access"]))
                    for locator in item.get("related_references", []):
                        related = str(locator) if access == "connector" else address(canonical, locator)
                        method = index_access(related) if urlparse(related).scheme else access
                        pending.append((index_address(related, method), method))
                except ValueError as error:
                    errors.append({"index": canonical, "id": item["id"], "type": type(error).__name__, "message": str(error)})
        remaining = [{"index": i, "access": a} for i, a in sorted(set(pending) - visited)]
        return {"indexes": results, "errors": errors, "pending": remaining, "complete": not errors and not remaining}

    def discover(self, indexes, query="", *, max_indexes=128, limit=20):
        if limit < 1:
            raise ValueError("limit must be positive")
        graph = self.walk(indexes, max_indexes=max_indexes)
        terms = list(dict.fromkeys(re.findall(r"[^\W_]+", unicodedata.normalize("NFC", query).casefold())))
        matches = []
        for index in graph["indexes"]:
            for item in index["entries"]:
                if item["kind"] != "source":
                    continue
                text = unicodedata.normalize("NFC", " ".join([item["id"], item["label"], item.get("description", ""), *item["topics"]])).casefold()
                matched = [term for term in terms if term in text]
                if terms and not matched:
                    continue
                try:
                    result = self.bind(index["index"], item, index["digest"], index["access"])
                    matches.append({**result, "relevance": {"matched_terms": matched}})
                except ValueError as error:
                    graph["errors"].append({"index": index["index"], "id": item["id"], "type": type(error).__name__, "message": str(error)})
        matches.sort(key=lambda r: (-len(r["relevance"]["matched_terms"]), r["address"], r["reference"]["id"]))
        return {"query": query, "references": matches[:limit], "errors": graph["errors"],
                "pending": graph["pending"], "complete": not graph["errors"] and not graph["pending"], "more_matches": len(matches) > limit}
