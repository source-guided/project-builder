#!/usr/bin/env python3
"""소비자가 지정한 평가 입력만 별도 작업 공간으로 복사한다."""

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(source: Path, destination: Path) -> Path:
    source = source.resolve()
    if not source.is_dir() or not (source / "README.md").is_file():
        raise ValueError("Input must be a consumer-owned directory with README.md")
    if any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("Evaluation inputs must not contain symlinks")
    destination = destination.resolve()
    if destination.is_relative_to(source):
        raise ValueError("Output must be outside the input directory")
    if destination.exists():
        raise ValueError("Use a new empty evaluation path; existing work is preserved")
    prompt = destination.parent / f"{destination.name}-prompt.txt"
    if prompt.exists():
        raise ValueError("Prompt output already exists")
    package = destination.parent / f"{destination.name}-plugin"
    if package.exists():
        raise ValueError("Package output already exists")
    shutil.copytree(source, destination)
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
    parser.add_argument("--input", type=Path, required=True, help="Consumer-owned raw input directory; exclude answers and evaluator criteria")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.input, args.output))
