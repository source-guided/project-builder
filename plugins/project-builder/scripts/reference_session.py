"""세션별 참조 영수증, 발견 메타데이터 캐시와 관리 확인 기록."""

import copy
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from reference_catalog import binding_digest
from reference_io import locked


SOURCE_STATUSES = {"read", "unavailable", "reused-from-current-context"}


def audit_records(records):
    if not records or records[0].get("event") != "session" or records[0].get("format") != 2:
        raise ValueError("Expected a v2 session; use the originating package to inspect historical traces")
    if not isinstance(records[0].get("scope"), str) or not records[0]["scope"]:
        raise ValueError("Session needs an explicit scope")
    pending, references, outcomes = {}, {}, {}
    reviews = []
    for event in records[1:]:
        kind = event.get("event")
        receipt = event.get("receipt")
        if kind == "reference":
            if not isinstance(receipt, str) or not receipt or receipt in references:
                raise ValueError("Reference receipts must be unique")
            resolved = event.get("resolved", {})
            if resolved.get("kind") != "source" or not resolved.get("address") or not isinstance(resolved.get("reference"), dict):
                raise ValueError("Receipt must identify a resolved source")
            references[receipt] = event
            pending[receipt] = event
        elif kind == "source":
            if receipt not in pending or event.get("status") not in SOURCE_STATUSES:
                raise ValueError("Source access needs an unconsumed matching reference receipt and valid status")
            if event.get("status") == "reused-from-current-context":
                origin = event.get("based_on")
                if origin not in outcomes or outcomes[origin].get("status") != "read":
                    raise ValueError("Context reuse requires a prior actual read")
                if binding_digest(references[origin]["resolved"]) != binding_digest(pending[receipt]["resolved"]):
                    raise ValueError("Context reuse must refer to the same source binding")
            outcomes[receipt] = event
            pending.pop(receipt)
        elif kind == "metadata-review":
            if receipt not in outcomes or outcomes[receipt].get("status") != "read" or not outcomes[receipt].get("observed_sha256"):
                raise ValueError("Metadata review requires a source revision observed by a read")
            if event.get("source_sha256") != outcomes[receipt]["observed_sha256"]:
                raise ValueError("Metadata review must retain the observed source revision")
            if not isinstance(event.get("binding_digest"), str) or not event.get("reference"):
                raise ValueError("Metadata review requires the reviewed reference binding")
            reviews.append(event)
        else:
            raise ValueError("Unknown session event")
    return {"valid": True, "source_accesses": len(outcomes),
            "read": sum(e["status"] == "read" for e in outcomes.values()),
            "unavailable": sum(e["status"] == "unavailable" for e in outcomes.values()),
            "reused": sum(e["status"] == "reused-from-current-context" for e in outcomes.values()),
            "pending": sorted(pending), "metadata_reviews": len(reviews)}


class Session:
    def __init__(self, trace, *, scope="local"):
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError("Session scope must be nonempty")
        self.path = Path(trace).absolute()
        self.scope = scope

    def _load(self):
        if self.path.is_symlink():
            raise ValueError("Session trace must not be a symlink")
        if not self.path.exists():
            return []
        records = [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]
        audit_records(records)
        if records[0]["scope"] != self.scope:
            raise ValueError("Session scope changed; use a separate session for this access context")
        return records

    def _append(self, event):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(self.path, flags, 0o600), "a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            stream.flush(); os.fsync(stream.fileno())

    def _transaction(self, create_event):
        with locked(self.path):
            records = self._load()
            if not records:
                records = [{"event": "session", "format": 2, "scope": self.scope, "created_at": time.time()}]
                self._append(records[0])
            event = create_event(records)
            audit_records([*records, event])
            self._append(event)
            return event

    def events(self):
        with locked(self.path):
            return self._load()

    def cached_metadata(self, index, identifier, signature, *, access="file"):
        if signature is None:
            return None
        for event in reversed(self.events()):
            if event.get("event") == "reference" and event["resolved"]["reference"] == {"index": index, "id": identifier, "access": access}:
                if event.get("index_signature") == signature and "metadata" in event["resolved"]:
                    resolved = event["resolved"]
                    return {"index": index, "item": copy.deepcopy(resolved["metadata"]),
                            "digest": resolved["index_digest"], "access": access}
                return None
        return None

    def prepare(self, resolved, *, index_signature=None, cache_hit=False, purpose=None):
        event = {"event": "reference", "receipt": str(uuid.uuid4()), "resolved": copy.deepcopy(resolved),
                 "created_at": time.time(), "index_signature": index_signature, "cache_hit": cache_hit}
        if purpose:
            event["purpose"] = purpose
        return self._transaction(lambda records: event)

    def record(self, receipt, *, status="read", digest=None, error=None, based_on=None):
        event = {"event": "source", "receipt": receipt, "status": status, "observed_at": time.time()}
        if digest is not None:
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Observed revision must be a SHA-256 digest")
            event["observed_sha256"] = digest
        if error:
            event["error"] = str(error)
        if based_on:
            event["based_on"] = based_on
        return self._transaction(lambda records: event)

    def review_metadata(self, receipt, resolved):
        def create(records):
            request = next((e for e in records if e.get("event") == "reference" and e.get("receipt") == receipt), None)
            outcome = next((e for e in records if e.get("event") == "source" and e.get("receipt") == receipt), None)
            if not request or not outcome or request["resolved"]["reference"] != resolved["reference"] or request["resolved"]["address"] != resolved["address"]:
                raise ValueError("Review must apply to the source actually inspected")
            return {"event": "metadata-review", "receipt": receipt, "reference": resolved["reference"],
                    "binding_digest": binding_digest(resolved), "source_sha256": outcome.get("observed_sha256"),
                    "reviewed_at": time.time()}
        return self._transaction(create)

    def metadata_status(self, resolved):
        records = self.events()
        requests = {e["receipt"]: e for e in records if e.get("event") == "reference"}
        observations = [e for e in records if e.get("event") == "source" and requests[e["receipt"]]["resolved"]["reference"] == resolved["reference"]]
        reviews = [e for e in records if e.get("event") == "metadata-review" and e["reference"] == resolved["reference"]]
        current = observations[-1] if observations else None
        reviewed = reviews[-1] if reviews else None
        state = "not_observed"
        if current:
            state = "unavailable" if current["status"] == "unavailable" else "review_required"
            if current["status"] == "read" and reviewed and reviewed["binding_digest"] == binding_digest(resolved) and reviewed["source_sha256"] == current.get("observed_sha256"):
                state = "reviewed_observation"
        return {"reference": resolved["reference"], "status": state, "observation": current, "review": reviewed,
                "meaning": "Based on this session's observed revision; not automatic source monitoring or semantic validation."}

    def audit(self):
        return audit_records(self.events())
