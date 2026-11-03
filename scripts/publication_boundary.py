"""저장소별 공개 목록과 Git 인덱스의 범위를 검증한다."""

import json
from pathlib import Path
import subprocess


def check_inventory(root, inventory_name):
    root=Path(root)
    tracked=[]
    if (root/".git").exists():
        tracked=subprocess.check_output(["git","ls-files","-z"],cwd=root,text=True).split("\0")
        assert not any(name.startswith(".local/") for name in tracked),"Consumer context is tracked in the Git index"
    inventory=json.loads((root/inventory_name).read_text())
    if not isinstance(inventory,list) or not all(isinstance(n,str) for n in inventory) or len(inventory)!=len(set(inventory)):
        raise ValueError("Invalid publication inventory")
    for name in inventory:
        path=Path(name)
        if path.is_absolute() or ".." in path.parts or path.as_posix()!=name or any(part in {".git",".local","node_modules","__pycache__"} for part in path.parts) or path.name.startswith('.env'):
            raise ValueError("Private or invalid publication path")
        if (root/path).is_symlink() or not (root/path).is_file():
            raise ValueError("Missing or linked publication file")
    if not (root/".git").exists():return inventory
    if inventory_name in tracked:
        staged=json.loads(subprocess.check_output(["git","show",":"+inventory_name],cwd=root))
        assert inventory==staged,"Stage the reviewed publication inventory before validation"
    candidates=set(filter(None,subprocess.check_output(["git","ls-files","--cached","--others","--exclude-standard","-z"],cwd=root,text=True).split("\0")))
    assert not candidates-set(inventory),f"Unreviewed public files: {sorted(candidates-set(inventory))}"
    ignored=subprocess.run(["git","check-ignore","--no-index","-q",".local/context/probe"],cwd=root)
    assert ignored.returncode==0,"Local context must be ignored"
    deny=root/".local/publication-denylist.json"
    if deny.exists():
        terms=json.loads(deny.read_text())
        for name in filter(None,tracked):
            file=root/name
            if file.is_file():
                data=file.read_bytes()
                assert not any(term.encode() in data for term in terms),f"Private source marker in tracked file: {name}"
    return inventory
