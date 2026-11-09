from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sqlite3
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/project-builder"
sys.path.insert(0, str(PLUGIN / "scripts"))
from document_local import SQLiteStore
from document_http import HTTPFailure
from document_store import ConflictError, StoreError, encode
from document_stores import Stores
from reference_session import Session, audit_records
from reference_trace import export_snapshot
from reference_workflow import Workflow


def sqlite_config(path, *, writable=True):
    return {"format": 1, "profiles": {"team": {"driver": "sqlite", "path": str(path), "writable": writable}}}


def fixture(root):
    entries = []
    for name in ("one", "two"):
        (root / (name + ".md")).write_text("private body " + name)
        entries.append({"id": name, "label": name, "kind": "source", "access": "file", "locator": name + ".md", "topics": []})
    index = root / "index.json"; index.write_text(json.dumps({"format": 1, "entries": entries}))
    return index


class CollisionAdapter:
    def __init__(self, delegate):
        self.delegate = delegate
        self.calls = 0
        self.lock = threading.Lock()
        self.barrier = threading.Barrier(2)

    def read(self, key): return self.delegate.read(key)

    def write(self, key, document, *, expected_revision):
        with self.lock:
            self.calls += 1
            collide = self.calls <= 2
        if collide: self.barrier.wait(timeout=5)
        return self.delegate.write(key, document, expected_revision=expected_revision)


@contextmanager
def permission_server():
    documents = {}
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self): self.execute()
        def do_PUT(self): self.execute()

        def respond(self, status, data, etag=None):
            self.send_response(status)
            if etag: self.send_header("ETag", etag)
            self.end_headers(); self.wfile.write(encode(data))

        def execute(self):
            actor = self.headers.get("Authorization", "").removeprefix("Bearer ")
            parts = self.path.strip("/").split("/")
            if actor not in {"alice", "bob"} or len(parts) < 3:
                self.respond(401, {}); return
            group, owner = parts[:2]
            if (group == "private" or self.command == "PUT") and owner != actor:
                self.respond(403, {}); return
            with lock:
                current = documents.get(self.path)
                if self.command == "GET":
                    if current is None: self.respond(404, {})
                    else: self.respond(200, current["document"], current["etag"])
                    return
                if self.headers.get("If-None-Match") == "*":
                    conflict = current is not None
                else:
                    conflict = current is None or self.headers.get("If-Match") != current["etag"]
                if conflict:
                    self.respond(412, {}); return
                document = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                etag = '"' + hashlib.sha256(encode(document)).hexdigest() + '"'
                documents[self.path] = {"document": document, "etag": etag}
                self.respond(200, document, etag)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with patch.dict("os.environ", {"TRACE_ALICE": "alice", "TRACE_BOB": "bob"}):
            yield base, documents
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


class SharedReceiptsTest(unittest.TestCase):
    def test_completion_capacity_failure_keeps_receipt_pending_until_record_recovery(self):
        from test_document_services import service
        with service() as (config, documents, requests, _):
            trace = "store://http/receipts/completion"
            stores = Stores(config); flow = self.bootstrap(trace, stores)
            request = flow.prepare(PLUGIN / "references/governance/index.json", "routing-policy")
            before = flow.session.snapshot()
            current_bytes = len(encode(documents[("http", "receipts/completion")]["document"]))
            limited_config = copy.deepcopy(config)
            limited_config["profiles"]["http"]["max_bytes"] = current_bytes
            limited = Workflow(trace, scope="alice-work", stores=Stores(limited_config))
            count = len(requests)
            with self.assertRaisesRegex(StoreError, "before sending"):
                limited.session.record(request["receipt"], digest="a" * 64)
            self.assertTrue(all(item["method"] == "GET" for item in requests[count:]))
            self.assertEqual(limited.session.snapshot(), before)
            self.assertIn(request["receipt"], limited.audit()["pending"])
            # 용량을 조정한 뒤 실제 원천 읽기를 반복하지 않고 같은 완료 기록만 재시도한다.
            flow.session.record(request["receipt"], digest="a" * 64)
            self.assertEqual(flow.audit()["pending"], [])
            with self.assertRaises(ValueError): flow.session.record(request["receipt"], digest="a" * 64)

    def test_trace_capacity_rejection_preserves_history_and_allows_new_session_key(self):
        from test_document_services import service
        with service() as (config, documents, requests, _), tempfile.TemporaryDirectory() as tmp:
            config["profiles"]["http"]["max_bytes"] = 4096
            stores = Stores(config); trace = "store://http/receipts/run-001"
            flow = self.bootstrap(trace, stores)
            index = fixture(Path(tmp))
            for _ in range(20):
                before = flow.session.snapshot()
                saved = copy.deepcopy(documents[("http", "receipts/run-001")])
                count = len(requests)
                try:
                    request = flow.prepare(index, "one")
                except StoreError as error:
                    self.assertIn("before sending", str(error))
                    self.assertTrue(all(item["method"] == "GET" for item in requests[count:]))
                    self.assertEqual(documents[("http", "receipts/run-001")], saved)
                    self.assertEqual(flow.session.snapshot(), before)
                    self.assertTrue(flow.audit()["valid"])
                    break
                # 완료 기록이 경계를 넘는 경우도 기존 영수증을 보존해야 한다.
                before = flow.session.snapshot()
                saved = copy.deepcopy(documents[("http", "receipts/run-001")])
                try:
                    flow.session.record(request["receipt"], digest="a" * 64)
                except StoreError as error:
                    self.assertIn("before sending", str(error))
                    self.assertEqual(documents[("http", "receipts/run-001")], saved)
                    self.assertEqual(flow.session.snapshot(), before)
                    self.assertIn(request["receipt"], flow.audit()["pending"])
                    break
            else:
                self.fail("Trace did not reach the configured capacity")
            snapshot = flow.session.snapshot()
            exported = export_snapshot(snapshot, Path(tmp) / "snapshot.jsonl")
            self.assertEqual(exported["revision"], snapshot["revision"])
            # 기존 기록을 자르거나 복사하지 않고 같은 저장소에 새 세션을 시작한다.
            next_flow = self.bootstrap("store://http/receipts/run-002", stores)
            self.assertEqual(next_flow.read(index, "two")["content"], "private body two")
            self.assertEqual(next_flow.audit()["read"], 2)
            self.assertEqual(flow.session.snapshot(), snapshot)

    def bootstrap(self, trace, stores, *, scope="alice-work"):
        flow = Workflow(trace, stores=stores, scope=scope)
        flow.read(PLUGIN / "references/governance/index.json", "routing-policy")
        return flow

    def test_sqlite_trace_round_trip_contains_no_body_or_local_trace_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); index = fixture(root); config = sqlite_config(root / "records.db")
            stores = Stores(config); trace = "store://team/receipts/alice/session"
            flow = self.bootstrap(trace, stores)
            flow.read(index, "one")
            second = Session(trace, scope="alice-work", stores=Stores(config))
            self.assertIsNone(second.path)
            self.assertEqual(second.audit()["read"], 2)
            self.assertEqual(second.audit()["pending"], [])
            document = stores.read(trace)["document"]
            self.assertEqual(document["format"], 1)
            self.assertNotIn("private body one", json.dumps(document))
            self.assertFalse(list(root.rglob("*.jsonl")))

    def test_shared_trace_requires_scope_and_rejects_context_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stores = Stores(sqlite_config(root / "records.db")); trace = "store://team/receipts/alice"
            with self.assertRaisesRegex(ValueError, "explicit scope"): Session(trace, stores=stores)
            self.bootstrap(trace, stores)
            before = stores.read(trace)["revision"]
            with self.assertRaisesRegex(ValueError, "scope changed"):
                Workflow(trace, stores=stores, scope="bob-work").read(PLUGIN / "references/governance/index.json", "routing-policy")
            self.assertEqual(stores.read(trace)["revision"], before)
            self.assertEqual(self.bootstrap("store://team/receipts/bob", stores, scope="bob-work").audit()["read"], 1)

    def test_colliding_independent_receipts_are_merged_without_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); index = fixture(root); config = sqlite_config(root / "records.db")
            stores = Stores(config); flow = self.bootstrap("store://team/receipts/alice", stores)
            adapter = CollisionAdapter(SQLiteStore(root / "records.db")); stores.adapters["team"] = adapter
            with ThreadPoolExecutor(max_workers=2) as pool:
                receipts = list(pool.map(lambda name: flow.prepare(index, name)["receipt"], ["one", "two"]))
            self.assertEqual(len(set(receipts)), 2)
            self.assertEqual(flow.audit()["pending"], sorted(receipts))
            self.assertGreaterEqual(adapter.calls, 3)
            for receipt in receipts: flow.session.record(receipt)
            self.assertEqual(flow.audit()["read"], 3)

    def test_duplicate_completion_collision_consumes_receipt_only_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); index = fixture(root); stores = Stores(sqlite_config(root / "records.db"))
            flow = self.bootstrap("store://team/receipts/alice", stores)
            receipt = flow.prepare(index, "one")["receipt"]
            stores.adapters["team"] = CollisionAdapter(SQLiteStore(root / "records.db"))
            def complete(_):
                try:
                    flow.session.record(receipt)
                    return "recorded"
                except ValueError:
                    return "rejected"
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertCountEqual(list(pool.map(complete, range(2))), ["recorded", "rejected"])
            self.assertEqual(flow.audit()["read"], 2)
            self.assertEqual(flow.audit()["pending"], [])

    def test_confirmed_conflict_retries_are_bounded_and_unknown_outcomes_are_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); index = fixture(root); stores = Stores(sqlite_config(root / "records.db"))
            trace = "store://team/receipts/alice"; flow = self.bootstrap(trace, stores)
            receipt = flow.prepare(index, "one")["receipt"]
            original = stores.write
            def changed(*args, **kwargs):
                observed = stores.read(trace)
                original(trace, observed["document"], expected_revision=observed["revision"])
                raise ConflictError("changed")
            with patch.object(stores, "write", side_effect=changed) as write:
                with self.assertRaises(ConflictError): Session(trace, scope="alice-work", stores=stores, max_attempts=2).record(receipt)
                self.assertEqual(write.call_count, 2)
            with patch.object(stores, "write", side_effect=ConflictError("not updated")) as write:
                with self.assertRaises(ConflictError): flow.session.record(receipt)
                self.assertEqual(write.call_count, 1)
            def uncertain(*args, **kwargs):
                original(*args, **kwargs)
                raise StoreError("Write outcome unknown")
            with patch.object(stores, "write", side_effect=uncertain) as write:
                with self.assertRaises(StoreError): flow.session.record(receipt)
                self.assertEqual(write.call_count, 1)
            self.assertEqual(flow.audit()["pending"], [])
            with self.assertRaises(ValueError): flow.session.record(receipt)

    def test_cloud_read_denial_and_team_readonly_permissions_are_preserved(self):
        with permission_server() as (base, documents):
            def stores(actor):
                return Stores({"format": 1, "profiles": {
                    group: {"driver": "http", "endpoint": base + "/" + group, "token_env": "TRACE_" + actor.upper(), "writable": True}
                    for group in ("private", "team")}})
            alice, bob = stores("alice"), stores("bob")
            private = "store://private/alice/session"; shared = "store://team/alice/session"
            self.bootstrap(private, alice); flow = self.bootstrap(shared, alice)
            before = copy.deepcopy(documents)
            with self.assertRaises(HTTPFailure) as denied:
                Session(private, stores=bob, scope="alice-work").audit()
            self.assertEqual(denied.exception.status, 403)
            self.assertEqual(Session(shared, stores=bob, scope="alice-work").audit()["read"], 1)
            resolved = flow.catalog.resolve(PLUGIN / "references/governance/index.json", "routing-policy")
            with self.assertRaises(HTTPFailure): Session(shared, stores=bob, scope="alice-work").prepare(resolved)
            self.assertEqual(documents, before)
            self.assertEqual(self.bootstrap("store://team/bob/session", bob, scope="bob-work").audit()["read"], 1)

    def test_receipts_use_existing_http_github_supabase_and_confluence_adapters(self):
        from test_document_services import service
        with service() as (config, documents, requests, secret):
            stores = Stores(config)
            for profile in config["profiles"]:
                with self.subTest(profile=profile):
                    trace = "store://" + profile + "/receipts/alice/session"
                    self.bootstrap(trace, stores)
                    session = Session(trace, scope="alice-work", stores=Stores(config))
                    self.assertEqual(session.audit()["read"], 1)
                    self.assertEqual(session.audit()["pending"], [])
                    self.assertNotIn(secret, json.dumps(session.events()))

    def test_context_reuse_metadata_review_and_changed_source_work_in_stored_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); index = fixture(root); stores = Stores(sqlite_config(root / "records.db"))
            flow = self.bootstrap("store://team/receipts/alice", stores)
            result = flow.read(index, "one"); receipt = result["observation"]["receipt"]; resolved = result["reference"]["resolved"]
            flow.session.review_metadata(receipt, resolved)
            self.assertEqual(flow.session.metadata_status(resolved)["status"], "reviewed_observation")
            same = flow.prepare(index, "one")["receipt"]
            flow.session.record(same, status="reused-from-current-context", based_on=receipt)
            other = flow.prepare(index, "two")["receipt"]
            with self.assertRaises(ValueError): flow.session.record(other, status="reused-from-current-context", based_on=receipt)
            flow.session.record(other, status="unavailable", error="Fixture source not read")
            (root / "one.md").write_text("changed private body")
            again = flow.read(index, "one")
            self.assertFalse(again["reference"]["cache_hit"])
            self.assertEqual(flow.session.metadata_status(resolved)["status"], "review_required")
            self.assertEqual(flow.audit()["pending"], [])

    def test_invalid_remote_envelope_and_readonly_profile_never_reset_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stores = Stores(sqlite_config(root / "records.db")); trace = "store://team/receipts/alice"
            stores.write(trace, {"format": 1, "entries": []}, expected_revision=None)
            before = stores.read(trace)["revision"]
            with self.assertRaisesRegex(ValueError, "trace document"):
                self.bootstrap(trace, stores)
            self.assertEqual(stores.read(trace)["revision"], before)
            trace = "store://team/receipts/correct"; flow = self.bootstrap(trace, stores)
            readonly = Stores(sqlite_config(root / "records.db", writable=False))
            session = Session(trace, stores=readonly, scope="alice-work")
            self.assertTrue(session.audit()["valid"])
            with self.assertRaises(PermissionError): session.prepare(flow.catalog.resolve(PLUGIN / "references/governance/index.json", "routing-policy"))

    def test_deleted_trace_cannot_recreate_unbootstrapped_source_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); index = fixture(root); database = root / "records.db"
            stores = Stores(sqlite_config(database)); flow = self.bootstrap("store://team/receipts/alice", stores)
            original = flow.session.storage.append
            def remove_before_append(create_records):
                with sqlite3.connect(database) as db: db.execute("DELETE FROM reference_documents WHERE key = ?", ("receipts/alice",))
                return original(create_records)
            with patch.object(flow.session.storage, "append", side_effect=remove_before_append):
                with self.assertRaisesRegex(ValueError, "governing routing source"):
                    flow.prepare(index, "one")
            self.assertEqual(flow.session.events(), [])

    def test_readonly_http_trace_without_revision_can_be_audited_but_not_appended(self):
        from test_document_services import service
        with service() as (config, documents, _, __):
            records = [{"event": "session", "format": 2, "scope": "alice-work"}]
            documents[("http", "without-etag")] = {"document": {"format": 1, "records": records}, "revision": 1, "etag": '"unused"'}
            session = Session("store://http/without-etag", scope="alice-work", stores=Stores(config))
            self.assertTrue(session.audit()["valid"])
            with self.assertRaisesRegex(ValueError, "conditional-write"):
                session.record("unknown")
            self.assertEqual(session.events(), records)

    def test_export_is_explicit_frozen_jsonl_and_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stores = Stores(sqlite_config(root / "records.db")); trace = "store://team/receipts/alice"
            flow = self.bootstrap(trace, stores); snapshot = flow.session.snapshot()
            output = root / "evidence.jsonl"; result = export_snapshot(snapshot, output)
            self.assertEqual(result["trace"], trace)
            self.assertEqual(result["revision"], snapshot["revision"])
            self.assertEqual(result["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
            records = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertTrue(audit_records(records)["valid"])
            with self.assertRaises(FileExistsError): export_snapshot(snapshot, output)
            flow.read(PLUGIN / "references/governance/index.json", "routing-policy")
            self.assertEqual(len(records), len(snapshot["records"]))
            self.assertLess(len(records), len(flow.session.events()))

    def test_cli_uses_remote_trace_for_source_connections_record_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); index = fixture(root); config = root / "stores.json"
            config.write_text(json.dumps(sqlite_config(root / "records.db")))
            trace = "store://team/receipts/alice"; flags = ["--store-config", str(config), "--trace", trace, "--scope", "alice-work"]
            def run(tool, *args):
                result = subprocess.run([sys.executable, str(PLUGIN / "scripts" / tool), *args], cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)
            run("references.py", "read", "--index", str(PLUGIN / "references/governance/index.json"), "--id", "routing-policy", *flags)
            run("sources.py", "init", "--state", "store://team/project", "--store-config", str(config))
            run("sources.py", "select", "--state", "store://team/project", "--store-config", str(config), "--intent", "knowledge", "--mode", "custom", "--index", str(index))
            read = run("sources.py", "read", "--state", "store://team/project", "--intent", "knowledge", "--id", "one", "--source-root", str(root), *flags)
            self.assertEqual(read["content"], "private body one")
            pending = run("references.py", "prepare-read", "--index", str(index), "--id", "two", *flags)
            run("references.py", "record", "--receipt", pending["receipt"], "--status", "unavailable", "--error", "Fixture observation", *flags)
            audit = run("references.py", "audit", *flags)
            self.assertEqual(audit["pending"], [])
            self.assertEqual(audit["read"], 2)
            self.assertEqual(audit["unavailable"], 1)
            snapshot = run("references.py", "trace-show", *flags)
            self.assertEqual(snapshot["trace"], trace)
            self.assertTrue(snapshot["revision"])
            self.assertFalse(list(root.rglob("*.jsonl")))
            run("references.py", "trace-export", "--output", str(root / "export.jsonl"), *flags)
            self.assertEqual(len(list(root.rglob("*.jsonl"))), 1)


if __name__ == "__main__":
    unittest.main()
