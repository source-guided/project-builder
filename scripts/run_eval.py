#!/usr/bin/env python3
"""GPT-6.1 Sol로 소비자 입력을 실행하고 증거를 로컬에 보관한다."""

import argparse
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

from prepare_eval import ROOT, prepare


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run = ROOT / ".local/evals" / stamp
    prompt = prepare(args.input, run / "project")
    digest = hashlib.sha256()
    for path in sorted((ROOT / "plugins/product-builder").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(path.relative_to(ROOT).as_posix().encode())
            digest.update(path.read_bytes())
    command = ["codex", "exec", "--model", "gpt-6.1-sol", "-c", 'model_reasoning_effort="high"', "--ignore-user-config", "--ephemeral", "--skip-git-repo-check", "--sandbox", "workspace-write", "--json", "--cd", str(run / "project"), "--output-last-message", str(run / "answer.md"), "-"]
    metadata = {"model_requested": "gpt-6.1-sol", "reasoning_effort_requested": "high", "input_directory": str(args.input.resolve()), "package_sha256": digest.hexdigest(), "status": "started", "started_utc": stamp}
    receipt = run / "receipt.json"
    receipt.write_text(json.dumps(metadata, indent=2))
    try:
        with prompt.open() as source, (run / "events.jsonl").open("w") as output, (run / "stderr.log").open("w") as error:
            result = subprocess.run(command, stdin=source, stdout=output, stderr=error, timeout=args.timeout)
        metadata.update(status="executed" if result.returncode == 0 else "execution_failed", exit_code=result.returncode)
    except subprocess.TimeoutExpired:
        metadata.update(status="timed_out")
    except OSError as error:
        metadata.update(status="execution_unavailable", error=str(error))
    receipt.write_text(json.dumps(metadata, indent=2))
    print(receipt)
    print("Execution is not a passing grade. Review artifacts and criteria separately.")
    raise SystemExit(0 if metadata["status"] == "executed" else 1)
