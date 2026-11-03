import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import shutil
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate import validate

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/project-builder"
sys.path.insert(0, str(PLUGIN / "scripts"))
from reference_catalog import Catalog
from reference_io import load_index
from reference_registry import change
from reference_session import audit_records
from reference_workflow import Workflow



class ReferenceRoutingTest(unittest.TestCase):
    def test_source_links_cannot_bypass_reference_indexes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(PLUGIN, root / "plugins/project-builder",ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
            shutil.copytree(ROOT / ".agents", root / ".agents")
            source = root / "plugins/project-builder/sources/reference-entry.md"
            original = source.read_text()
            for link in ("https://example.com/source", "source-contract.md"):
                with self.subTest(link=link):
                    source.write_text(original + f"\n[Direct source]({link})\n")
                    with self.assertRaisesRegex(AssertionError, "return through a reference"):
                        validate(root)
            source.write_text(original + "\n[Relevant references](../references/usage/index.json)\n")
            self.assertEqual(validate(root)[0], 1)

    def test_git_index_rejects_custom_content_even_when_worktree_copy_is_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(PLUGIN, root / "plugins/project-builder",ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
            shutil.copytree(ROOT / ".agents", root / ".agents")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            source = root / ".local/consumer.txt"
            source.parent.mkdir()
            source.write_text("local-only sentinel")
            subprocess.run(["git", "add", ".local/consumer.txt"], cwd=root, check=True)
            source.unlink()
            with self.assertRaisesRegex(AssertionError, "Git index"):
                validate(root)

    def test_publication_inventory_requires_review_of_new_public_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(PLUGIN, root / "plugins/project-builder",ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
            shutil.copytree(ROOT / ".agents", root / ".agents")
            (root / ".gitignore").write_text(".local/\n")
            approved = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
            approved.append("publication-files.json")
            (root / "publication-files.json").write_text(json.dumps(approved))
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            candidate = root / "new-case.txt"
            candidate.write_text("unreviewed task-specific input")
            with self.assertRaisesRegex(AssertionError, "Unreviewed public files"):
                validate(root)
            candidate.unlink()
            self.assertEqual(validate(root)[0], 1)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            candidate.write_text("new candidate")
            subprocess.run(["git", "add", "new-case.txt"], cwd=root, check=True)
            (root / "publication-files.json").write_text(json.dumps([*approved, "new-case.txt"]))
            with self.assertRaisesRegex(AssertionError, "Stage the reviewed publication inventory"):
                validate(root)

    def bootstrap(self, trace):
        workflow = Workflow(trace)
        workflow.read(PLUGIN / "references/governance/index.json", "routing-policy")
        return workflow

    def test_horizontal_sources_have_independent_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            flow = self.bootstrap(Path(temp) / "trace.jsonl")
            flow.read(PLUGIN / "references/usage/index.json", "entry")
            flow.read(PLUGIN / "references/usage/index.json", "source-contract")
            report = flow.audit()
            self.assertEqual(report["source_accesses"], 3)
            self.assertTrue(report["current_policy_read"])
            self.assertEqual(report["pending"], [])

    def test_source_without_reference_and_receipt_reuse_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            flow = self.bootstrap(Path(temp) / "trace.jsonl")
            history = flow.session.events()
            with self.assertRaises(ValueError):
                flow.session.record(history[-1]["receipt"])
            with self.assertRaises(ValueError):
                flow.session.record("not-issued")
            with self.assertRaises(ValueError):
                audit_records([*history, history[-1]])

    def test_governance_is_an_execution_requirement_not_a_discovery_requirement(self):
        with tempfile.TemporaryDirectory() as temp:
            trace = Path(temp) / "trace.jsonl"
            index = PLUGIN / "references/usage/index.json"
            resolved = Catalog(load_index).resolve(index, "entry")
            self.assertEqual(resolved["kind"], "source")
            self.assertFalse(trace.exists())
            with self.assertRaisesRegex(ValueError, "governing"):
                Workflow(trace).read(index, "entry")
            self.assertFalse(trace.exists())

    def test_reference_metadata_rejects_copied_source_and_authoritative_values(self):
        base = {"format": 1, "entries": [{"id": "x", "label": "x", "kind": "source", "access": "file", "locator": "x.md", "topics": []}]}
        for field in ("body", "content", "rules", "owner", "version"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                data = json.loads(json.dumps(base)); data["entries"][0][field] = "copied value"
                path = Path(temp) / "index.json"; path.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError, "metadata only"):
                    Catalog(load_index).read_index(path)

    def test_trace_never_contains_read_source_body(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); flow = self.bootstrap(root / "trace.jsonl")
            (root / "source.md").write_text("unique-private-body-sentinel")
            index = root / "index.json"; index.write_text('{"format":1,"entries":[]}')
            change(index, "sample", operation="add", entry={"id":"sample","label":"sample","kind":"source","access":"file","locator":"source.md","topics":["test"]})
            self.assertEqual(flow.read(index, "sample")["content"], "unique-private-body-sentinel")
            self.assertNotIn("unique-private-body-sentinel", flow.session.path.read_text())

    def test_horizontal_cycles_stop_without_fetching_source_bodies(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, other in (("a", "b"), ("b", "a")):
                (root / f"{name}.json").write_text(json.dumps({"format":1,"entries":[{"id":"next","label":"next","kind":"reference","access":"file","locator":f"{other}.json","topics":[]}]}))
            result = Catalog(load_index).walk([root / "a.json"])
            self.assertTrue(result["complete"])
            self.assertEqual(len(result["indexes"]), 2)

    def test_session_can_be_audited_from_a_moved_identical_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); flow = self.bootstrap(root / "trace.jsonl")
            shutil.copytree(PLUGIN, root / "plugin")
            result = subprocess.run([sys.executable,str(root/"plugin/scripts/references.py"),"audit","--trace",str(flow.session.path)],capture_output=True,text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["current_policy_read"])

    def test_invalid_registration_preserves_existing_registry(self):
        for label, locator in (("x" * 241, "https://example.com/docs"), ("valid label", "not-a-url"), ("valid label", "https://user:secret@example.com/docs")):
            with self.subTest(label_length=len(label), locator=locator), tempfile.TemporaryDirectory() as temp:
                index = Path(temp) / "index.json"; original = '{"format":1,"entries":[]}'
                index.write_text(original)
                with self.assertRaises(ValueError):
                    change(index,"candidate",operation="add",entry={"id":"candidate","label":label,"kind":"source","access":"web","locator":locator,"topics":["test"]})
                self.assertEqual(index.read_text(), original)


if __name__ == "__main__":
    unittest.main()
