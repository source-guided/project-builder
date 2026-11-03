"""호출자 소유 저장소 연결과 전송 어댑터 조합. 인증·공유 정책은 원천이 소유한다."""

import base64
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlparse

from document_http import HTTPStore, Transport, environment
from document_local import FileStore, SQLiteStore
from document_store import StoreError, encode, require_revision
from reference_address import index_access, index_address
from reference_catalog import Catalog
from reference_http import IndexReader


FIELDS = {
    "sqlite": {"path"},
    "http": {"endpoint", "token_env"},
    "github": {"endpoint", "repository", "branch", "prefix", "token_env"},
    "supabase": {"endpoint", "table", "key_env", "token_env"},
    "confluence": {"endpoint", "page_id", "email_env", "token_env"},
    "s3": {"bucket", "prefix", "region", "profile"},
    "host": set(),
}
REQUIRED = {
    "sqlite": {"path"}, "http": {"endpoint"},
    "github": {"endpoint", "repository", "branch"},
    "supabase": {"endpoint", "table", "key_env"},
    "confluence": {"endpoint", "page_id"}, "s3": {"bucket"}, "host": set(),
}


def load_config(path):
    if not path:
        return None
    location = Path(path).resolve()
    config = json.loads(location.read_text(encoding="utf-8"))
    if isinstance(config, dict) and isinstance(config.get("profiles"), dict):
        for profile in config["profiles"].values():
            if isinstance(profile, dict) and profile.get("driver") == "sqlite" and isinstance(profile.get("path"), str):
                profile["path"] = str(location.parent / profile["path"])
    return config


def store_location(address):
    parsed = urlparse(str(address))
    if parsed.scheme != "store" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Store address must be store://profile/document-key without credentials or query")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", parsed.netloc):
        raise ValueError("Invalid store profile name")
    key = unquote(parsed.path.removeprefix("/"))
    if not key or any(part in {"", ".", ".."} for part in key.split("/")) or "\\" in key or any(ord(c) < 32 for c in key):
        raise ValueError("Store document keys must not contain traversal, empty segments or control characters")
    return parsed.netloc, key


class Stores:
    def __init__(self, config=None, *, adapters=None):
        config = config if config is not None else {"format": 1, "profiles": {}}
        if not isinstance(config, dict) or set(config) != {"format", "profiles"} or config["format"] != 1 or not isinstance(config["profiles"], dict):
            raise ValueError("Invalid store profile configuration")
        self.profiles = config["profiles"]
        self.adapters = dict(adapters or {})
        self.file = FileStore()
        for name, profile in self.profiles.items():
            store_location("store://" + name + "/document")
            if not isinstance(profile, dict) or profile.get("driver") not in FIELDS:
                raise ValueError("Unknown document store driver")
            allowed = FIELDS[profile["driver"]] | {"driver", "writable", "timeout", "max_bytes"}
            if set(profile) - allowed:
                raise ValueError("Unknown store configuration field; credentials belong in environment variables")
            for field in REQUIRED[profile["driver"]]:
                if not isinstance(profile.get(field), str) or not profile[field].strip():
                    raise ValueError(f"Store profile requires a nonempty {field}")
            for field in ("timeout", "max_bytes"):
                if field in profile and (type(profile[field]) is not int or profile[field] <= 0):
                    raise ValueError("Store timeout and response size limit must be positive integers")
            if profile.get("prefix"):
                store_location("store://profile/" + profile["prefix"].strip("/"))
            if not isinstance(profile.get("writable", False), bool):
                raise ValueError("Store writable must be a boolean; it does not grant service permissions")
            for field, value in profile.items():
                if field.endswith("_env") and (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value)):
                    raise ValueError("Credential fields name environment variables, not secret values")

    def _adapter(self, name):
        profile = self.profiles.get(name)
        if profile is None:
            raise ValueError("Store profile is not configured in this access context")
        if name in self.adapters:
            return self.adapters[name]
        driver = profile["driver"]
        if driver == "sqlite":
            adapter = SQLiteStore(profile["path"])
        elif driver == "s3":
            from document_s3 import S3Store
            adapter = S3Store(bucket=profile["bucket"], prefix=profile.get("prefix", ""),
                              region=profile.get("region"), profile=profile.get("profile"),
                              max_bytes=profile.get("max_bytes", 1024 * 1024))
        elif driver == "host":
            raise ValueError("This store needs an authorized host adapter; standalone CLI cannot supply it")
        else:
            headers = {}
            token = environment(profile["token_env"]) if profile.get("token_env") else None
            if token:
                if driver == "confluence" and profile.get("email_env"):
                    credential = environment(profile["email_env"]) + ":" + token
                    headers["Authorization"] = "Basic " + base64.b64encode(credential.encode()).decode()
                else:
                    headers["Authorization"] = "Bearer " + token
            if driver == "supabase":
                headers["apikey"] = environment(profile["key_env"])
            if driver == "github":
                headers.update({"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"})
            transport = Transport(profile["endpoint"], headers=headers, timeout=profile.get("timeout", 15), max_bytes=profile.get("max_bytes", 1024 * 1024))
            if driver == "http":
                adapter = HTTPStore(transport)
            elif driver == "github":
                from document_github import GitHubStore
                adapter = GitHubStore(transport, repository=profile["repository"], branch=profile["branch"], prefix=profile.get("prefix", ""))
            elif driver == "supabase":
                from document_supabase import SupabaseStore
                adapter = SupabaseStore(transport, table=profile["table"])
            else:
                from document_confluence import ConfluenceStore
                adapter = ConfluenceStore(transport, page_id=profile["page_id"])
        self.adapters[name] = adapter
        return adapter

    def _target(self, address, *, writing=False):
        if str(address).startswith("store:"):
            name, key = store_location(address)
            if writing and not self.profiles.get(name, {}).get("writable", False):
                raise PermissionError("Store profile is read-only; change its setting only within authorized scope")
            return self._adapter(name), key
        if index_access(address) != "file":
            raise ValueError("Use an explicitly configured store:// profile for remote document storage")
        return self.file, str(address)

    def read(self, address):
        adapter, key = self._target(address)
        result = adapter.read(key)
        if not isinstance(result, dict) or not {"document", "digest", "revision"} <= set(result):
            raise StoreError("Store adapter returned an invalid document observation")
        if not isinstance(result["digest"], str) or not re.fullmatch(r"[0-9a-f]{64}", result["digest"]):
            raise StoreError("Store adapter returned an invalid document digest")
        require_revision(result["revision"])
        return {"document": result["document"], "digest": result["digest"], "revision": result["revision"],
                "address": index_address(address, index_access(address))}

    def write(self, address, document, *, expected_revision):
        require_revision(expected_revision)
        encode(document)
        adapter, key = self._target(address, writing=True)
        result = adapter.write(key, document, expected_revision=expected_revision)
        if not result.get("revision"):
            raise StoreError("Write has no confirmed revision; inspect the store before any retry")
        return {**result, "address": index_address(address, index_access(address))}

    def catalog(self, roots, *, connector_reader=None):
        allowed = set()
        for root in roots:
            try:
                address = root["index"] if isinstance(root, dict) else root
                if str(address).startswith("store:"):
                    allowed.add(store_location(address)[0])
            except (ValueError, TypeError, KeyError):
                # 잘못된 분기는 Catalog가 보고하고 정상 분기의 탐색은 계속한다.
                continue

        def read_connector(address):
            if str(address).startswith("store:"):
                if store_location(address)[0] not in allowed:
                    raise PermissionError("A discovered reference cannot authorize another store profile")
                return self.read(address)
            if connector_reader is None:
                raise ValueError("No host connector index adapter configured")
            return connector_reader(address)

        return Catalog(IndexReader(roots), connector_reader=read_connector)
