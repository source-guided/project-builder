"""저장 위치와 독립적인 JSON 문서 관측·조건부 변경 계약."""

import hashlib
import json


class ConflictError(ValueError):
    """관측 이후 문서가 바뀌었으므로 다시 읽어야 한다."""


class MissingDocument(FileNotFoundError):
    """저장소가 문서 부재를 확인했다. 접근 거부와 구분한다."""


class StoreError(OSError):
    """인증정보나 원격 응답 본문을 노출하지 않는 저장소 오류."""


def validate_write_size(data, max_bytes):
    if len(data) > max_bytes:
        raise StoreError("Write exceeds the configured size limit; rejected before sending. Existing document is unchanged. Inspect capacity before retrying.")


def encode(document):
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def observation(document, revision, *, raw=None):
    data = encode(document) if raw is None else raw
    return {"document": document, "digest": hashlib.sha256(data).hexdigest(), "revision": revision}


def require_revision(revision):
    if revision is not None and (not isinstance(revision, str) or not revision):
        raise ValueError("Revision must be an observed nonempty string, or null for creation")


def compare_revision(actual, expected):
    require_revision(expected)
    if actual != expected:
        raise ConflictError("Document changed since inspection; read it again before writing")
