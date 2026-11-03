#!/usr/bin/env python3
"""프로젝트 로컬 기록을 기존 파일을 덮어쓰지 않고 준비한다."""

import argparse
from pathlib import Path


def initialize(project: Path) -> Path:
    project = project.resolve(strict=True)
    if not project.is_dir():
        raise ValueError("Project must be a directory")
    ignore = project / ".gitignore"
    local = project / ".local"
    target = local / "product-builder"
    record = target / "work-record.md"
    for path in (ignore, local, target, record):
        if path.is_symlink():
            raise ValueError(f"Refusing symlink: {path.name}")
    current = ignore.read_text() if ignore.exists() else ""
    # 마지막 규칙으로 추가하여 기존 negation 뒤에서도 전체 로컬 디렉터리를 제외한다.
    lines = current.splitlines()
    if not lines or lines[-1] != "/.local/":
        with ignore.open("a") as stream:
            stream.write(("\n" if current and not current.endswith("\n") else "") + "/.local/\n")
    target.mkdir(parents=True, exist_ok=True)
    template = Path(__file__).resolve().parents[1] / "assets" / "work-record.md"
    if not record.exists():
        with record.open("x") as stream:
            stream.write(template.read_text())
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    print(initialize(args.project))
    print("Existing tracked files remain tracked; inspect git status before publishing.")
