#!/usr/bin/env python3
"""평가용 원본 입력만 별도 작업 공간으로 복사한다."""

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ("reservation", "reconciliation", "review-screen", "resume", "order-contact")


def prepare(case: str, destination: Path) -> Path:
    if case not in CASES:
        raise ValueError("Unknown case")
    destination = destination.resolve()
    if destination.exists():
        raise ValueError("Use a new empty evaluation path; existing work is preserved")
    prompt = destination.parent / f"{destination.name}-prompt.txt"
    if prompt.exists():
        raise ValueError("Prompt output already exists")
    package = destination.parent / f"{destination.name}-plugin"
    if package.exists():
        raise ValueError("Package output already exists")
    shutil.copytree(ROOT / "evals/cases" / case, destination)
    shutil.copytree(ROOT / "plugins/product-builder", package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    skill = package / "skills/start/SKILL.md"
    prompt.write_text(
        f"Use the Product Builder start skill at {skill} to complete the user request in README.md.\n"
        f"Work only in {destination}; treat the skill package as read-only.\n"
        "Use GPT-6.1 Sol with reasoning effort high only; do not spawn agents. Do not access external accounts.\n"
        "Read only this project and the supplied package; do not inspect evaluator criteria or other projects.\n"
        "Follow the user's requested scope. Execute feasible checks and report actual outcomes and limitations.\n"
    )
    return prompt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.case, args.output))
