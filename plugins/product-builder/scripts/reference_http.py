"""명시된 HTTP 색인 원천의 메타데이터 읽기 어댑터. 원천 본문은 조회하지 않는다."""

import hashlib
from http.client import HTTPException
import json
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from reference_io import load_index
from reference_address import local_path


def origin(address):
    parsed = urlparse(str(address))
    if parsed.username or parsed.password:
        raise ValueError("Index addresses must not include credentials")
    return (parsed.scheme.lower(), parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))


class _RedirectPolicy(HTTPRedirectHandler):
    def __init__(self, allowed):
        self.allowed = allowed

    def redirect_request(self, request, response, code, message, headers, newurl):
        if origin(newurl) not in self.allowed:
            raise ValueError("Redirect leaves the explicitly configured index origins")
        return super().redirect_request(request, response, code, message, headers, newurl)


class IndexReader:
    def __init__(self, roots, *, timeout=5, max_bytes=1024 * 1024, file_roots=()):
        self.allowed = set()
        self.file_roots = {local_path(path) for path in file_roots}
        for root in roots:
            try:
                method=root.get("access") if isinstance(root,dict) else None
                root=root["index"] if isinstance(root,dict) else root
                if method=="connector":
                    continue
                scheme=urlparse(str(root)).scheme
                if method=="web" and scheme not in {"http","https"}:
                    continue
                if method=="file" and scheme not in {"","file"} and len(scheme)!=1:
                    continue
                if scheme in {"http","https"}:
                    self.allowed.add(origin(root))
                elif scheme in {"","file"} or len(scheme)==1:
                    self.file_roots.add(local_path(root).parent)
            except (ValueError, TypeError, KeyError):
                # 잘못된 root는 카탈로그가 해당 분기의 오류로 보고한다.
                continue
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.opener = build_opener(_RedirectPolicy(self.allowed))

    def __call__(self, address):
        if urlparse(str(address)).scheme not in {"http", "https"}:
            path=local_path(address)
            if not any(path.is_relative_to(root) for root in self.file_roots):
                raise PermissionError("Local index is outside the explicitly supplied file roots")
            return load_index(path)
        if origin(address) not in self.allowed:
            raise ValueError("Index origin was not explicitly supplied; discover it before adding it as a root")
        request = Request(address, headers={"Accept": "application/json"})
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                final_address = response.geturl()
                data = response.read(self.max_bytes + 1)
                if len(data) > self.max_bytes:
                    raise ValueError("Index exceeds the configured metadata size limit")
        except HTTPException as error:
            raise OSError(f"Index HTTP transfer failed: {type(error).__name__}") from error
        return {"document": json.loads(data), "digest": hashlib.sha256(data).hexdigest(), "address": final_address}
