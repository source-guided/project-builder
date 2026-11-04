"""Project Builder의 참조 경유 정책과 원천 읽기 실행. 발견 규약과 분리한다."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
from urllib.parse import urlparse

from reference_catalog import Catalog
from reference_address import index_access, index_address, local_path
from reference_io import fingerprint, load_index
from reference_session import Session


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "sources/governance/reference-routing.md"
BOOTSTRAP = "project-builder:routing-bootstrap"


class Workflow:
    def __init__(self, trace, *, scope=None, catalog=None, index_fingerprint=fingerprint, source_roots=(), stores=None):
        self.session = Session(trace, scope=scope, stores=stores)
        self.catalog = catalog or Catalog(load_index)
        self.index_fingerprint = index_fingerprint
        self.source_roots = [Path(root).resolve() for root in source_roots]
        if not all(root.is_dir() for root in self.source_roots):
            raise ValueError("Explicit source roots must be existing directories")

    def _policy_read(self, records=None):
        expected = hashlib.sha256(POLICY.read_bytes()).hexdigest()
        records = self.session.events() if records is None else records
        starts = {e["receipt"] for e in records if e.get("event") == "reference" and e.get("purpose") == BOOTSTRAP}
        return any(e.get("event") == "source" and e["receipt"] in starts and e["status"] == "read" and e.get("observed_sha256") == expected for e in records)

    def prepare(self, index, identifier, *, access=None):
        method = access or index_access(index)
        normalized = index_address(index, method)
        signature = self.index_fingerprint(normalized) if self.index_fingerprint and method == "file" else None
        cached = self.session.cached_metadata(normalized, identifier, signature, access=method)
        resolved = self.catalog.bind(**cached) if cached else self.catalog.resolve(normalized, identifier, access=method)
        is_policy = resolved["access"] == "file" and local_path(resolved["address"]) == POLICY.resolve()
        def validate_context(records):
            if not is_policy and not self._policy_read(records):
                raise ValueError("Read the current governing routing source through its reference first")
        if resolved["access"] == "file" and resolved["reference"]["access"] != "file":
            target=local_path(resolved["address"])
            if not any(target.is_relative_to(root) for root in self.source_roots):
                raise PermissionError("A remote or connector index cannot authorize a local source read; explicitly supply its source root")
        return self.session.prepare(resolved, index_signature=signature, cache_hit=cached is not None,
                                    purpose=BOOTSTRAP if is_policy else None, validate_context=validate_context)

    def read(self, index, identifier, *, access=None):
        request = self.prepare(index, identifier, access=access)
        resolved, receipt = request["resolved"], request["receipt"]
        try:
            if resolved["access"] != "file":
                raise ValueError("Use prepare-read and the authorized source adapter, then record the receipt")
            data = local_path(resolved["address"]).read_bytes()
            content = data.decode("utf-8")
        except (OSError, ValueError) as error:
            self.session.record(receipt, status="unavailable", error=error)
            raise
        observation = self.session.record(receipt, digest=hashlib.sha256(data).hexdigest())
        return {"reference": request, "observation": observation, "content": content}

    def read_many(self, requests, *, workers=4):
        if not self._policy_read():
            raise ValueError("Read the current governing routing source before starting independent reads")
        if not 1 <= workers <= 32:
            raise ValueError("workers must be between 1 and 32")
        def read_one(request):
            try:
                return {"request": request, "status": "read", "result": self.read(request["index"], request["id"], access=request.get("access"))}
            except (OSError, ValueError, KeyError) as error:
                return {"request": request, "status": "unavailable", "error": str(error)}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(executor.map(read_one, requests))

    def audit(self):
        report = self.session.audit()
        return {**report, "current_policy_read": self._policy_read()}
