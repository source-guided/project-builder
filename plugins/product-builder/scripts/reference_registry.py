"""참조 관리자의 메타데이터 변경. 본문이나 업무 판단을 갱신하지 않는다."""

import copy
import hashlib
from pathlib import Path

from reference_catalog import validate_index
from reference_io import load_index, locked, write_json
from reference_address import local_path, source_address


def _validate_local_targets(index, entries):
    for item in entries:
        if item["access"] == "file" and not local_path(source_address(index, item["locator"], "file")).is_file():
            raise ValueError("Register only an observed existing file")


def change(index, identifier, *, operation, entry=None, patch=None, expected_digest=None):
    path = local_path(index)
    if Path(index).is_symlink():
        raise ValueError("Registry changes cannot replace a symlink")
    if operation not in {"add", "update", "remove"}:
        raise ValueError("Unsupported registry operation")
    if operation != "add" and not expected_digest:
        raise ValueError("Update/remove requires the observed index digest")
    with locked(path):
        observed = load_index(path)
        data = copy.deepcopy(validate_index(observed["document"]))
        if expected_digest is not None and expected_digest != observed["digest"]:
            raise ValueError("Registry changed since inspection; read it again before updating")
        matches = [item for item in data["entries"] if item["id"] == identifier]
        before = copy.deepcopy(matches[0]) if matches else None
        if operation == "add":
            if matches:
                raise ValueError("Reference already exists; use a reviewed update")
            if not isinstance(entry, dict) or entry.get("id") != identifier:
                raise ValueError("New entry must have the requested identifier")
            data["entries"].append(copy.deepcopy(entry))
        else:
            if not matches:
                raise ValueError("Reference does not exist")
            if operation == "remove":
                data["entries"].remove(matches[0])
            else:
                if not isinstance(patch, dict) or "id" in patch:
                    raise ValueError("Update metadata without changing the reference identity")
                matches[0].update(patch)
        validate_index(data)
        after = next((item for item in data["entries"] if item["id"] == identifier), None)
        if after is not None:
            _validate_local_targets(path, [after])
        write_json(path, data)
        return {"operation": operation, "reference": {"index": str(path), "id": identifier},
                "before": before, "after": after, "previous_digest": observed["digest"],
                "index_digest": hashlib.sha256(path.read_bytes()).hexdigest()}
