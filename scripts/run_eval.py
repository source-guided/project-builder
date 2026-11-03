#!/usr/bin/env python3
"""사용자의 모델 설정으로 소비자 입력을 실행하고 증거를 로컬에 보관한다."""

import argparse
import datetime
import hashlib
import json
import subprocess
from evaluation_process import run_process
from evaluation_dispatch import build_command, selection_record
from pathlib import Path

from prepare_eval import ROOT, prepare
from review_eval import execute_review, freeze_completion


def execute(source: Path, run: Path, *, context: Path = None, timeout: int = 600,
            review: bool = False, review_timeout: int = 600, model=None, reasoning_effort=None) -> dict:
    selection = selection_record(model=model, reasoning_effort=reasoning_effort)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    prompt = prepare(source, run / "project", context=context)
    handoff = json.loads((run / "project-handoff.json").read_text())
    digest = hashlib.sha256(json.dumps(handoff["package_files"], sort_keys=True).encode()).hexdigest()
    command = build_command(workspace=run / "project", answer=run / "answer.md", model=model, reasoning_effort=reasoning_effort)
    metadata = {**selection, "input_directory": str(source.resolve()), "package_manifest_sha256": digest, "status": "started", "started_utc": stamp, "review_status": "not_run"}
    receipt = run / "receipt.json"
    receipt.write_text(json.dumps(metadata, indent=2))
    try:
        with prompt.open() as input_stream, (run / "events.jsonl").open("w") as output, (run / "stderr.log").open("w") as error:
            result = run_process(command, stdin=input_stream, stdout=output, stderr=error, timeout=timeout)
        metadata.update(status="executed" if result.returncode == 0 else "execution_failed", exit_code=result.returncode)
    except subprocess.TimeoutExpired:
        metadata.update(status="timed_out")
    except OSError as error:
        metadata.update(status="execution_unavailable", error=str(error))
    if metadata["status"] == "executed":
        try:
            frozen, completion = freeze_completion(run / "project", origin="runner_completion")
            metadata["completion"] = {"path": str(frozen), "origin": completion["origin"], "captured_at": completion["captured_at"]}
        except (OSError, ValueError) as error:
            metadata.update(status="snapshot_failed", snapshot_error=str(error))
    if review and metadata["status"] == "executed":
        try:
            metadata["review"] = execute_review(run / "project", timeout=review_timeout, model=model, reasoning_effort=reasoning_effort)
            metadata["review_status"] = metadata["review"].get("report_status", metadata["review"]["status"])
        except (OSError, ValueError) as error:
            metadata.update(review_status="preparation_failed", review_error=str(error))
    receipt.write_text(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="Optional override of your CLI model setting")
    parser.add_argument("--reasoning-effort", help="Optional override of your CLI reasoning effort")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--context", type=Path, help="Current user clarifications and preferences; no prior answers")
    parser.add_argument("--review", action="store_true", help="Run a separate reviewer after implementation; does not assign a product pass")
    parser.add_argument("--review-timeout", type=int, default=600)
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run = ROOT / ".local/evals" / stamp
    metadata = execute(args.input, run, context=args.context, timeout=args.timeout,
                       review=args.review, review_timeout=args.review_timeout, model=args.model, reasoning_effort=args.reasoning_effort)
    print(run / "receipt.json")
    print("Execution is not a passing grade. Review artifacts and criteria separately.")
    complete = metadata["status"] == "executed" and (not args.review or metadata["review_status"] == "contract_verified")
    raise SystemExit(0 if complete else 1)
