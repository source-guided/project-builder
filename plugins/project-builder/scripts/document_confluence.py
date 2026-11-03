"""Confluence 페이지의 JSON content property를 저장하며 페이지 본문은 변경하지 않는다."""

from urllib.parse import quote, urlencode

from document_http import HTTPFailure
from document_store import ConflictError, MissingDocument, StoreError, compare_revision, observation


class ConfluenceStore:
    def __init__(self, transport, *, page_id):
        if not str(page_id).isdecimal():
            raise ValueError("Confluence store needs an existing page ID")
        self.transport = transport
        self.path = "/api/v2/pages/" + str(page_id) + "/properties"

    def _observation(self, value):
        return observation(value["value"], str(value["id"]) + ":" + str(value["version"]["number"]))

    def read(self, key):
        result, _ = self.transport.json("GET", self.path + "?" + urlencode({"key": key}))
        if result.get("_links", {}).get("next"):
            raise StoreError("Confluence property key query was not unique; inspect the page")
        rows = result["results"]
        if not rows:
            raise MissingDocument("Confluence property does not exist on the accessible page")
        if len(rows) != 1 or rows[0].get("key") != key:
            raise StoreError("Confluence returned an unexpected property key")
        return self._observation(rows[0])

    def write(self, key, document, *, expected_revision):
        payload = {"key": key, "value": document}
        path, method = self.path, "POST"
        if expected_revision is not None:
            current = self.read(key)
            compare_revision(current["revision"], expected_revision)
            identifier, number = expected_revision.split(":")
            payload["version"] = {"number": int(number) + 1}
            path += "/" + quote(identifier, safe="")
            method = "PUT"
        try:
            result, _ = self.transport.json(method, path, document=payload)
        except HTTPFailure as error:
            if error.status == 409:
                raise ConflictError("Confluence property changed; read it again") from None
            if error.status == 400:
                # 일부 버전 충돌은 400으로 전달된다. 변경 여부를 관측하고 쓰기는 재시도하지 않는다.
                try:
                    latest = self.read(key)
                except MissingDocument:
                    raise error from None
                if latest["revision"] != expected_revision:
                    raise ConflictError("Confluence property changed; read it again") from None
            raise
        return self._observation(result)
