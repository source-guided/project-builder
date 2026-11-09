from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/project-builder"
sys.path.insert(0, str(PLUGIN / "scripts"))
from document_local import FileStore, SQLiteStore
from document_store import ConflictError, MissingDocument
from document_stores import Stores, load_config, store_location
from reference_registry import change, initialize
from reference_workflow import Workflow
from source_connections import Connections


def entry(identifier, location="https://example.com/policy"):
    return {"id": identifier, "label": identifier, "kind": "source", "access": "web", "locator": location, "topics": ["policy"]}


class DocumentStoreTest(unittest.TestCase):
    def test_file_and_sqlite_support_create_read_update_without_overwriting_stale_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for store, key in ((FileStore(), root / "arbitrary-folder/refs.json"), (SQLiteStore(root / "local.db"), "team/refs")):
                with self.subTest(store=type(store).__name__):
                    with self.assertRaises(MissingDocument):
                        store.read(key)
                    first = store.write(key, {"value": 1}, expected_revision=None)
                    with self.assertRaises(ConflictError):
                        store.write(key, {"value": 99}, expected_revision=None)
                    second = store.write(key, {"value": 2}, expected_revision=first["revision"])
                    with self.assertRaises(ConflictError):
                        store.write(key, {"value": 99}, expected_revision=first["revision"])
                    self.assertEqual(store.read(key)["document"], {"value": 2})
                    self.assertNotEqual(first["revision"], second["revision"])

    def test_two_sqlite_clients_cannot_overwrite_each_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shared.db"
            version = SQLiteStore(path).write("refs", {"label": "initial"}, expected_revision=None)["revision"]
            barrier = threading.Barrier(2)
            def write(label):
                barrier.wait()
                try:
                    SQLiteStore(path).write("refs", {"label": label}, expected_revision=version)
                    return "written"
                except ConflictError:
                    return "conflict"
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertCountEqual(list(pool.map(write, ["first", "second"])), ["written", "conflict"])

    def test_registry_and_connection_state_persist_in_db_without_json_side_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {"format": 1, "profiles": {"team": {"driver": "sqlite", "path": str(root / "team.db"), "writable": True}}}
            stores = Stores(config)
            initialize("store://team/references", stores=stores)
            first = change("store://team/references", "policy", operation="add", entry=entry("policy"), stores=stores)
            connections = Connections("store://team/project", stores=stores)
            with self.assertRaises(MissingDocument):
                connections.show()
            connections.initialize()
            connections.select("design", "custom", index="store://team/references", access="connector")
            connections.select("authoring", "general")
            second_client = Connections("store://team/project", stores=Stores(config))
            self.assertEqual(second_client.selected("authoring"), {"mode": "general"})
            found = second_client.discover("design")
            self.assertTrue(found["complete"])
            self.assertEqual(found["references"][0]["address"], "https://example.com/policy")
            changed = change("store://team/references", "policy", operation="update", patch={"label": "New"}, expected_digest=first["index_digest"], stores=stores)
            with self.assertRaises(ValueError):
                change("store://team/references", "policy", operation="remove", expected_digest=first["index_digest"], stores=stores)
            change("store://team/references", "policy", operation="remove", expected_digest=changed["index_digest"], stores=stores)
            self.assertEqual(second_client.discover("design")["references"], [])
            self.assertEqual([p.name for p in root.iterdir()], ["team.db"])

    def test_shared_connection_does_not_grant_local_file_or_index_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); body = root / "policy.md"; body.write_text("local only")
            index = root / "index.json"; index.write_text(json.dumps({"format": 1, "entries": [{**entry("local"), "access": "file", "locator": str(body)}]}))
            stores = Stores({"format": 1, "profiles": {"team": {"driver": "sqlite", "path": str(root / "team.db"), "writable": True}}})
            connections = Connections("store://team/project", stores=stores); connections.initialize()
            connections.select("document", "custom", index=str(body), kind="source")
            connections.select("index", "custom", index=str(index), kind="reference")
            trace = root / "trace.jsonl"; Workflow(trace).read(PLUGIN / "references/governance/index.json", "routing-policy")
            for intent in ("document", "index"):
                with self.assertRaises(PermissionError): connections.discover(intent)
                with self.assertRaises(PermissionError): connections.access(intent, trace, identifier="local" if intent=="index" else None)
            self.assertEqual(connections.access("document", trace, source_roots=[root])["content"], "local only")
            self.assertEqual(connections.access("index", trace, identifier="local", source_roots=[root])["content"], "local only")

    def test_remote_direct_document_uses_virtual_metadata_without_local_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stores = Stores({"format": 1, "profiles": {"team": {"driver": "sqlite", "path": str(root / "state.db"), "writable": True}}})
            connections = Connections("store://team/project", stores=stores); connections.initialize()
            connections.select("design", "custom", index="https://example.com/design", kind="source")
            trace = root / "trace.jsonl"; Workflow(trace).read(PLUGIN / "references/governance/index.json", "routing-policy")
            request = connections.access("design", trace, prepare_only=True)
            self.assertEqual(request["resolved"]["address"], "https://example.com/design")
            self.assertEqual(request["resolved"]["reference"]["access"], "connector")
            self.assertFalse(any(root.glob("*.references")))

    def test_shared_local_index_keeps_source_grant_through_nested_and_cached_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); allowed = root / "allowed"; allowed.mkdir()
            outside = root / "outside.md"; outside.write_text("outside grant")
            inside = allowed / "inside.md"; inside.write_text("inside grant")
            linked = allowed / "linked.md"; linked.symlink_to(inside)
            nested = allowed / "nested"; nested.mkdir()
            index = allowed / "index.json"; child = nested / "index.json"
            index.write_text(json.dumps({"format": 1, "entries": [
                {**entry("nested"), "kind": "reference", "access": "relative", "locator": "nested/index.json"}]}))
            child.write_text(json.dumps({"format": 1, "entries": [
                {**entry("outside"), "access": "relative", "locator": "../../outside.md"},
                {**entry("linked"), "access": "file", "locator": str(linked)}]}))
            stores = Stores({"format": 1, "profiles": {"team": {"driver": "sqlite", "path": str(root / "state.db"), "writable": True}}})
            connections = Connections("store://team/project", stores=stores); connections.initialize()
            connections.select("work", "custom", index=str(index))
            trace = root / "trace.jsonl"; flow = Workflow(trace)
            flow.read(PLUGIN / "references/governance/index.json", "routing-policy")
            options = {"reference_index": str(child), "source_roots": [allowed]}
            self.assertEqual(connections.access("work", trace, identifier="linked", **options)["content"], "inside grant")
            before = flow.session.events()
            for prepare_only in (False, True):
                with self.subTest(prepare_only=prepare_only), self.assertRaises(PermissionError):
                    connections.access("work", trace, identifier="outside", prepare_only=prepare_only, **options)
            linked.unlink(); linked.symlink_to(outside)
            with self.assertRaises(PermissionError):
                connections.access("work", trace, identifier="linked", **options)
            self.assertEqual(flow.session.events(), before)
            # 명시적으로 넓힌 범위만 허용하며 공유 상태 자체는 권한을 확장하지 않는다.
            self.assertEqual(connections.access("work", trace, identifier="outside", reference_index=str(child), source_roots=[root])["content"], "outside grant")

    def test_read_only_profile_and_unselected_profile_do_not_grant_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "store.db")
            config = {"format": 1, "profiles": {name: {"driver": "sqlite", "path": path, "writable": True} for name in ("team", "personal")}}
            stores = Stores(config)
            stores.write("store://personal/private", {"format": 1, "entries": [entry("secret-location")]}, expected_revision=None)
            stores.write("store://team/registry", {"format": 1, "entries": [{**entry("other"), "kind": "reference", "access": "connector", "locator": "store://personal/private"}]}, expected_revision=None)
            graph = stores.catalog(["store://team/registry"]).walk(["store://team/registry"])
            self.assertFalse(graph["complete"])
            self.assertEqual(graph["errors"][0]["type"], "PermissionError")
            config["profiles"]["team"]["writable"] = False
            readonly = Stores(config)
            self.assertEqual(readonly.read("store://team/registry")["document"]["format"], 1)
            with self.assertRaises(PermissionError): readonly.write("store://team/new", {}, expected_revision=None)

    def test_invalid_profile_and_traversal_keys_fail_before_io(self):
        for address in ("store://team/../secret", "store://team/%2e%2e/secret", "store://team/refs?token=secret", "store://user:secret@team/refs", "store://team/a//b"):
            with self.subTest(address=address), self.assertRaises(ValueError): store_location(address)
        for profile in ({"driver": "http", "endpoint": "https://example.com", "token": "not-allowed"}, {"driver": "sqlite"}, {"driver": "http", "endpoint": "https://example.com", "writable": "true"}):
            with self.subTest(profile=profile), self.assertRaises(ValueError): Stores({"format": 1, "profiles": {"team": profile}})

    def test_invalid_store_root_preserves_healthy_discovery_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.json"
            index.write_text(json.dumps({"format": 1, "entries": [entry("healthy")]}))
            roots = ["store://team/../invalid", str(index)]
            found = Stores().catalog(roots).discover(roots)
            self.assertFalse(found["complete"])
            self.assertEqual(found["references"][0]["reference"]["id"], "healthy")
            self.assertEqual(len(found["errors"]), 1)

    def test_file_and_file_uri_reject_symlink_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); target = root / "target.json"; target.write_text('{"format":1,"selections":{}}')
            linked = root / "linked.json"; linked.symlink_to(target)
            for path in (str(linked), linked.as_uri()):
                with self.assertRaisesRegex(ValueError, "symlink"): Connections(path).show()

    def test_host_adapter_is_explicit_and_uses_the_same_document_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {"format": 1, "profiles": {"custom": {"driver": "host", "writable": True}}}
            with self.assertRaisesRegex(ValueError, "authorized host adapter"):
                Stores(config).read("store://custom/refs")
            stores = Stores(config, adapters={"custom": SQLiteStore(Path(tmp) / "host.db")})
            initialize("store://custom/refs", stores=stores)
            change("store://custom/refs", "policy", operation="add", entry=entry("policy"), stores=stores)
            self.assertEqual(stores.catalog(["store://custom/refs"]).discover(["store://custom/refs"])["references"][0]["reference"]["id"], "policy")

    def test_cli_uses_configured_db_for_registry_and_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); config = root / "stores.json"
            config.write_text(json.dumps({"format": 1, "profiles": {"team": {"driver": "sqlite", "path": "team.db", "writable": True}}}))
            self.assertEqual(load_config(config)["profiles"]["team"]["path"], str((root / "team.db").resolve()))
            def run(tool, *args):
                result = subprocess.run([sys.executable, str(PLUGIN / "scripts" / tool), *args, "--store-config", str(config)], cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)
            run("references.py", "init", "--index", "store://team/refs")
            run("references.py", "add", "--index", "store://team/refs", "--id", "policy", "--label", "Policy", "--access", "web", "--locator", "https://example.com/policy")
            self.assertTrue(run("references.py", "list", "--index", "store://team/refs")["index_revision"])
            run("sources.py", "init", "--state", "store://team/project")
            run("sources.py", "select", "--state", "store://team/project", "--intent", "design", "--mode", "custom", "--index", "store://team/refs", "--access", "connector")
            self.assertTrue(run("sources.py", "discover", "--state", "store://team/project", "--intent", "design")["complete"])
            self.assertFalse((root / ".local").exists())


if __name__ == "__main__":
    unittest.main()
