from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import subprocess
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/project-builder"
sys.path.insert(0, str(PLUGIN / "scripts"))
from reference_catalog import Catalog
from reference_io import load_index
from reference_registry import change
from reference_session import Session
from reference_workflow import Workflow
from reference_http import IndexReader


def entry(identifier, locator, *, kind="source", access="file", description=""):
    return {"id": identifier, "label": identifier, "description": description, "kind": kind,
            "access": access, "locator": locator, "topics": []}


def registry(path, entries):
    path.write_text(json.dumps({"format": 1, "entries": entries}))
    return path


class ReferenceRuntimeTest(unittest.TestCase):
    def setup_flow(self, root):
        flow = Workflow(root / "session.jsonl")
        flow.read(PLUGIN / "references/governance/index.json", "routing-policy")
        for name in ("a", "b"):
            (root / f"{name}.txt").write_text(name)
        index = registry(root / "index.json", [entry("a", "a.txt"), entry("b", "b.txt"), entry("gone", "gone.txt")])
        return flow, index

    def test_independent_receipts_can_finish_in_either_order(self):
        for order in ((0, 1), (1, 0)):
            with self.subTest(order=order), tempfile.TemporaryDirectory() as temp:
                flow, index = self.setup_flow(Path(temp).resolve())
                requests = [flow.prepare(index, name) for name in ("a", "b")]
                for i in order:
                    flow.session.record(requests[i]["receipt"])
                self.assertEqual(flow.audit()["pending"], [])
                self.assertEqual(flow.audit()["read"], 3)

    def test_duplicate_concurrent_completion_is_rejected_atomically(self):
        with tempfile.TemporaryDirectory() as temp:
            flow, index = self.setup_flow(Path(temp).resolve())
            request = flow.prepare(index, "a")
            barrier = threading.Barrier(2)
            def complete(_):
                barrier.wait()
                try:
                    flow.session.record(request["receipt"])
                    return "recorded"
                except ValueError:
                    return "rejected"
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertCountEqual(list(pool.map(complete, range(2))), ["recorded", "rejected"])
            self.assertEqual(flow.audit()["read"], 2)

    def test_receipt_completion_is_serialized_across_cli_processes(self):
        with tempfile.TemporaryDirectory() as temp:
            flow, index = self.setup_flow(Path(temp).resolve())
            receipt = flow.prepare(index, "a")["receipt"]
            command = [sys.executable,str(PLUGIN/"scripts/references.py"),"record","--trace",str(flow.session.path),"--receipt",receipt]
            first = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            second = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            first.communicate(timeout=10); second.communicate(timeout=10)
            self.assertCountEqual([first.returncode, second.returncode], [0, 1])
            self.assertEqual(flow.audit()["read"], 2)

    def test_parallel_reads_preserve_success_when_another_source_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); flow, index = self.setup_flow(root)
            barrier = threading.Barrier(2)
            original = Path.read_bytes
            def synchronized(path):
                if path in {root / "a.txt", root / "b.txt"}:
                    barrier.wait(timeout=3)
                return original(path)
            with patch.object(Path, "read_bytes", synchronized):
                results = flow.read_many([{"index": str(index), "id": name} for name in ("a", "gone", "b")], workers=3)
            self.assertEqual([r["status"] for r in results], ["read", "unavailable", "read"])
            self.assertEqual(flow.audit()["unavailable"], 1)
            self.assertEqual(flow.audit()["pending"], [])

    def test_metadata_cache_does_not_cache_source_body_and_invalidates_on_registry_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); flow, index = self.setup_flow(root)
            flow.read(index, "a")
            (root / "a.txt").write_text("new body")
            with patch.object(flow.catalog, "resolve", wraps=flow.catalog.resolve) as resolve:
                result = flow.read(index, "a")
                self.assertTrue(result["reference"]["cache_hit"])
                self.assertEqual(result["content"], "new body")
                self.assertEqual(resolve.call_count, 0)
                change(index, "a", operation="update", patch={"description": "Updated discovery cue"}, expected_digest=load_index(index)["digest"])
                result = flow.read(index, "a")
                self.assertFalse(result["reference"]["cache_hit"])
                self.assertEqual(resolve.call_count, 1)

    def test_cached_metadata_rebinds_retargeted_and_broken_source_links(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); flow, index = self.setup_flow(root)
            link = root / "current.txt"; link.symlink_to(root / "a.txt")
            change(index, "a", operation="update", patch={"locator": "current.txt"}, expected_digest=load_index(index)["digest"])
            first = flow.read(index, "a")
            flow.session.review_metadata(first["observation"]["receipt"], first["reference"]["resolved"])
            link.unlink(); link.symlink_to(root / "b.txt")
            second = flow.read(index, "a")
            self.assertTrue(second["reference"]["cache_hit"])
            self.assertEqual(second["content"], (root / "b.txt").read_text())
            self.assertEqual(flow.session.metadata_status(second["reference"]["resolved"])["status"], "review_required")
            link.unlink(); link.symlink_to(root / "missing.txt")
            with self.assertRaises(FileNotFoundError):
                flow.read(index, "a")
            self.assertEqual(flow.audit()["unavailable"], 1)

    def test_file_uri_management_uses_the_same_address_contract_as_reads(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); flow, index = self.setup_flow(root)
            target = root / "source 한 글.txt"; target.write_text("source content")
            change(index, "uri", operation="add", entry=entry("uri", target.as_uri()))
            self.assertEqual(flow.read(index, "uri")["content"], "source content")
            change(index, "uri", operation="update", patch={"description":"Updated cue"}, expected_digest=load_index(index)["digest"])
            read = flow.read(index, "uri")
            flow.session.review_metadata(read["observation"]["receipt"], read["reference"]["resolved"])
            self.assertEqual(flow.session.metadata_status(read["reference"]["resolved"])["status"], "reviewed_observation")
            change(index, "uri", operation="remove", expected_digest=load_index(index)["digest"])

    def test_session_scope_cannot_be_reused_as_another_access_context(self):
        with tempfile.TemporaryDirectory() as temp:
            flow, index = self.setup_flow(Path(temp).resolve())
            flow.read(index, "a")
            with self.assertRaisesRegex(ValueError, "scope changed"):
                Session(flow.session.path, scope="another-account").events()

    def test_context_reuse_is_bound_to_a_prior_actual_read(self):
        with tempfile.TemporaryDirectory() as temp:
            flow, index = self.setup_flow(Path(temp).resolve())
            original = flow.read(index, "a")["observation"]["receipt"]
            same = flow.prepare(index, "a")
            flow.session.record(same["receipt"], status="reused-from-current-context", based_on=original)
            other = flow.prepare(index, "b")
            with self.assertRaises(ValueError):
                flow.session.record(other["receipt"], status="reused-from-current-context", based_on=original)
            self.assertEqual(flow.audit()["reused"], 1)

    def test_changed_source_requires_new_metadata_review_without_copying_its_body(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); flow, index = self.setup_flow(root)
            receipt = flow.read(index, "a")["observation"]["receipt"]
            resolved = flow.catalog.resolve(index, "a")
            flow.session.review_metadata(receipt, resolved)
            self.assertEqual(flow.session.metadata_status(resolved)["status"], "reviewed_observation")
            (root / "a.txt").write_text("changed-source-private-sentinel")
            new_receipt = flow.read(index, "a")["observation"]["receipt"]
            self.assertEqual(flow.session.metadata_status(resolved)["status"], "review_required")
            change(index, "a", operation="update", patch={"description": "New source purpose"}, expected_digest=load_index(index)["digest"])
            resolved = flow.catalog.resolve(index, "a")
            flow.session.review_metadata(new_receipt, resolved)
            self.assertEqual(flow.session.metadata_status(resolved)["status"], "reviewed_observation")
            self.assertNotIn("changed-source-private-sentinel", flow.session.path.read_text())

    def test_registry_update_move_remove_and_conflict_preserve_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); flow, index = self.setup_flow(root)
            previous = load_index(index)["digest"]
            result = change(index, "a", operation="update", patch={"locator": "b.txt", "description": "Moved purpose"}, expected_digest=previous)
            self.assertEqual(Catalog(load_index).resolve(index, "a")["address"], str(root / "b.txt"))
            with self.assertRaisesRegex(ValueError, "changed since inspection"):
                change(index, "a", operation="remove", expected_digest=previous)
            change(index, "a", operation="remove", expected_digest=result["index_digest"])
            with self.assertRaises(ValueError):
                Catalog(load_index).resolve(index, "a")

    def test_two_registry_writers_do_not_overwrite_each_other(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); _, index = self.setup_flow(root)
            revision = load_index(index)["digest"]
            barrier = threading.Barrier(2)
            def update(label):
                barrier.wait()
                try:
                    change(index, "a", operation="update", patch={"label": label}, expected_digest=revision)
                    return "updated"
                except ValueError:
                    return "conflict"
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertCountEqual(list(pool.map(update, ["one", "two"])), ["updated", "conflict"])


class DiscoveryTest(unittest.TestCase):
    def test_malformed_roots_do_not_abort_healthy_discovery(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();index=registry(root/"index.json",[entry("healthy","source.md",description="Policy")])
            roots=["http://[",str(index)]
            result=Catalog(IndexReader(roots)).discover(roots,"policy")
            self.assertEqual(result["references"][0]["reference"]["id"],"healthy")
            self.assertEqual(len(result["errors"]),1)
            command=[sys.executable,str(PLUGIN/"scripts/references.py"),"discover","--index",*roots,"--query","policy"]
            process=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(process.returncode,0,process.stderr)
            self.assertEqual(json.loads(process.stdout)["references"][0]["reference"]["id"],"healthy")

    def test_http_metadata_cannot_grant_implicit_local_index_access(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();private=registry(root/"private.json",[entry("local-only","source.md",description="Policy")])
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    body=json.dumps({"format":1,"entries":[entry("local",private.as_uri(),kind="reference",access="file")]}).encode()
                    self.send_response(200);self.end_headers();self.wfile.write(body)
                def log_message(self,*args):pass
            server=ThreadingHTTPServer(("127.0.0.1",0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                remote=f"http://127.0.0.1:{server.server_port}/index.json"
                result=Catalog(IndexReader([remote])).discover([remote],"policy")
                self.assertEqual(result["references"],[])
                self.assertEqual(result["errors"][0]["type"],"PermissionError")
                roots=[remote,str(private)]
                result=Catalog(IndexReader(roots)).discover(roots,"policy")
                self.assertTrue(result["complete"])
                self.assertEqual([r["reference"]["id"] for r in result["references"]],["local-only"])
            finally:
                server.shutdown();server.server_close();thread.join(timeout=2)

    def test_remote_index_cannot_grant_implicit_local_body_access(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();body=root/"private.txt";body.write_text("synthetic-private-body")
            trace=root/"session.jsonl";Workflow(trace).read(PLUGIN/"references/governance/index.json","routing-policy")
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    payload=json.dumps({"format":1,"entries":[entry("body",body.as_uri(),access="file")]}).encode()
                    self.send_response(200);self.end_headers();self.wfile.write(payload)
                def log_message(self,*args):pass
            server=ThreadingHTTPServer(("127.0.0.1",0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                remote=f"http://127.0.0.1:{server.server_port}/index.json"
                command=[sys.executable,str(PLUGIN/"scripts/references.py"),"read","--index",remote,"--id","body","--trace",str(trace)]
                denied=subprocess.run(command,capture_output=True,text=True)
                self.assertNotEqual(denied.returncode,0)
                self.assertNotIn("synthetic-private-body",denied.stdout+denied.stderr)
                allowed=subprocess.run(command+["--source-root",str(root)],capture_output=True,text=True)
                self.assertEqual(allowed.returncode,0,allowed.stderr)
                self.assertEqual(json.loads(allowed.stdout)["content"],"synthetic-private-body")
                denied_again=subprocess.run(command,capture_output=True,text=True)
                self.assertNotEqual(denied_again.returncode,0)
            finally:
                server.shutdown();server.server_close();thread.join(timeout=2)

    def test_visually_identical_unicode_metadata_is_discoverable(self):
        with tempfile.TemporaryDirectory() as temp:
            index = registry(Path(temp)/"index.json",[entry("policy","policy.md",description=unicodedata.normalize("NFD","결제 승인 정책"))])
            result = Catalog(load_index).discover([index],"결제 승인")
            self.assertEqual(result["references"][0]["reference"]["id"],"policy")

    def test_http_catalogs_return_partial_results_without_fetching_source_bodies(self):
        hits = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                if self.path == "/denied.json":
                    self.send_response(403); self.end_headers(); return
                if self.path == "/redirect.json":
                    self.send_response(302); self.send_header("Location", "http://example.invalid/private.json"); self.end_headers(); return
                body = json.dumps({"format":1,"entries":[entry("policy",f"http://127.0.0.1:{self.server.server_port}/never-read",access="web",description="Service policy")]}).encode()
                self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(body)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1",0),Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            roots = [base+"/catalog.json",base+"/denied.json",base+"/redirect.json"]
            result = Catalog(IndexReader(roots)).discover(roots,"policy")
            self.assertEqual(len(result["references"]),1)
            self.assertEqual(len(result["errors"]),2)
            self.assertFalse(result["complete"])
            self.assertNotIn("/never-read",hits)
            with self.assertRaisesRegex(ValueError,"not explicitly"):
                IndexReader([])(base+"/catalog.json")
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)

    def test_truncated_http_response_isolated_and_redirect_uses_final_base(self):
        hits=[]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                base=f"http://127.0.0.1:{self.server.server_port}"
                if self.path=="/broken.json":
                    self.send_response(200);self.send_header("Transfer-Encoding","chunked");self.end_headers();self.wfile.write(b"10\r\nabc");self.close_connection=True;return
                if self.path=="/old/index.json":
                    self.send_response(302);self.send_header("Location",base+"/new/index.json");self.end_headers();return
                if self.path=="/new/index.json":
                    entries=[{**entry("root",base+"/source",access="web"),"related_references":["child.json"]}]
                elif self.path=="/new/child.json":
                    entries=[entry("child",base+"/child-source",access="web",description="Policy document")]
                else:
                    self.send_response(404);self.end_headers();return
                body=json.dumps({"format":1,"entries":entries}).encode();self.send_response(200);self.end_headers();self.wfile.write(body)
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            base=f"http://127.0.0.1:{server.server_port}";roots=[base+"/broken.json",base+"/old/index.json"]
            result=Catalog(IndexReader(roots)).discover(roots,"policy")
            self.assertEqual([r["reference"]["id"] for r in result["references"]],["child"])
            self.assertEqual(len(result["errors"]),1)
            self.assertIn("/new/child.json",hits)
            self.assertNotIn("/old/child.json",hits)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)

    def test_connector_identifiers_stay_opaque_and_do_not_use_file_adapter(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve()
            child=registry(root/"child.json",[entry("local-only","body.md")])
            index=registry(root/"index.json",[entry("ticket","TASK-17",access="connector"),entry("child","child.json",kind="reference",access="connector")])
            catalog=Catalog(load_index)
            self.assertEqual(catalog.resolve(index,"ticket")["address"],"TASK-17")
            result=catalog.walk([index])
            self.assertEqual(len(result["indexes"]),1)
            self.assertEqual(result["errors"][0]["access"],"connector")
            calls=[]
            def connector(identifier):
                calls.append(identifier)
                return {"document":{"format":1,"entries":[entry("remote","ITEM-8",access="connector")]},"digest":"remote-index"}
            result=Catalog(load_index,connector_reader=connector).discover([index],"remote")
            self.assertEqual(calls,["child.json"])
            self.assertEqual(result["references"][0]["address"],"ITEM-8")
            self.assertEqual(result["references"][0]["reference"]["access"],"connector")

    def test_unavailable_branch_returns_healthy_results(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            registry(root / "good.json", [entry("policy", "body.md", description="Payment retry policy")])
            main = registry(root / "main.json", [entry("missing", "missing.json", kind="reference"), entry("good", "good.json", kind="reference")])
            result = Catalog(load_index).discover([main], "payment retry")
            self.assertEqual(result["references"][0]["reference"]["id"], "policy")
            self.assertEqual(result["references"][0]["relevance"]["matched_terms"], ["payment", "retry"])
            self.assertEqual(len(result["errors"]), 1)
            self.assertFalse(result["complete"])
            self.assertFalse((root / "body.md").exists())

    def test_injected_provider_resolves_remote_index_edges_without_local_path_coercion(self):
        data = {
            "https://refs.example/root.json": {"format":1,"entries":[{**entry("documentation","https://docs.example/guide",access="web"),"related_references":["nested/child.json"]}]},
            "https://refs.example/nested/child.json": {"format":1,"entries":[entry("ticket","jira://TASK-1",access="connector",description="Approval decision")]},
        }
        calls = []
        def provider(location):
            calls.append(location)
            document = data[location]
            return {"document": copy.deepcopy(document), "digest": hashlib.sha256(json.dumps(document).encode()).hexdigest()}
        result = Catalog(provider).discover(["https://refs.example/root.json"], "approval")
        self.assertTrue(result["complete"])
        self.assertEqual(result["references"][0]["address"], "jira://TASK-1")
        self.assertEqual(set(calls), set(data))

    def test_discovery_budget_and_partial_failure_are_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            first = registry(root / "a.json", [entry("next", "b.json", kind="reference")])
            registry(root / "b.json", [entry("target", "never-read.txt")])
            result = Catalog(load_index).walk([first], max_indexes=1)
            self.assertFalse(result["complete"])
            self.assertEqual(result["pending"], [{"index": str(root / "b.json"), "access": "file"}])
            self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
