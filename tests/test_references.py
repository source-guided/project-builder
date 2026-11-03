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
PLUGIN = ROOT / "plugins/product-builder"
spec = importlib.util.spec_from_file_location("reference_routes", PLUGIN / "scripts/references.py")
routes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routes)


class ReferenceRoutingTest(unittest.TestCase):
    def test_source_links_cannot_bypass_reference_indexes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(PLUGIN, root / "plugins/product-builder")
            shutil.copytree(ROOT / ".agents", root / ".agents")
            source = root / "plugins/product-builder/skills/product-ux/sources/workflow.md"
            original = source.read_text()
            for link in ("https://example.com/source", "feedback-and-actions.md"):
                with self.subTest(link=link):
                    source.write_text(original + f"\n[Direct source]({link})\n")
                    with self.assertRaisesRegex(AssertionError, "return through a reference"):
                        validate(root)
            source.write_text(original + "\n[Relevant references](../../../references/design/ux/index.json)\n")
            self.assertEqual(validate(root)[0], 5)

    def test_git_index_rejects_custom_content_even_when_worktree_copy_is_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(PLUGIN, root / "plugins/product-builder")
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
            shutil.copytree(PLUGIN, root / "plugins/product-builder")
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
            self.assertEqual(validate(root)[0], 5)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            candidate.write_text("new candidate")
            subprocess.run(["git", "add", "new-case.txt"], cwd=root, check=True)
            (root / "publication-files.json").write_text(json.dumps([*approved, "new-case.txt"]))
            with self.assertRaisesRegex(AssertionError, "Stage the reviewed publication inventory"):
                validate(root)

    def bootstrap(self, trace):
        routes.read_source(PLUGIN / "references/governance/index.json", "routing-policy", trace)

    def test_horizontal_sources_always_return_through_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            trace = Path(temp) / "trace.jsonl"
            self.bootstrap(trace)
            routes.read_source(PLUGIN / "references/delivery/index.json", "brief", trace)
            routes.read_source(PLUGIN / "references/design/ux/index.json", "workflow", trace)
            report = routes.audit_records(routes.events(trace), require_policy=True)
            self.assertEqual(report["source_accesses"], 3)
            self.assertEqual([e["event"] for e in routes.events(trace)], ["reference", "source"] * 3)

    def test_source_to_source_and_receipt_reuse_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            trace = Path(temp) / "trace.jsonl"
            self.bootstrap(trace)
            history = routes.events(trace)
            with self.assertRaises(ValueError):
                routes.record(trace, history[-1]["receipt"])
            with self.assertRaises(ValueError):
                routes.audit_records([*history, history[-1]])

    def test_governance_must_be_read_before_another_source(self):
        with tempfile.TemporaryDirectory() as temp:
            trace = Path(temp) / "trace.jsonl"
            with self.assertRaisesRegex(ValueError, "governing"):
                routes.read_source(PLUGIN / "references/delivery/index.json", "brief", trace)
            with self.assertRaises(ValueError):
                routes.audit_records(routes.events(trace), require_policy=True)

    def test_reference_metadata_rejects_copied_source_and_authoritative_values(self):
        base = {"format": 1, "entries": [{"id": "x", "label": "x", "kind": "source", "access": "file", "locator": "x.md", "topics": []}]}
        for field in ("body", "content", "rules", "owner", "version"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                data = json.loads(json.dumps(base));data["entries"][0][field] = "copied value"
                path = Path(temp) / "index.json";path.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError, "metadata only"):
                    routes.read_index(path)

    def test_trace_never_contains_read_source_body(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);trace = root / "trace.jsonl"
            self.bootstrap(trace)
            (root / "source.md").write_text("unique-private-body-sentinel")
            index = root / "index.json";index.write_text('{"format":1,"entries":[]}')
            routes.add(index, "sample", "sample", "source.md", "file", ["test"])
            result = routes.read_source(index, "sample", trace)
            self.assertEqual(result["content"], "unique-private-body-sentinel")
            self.assertNotIn("unique-private-body-sentinel", trace.read_text())

    def test_horizontal_cycles_stop_without_fetching_source_bodies(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, other in (("a", "b"), ("b", "a")):
                (root / f"{name}.json").write_text(json.dumps({"format":1,"entries":[{"id":"next","label":"next","kind":"reference","access":"file","locator":f"{other}.json","topics":[]}]}))
            result = routes.walk_references(root / "a.json")
            self.assertEqual(len(result), 2)
            self.assertEqual(len({item["index"] for item in result}), 2)

    def test_recorded_history_can_move_between_package_install_locations(self):
        with tempfile.TemporaryDirectory() as temp:
            trace = Path(temp) / "trace.jsonl"
            self.bootstrap(trace)
            history = routes.events(trace)
            history[0]["location"] = history[1]["location"] = "/previous-install/sources/governance/reference-routing.md"
            trace.write_text("".join(json.dumps(event) + "\n" for event in history))
            self.bootstrap(trace)
            self.assertEqual(routes.audit_records(routes.events(trace), require_policy=True)["source_accesses"], 2)

    def test_invalid_registration_preserves_existing_registry(self):
        for label, locator in (("x" * 241, "https://example.com/docs"), ("valid label", "not-a-url"), ("valid label", "https://user:secret@example.com/docs")):
            with self.subTest(label_length=len(label), locator=locator), tempfile.TemporaryDirectory() as temp:
                index = Path(temp) / "index.json"
                original = '{"format":1,"entries":[]}'
                index.write_text(original)
                with self.assertRaises(ValueError):
                    routes.add(index, "candidate", label, locator, "web", ["test"])
                self.assertEqual(index.read_text(), original)
                self.assertEqual(routes.read_index(index)["entries"], [])


if __name__ == "__main__":
    unittest.main()
