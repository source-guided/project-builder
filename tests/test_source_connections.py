from concurrent.futures import ThreadPoolExecutor
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=ROOT/"plugins/project-builder"
sys.path.insert(0,str(PLUGIN/"scripts"))
from source_connections import Connections,offers
from reference_workflow import Workflow
from reference_session import Session


def source(root):
    index=root/"references/index.json";index.parent.mkdir(parents=True)
    body=root/"capabilities/example/SKILL.md";body.parent.mkdir(parents=True)
    body.write_text("source-local-body-sentinel")
    index.write_text(json.dumps({"format":1,"entries":[{"id":"example","label":"Example","kind":"source","access":"relative","locator":"../capabilities/example/SKILL.md","topics":["example"]}]}))
    return index,body


class SourceConnectionsTest(unittest.TestCase):
    def bootstrap(self,trace):
        Workflow(trace).read(PLUGIN/"references/governance/index.json","routing-policy")

    def test_suggestions_do_not_fetch_or_install_default_sources(self):
        with patch("urllib.request.OpenerDirector.open",side_effect=AssertionError("No network permitted")):
            candidates=offers("design")
        self.assertEqual([e["id"] for e in candidates],["design"])
        self.assertEqual(candidates[0]["kind"],"reference")

    def test_general_mode_is_a_persisted_choice_without_hidden_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/"connections.json";connections=Connections(state)
            with self.assertRaisesRegex(ValueError,"ask"):
                connections.selected("skill-authoring")
            connections.select("skill-authoring","general")
            with patch("urllib.request.OpenerDirector.open",side_effect=AssertionError("No fetch")):
                self.assertEqual(connections.discover("skill-authoring")["mode"],"general")
            self.assertEqual(connections.show()["selections"]["skill-authoring"],{"mode":"general"})
            with self.assertRaises(ValueError):connections.access("skill-authoring",Path(tmp)/"trace")
            self.assertEqual([p.name for p in Path(tmp).iterdir()],["connections.json"])

    def test_default_choice_reads_only_on_explicit_source_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);index,body=source(root/"provider")
            catalog=root/"catalog.json";catalog.write_text(json.dumps({"format":1,"entries":[{"id":"test","label":"Test source","kind":"reference","access":"relative","locator":"provider/references/index.json","topics":[]}]}))
            work=root/"consumer";work.mkdir();connections=Connections(work/"connections.json")
            original=Path.read_bytes
            def read(path):
                if path==body:raise AssertionError("Body read before access")
                return original(path)
            with patch.object(Path,"read_bytes",read):
                connections.select("design","default",candidate="test",catalog=catalog)
                discovered=connections.discover("design")
            self.assertEqual(discovered["references"][0]["address"],str(body.resolve()))
            trace=work/"trace.jsonl";self.bootstrap(trace)
            self.assertEqual(connections.access("design",trace,identifier="example")["content"],"source-local-body-sentinel")
            self.assertEqual(list(work.rglob("SKILL.md")),[])
            self.assertNotIn("source-local-body-sentinel",(work/"connections.json").read_text())

    def test_custom_documents_and_connector_locations_do_not_need_an_index_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);doc=root/"policy.md";doc.write_text("custom policy")
            connections=Connections(root/"connections.json");trace=root/"trace.jsonl";self.bootstrap(trace)
            connections.select("authoring","custom",index=str(doc),kind="source")
            self.assertEqual(connections.access("authoring",trace)["content"],"custom policy")
            connections.select("knowledge","custom",index="SPACE:PAGE",access="connector",kind="source")
            request=connections.access("knowledge",trace,prepare_only=True)
            self.assertEqual(request["resolved"]["address"],"SPACE:PAGE")
            self.assertEqual(request["resolved"]["access"],"connector")
            Session(trace).record(request["receipt"],status="unavailable",error="Host adapter unavailable in this fixture")

    def test_independent_direct_sources_can_be_read_concurrently(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);connections=Connections(root/"connections.json");trace=root/"trace.jsonl";self.bootstrap(trace)
            for name in ("one","two"):
                body=root/(name+".md");body.write_text(name);connections.select(name,"custom",index=str(body),kind="source")
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda name:connections.access(name,trace)["content"],["one","two"]))
            self.assertEqual(results,["one","two"])

    def test_nested_reference_uses_observed_index_without_expanding_selected_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);nested,body=source(root/"provider/nested")
            index=root/"provider/index.json"
            index.write_text(json.dumps({"format":1,"entries":[{"id":"nested","label":"Nested","kind":"reference","access":"relative","locator":"nested/references/index.json","topics":[]}]}))
            connections=Connections(root/"choices.json");connections.select("design","custom",index=str(index))
            reference=connections.discover("design")["references"][0]["reference"]
            trace=root/"trace.jsonl";self.bootstrap(trace)
            result=connections.access("design",trace,identifier=reference["id"],reference_index=reference["index"],reference_access=reference["access"])
            self.assertEqual(result["content"],body.read_text())
            outside,_=source(root/"outside")
            with self.assertRaisesRegex(ValueError,"not reachable"):
                connections.access("design",trace,identifier="example",reference_index=outside)
            unrelated,_=source(root/"provider/unlinked")
            with self.assertRaisesRegex(ValueError,"not reachable"):
                connections.access("design",trace,identifier="example",reference_index=unrelated)

    def test_connector_index_uses_host_adapter_and_preserves_source_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);hits=[]
            def reader(address):
                hits.append(address)
                document={"format":1,"entries":[{"id":"policy","label":"Policy","kind":"source","access":"connector","locator":"SPACE:POLICY","topics":["policy"]}]}
                return {"document":document,"digest":hashlib.sha256(json.dumps(document).encode()).hexdigest(),"address":address}
            connections=Connections(root/"choices.json",connector_reader=reader)
            connections.select("knowledge","custom",index="SPACE:INDEX",access="connector")
            self.assertEqual(hits,[])
            reference=connections.discover("knowledge")["references"][0]["reference"]
            trace=root/"trace.jsonl";self.bootstrap(trace)
            request=connections.access("knowledge",trace,identifier=reference["id"],reference_index=reference["index"],reference_access=reference["access"],prepare_only=True)
            self.assertEqual(request["resolved"]["address"],"SPACE:POLICY")
            self.assertEqual(set(hits),{"SPACE:INDEX"})
            self.assertEqual(Session(trace).audit()["pending"],[request["receipt"]])
            unavailable=Connections(root/"choices.json").discover("knowledge")
            self.assertFalse(unavailable["complete"])
            self.assertIn("No host connector",unavailable["errors"][0]["message"])

    def test_choice_replacement_is_explicit_and_conflicts_preserve_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            connections=Connections(Path(tmp)/"choices.json")
            initial=connections.select("design","general")
            with self.assertRaises(ValueError):connections.select("design","default",candidate="design")
            connections.select("work","general")
            with self.assertRaises(ValueError):connections.select("design","default",candidate="design",expected_digest=initial["digest"])
            current=connections.show();connections.select("design","default",candidate="design",expected_digest=current["digest"])
            self.assertEqual(connections.selected("work"),{"mode":"general"})

    def test_one_source_index_works_locally_and_over_http_without_body_prefetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);index,body=source(root/"provider");hits=[]
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    hits.append(self.path)
                    path=root/"provider"/self.path.lstrip("/")
                    if not path.is_file():self.send_response(404);self.end_headers();return
                    self.send_response(200);self.end_headers();self.wfile.write(path.read_bytes())
                def log_message(self,*args):pass
            server=ThreadingHTTPServer(("127.0.0.1",0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                base=f"http://127.0.0.1:{server.server_port}"
                connections=Connections(root/"choices.json");connections.select("remote","custom",index=base+"/references/index.json")
                result=connections.discover("remote");self.assertEqual(hits,["/references/index.json"])
                self.assertEqual(result["references"][0]["access"],"web")
                self.assertEqual(result["references"][0]["address"],base+"/capabilities/example/SKILL.md")
                trace=root/"trace.jsonl";self.bootstrap(trace);request=connections.access("remote",trace,identifier="example",prepare_only=True)
                self.assertNotIn("/capabilities/example/SKILL.md",hits)
                with urlopen(request["resolved"]["address"]) as response:data=response.read()
                Session(trace).record(request["receipt"],digest=hashlib.sha256(data).hexdigest())
                self.assertEqual(data,body.read_bytes())
                self.assertEqual(Workflow(trace).audit()["pending"],[])
            finally:server.shutdown();server.server_close();thread.join(timeout=2)


if __name__=="__main__":unittest.main()
