import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_eval", ROOT / "scripts/prepare_eval.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EvaluationPreparationTest(unittest.TestCase):
    def test_provides_only_selected_input_and_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            prompt = module.prepare("resume", project)
            self.assertEqual({p.name for p in project.iterdir()}, {"README.md", "summary.py", "work-record.md"})
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
                module.prepare("resume", project)
            self.assertEqual(sentinel.read_text(), "user work")

    def test_conflicting_prompt_does_not_create_partial_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "project-prompt.txt").write_text("existing prompt")
            with self.assertRaises(ValueError):
                module.prepare("resume", root / "project")
            self.assertFalse((root / "project").exists())


if __name__ == "__main__":
    unittest.main()
