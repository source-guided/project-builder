#!/usr/bin/env python3
"""프로젝트 로컬 기록을 기존 파일을 덮어쓰지 않고 준비한다."""

import argparse
import json
import os
from pathlib import Path


def initialize_references(project, target):
    registry = target / "references"
    def index(name, entries):
        path = registry / name
        for candidate in (path, *path.parents):
            if candidate.is_symlink():
                raise ValueError("Reference indexes must not pass through symlinks")
            if candidate == target:
                break
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(json.dumps({"format": 1, "entries": entries}, ensure_ascii=False, indent=2) + "\n")
    def ref(identifier, label, locator, topics):
        return {"id": identifier, "label": label, "kind": "reference", "access": "file", "locator": locator, "topics": topics}
    def sources(name, paths, topics):
        return [{"id": path.name, "label": path.name, "kind": "source", "access": "file", "locator": os.path.relpath(path, (registry / name).parent), "topics": topics} for path in paths if path.is_file() and not path.is_symlink()]
    index("index.json", [ref("project", "현재 프로젝트 참조", "project/index.json", ["project", "프로젝트"]), ref("version", "프로젝트 버전·소유 정보 원천", "version/index.json", ["version", "ownership"])])
    index("version/index.json", sources("version/index.json", [project / "package.json", project / "CODEOWNERS"], ["version", "ownership"]))
    index("project/index.json", [ref("brief", "요구사항·제공 데이터", "brief/index.json", ["brief", "data"]), ref("frontend", "프로젝트 프론트", "frontend/index.json", ["frontend", "프론트"])])
    candidates = [p for p in sorted(project.iterdir()) if p.suffix in {".md", ".json", ".yaml", ".yml", ".csv"} and p.name not in {"package-lock.json", "package.json", "AGENTS.md"}]
    index("project/brief/index.json", sources("project/brief/index.json", candidates, ["brief", "input"]))
    index("project/frontend/index.json", [ref("conventions", "프로젝트 컨벤션", "conventions/index.json", ["convention"]), ref("design", "프로젝트 디자인", "design/index.json", ["design", "figma"]), ref("api", "프로젝트 API", "api/index.json", ["api", "contract"]), ref("implementation", "프로젝트 구현", "implementation/index.json", ["code", "implementation"])])
    index("project/frontend/conventions/index.json", sources("project/frontend/conventions/index.json", [project / "AGENTS.md", project / "docs/README.md"], ["conventions"]))
    index("project/frontend/design/index.json", sources("project/frontend/design/index.json", [project / "design.md", project / "figma.md"], ["design"]))
    index("project/frontend/api/index.json", sources("project/frontend/api/index.json", [project / "openapi.json", project / "swagger.json"], ["api"]))
    index("project/frontend/implementation/index.json", [])
    return registry


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
    initialize_references(project, target)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    print(initialize(args.project))
    print("Existing tracked files remain tracked; inspect git status before publishing.")
