#!/usr/bin/env python3
"""소비자가 지정한 평가 입력만 별도 작업 공간으로 복사한다."""

import argparse
import json
import shutil
from pathlib import Path

from evaluation_artifacts import EXCLUDED_DIRECTORIES, executable_manifest, file_manifest, snapshot

ROOT = Path(__file__).resolve().parents[1]
HARNESS_FILES = (
    "evaluation_sources.py", "evaluation_dispatch.py", "evaluation_process.py", "evaluation_inputs.py",
    "evaluation_artifacts.py", "evaluation_execution.py", "evaluation_report.py", "evaluation_contract.json",
    "prepare_eval.py", "review_eval.py", "run_eval.py",
)


def prepare(source: Path, destination: Path, *, context: Path = None) -> Path:
    source = source.resolve()
    if not source.is_dir() or not (source / "README.md").is_file():
        raise ValueError("Input must be a consumer-owned directory with README.md")
    if any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("Evaluation inputs must not contain symlinks")
    if context is not None:
        context = context.resolve()
        if not context.is_dir() or not (context / "README.md").is_file():
            raise ValueError("User context must be a directory with README.md describing its source and scope")
        if any(path.is_symlink() for path in context.rglob("*")):
            raise ValueError("User context must not contain symlinks")
        if (source / "user-context").exists():
            raise ValueError("Input already contains user-context; reconcile it before preparation")
    destination = destination.resolve()
    if destination.is_relative_to(source) or (context and destination.is_relative_to(context)):
        raise ValueError("Output must be outside the input directory")
    if destination.exists():
        raise ValueError("Use a new empty evaluation path; existing work is preserved")
    prompt = destination.parent / f"{destination.name}-prompt.txt"
    if prompt.exists():
        raise ValueError("Prompt output already exists")
    package = destination.parent / f"{destination.name}-plugin"
    if package.exists():
        raise ValueError("Package output already exists")
    raw_input = destination.parent / f"{destination.name}-input"
    handoff = destination.parent / f"{destination.name}-handoff.json"
    harness = destination.parent / f"{destination.name}-harness"
    reserved = [destination.with_name(f"{destination.name}-{suffix}") for suffix in ("completed", "completion.json", "review", "review-baseline.json")]
    if raw_input.exists() or handoff.exists() or harness.exists() or any(path.exists() for path in reserved):
        raise ValueError("Preserved input or handoff output already exists")
    shutil.copytree(source, destination)
    if context is not None:
        shutil.copytree(context, destination / "user-context")
    input_files = snapshot(destination, raw_input)
    shutil.copytree(ROOT / "plugins/project-builder", package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    harness.mkdir()
    for name in HARNESS_FILES:
        shutil.copy2(Path(__file__).parent / name, harness / name)
    handoff.write_text(json.dumps({
        "format": 2,
        "artifact_manifest_format": 2,
        "input_source": str(source), "user_context_source": str(context) if context else None,
        "preserved_input": str(raw_input), "input_files": input_files,
        "package_files": file_manifest(package), "harness_files": file_manifest(harness),
        "input_modes": executable_manifest(raw_input), "package_modes": executable_manifest(package),
        "harness_modes": executable_manifest(harness),
        "excluded_directories": sorted(EXCLUDED_DIRECTORIES),
        "boundary": "User requirements belong in input/context. Prior answers and evaluator hints do not.",
    }, indent=2) + "\n")
    skill = package / "skills/start/SKILL.md"
    prompt.write_text(
        f"First read the Product Builder start skill at {skill} and complete its reference bootstrap. "
        "Do this before opening task files, including README.md or user-context/. Applicable host instructions "
        "may be read first. Then complete the user request through the skill's workflow.\n"
        f"Work only in {destination}; treat the skill package as read-only.\n"
        + ("Also reconcile user-context/README.md and its supplied material with the original brief. "
           "Preserve each clarification's source and scope; do not silently drop user preferences.\n" if context else "")
        +
        "Use the caller-selected model configuration; do not change it or spawn agents. Do not access external accounts.\n"
        "Read task material only from this project and the supplied package; do not inspect evaluator criteria or other projects. "
        "Public sources discovered through the reference workflow may be inspected; source access does not authorize external writes.\n"
        "Follow the user's requested scope. Execute feasible checks and report actual outcomes and limitations.\n"
    )
    return prompt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Consumer-owned raw input directory; exclude answers and evaluator criteria")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--context", type=Path, help="User-authored clarifications/preferences with source and scope; no prior solutions")
    args = parser.parse_args()
    print(prepare(args.input, args.output, context=args.context))
