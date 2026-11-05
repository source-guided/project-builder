#!/usr/bin/env python3
"""원천의 참조 참여·노출 계약 검사. 도메인 판단 기준은 검사하지 않는다."""

import argparse
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"plugins/project-builder/scripts"))
from publication_boundary import check_inventory
from reference_catalog import Catalog
from reference_io import load_index
from reference_address import source_address,local_path


def validate_source(root):
    root=Path(root).resolve()
    manifest=json.loads((root/"source.json").read_text())
    required={"format","id","version","role","exposure","contract","entry","capabilities"}
    if set(manifest)!=required or manifest["format"]!=1 or manifest["exposure"]!="source-only" or manifest["contract"]!="project-builder.source/v1":
        raise ValueError("Invalid source participation manifest")
    if not re.fullmatch(r"[a-z][a-z0-9-]*",manifest["id"]) or not re.fullmatch(r"\d+\.\d+\.\d+",manifest["version"]):
        raise ValueError("Invalid source identity/version")
    if not isinstance(manifest["role"],str) or not manifest["role"].strip():raise ValueError("Source role is required")
    for path in (root/"skills",root/"plugins",root/"plugin.json",root/".agents/skills",root/".agents/plugins",root/".codex/skills"):
        if path.exists():raise ValueError("A source cannot export global skills or a plugin")
    inventory=check_inventory(root,"source-files.json")
    if not isinstance(inventory,list) or len(inventory)!=len(set(inventory)):raise ValueError("Invalid source inventory")
    for name in inventory:
        path=Path(name)
        if path.is_absolute() or ".." in path.parts or path.as_posix()!=name:raise ValueError("Invalid source inventory path")
        file=root/path
        if file.is_symlink() or not file.is_file():raise ValueError("Missing or linked source file")
    expected={p.relative_to(root).as_posix() for p in root.rglob("SKILL.md") if not any(v in p.relative_to(root).parts for v in (".git",".local","node_modules"))}
    if set(manifest["capabilities"])!=expected or not all(n.startswith("capabilities/") for n in expected):raise ValueError("Capabilities must be internal and explicitly inventoried")
    for name in expected:
        if name not in inventory or (root/name).parent.joinpath("agents").exists():raise ValueError("Source skills must not carry host discovery registration")
        if not re.match(r"\A---\nname: [a-z0-9-]+\ndescription: .+\n---\n",(root/name).read_text()):raise ValueError("Invalid capability frontmatter")
    entry=(root/manifest["entry"]).resolve()
    if not entry.is_relative_to(root/"references"):raise ValueError("Source entry must stay inside references")
    graph=Catalog(load_index).walk([entry])
    if not graph["complete"]:raise ValueError(f"Incomplete source reference graph: {graph['errors']}")
    reached=set()
    index_directories=set()
    for index in graph["indexes"]:
        current=Path(index["index"])
        if not current.is_relative_to(root/"references"):raise ValueError("Source indexes must stay in their owner")
        if current.parent in index_directories:
            raise ValueError("Reference area indexes must have separate owner directories")
        index_directories.add(current.parent)
        for item in index["entries"]:
            if item["access"] in {"file","relative"}:
                target=local_path(source_address(current,item["locator"],item["access"]))
                if not target.is_relative_to(root) or not target.is_file():raise ValueError("Source locator escapes or is missing")
                reached.add(target.relative_to(root).as_posix())
    if not expected<=reached:raise ValueError("Internal capabilities must be reachable through references")
    for name in inventory:
        path=root/name
        if path.suffix==".md" and name.startswith("capabilities/"):
            for link in re.findall(r"\]\(([^)]+)\)",path.read_text()):
                if link.startswith("#"):continue
                if "://" in link:raise ValueError("Capability navigation must return through a reference")
                target=(path.parent/link.split("#")[0]).resolve()
                if not target.is_relative_to(root/"references") or not target.is_file():raise ValueError("Capability link must point to its reference index")
    return {"source":manifest["id"],"capabilities":len(expected),"files":len(inventory),"exposure":"source-only"}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--source",type=Path,required=True)
    print(json.dumps(validate_source(parser.parse_args().source),ensure_ascii=False))
