#!/usr/bin/env python3
"""독립 검토의 작업 공간 준비와 모델 실행. 판단 기준은 스킬 원천이 소유한다."""

import argparse
import hashlib
import json
import subprocess
from evaluation_process import run_process
from evaluation_dispatch import build_command, selection_record
import time
import uuid
import shutil
from pathlib import Path

from evaluation_artifacts import EXCLUDED_DIRECTORIES, executable_manifest, file_manifest, snapshot
import evaluation_report
from prepare_eval import HARNESS_FILES


def freeze_completion(project: Path, *, origin="manual_capture"):
    project = project.resolve()
    if origin not in {"manual_capture", "runner_completion"}:
        raise ValueError("Unknown completion capture origin")
    frozen = project.with_name(f"{project.name}-completed")
    record_path = project.with_name(f"{project.name}-completion.json")
    if frozen.exists() or record_path.exists():
        if not frozen.is_dir() or not record_path.is_file():
            raise ValueError("Incomplete completion snapshot; preserve it and use a new run")
        record = json.loads(record_path.read_text())
        if file_manifest(frozen) != record["files"] or executable_manifest(frozen) != record["modes"]:
            raise ValueError("Completion snapshot changed after capture")
        return frozen, record
    files = snapshot(project, frozen)
    record = {"origin": origin, "captured_at": time.time(), "files": files, "modes": executable_manifest(frozen),
              "meaning": "Frozen when the model process returned" if origin == "runner_completion" else "Current artifact at explicit manual capture; not proof of an earlier model completion"}
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    return frozen, record


def prepare_review(project: Path, *, harness_source=None) -> Path:
    project = project.resolve()
    handoff = json.loads((project.parent / f"{project.name}-handoff.json").read_text())
    if handoff.get("format") != 2:
        raise ValueError("Prepare a format 2 run; historical runs retain their originating harness")
    if handoff.get("artifact_manifest_format") != 2:
        raise ValueError("This historical snapshot lacks executable-mode provenance; use its originating harness or prepare a new run")
    original = Path(handoff["preserved_input"])
    package = project.parent / f"{project.name}-plugin"
    dispatch_harness = project.parent / f"{project.name}-harness"
    harness = dispatch_harness
    for path, key in ((original, "input_files"), (package, "package_files"), (dispatch_harness, "harness_files")):
        if file_manifest(path) != handoff[key] or executable_manifest(path) != handoff.get(key.replace("_files", "_modes")):
            raise ValueError(f"Preserved dispatch material changed: {key}")
    review = project.parent / f"{project.name}-review"
    baseline_path = review.with_name(f"{review.name}-baseline.json")
    if review.exists() or baseline_path.exists():
        raise ValueError("Use a new review path; previous findings are preserved")
    if harness_source is not None:
        harness_source = Path(harness_source).resolve()
        harness = project.with_name(f"{project.name}-review-harness")
        if harness.exists() or not all((harness_source/name).is_file() and not (harness_source/name).is_symlink() for name in HARNESS_FILES):
            raise ValueError("Review harness must be an explicitly supplied complete new snapshot")
        harness.mkdir()
        for name in HARNESS_FILES:
            shutil.copy2(harness_source/name,harness/name)
    frozen, completion = freeze_completion(project)
    review.mkdir()
    before = snapshot(frozen, review / "subject")
    snapshot(original, review / "input")
    contract = json.loads((harness / "evaluation_contract.json").read_text())
    contract["execution"] = {"tool": str(harness / "evaluation_execution.py"), "review": str(review),
                             "outputs": "evidence/", "records_owner": str(review / ".harness" / "executions")}
    (review / "contract.json").write_text(json.dumps(contract, indent=2) + "\n")
    baseline_path.write_text(json.dumps({
        "format": 2, "artifact_manifest_format": 2, "review_id": uuid.uuid4().hex,
        "subject_files": before, "input_files": handoff["input_files"],
        "subject_modes": executable_manifest(review / "subject"), "input_modes": handoff["input_modes"],
        "package_path": str(package), "package_files": handoff["package_files"],
        "harness_path": str(harness), "harness_files": file_manifest(harness),
        "package_modes": handoff["package_modes"], "harness_modes": executable_manifest(harness),
        "dispatch_harness_path": str(dispatch_harness), "dispatch_harness_files": handoff["harness_files"],
        "dispatch_harness_modes": handoff["harness_modes"],
        "completion": completion,
        "contract_sha256": hashlib.sha256((review / "contract.json").read_bytes()).hexdigest(),
        "excluded_directories": sorted(EXCLUDED_DIRECTORIES),
    }, indent=2) + "\n")
    (review / "evidence").mkdir()
    (review / "prompt.txt").write_text(
        f"First read the Product Builder verification skill at {package / 'skills/start/SKILL.md'} "
        "and complete its reference bootstrap before opening task or artifact files. Applicable host instructions may be read first.\n"
        "Use source-specific review guidance only when it is already connected for this task. Do not install or automatically select default sources. Derive the expected behavior from preserved user input and distinguish confirmed requirements from assumptions.\n"
        f"Preserved user input is at {review / 'input'}; the first completed artifact is at {review / 'subject'}.\n"
        f"The report and execution contract is at {review / 'contract.json'}. Discover it through a local reference. "
        "Write report.json using that contract and the actual evidence.\n"
        f"Write only beneath {review}. Keep input/, subject/, contract.json, and the supplied package/harness unchanged. "
        "The declared execution tool owns .harness/executions/ records inside the writable workspace; do not edit them manually. "
        "This ownership is a workflow convention, not a separate OS identity or tamper-proof attestation.\n"
        "Do not access other projects, previous reviews, external accounts or local credentials; do not spawn agents. "
        "Public sources discovered through the supplied reference workflow may be read. Do not publish externally.\n"
    )
    return review


def execute_review(project: Path, *, timeout: int = 600, model=None, reasoning_effort=None) -> dict:
    selection = selection_record(model=model, reasoning_effort=reasoning_effort)
    review = prepare_review(project)
    receipt = {**selection, "status": "started"}
    receipt_path = review / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    command = build_command(workspace=review, answer=review / "answer.md", model=model, reasoning_effort=reasoning_effort)
    try:
        with (review / "prompt.txt").open() as prompt, (review / "events.jsonl").open("w") as output, (review / "stderr.log").open("w") as error:
            result = run_process(command, stdin=prompt, stdout=output, stderr=error, timeout=timeout)
        receipt.update(status="executed" if result.returncode == 0 else "execution_failed", exit_code=result.returncode)
        if result.returncode == 0:
            try:
                receipt.update(evaluation_report.check_report(review))
            except (OSError, ValueError, TypeError) as error:
                receipt.update(report_status="invalid_or_missing", report_error=str(error))
    except subprocess.TimeoutExpired:
        receipt["status"] = "timed_out"
    except OSError as error:
        receipt.update(status="execution_unavailable", error=str(error))
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="Optional override of your CLI model setting")
    parser.add_argument("--reasoning-effort", help="Optional override of your CLI reasoning effort")
    parser.add_argument("--project", type=Path)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--harness", type=Path, help="Explicitly freeze this review harness separately from the original dispatch harness")
    parser.add_argument("--check-only", type=Path)
    args = parser.parse_args()
    if args.check_only:
        print(json.dumps(evaluation_report.check_report(args.check_only), indent=2))
    elif args.project is None:
        parser.error("--project is required unless using --check-only")
    elif args.prepare_only:
        print(prepare_review(args.project,harness_source=args.harness))
    else:
        if args.harness is not None:
            parser.error("--harness is used with --prepare-only; the normal runner preserves its dispatch harness")
        result = execute_review(args.project, timeout=args.timeout, model=args.model, reasoning_effort=args.reasoning_effort)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result.get("report_status") == "contract_verified" else 1)
