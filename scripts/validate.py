#!/usr/bin/env python3
"""플러그인 계약, 내부 참조와 공개 파일 경계를 검사한다."""

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "product-builder"
PRIVATE_PARTS = {".local", ".git", "node_modules"}


def plugin_files(plugin: Path):
    allowlist_path = plugin / "package-files.json"
    if allowlist_path.is_symlink():
        raise ValueError("Package allowlist must not be a symlink")
    allowed = json.loads(allowlist_path.read_text())
    if not isinstance(allowed, list) or not all(isinstance(name, str) for name in allowed):
        raise ValueError("Package allowlist must be an array of relative file paths")
    if len(allowed) != len(set(allowed)):
        raise ValueError("Duplicate package allowlist entry")
    for name in allowed:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != name:
            raise ValueError("Invalid package allowlist path")
    files = []
    for path in sorted(plugin.rglob("*")):
        relative = path.relative_to(plugin)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError(f"Symlinks are not distributable: {relative}")
        if any(part in PRIVATE_PARTS for part in relative.parts):
            raise ValueError(f"Private/generated content in plugin: {relative}")
        if path.name.startswith(".env") and path.name != ".env.example":
            raise ValueError(f"Environment file in plugin: {relative}")
        if path.is_file():
            if relative.as_posix() not in allowed:
                raise ValueError(f"Unexpected file not in package allowlist: {relative}")
            files.append(path)
    if set(allowed) != {p.relative_to(plugin).as_posix() for p in files}:
        raise ValueError("Missing allowlisted package file")
    return files


def validate(root: Path = ROOT):
    plugin = root / "plugins" / "product-builder"
    manifest = json.loads((plugin / "plugin.json").read_text())
    assert manifest["name"] == "product-builder", "Unexpected plugin identity"
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"]), "Invalid version"
    assert manifest["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    catalog = json.loads((root / ".agents/plugins/marketplace.json").read_text())
    entry, = catalog["plugins"]
    assert entry["name"] == manifest["name"]
    assert (root / entry["source"]["path"]).resolve() == plugin.resolve()
    assert entry["policy"]["installation"] == "AVAILABLE"
    files = plugin_files(plugin)
    skills = sorted((plugin / "skills").glob("*/SKILL.md"))
    assert {p.parent.name for p in skills} == {"start", "brief", "product-ux", "implementation", "verification"}
    for skill in skills:
        text = skill.read_text()
        frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
        assert frontmatter, f"Missing frontmatter: {skill}"
        fields = dict(line.split(": ", 1) for line in frontmatter[1].splitlines() if ": " in line)
        assert fields.get("name") == skill.parent.name
        assert fields.get("description"), f"Missing description: {skill}"
        assert len(text) < 16000, f"Move optional details into references: {skill}"
    for path in files:
        if path.suffix != ".md":
            continue
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" in link or link.startswith("#"):
                continue
            target = (path.parent / link.split("#")[0]).resolve()
            assert target.is_relative_to(plugin.resolve()), f"Link leaves package: {path.name}"
            assert target.exists(), f"Broken link in {path.name}: {link}"
    if (root / ".git").exists():
        tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
        assert not any(name.startswith(".local/") for name in tracked), "Local context is tracked"
        ignored = subprocess.run(["git", "check-ignore", "--no-index", "-q", ".local/context/probe"], cwd=root)
        assert ignored.returncode == 0, "Local context must be ignored"
        denylist = root / ".local/publication-denylist.json"
        if denylist.exists():
            terms = json.loads(denylist.read_text())
            for name in filter(None, tracked):
                path = root / name
                if path.is_file():
                    data = path.read_bytes()
                    assert not any(term.encode() in data for term in terms), f"Private source marker in tracked file: {name}"
    return len(skills), len(files)


if __name__ == "__main__":
    skills, files = validate()
    print(f"PASS: {skills} skills, {files} distributable files; references and publication boundary checked")
