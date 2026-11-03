"""참조 메타데이터 변경 정책. 저장·인증은 문서 저장소 어댑터에 위임한다."""

import copy

from document_stores import Stores
from reference_catalog import validate_index
from reference_address import index_access, local_path, source_address


def _validate_targets(index, entry):
    if entry is None:
        return
    if entry["access"] == "relative" and index_access(index) == "connector":
        raise ValueError("Opaque store indexes need explicit file/web/connector target addresses")
    if index_access(index) == "file" and entry["access"] in {"file", "relative"}:
        if not local_path(source_address(index, entry["locator"], entry["access"])).is_file():
            raise ValueError("Register only an observed existing file")


def initialize(index, *, stores=None):
    storage = stores or Stores()
    return storage.write(index, {"format": 1, "entries": []}, expected_revision=None)


def change(index, identifier, *, operation, entry=None, patch=None, expected_digest=None, stores=None):
    storage = stores or Stores()
    if operation not in {"add", "update", "remove"}:
        raise ValueError("Unsupported registry operation")
    if operation != "add" and not expected_digest:
        raise ValueError("Update/remove requires the observed index digest")
    observed = storage.read(index)
    if observed["revision"] is None:
        raise ValueError("Registry has no conditional-write revision; use a store that supports safe changes")
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
    _validate_targets(index, after)
    written = storage.write(index, data, expected_revision=observed["revision"])
    return {"operation": operation, "reference": {"index": written["address"], "id": identifier},
            "before": before, "after": after, "previous_digest": observed["digest"],
            "index_digest": written["digest"], "index_revision": written["revision"]}
