import base64
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/project-builder/scripts"))
from document_http import HTTPFailure
from document_s3 import S3Store
from document_store import ConflictError, MissingDocument, StoreError, encode
from document_stores import Stores


@contextmanager
def service():
    documents, requests = {}, []
    gate = threading.Lock()
    secret = "private-test-token-not-for-errors"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def do_GET(self): self.handle_document()
        def do_POST(self): self.handle_document()
        def do_PUT(self): self.handle_document()
        def do_PATCH(self): self.handle_document()

        def respond(self, status, data, headers=None):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            for name, value in (headers or {}).items(): self.send_header(name, value)
            self.end_headers(); self.wfile.write(encode(data))

        def handle_document(self):
            with gate:
                parsed = urlparse(self.path); query = parse_qs(parsed.query)
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"]))) if self.headers.get("Content-Length") else None
                requests.append({"method": self.command, "path": self.path, "body": data, "headers": dict(self.headers)})
                if "denied" in parsed.path:
                    self.respond(403, {"error": secret}); return
                if parsed.path == "/http/redirect":
                    self.respond(302, {}, {"Location": "/capture"}); return
                driver = parsed.path.split("/")[1]
                if driver == "github":
                    key = unquote(parsed.path.split("/contents/", 1)[1])
                elif driver == "supabase":
                    literal = query.get("id", [""])[0].removeprefix("eq.")
                    key = data["id"] if self.command == "POST" else json.loads(literal)
                elif driver == "wiki":
                    key = query["key"][0] if self.command == "GET" else data["key"]
                else:
                    key = unquote(parsed.path.removeprefix("/http/"))
                identity = (driver, key); current = documents.get(identity)
                if self.command == "GET":
                    if current is None:
                        if driver == "supabase": self.respond(200, [])
                        elif driver == "wiki": self.respond(200, {"results": []})
                        else: self.respond(404, {})
                        return
                    if driver == "github":
                        self.respond(200, {"type": "file", "encoding": "base64", "content": base64.b64encode(encode(current["document"])).decode(), "sha": current["etag"]})
                    elif driver == "supabase": self.respond(200, [{"document": current["document"], "revision": current["revision"]}])
                    elif driver == "wiki": self.respond(200, {"results": [{"id": "41", "key": key, "value": current["document"], "version": {"number": current["revision"]}}]})
                    else: self.respond(200, current["document"], {} if key == "without-etag" else {"ETag": current["etag"]})
                    return
                if driver == "github":
                    conflict = data.get("sha") != (current["etag"] if current else None)
                    document = json.loads(base64.b64decode(data["content"]))
                elif driver == "supabase":
                    wanted = query.get("revision", [""])[0].removeprefix("eq.")
                    conflict = (current is not None) if self.command == "POST" else (current is None or str(current["revision"]) != wanted)
                    document = data["document"]
                elif driver == "wiki":
                    conflict = (current is not None) if self.command == "POST" else (current is None or data["version"]["number"] != current["revision"] + 1)
                    document = data["value"]
                else:
                    conflict = (current is not None) if self.headers.get("If-None-Match") == "*" else (current is None or self.headers.get("If-Match") != current["etag"])
                    document = data
                if conflict:
                    if driver == "supabase" and self.command == "PATCH": self.respond(200, [])
                    else: self.respond(412 if driver == "http" else 400 if driver == "wiki" else 422 if driver == "github" else 409, {})
                    return
                saved = {"document": document, "revision": current["revision"] + 1 if current else 1, "etag": '"' + hashlib.sha256(encode(document)).hexdigest() + '"'}
                documents[identity] = saved
                if driver == "github": self.respond(200, {"content": {"sha": saved["etag"]}})
                elif driver == "supabase": self.respond(201 if self.command == "POST" else 200, [{"document": document, "revision": saved["revision"]}])
                elif driver == "wiki": self.respond(200, {"id": "41", "key": key, "value": document, "version": {"number": saved["revision"]}})
                else: self.respond(200, document, {"ETag": saved["etag"]})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    profiles = {
        "http": {"driver": "http", "endpoint": base + "/http", "token_env": "TEST_STORE_TOKEN"},
        "github": {"driver": "github", "endpoint": base + "/github", "repository": "owner/repository", "branch": "main", "token_env": "TEST_STORE_TOKEN"},
        "supabase": {"driver": "supabase", "endpoint": base + "/supabase", "table": "reference_documents", "key_env": "TEST_STORE_KEY", "token_env": "TEST_STORE_TOKEN"},
        "confluence": {"driver": "confluence", "endpoint": base + "/wiki", "page_id": "123", "email_env": "TEST_STORE_EMAIL", "token_env": "TEST_STORE_TOKEN"},
    }
    for profile in profiles.values(): profile["writable"] = True
    try:
        with patch.dict("os.environ", {"TEST_STORE_TOKEN": secret, "TEST_STORE_KEY": "public-test-key", "TEST_STORE_EMAIL": "user@example.com"}):
            yield {"format": 1, "profiles": profiles}, documents, requests, secret
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


class DocumentServicesTest(unittest.TestCase):
    def test_service_adapters_round_trip_and_reject_stale_changes(self):
        with service() as (config, documents, requests, secret):
            stores = Stores(config)
            for name in config["profiles"]:
                address = "store://" + name + "/references"
                with self.subTest(driver=name):
                    with self.assertRaises(MissingDocument): stores.read(address)
                    first = stores.write(address, {"entries": ["one"]}, expected_revision=None)
                    self.assertEqual(stores.read(address)["document"], {"entries": ["one"]})
                    with self.assertRaises((ConflictError, HTTPFailure)): stores.write(address, {}, expected_revision=None)
                    second = stores.write(address, {"entries": ["two"]}, expected_revision=first["revision"])
                    with self.assertRaises(ConflictError): stores.write(address, {"entries": ["lost-update"]}, expected_revision=first["revision"])
                    self.assertEqual(stores.read(address)["document"], second["document"])
            self.assertTrue(any(r["method"] == "PATCH" and "revision=eq.1" in r["path"] for r in requests))
            self.assertTrue(any(r["method"] == "PUT" and r["path"].endswith("/properties/41") and r["body"]["version"]["number"] == 2 for r in requests))
            self.assertTrue(all("Authorization" in r["headers"] for r in requests))

    def test_denied_read_is_not_empty_state_and_secrets_are_not_in_errors(self):
        from source_connections import Connections
        with service() as (config, _, requests, secret):
            connections = Connections("store://http/denied", stores=Stores(config))
            with self.assertRaises(HTTPFailure) as raised: connections.show()
            self.assertEqual(raised.exception.status, 403)
            self.assertNotIn(secret, str(raised.exception))
            self.assertEqual([r["method"] for r in requests], ["GET"])

    def test_authenticated_redirect_is_not_followed(self):
        with service() as (config, _, requests, secret):
            with self.assertRaisesRegex(StoreError, "redirects"): Stores(config).read("store://http/redirect")
            self.assertEqual(len(requests), 1)

    def test_http_without_etag_remains_read_only_for_existing_document(self):
        from source_connections import Connections
        with service() as (config, documents, requests, _):
            documents[("http", "without-etag")] = {"document": {"format": 1, "selections": {}}, "revision": 1, "etag": '"unused"'}
            connections = Connections("store://http/without-etag", stores=Stores(config))
            self.assertEqual(connections.show()["selections"], {})
            with self.assertRaisesRegex(ValueError, "conditional-write"): connections.select("authoring", "general")
            self.assertTrue(all(r["method"] == "GET" for r in requests))

    def test_supabase_filters_a_reserved_character_key_as_one_literal(self):
        with service() as (config, _, requests, __):
            stores = Stores(config); address = 'store://supabase/team,a"b'
            result = stores.write(address, {"value": 1}, expected_revision=None)
            self.assertEqual(stores.read(address)["document"], {"value": 1})
            stores.write(address, {"value": 2}, expected_revision=result["revision"])
            self.assertEqual(stores.read(address)["document"], {"value": 2})

    def test_missing_credentials_and_plain_http_remote_fail_before_request(self):
        with self.assertRaises(StoreError):
            Stores({"format": 1, "profiles": {"team": {"driver": "http", "endpoint": "https://example.com", "token_env": "ABSENT_REFERENCE_TEST_TOKEN"}}}).read("store://team/refs")
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            Stores({"format": 1, "profiles": {"team": {"driver": "http", "endpoint": "http://example.com"}}}).read("store://team/refs")

    def test_s3_sdk_contract_uses_conditional_put_and_closes_reads(self):
        class APIError(Exception):
            def __init__(self, code): self.response = {"Error": {"Code": code}}
        class S3Client:
            value = None
            stream = None
            requests = []
            def get_object(self, *, Bucket, Key):
                if self.value is None: raise APIError("NoSuchKey")
                self.stream = io.BytesIO(self.value)
                return {"Body": self.stream, "ETag": self.etag}
            def put_object(self, *, Bucket, Key, Body, ContentType, IfNoneMatch=None, IfMatch=None):
                self.requests.append({"Bucket": Bucket, "Key": Key, "IfNoneMatch": IfNoneMatch, "IfMatch": IfMatch})
                if (IfNoneMatch == "*" and self.value is not None) or (IfMatch is not None and IfMatch != self.etag): raise APIError("PreconditionFailed")
                self.value = Body; self.etag = '"' + hashlib.sha256(Body).hexdigest() + '"'
                return {"ETag": self.etag}
        client = S3Client(); store = S3Store(bucket="private-bucket", prefix="team", client=client)
        with self.assertRaises(MissingDocument): store.read("refs")
        first = store.write("refs", {"version": 1}, expected_revision=None)
        self.assertEqual(store.read("refs")["document"], {"version": 1})
        self.assertTrue(client.stream.closed)
        store.write("refs", {"version": 2}, expected_revision=first["revision"])
        with self.assertRaises(ConflictError): store.write("refs", {}, expected_revision=first["revision"])
        self.assertEqual(client.requests[0]["IfNoneMatch"], "*")
        self.assertEqual(client.requests[1]["IfMatch"], first["revision"])
        self.assertEqual(client.requests[0]["Key"], "team/refs")


if __name__ == "__main__":
    unittest.main()
