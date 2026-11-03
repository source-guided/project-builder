"""Supabase/PostgREST 행의 리비전 조건으로 JSON 문서를 읽고 변경한다."""

import re
from urllib.parse import urlencode

from document_http import HTTPFailure
from document_store import ConflictError, MissingDocument, StoreError, observation


class SupabaseStore:
    def __init__(self, transport, *, table):
        if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", table):
            raise ValueError("Invalid Supabase document table")
        self.transport, self.table = transport, table

    def _path(self, key, revision=None):
        # 문자열 필터의 예약 문자를 인용하여 다른 행 조건으로 해석되지 않게 한다.
        literal = '"' + key.replace('\\', '\\\\').replace('"', '\\"') + '"'
        filters = {"id": "eq." + literal, "select": "document,revision"}
        if revision is not None:
            filters["revision"] = "eq." + revision
        return "/rest/v1/" + self.table + "?" + urlencode(filters)

    def read(self, key):
        rows, _ = self.transport.json("GET", self._path(key))
        if not isinstance(rows, list):
            raise StoreError("Supabase returned an invalid document row set")
        if not rows:
            raise MissingDocument("Supabase document is missing or not visible under RLS")
        if len(rows) != 1:
            raise StoreError("Supabase document id must be unique")
        return observation(rows[0]["document"], str(rows[0]["revision"]))

    def write(self, key, document, *, expected_revision):
        if expected_revision is not None and (not expected_revision.isdecimal() or int(expected_revision) < 1):
            raise ValueError("Supabase changes require an observed positive revision")
        revision = int(expected_revision) + 1 if expected_revision else 1
        payload = {"document": document, "revision": revision}
        if expected_revision is None:
            payload["id"] = key
        method = "POST" if expected_revision is None else "PATCH"
        path = "/rest/v1/" + self.table if expected_revision is None else self._path(key, expected_revision)
        try:
            rows, _ = self.transport.json(method, path, document=payload, headers={"Prefer": "return=representation"})
        except HTTPFailure as error:
            if error.status == 409:
                raise ConflictError("Supabase document already exists or changed") from None
            raise
        if not isinstance(rows, list) or len(rows) != 1:
            raise ConflictError("Supabase conditional write returned no unique row; recheck revision and RLS")
        return observation(rows[0]["document"], str(rows[0]["revision"]))
