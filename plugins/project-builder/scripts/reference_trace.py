"""영수증 기록의 파일·문서 저장. 이벤트 의미와 접근 맥락은 Session이 검사한다."""

import copy
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from document_store import ConflictError, MissingDocument
from document_stores import Stores, store_location
from reference_address import index_access
from reference_io import locked


def _jsonl(records):
    return "".join(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n" for record in records)


class TraceStorage:
    def __init__(self, trace, *, stores=None, max_attempts=8):
        if type(max_attempts) is not int or max_attempts < 1:
            raise ValueError("Trace write attempts must be a positive integer")
        self.stores = stores or Stores()
        self.max_attempts = max_attempts
        if str(trace).startswith("store:"):
            store_location(trace)
            self.address, self.path = str(trace), None
        elif index_access(trace) == "file":
            parsed = urlparse(str(trace))
            if parsed.scheme == "file" and parsed.netloc not in {"", "localhost"}:
                raise ValueError("Remote file authorities need a configured store")
            self.path = Path(unquote(parsed.path) if parsed.scheme == "file" else trace).absolute()
            self.address = str(self.path)
        else:
            raise ValueError("Trace needs a local path or a configured store:// profile")

    def _file_snapshot(self):
        if self.path.is_symlink():
            raise ValueError("Session trace must not be a symlink")
        try:
            raw = self.path.read_bytes()
        except FileNotFoundError:
            return {"records": [], "revision": None, "exists": False}
        records = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        return {"records": records, "revision": hashlib.sha256(raw).hexdigest(), "exists": True}

    def _store_snapshot(self):
        try:
            observed = self.stores.read(self.address)
        except MissingDocument:
            return {"records": [], "revision": None, "exists": False}
        document = observed["document"]
        if not isinstance(document, dict) or set(document) != {"format", "records"} or document["format"] != 1 or not isinstance(document["records"], list):
            raise ValueError("Expected a trace document with format 1 and records; existing documents are not migrated implicitly")
        if not document["records"]:
            raise ValueError("Stored trace document has no session header")
        return {"records": copy.deepcopy(document["records"]), "revision": observed["revision"], "exists": True}

    def snapshot(self):
        if self.path is not None:
            with locked(self.path):
                observed = self._file_snapshot()
        else:
            observed = self._store_snapshot()
        return {"trace": self.address, **observed}

    def append(self, create_records):
        if self.path is not None:
            with locked(self.path):
                current = self._file_snapshot()
                additions = create_records(current["records"])
                data = _jsonl(additions)
                self.path.parent.mkdir(parents=True, exist_ok=True)
                flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
                with os.fdopen(os.open(self.path, flags, 0o600), "a", encoding="utf-8") as stream:
                    stream.write(data); stream.flush(); os.fsync(stream.fileno())
                return additions
        for _ in range(self.max_attempts):
            current = self._store_snapshot()
            if current["exists"] and current["revision"] is None:
                raise ValueError("Shared trace has no conditional-write revision")
            additions = create_records(current["records"])
            document = {"format": 1, "records": [*current["records"], *additions]}
            try:
                self.stores.write(self.address, document, expected_revision=current["revision"])
                return additions
            except ConflictError:
                # 확인된 충돌만 다시 읽고 병합한다. 실제 원천 조회는 이 함수 안에서 실행하지 않는다.
                refreshed = self._store_snapshot()
                if current["exists"] and not refreshed["exists"]:
                    raise ConflictError("Trace was removed during recording; inspect it before starting a new session") from None
                if refreshed["revision"] == current["revision"]:
                    # RLS에 막힌 조건부 갱신 등은 리비전 충돌과 같은 응답일 수 있다.
                    raise
                continue
        raise ConflictError("Trace kept changing; inspect current receipts and retry this recording deliberately")


def export_snapshot(snapshot, output):
    """명시적으로 요청한 감사용 JSONL 스냅샷을 새 파일로 내보낸다."""
    path = Path(output).absolute()
    data = _jsonl(snapshot["records"]).encode("utf-8")
    # 실행 환경의 스냅샷은 원격 기록의 새로운 권위 있는 복사본이 아니다.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags, 0o600), "wb") as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    return {"output": str(path), "trace": snapshot["trace"], "revision": snapshot["revision"],
            "scope": snapshot["scope"], "records": len(snapshot["records"]),
            "sha256": hashlib.sha256(data).hexdigest()}
