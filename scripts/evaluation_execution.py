#!/usr/bin/env python3
"""첫 산출물과 실행 명령·실행 리비전·증거 파일을 연결한다."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

from evaluation_inputs import capture_inputs, verify_inputs
from evaluation_process import run_process

from evaluation_artifacts import executable_manifest, file_manifest, snapshot, workspace_lock


def baseline_for(review):
    review = Path(review).resolve()
    baseline = json.loads(review.with_name(f"{review.name}-baseline.json").read_text())
    if not isinstance(baseline,dict) or baseline.get("format") != 2:
        raise ValueError("Review format 2 is required; inspect historical runs with their originating harness")
    if baseline.get("artifact_manifest_format") != 2:
        raise ValueError("Historical snapshot lacks executable-mode provenance; use its originating harness")
    if not baseline.get("review_id"):
        raise ValueError("Historical snapshot lacks review identity; use its originating harness")
    required={"subject_files","subject_modes","input_files","input_modes","package_path","package_files","package_modes", "harness_path","harness_files","harness_modes","dispatch_harness_path","dispatch_harness_files","dispatch_harness_modes","contract_sha256"}
    if not required <= set(baseline):
        raise ValueError("Historical snapshot uses a different provenance contract; use its originating harness")
    return baseline


def changed_files(expected, observed):
    return {"modified": sorted(name for name in expected.keys() & observed.keys() if expected[name] != observed[name]),
            "removed": sorted(expected.keys() - observed.keys()), "added": sorted(observed.keys() - expected.keys())}


def verify_baseline(review, baseline=None):
    review = Path(review).resolve(); baseline = baseline or baseline_for(review)
    for folder, field in ((review / "subject", "subject_files"), (review / "input", "input_files"),
                          (Path(baseline["package_path"]), "package_files"), (Path(baseline["harness_path"]), "harness_files"),
                          (Path(baseline["dispatch_harness_path"]), "dispatch_harness_files")):
        if file_manifest(folder) != baseline[field] or executable_manifest(folder) != baseline[field.replace("_files", "_modes")]:
            raise ValueError(f"Preserved review material changed: {field}")
    contract = review / "contract.json"
    if hashlib.sha256(contract.read_bytes()).hexdigest() != baseline["contract_sha256"]:
        raise ValueError("Review report contract changed after preparation")
    return baseline


def prepare_runtime(review):
    review = Path(review).resolve()
    baseline = verify_baseline(review)
    runtime = review / "runtime"
    if not runtime.exists():
        snapshot(review / "subject", runtime)
    current = file_manifest(runtime)
    changes = changed_files(baseline["subject_files"], current)
    if any(changes.values()) or executable_manifest(runtime) != baseline["subject_modes"]:
        raise ValueError(f"Runtime no longer matches the first artifact: {changes}")
    return runtime


def execute(review, command, *, timeout=60, evidence_paths=(), test_inputs=()):
    review = Path(review).resolve()
    verify_baseline(review)
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    with workspace_lock(review, timeout=timeout):
        return _capture(review,command,timeout=timeout,evidence_paths=evidence_paths,test_inputs=test_inputs)


def _capture(review, command, *, timeout, evidence_paths, test_inputs):
    review = Path(review).resolve()
    if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
        raise ValueError("Execution needs a nonempty argument vector")
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    baseline = verify_baseline(review)
    runtime = prepare_runtime(review)
    identifier = uuid.uuid4().hex
    output_dir = review / "evidence" / identifier
    output_dir.mkdir(parents=True)
    inputs = capture_inputs(review, runtime, command, test_inputs)
    extra_evidence = []
    for name in evidence_paths:
        path = (review / name).resolve()
        if not path.is_relative_to(review / "evidence"):
            raise ValueError("Captured evidence must stay in the review evidence directory")
        if path.exists():
            raise ValueError("Capture requires a new evidence path for this execution; preserve earlier evidence separately")
        extra_evidence.append(path)
    before = file_manifest(runtime)
    before_modes = executable_manifest(runtime)
    record = {"format": 1, "id": identifier, "review_id": baseline["review_id"], "command": command, "cwd": str(runtime),
              "subject_manifest_sha256": hashlib.sha256(json.dumps(baseline["subject_files"], sort_keys=True).encode()).hexdigest(),
              "started_at": time.time(), "test_inputs": inputs, "before": before, "before_modes": before_modes}
    stdout_path, stderr_path = output_dir / "stdout.txt", output_dir / "stderr.txt"
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        try:
            result = run_process(command, cwd=runtime, stdout=stdout, stderr=stderr, timeout=timeout)
            record.update(status="completed", exit_code=result.returncode)
        except subprocess.TimeoutExpired as error:
            record.update(status="timed_out", exit_code=error.returncode)
        except OSError as error:
            record.update(status="unavailable", error=str(error), exit_code=None)
    after = file_manifest(runtime)
    after_modes = executable_manifest(runtime)
    changes = changed_files(baseline["subject_files"], after)
    record.update(finished_at=time.time(), after=after, after_modes=after_modes, source_changes=changes,
                  source_revision_verified=not any(changes.values()) and after_modes == baseline["subject_modes"],
                  runtime_additions=changes["added"])
    outputs = [stdout_path, stderr_path, *extra_evidence]
    record["evidence"] = {p.relative_to(review).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs if p.is_file()}
    record["missing_evidence"] = [str(p.relative_to(review)) for p in extra_evidence if not p.is_file()]
    owner_dir = review / ".harness" / "executions"
    owner_dir.mkdir(parents=True, exist_ok=True)
    (owner_dir / f"{identifier}.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def verify_execution(review, identifier, evidence):
    review = Path(review).resolve()
    if not isinstance(identifier, str) or len(identifier) != 32 or any(c not in "0123456789abcdef" for c in identifier):
        raise ValueError("Invalid execution identifier")
    baseline = verify_baseline(review)
    path = review / ".harness" / "executions" / f"{identifier}.json"
    record = json.loads(path.read_text())
    expected = hashlib.sha256(json.dumps(baseline["subject_files"], sort_keys=True).encode()).hexdigest()
    if record.get("id") != identifier or record.get("review_id") != baseline["review_id"] or record.get("subject_manifest_sha256") != expected or not record.get("source_revision_verified"):
        raise ValueError("Execution is not bound to the preserved first artifact")
    for phase in ("before", "after"):
        changes = changed_files(baseline["subject_files"], record.get(phase, {}))
        if any(changes.values()) or record.get(phase + "_modes") != baseline["subject_modes"]:
            raise ValueError("Executed source differs from the first artifact")
    verify_inputs(review, record.get("test_inputs", {}))
    if record.get("status") not in {"completed", "timed_out"}:
        raise ValueError("The recorded command was not executed")
    for item in evidence:
        name = item["path"]
        if name not in record.get("evidence", {}):
            raise ValueError("Runtime evidence was not captured by the referenced execution")
        source = (review / name).resolve()
        if not source.is_relative_to(review / "evidence") or hashlib.sha256(source.read_bytes()).hexdigest() != record["evidence"][name]:
            raise ValueError("Runtime evidence changed after execution")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--test-input", action="append", default=[])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.prepare_only:
        print(prepare_runtime(args.review))
    else:
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        result = execute(args.review, command, timeout=args.timeout, evidence_paths=args.evidence, test_inputs=args.test_input)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["status"] == "completed" and result["source_revision_verified"] else 1)
