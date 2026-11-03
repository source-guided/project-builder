"""명시적으로 설정한 서비스의 HTTP 전송과 JSON/ETag 저장 계약."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from document_store import ConflictError, MissingDocument, StoreError, encode, observation


class HTTPFailure(StoreError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"Store HTTP request failed ({status}); inspect service permissions or request contract")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        response.close()
        raise StoreError("Store redirects are not followed; configure the intended endpoint explicitly")


def environment(name):
    value = os.environ.get(name) if isinstance(name, str) else None
    if not value:
        raise StoreError("A configured credential environment variable is unavailable")
    if "\n" in value or "\r" in value:
        raise StoreError("Invalid credential header value")
    return value


class Transport:
    def __init__(self, endpoint, *, headers=None, timeout=15, max_bytes=1024 * 1024):
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Store endpoint must be an HTTP(S) base URL without credentials, query or fragment")
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Remote store endpoints must use HTTPS")
        if timeout <= 0 or max_bytes < 1:
            raise ValueError("Store timeout and response size limit must be positive")
        self.endpoint = endpoint.rstrip("/")
        self.headers = headers or {}
        self.timeout, self.max_bytes = timeout, max_bytes
        self.opener = build_opener(NoRedirect())

    def request(self, method, suffix="", *, body=None, headers=None):
        request_headers = {"Accept": "application/json", **self.headers, **(headers or {})}
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        request = Request(self.endpoint + suffix, data=body, method=method, headers=request_headers)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(self.max_bytes + 1)
                if len(raw) > self.max_bytes:
                    raise StoreError("Store response exceeds the configured size limit")
                return raw, response.headers
        except HTTPError as error:
            # 응답 본문·URL에는 비밀값이 있을 수 있으므로 오류에 복제하지 않는다.
            error.close()
            raise HTTPFailure(error.code) from None
        except (URLError, TimeoutError):
            raise StoreError("Store transport failed; check endpoint availability") from None

    def json(self, method, suffix="", *, document=None, headers=None):
        raw, response_headers = self.request(method, suffix, body=encode(document) if document is not None else None, headers=headers)
        try:
            return json.loads(raw), response_headers
        except (ValueError, UnicodeError):
            raise StoreError("Store returned an invalid JSON response") from None


class HTTPStore:
    def __init__(self, transport):
        self.transport = transport

    def read(self, key):
        from urllib.parse import quote
        try:
            raw, headers = self.transport.request("GET", "/" + quote(key, safe="/"))
        except HTTPFailure as error:
            if error.status == 404:
                raise MissingDocument("HTTP document was not found") from None
            raise
        revision = headers.get("ETag")
        return observation(json.loads(raw), revision, raw=raw)

    def write(self, key, document, *, expected_revision):
        from urllib.parse import quote
        if expected_revision is not None and (expected_revision.startswith("W/") or not expected_revision.startswith('"')):
            raise ValueError("HTTP changes require a strong observed ETag")
        conditions = {"If-None-Match": "*"} if expected_revision is None else {"If-Match": expected_revision}
        try:
            _, headers = self.transport.request("PUT", "/" + quote(key, safe="/"), body=encode(document), headers=conditions)
        except HTTPFailure as error:
            if error.status in {409, 412}:
                raise ConflictError("HTTP document changed; read it again") from None
            raise
        revision = headers.get("ETag")
        if not revision or revision.startswith("W/"):
            raise StoreError("Write completed but no strong ETag was returned; inspect before any retry")
        return observation(document, revision)
