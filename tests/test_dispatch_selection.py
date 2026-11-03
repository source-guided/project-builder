import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluation_dispatch import build_command, selection_record
import run_eval
import review_eval


class DispatchSelectionTest(unittest.TestCase):
    def test_default_keeps_user_cli_model_configuration(self):
        command = build_command(workspace="project", answer="answer.md")
        self.assertNotIn("--model", command)
        self.assertNotIn("--ignore-user-config", command)
        self.assertFalse(any("model_reasoning_effort=" in value for value in command))
        record = selection_record()
        self.assertIsNone(record["model_requested"])
        self.assertEqual(record["configuration_source"]["model"], "caller_cli_configuration")

    def test_overrides_only_supplied_settings_without_shell_interpolation(self):
        for model, effort in [("caller-selected-model", None), (None, "caller-selected-effort"), ('model"value', 'effort"value')]:
            with self.subTest(model=model, effort=effort):
                command = build_command(workspace="project", answer="answer.md", model=model, reasoning_effort=effort)
                self.assertEqual("--model" in command, model is not None)
                self.assertEqual("-c" in command, effort is not None)
                if model is not None:
                    self.assertEqual(command[command.index("--model") + 1], model)
                if effort is not None:
                    value = command[command.index("-c") + 1].split("=", 1)[1]
                    self.assertEqual(json.loads(value), effort)

    def test_implementation_and_review_receive_the_callers_explicit_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "input"; source.mkdir()
            (source / "README.md").write_text("Produce a local result")
            commands = []
            def complete(command, **kwargs):
                commands.append(command)
                return subprocess.CompletedProcess(command, 0)
            with patch.object(run_eval, "run_process", side_effect=complete), patch.object(review_eval, "run_process", side_effect=complete):
                result = run_eval.execute(source, root / "run", review=True, model="caller-model", reasoning_effort="caller-effort")
            self.assertEqual(len(commands), 2)
            for command in commands:
                self.assertEqual(command[command.index("--model") + 1], "caller-model")
                self.assertIn('model_reasoning_effort="caller-effort"', command)
            self.assertEqual(result["model_requested"], "caller-model")
            self.assertEqual(result["review"]["reasoning_effort_requested"], "caller-effort")
            self.assertEqual(result["review_status"], "invalid_or_missing")


if __name__ == "__main__":
    unittest.main()
