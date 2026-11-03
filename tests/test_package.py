import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from package import package
from validate import plugin_files, validate

spec = importlib.util.spec_from_file_location("init_context", ROOT / "plugins/project-builder/scripts/init_context.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PackageTest(unittest.TestCase):
    def allow(self, plugin, names):
        (plugin / "package-files.json").write_text(json.dumps(["package-files.json", *names]))

    def test_current_package_contract(self):
        self.assertEqual(validate()[0], 1)

    def test_initializer_preserves_work_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".gitignore").write_text("dist/\n!.local/\n")
            record = module.initialize(root)
            record.write_text("existing decisions")
            ignore = (root / ".gitignore").read_text()
            self.assertEqual(module.initialize(root).read_text(), "existing decisions")
            self.assertEqual((root / ".gitignore").read_text(), ignore)
            self.assertTrue(ignore.endswith("/.local/\n"))
            self.assertTrue(ignore.startswith("dist/"))

    def test_initializer_refuses_symlink_without_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outside = root / "outside"
            outside.mkdir()
            (root / ".local").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                module.initialize(root)
            self.assertFalse((root / ".gitignore").exists())
            self.assertEqual(list(outside.iterdir()), [])

    def test_project_bindings_are_metadata_in_the_consuming_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "README.md").write_text("private-product-body-sentinel")
            (root / "AGENTS.md").write_text("private-project-convention-sentinel")
            record = module.initialize(root)
            registry = record.parent
            self.assertTrue((registry / "index.json").is_file())
            self.assertFalse((registry / "project/frontend").exists())
            metadata = "".join(p.read_text() for p in registry.rglob("*.json"))
            self.assertNotIn("private-product-body-sentinel", metadata)
            self.assertNotIn("private-project-convention-sentinel", metadata)
            conventions = json.loads((registry / "index.json").read_text())
            self.assertIn("AGENTS.md", [entry["id"] for entry in conventions["entries"]])

    def test_initializer_does_not_confuse_comments_or_negations_with_ignore_rule(self):
        for existing in ("# /.local/\n", "!/.local/\n", "prefix/.local/\n", " /.local/\n", "\t/.local/\n"):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / ".gitignore").write_text(existing)
                module.initialize(root)
                self.assertEqual((root / ".gitignore").read_text(), existing + "/.local/\n")
                subprocess.run(["git", "init", "-q", str(root)], check=True)
                ignored = subprocess.run(["git", "check-ignore", "-q", ".local/project-builder/work-record.md"], cwd=root)
                self.assertEqual(ignored.returncode, 0)

    def test_archive_does_not_include_neighboring_private_context(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plugin = root / "plugin"
            plugin.mkdir()
            (plugin / "plugin.json").write_text('{"name":"fixture"}')
            self.allow(plugin, ["plugin.json"])
            private = root / ".local"
            private.mkdir()
            (private / "source.md").write_text("private-source-sentinel")
            first = package(root / "one.zip", plugin)
            second = package(root / "two.zip", plugin)
            self.assertEqual(first, second)
            with zipfile.ZipFile(root / "one.zip") as archive:
                self.assertEqual(archive.namelist(), ["package-files.json", "plugin.json"])
                self.assertNotIn(b"private-source-sentinel", b"".join(archive.read(n) for n in archive.namelist()))

    def test_package_rejects_private_directory_inside_plugin(self):
        with tempfile.TemporaryDirectory() as temp:
            plugin = Path(temp)
            self.allow(plugin, [])
            (plugin / ".local").mkdir()
            with self.assertRaises(ValueError):
                plugin_files(plugin)

    def test_package_rejects_symlink_and_env(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outside = root / "secret"
            outside.write_text("private")
            plugin = root / "plugin"
            plugin.mkdir()
            self.allow(plugin, [])
            link = plugin / "source.md"
            link.symlink_to(outside)
            with self.assertRaises(ValueError):
                plugin_files(plugin)
            link.unlink()
            (plugin / ".env").write_text("SECRET=example")
            with self.assertRaises(ValueError):
                plugin_files(plugin)

    def test_package_rejects_unlisted_notes(self):
        with tempfile.TemporaryDirectory() as temp:
            plugin = Path(temp)
            self.allow(plugin, [])
            (plugin / "private-notes.txt").write_text("synthetic-private-sentinel")
            with self.assertRaisesRegex(ValueError, "Unexpected file"):
                plugin_files(plugin)

    def test_package_rejects_missing_or_escaping_allowlist_entries(self):
        for name in ("missing.md", "../outside.txt"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                plugin = Path(temp)
                self.allow(plugin, [name])
                with self.assertRaises(ValueError):
                    plugin_files(plugin)


if __name__ == "__main__":
    unittest.main()
