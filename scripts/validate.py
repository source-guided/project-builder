#!/usr/bin/env python3
"""플러그인 계약, 내부 참조와 공개 파일 경계를 검사한다."""

import json
import re
import subprocess
import importlib.util
import sys
from pathlib import Path
from publication_boundary import check_inventory

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "project-builder"
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
    plugin = root / "plugins" / "project-builder"
    manifest = json.loads((plugin / "plugin.json").read_text())
    assert manifest["name"] == "project-builder", "Unexpected plugin identity"
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"]), "Invalid version"
    assert manifest["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    catalog = json.loads((root / ".agents/plugins/marketplace.json").read_text())
    entry, = catalog["plugins"]
    assert entry["name"] == manifest["name"]
    assert (root / entry["source"]["path"]).resolve() == plugin.resolve()
    assert entry["policy"]["installation"] == "AVAILABLE"
    files = plugin_files(plugin)
    skills = sorted((plugin / "skills").glob("*/SKILL.md"))
    assert {p.relative_to(plugin).as_posix() for p in plugin.rglob("SKILL.md")} == {"skills/start/SKILL.md"}, "Only the reference entry skill may be exposed"
    assert {p.parent.name for p in skills} == {"start"}
    core_sources = {"sources/governance/reference-routing.md", "sources/reference-entry.md", "sources/source-contract.md"}
    assert {p.relative_to(plugin).as_posix() for p in (plugin / "sources").rglob("*") if p.is_file()} == core_sources, "Domain source bodies cannot ship with the reference entrypoint"
    assert not (plugin / "capabilities").exists(), "Source capabilities cannot be bundled"
    defaults = json.loads((plugin / "catalog/defaults.json").read_text())
    assert all(e["kind"] == "reference" and e["access"] in {"web","connector"} for e in defaults["entries"]), "Default sources must stay external metadata"
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
            is_source = "sources" in path.relative_to(plugin).parts
            if link.startswith("#"):
                continue
            if "://" in link:
                assert not is_source, f"Source-to-source URL must return through a reference: {path.name}"
                continue
            target = (path.parent / link.split("#")[0]).resolve()
            assert target.is_relative_to(plugin.resolve()), f"Link leaves package: {path.name}"
            assert target.exists(), f"Broken link in {path.name}: {link}"
            if is_source:
                assert target.is_relative_to((plugin / "references").resolve()), f"Source-to-source link must return through a reference: {path.name}"
    sys.path.insert(0, str(plugin / "scripts"))
    def load_module(name, filename):
        spec = importlib.util.spec_from_file_location(name, plugin / "scripts" / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    catalog_module = load_module("package_reference_catalog", "reference_catalog.py")
    catalog_module.validate_index(defaults)
    io_module = load_module("package_reference_io", "reference_io.py")
    address_module = load_module("package_reference_address", "reference_address.py")
    graph = catalog_module.Catalog(io_module.load_index).walk([plugin / "references/index.json"])
    assert graph["complete"], f"Incomplete package reference graph: {graph['errors']} {graph['pending']}"
    indexes = graph["indexes"]
    assert indexes, "Missing reference graph"
    for index in indexes:
        current = Path(index["index"])
        assert current.is_relative_to((plugin / "references").resolve()), "Public references cannot bind a consumer registry"
        for entry in index["entries"]:
            if entry["access"] == "file":
                target = address_module.local_path(address_module.source_address(current, entry["locator"], "file"))
                assert target.is_relative_to(plugin.resolve()) and target.is_file(), f"Invalid source location: {entry['id']}"
    if (root / ".git").exists():
        check_inventory(root,"publication-files.json")
    return len(skills), len(files)


if __name__ == "__main__":
    skills, files = validate()
    print(f"PASS: {skills} skills, {files} distributable files; references and publication boundary checked")
