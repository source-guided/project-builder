#!/usr/bin/env python3
"""Initialize only discovery references for existing project material."""
import argparse
import json
import os
from pathlib import Path


def initialize(project: Path) -> Path:
    project = project.resolve(strict=True)
    if not project.is_dir():
        raise ValueError("Project must be a directory")
    ignore = project / ".gitignore"
    local = project / ".local"
    target = local / "project-builder"
    registry = target / "references"
    index = registry / "index.json"
    for path in (ignore, local, target, registry, index):
        if path.is_symlink():
            raise ValueError(f"Refusing symlink: {path.name}")
    current = ignore.read_text() if ignore.exists() else ""
    if not current.splitlines() or current.splitlines()[-1] != "/.local/":
        with ignore.open("a") as stream:
            stream.write(("\n" if current and not current.endswith("\n") else "") + "/.local/\n")
    registry.mkdir(parents=True, exist_ok=True)
    if not index.exists():
        candidates = [project / name for name in ("README.md", "AGENTS.md", "CODEOWNERS", "package.json", "pyproject.toml")]
        entries = [{"id": p.name, "label": p.name, "kind": "source", "access": "file", "locator": os.path.relpath(p, registry), "topics": ["project", p.stem]} for p in candidates if p.is_file() and not p.is_symlink()]
        with index.open("x") as stream:
            json.dump({"format": 1, "entries": entries}, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    print(initialize(parser.parse_args().project))
