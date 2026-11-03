"""GitHub Contents API의 파일 SHA를 문서 변경 조건으로 사용한다."""

import base64
import json
import re
from urllib.parse import quote, urlencode

from document_http import HTTPFailure
from document_store import ConflictError, MissingDocument, StoreError, encode, observation


class GitHubStore:
    def __init__(self, transport, *, repository, branch, prefix=""):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or any(p in {".", ".."} for p in repository.split("/")):
            raise ValueError("GitHub repository must be owner/repository")
        self.transport, self.repository, self.branch = transport, repository, branch
        self.prefix = prefix.strip("/")

    def _path(self, key):
        path = "/".join(filter(None, (self.prefix, key)))
        return "/repos/" + quote(self.repository, safe="/") + "/contents/" + quote(path, safe="/")

    def read(self, key):
        try:
            result, _ = self.transport.json("GET", self._path(key) + "?" + urlencode({"ref": self.branch}))
        except HTTPFailure as error:
            if error.status == 404:
                raise MissingDocument("GitHub file is missing or not visible to this account") from None
            raise
        if result.get("type") != "file" or result.get("encoding") != "base64":
            raise StoreError("GitHub document must be a file supported by the Contents API base64 response")
        try:
            raw = base64.b64decode(result["content"])
            return observation(json.loads(raw), result["sha"], raw=raw)
        except (ValueError, KeyError, UnicodeError):
            raise StoreError("GitHub returned an invalid document") from None

    def write(self, key, document, *, expected_revision):
        payload = {"message": "Update reference document", "content": base64.b64encode(encode(document)).decode(), "branch": self.branch}
        if expected_revision is not None:
            payload["sha"] = expected_revision
        try:
            result, _ = self.transport.json("PUT", self._path(key), document=payload)
        except HTTPFailure as error:
            if error.status == 409:
                raise ConflictError("GitHub file changed; read it again") from None
            if error.status == 422:
                try:
                    latest = self.read(key)
                except MissingDocument:
                    raise error from None
                if latest["revision"] != expected_revision:
                    raise ConflictError("GitHub file already exists or changed; read it again") from None
            raise
        return observation(document, result["content"]["sha"])
