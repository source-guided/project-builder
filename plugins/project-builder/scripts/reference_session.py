"""세션별 참조 영수증, 발견 메타데이터 캐시와 관리 확인 기록."""

import copy
import time
import uuid

from reference_catalog import binding_digest
from reference_trace import TraceStorage


SOURCE_STATUSES = {"read", "unavailable", "reused-from-current-context"}


def audit_records(records):
    if not isinstance(records, list) or not records or not all(isinstance(e, dict) for e in records) or records[0].get("event") != "session" or records[0].get("format") != 2:
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
    def __init__(self, trace, *, scope=None, stores=None, max_attempts=8):
        self.storage = TraceStorage(trace, stores=stores, max_attempts=max_attempts)
        self.path = self.storage.path
        if scope is None and self.path is None:
            raise ValueError("Stored traces need an explicit scope; use a separate trace key for each access context")
        scope = "local" if scope is None else scope
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError("Session scope must be nonempty")
        self.scope = scope

    def _checked(self, records):
        if records:
            audit_records(records)
            if records[0]["scope"] != self.scope:
                raise ValueError("Session scope changed; use a separate session for this access context")
        return records

    def _transaction(self, create_event):
        def additions(records):
            self._checked(records)
            header = []
            if not records:
                header = [{"event": "session", "format": 2, "scope": self.scope, "created_at": time.time()}]
            event = create_event([*records, *header])
            audit_records([*records, *header, event])
            return [*header, event]
        return self.storage.append(additions)[-1]

    def snapshot(self):
        observed = self.storage.snapshot()
        self._checked(observed["records"])
        return {**observed, "scope": self.scope}

    def events(self):
        return self.snapshot()["records"]

    def cached_metadata(self, index, identifier, signature, *, access="file"):
        if signature is None or self.path is None:
            return None
        for event in reversed(self.events()):
            if event.get("event") == "reference" and event["resolved"]["reference"] == {"index": index, "id": identifier, "access": access}:
                if event.get("index_signature") == signature and "metadata" in event["resolved"]:
                    resolved = event["resolved"]
                    return {"index": index, "item": copy.deepcopy(resolved["metadata"]),
                            "digest": resolved["index_digest"], "access": access}
                return None
        return None

    def prepare(self, resolved, *, index_signature=None, cache_hit=False, purpose=None, validate_context=None):
        event = {"event": "reference", "receipt": str(uuid.uuid4()), "resolved": copy.deepcopy(resolved),
                 "created_at": time.time(), "index_signature": index_signature, "cache_hit": cache_hit}
        if purpose:
            event["purpose"] = purpose
        def create(records):
            if validate_context is not None:
                validate_context(records)
            return event
        return self._transaction(create)

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
