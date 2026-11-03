import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_eval", ROOT / "scripts/prepare_eval.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EvaluationPreparationTest(unittest.TestCase):
    def input(self, root):
        source = root / "consumer-input"
        source.mkdir()
        (source / "README.md").write_text("Test-only request")
        (source / "input.txt").write_text("fixture")
        return source

    def test_provides_only_selected_input_and_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            source = self.input(root)
            (root / "criteria.json").write_text("Do not supply this")
            prompt = module.prepare(source, project)
            self.assertEqual({p.name for p in project.iterdir()}, {"README.md", "input.txt"})
            package = root / "project-plugin"
            self.assertTrue((package / "skills/start/SKILL.md").is_file())
            self.assertFalse((package / "evals/criteria.json").exists())
            self.assertFalse((package / ".local").exists())
            self.assertIn(str(package / "skills/start/SKILL.md"), prompt.read_text())

    def test_existing_work_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            project.mkdir()
            sentinel = project / "sentinel"
            sentinel.write_text("user work")
            with self.assertRaises(ValueError):
                module.prepare(self.input(Path(temp)), project)
            self.assertEqual(sentinel.read_text(), "user work")

    def test_conflicting_prompt_does_not_create_partial_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "project-prompt.txt").write_text("existing prompt")
            with self.assertRaises(ValueError):
                module.prepare(self.input(root), root / "project")
            self.assertFalse((root / "project").exists())

    def test_input_symlinks_and_nested_output_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.input(root)
            with self.assertRaises(ValueError):
                module.prepare(source, source / "output")
            (source / "leak").symlink_to(root / "criteria.json")
            with self.assertRaises(ValueError):
                module.prepare(source, root / "project")
            self.assertFalse((root / "project").exists())


if __name__ == "__main__":
    unittest.main()
