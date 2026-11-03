import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import review_eval
import run_eval
import evaluation_report
from evaluation_execution import execute as execute_capture, prepare_runtime
from evaluation_artifacts import snapshot
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

    def test_user_context_is_preserved_separately_from_prior_answers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            context = root / "context"
            context.mkdir()
            (context / "README.md").write_text("User clarification with its original source and scope")
            (root / "prior-answer.md").write_text("Evaluator-only material")
            project = root / "project"
            module.prepare(self.input(root), project, context=context)
            self.assertEqual((project / "user-context/README.md").read_text(), (context / "README.md").read_text())
            handoff = json.loads((root / "project-handoff.json").read_text())
            self.assertIn("user-context/README.md", handoff["input_files"])
            self.assertNotIn("prior-answer.md", handoff["input_files"])
            (project / "README.md").write_text("Implementation changed the working copy")
            self.assertEqual((root / "project-input/README.md").read_text(), "Test-only request")

    def test_context_collision_and_symlink_fail_before_copying(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.input(root)
            context = root / "context"
            context.mkdir()
            (context / "README.md").write_text("Clarification")
            (context / "link").symlink_to(source / "README.md")
            with self.assertRaises(ValueError):
                module.prepare(source, root / "project", context=context)
            self.assertFalse((root / "project").exists())
            (context / "link").unlink()
            (source / "user-context").mkdir()
            with self.assertRaises(ValueError):
                module.prepare(source, root / "project", context=context)
            self.assertFalse((root / "project").exists())


class IndependentReviewTest(unittest.TestCase):
    def test_snapshot_excludes_dependencies_without_dropping_same_named_regular_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            (source / "node_modules").mkdir(parents=True)
            (source / "node_modules/dependency.js").write_text("dependency")
            (source / "venv").write_text("ordinary input file")
            manifest = snapshot(source, root / "copy")
            self.assertEqual(set(manifest), {"venv"})
            self.assertEqual((root / "copy/venv").read_text(), "ordinary input file")
            self.assertFalse((root / "copy/node_modules").exists())

    def prepare(self, root):
        source = root / "input"
        source.mkdir()
        (source / "README.md").write_text("Produce the requested output from the input.")
        project = root / "project"
        module.prepare(source, project)
        (project / "result.txt").write_text("Initial completed output")
        return project

    def report(self, review, *, status="observed"):
        (review / "evidence/run.log").write_text("Input and observed result")
        report = {"format": 2, "checks": [{"id": "outcome", "source": {"kind": "input", "path": "README.md", "locator": "line 1"},
                  "outcome": "Required output", "status": status, "method": "inspection", "explanation": "Compared input with result",
                  "steps": ["Run the declared entry point with the supplied input"],
                  "evidence": [{"path": "evidence/run.log", "note": "Input and observed output"}]}],
                  "scope_limits": ["This observation does not establish universal correctness."]}
        (review / "report.json").write_text(json.dumps(report))
        return report

    def test_review_preserves_first_output_and_uses_original_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = self.prepare(root)
            (project / "README.md").write_text("Changed implementation document")
            review = review_eval.prepare_review(project)
            self.assertEqual((review / "input/README.md").read_text(), "Produce the requested output from the input.")
            self.assertEqual((review / "subject/result.txt").read_text(), "Initial completed output")
            self.report(review, status="finding")
            result = evaluation_report.check_report(review)
            self.assertEqual(result["counts"]["finding"], 1)
            self.assertNotIn("passed", result)
            with self.assertRaises(ValueError):
                review_eval.prepare_review(project)

    def test_changed_input_or_package_cannot_be_presented_as_same_run(self):
        for name in ("project-input/README.md", "project-plugin/skills/start/SKILL.md"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                project = self.prepare(root)
                (root / name).write_text("Changed after dispatch")
                with self.assertRaises(ValueError):
                    review_eval.prepare_review(project)

    def test_reviewer_cannot_repair_or_rewrite_the_reviewed_material(self):
        for name in ("subject/result.txt", "input/README.md"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                review = review_eval.prepare_review(self.prepare(root))
                self.report(review)
                (review / name).write_text("Repair after first completion")
                (review / "baseline.json").write_text("Reviewer-created baseline cannot replace the harness baseline")
                with self.assertRaises(ValueError):
                    evaluation_report.check_report(review)

    def test_observed_result_needs_local_evidence_and_steps(self):
        for change in ("missing", "outside", "empty", "steps", "source", "duplicate"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                review = review_eval.prepare_review(self.prepare(root))
                report = self.report(review)
                check = report["checks"][0]
                if change == "missing":
                    (review / "evidence/run.log").unlink()
                elif change == "outside":
                    check["evidence"][0]["path"] = "../project/result.txt"
                elif change == "empty":
                    (review / "evidence/run.log").write_text("")
                elif change == "steps":
                    check["steps"] = []
                elif change == "source":
                    check["source"]["path"] = "../subject/README.md"
                else:
                    report["checks"].append(dict(check))
                (review / "report.json").write_text(json.dumps(report))
                with self.assertRaises(ValueError):
                    evaluation_report.check_report(review)

    def test_unavailable_behavior_stays_unverified(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review = review_eval.prepare_review(self.prepare(root))
            report = self.report(review, status="unverified")
            del report["checks"][0]["evidence"]
            del report["checks"][0]["steps"]
            (review / "report.json").write_text(json.dumps(report))
            result = evaluation_report.check_report(review)
            self.assertEqual(result["counts"]["unverified"], 1)

    def test_workflow_policy_can_cite_its_owner_without_becoming_a_user_requirement(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review = review_eval.prepare_review(self.prepare(root))
            report = self.report(review, status="finding")
            report["checks"][0]["source"] = {
                "kind": "package", "path": "sources/source-contract.md", "locator": "Evidence and completion"}
            (review / "report.json").write_text(json.dumps(report))
            self.assertEqual(evaluation_report.check_report(review)["counts"]["finding"], 1)
            (root / "project-plugin/sources/source-contract.md").write_text("Changed policy")
            with self.assertRaises(ValueError):
                evaluation_report.check_report(review)

    def test_external_source_attribution_requires_a_recorded_read_and_matching_address(self):
        sys.path.insert(0,str(ROOT/"plugins/project-builder/scripts"))
        from reference_workflow import Workflow
        for invalid in (None,"path","receipt","trace","unread"):
            with self.subTest(invalid=invalid),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);review=review_eval.prepare_review(self.prepare(root))
                provider=root/"provider";provider.mkdir();body=provider/"policy.md";body.write_text("Source-owned review guidance")
                index=provider/"index.json";index.write_text(json.dumps({"format":1,"entries":[{"id":"policy","label":"Policy","kind":"source","access":"relative","locator":"policy.md","topics":[]}]}))
                trace=review/"evidence/source.jsonl";workflow=Workflow(trace)
                workflow.read(ROOT/"plugins/project-builder/references/governance/index.json","routing-policy")
                request=workflow.prepare(index,"policy") if invalid=="unread" else workflow.read(index,"policy")["reference"]
                report=self.report(review);source={"kind":"reference","path":str(body.resolve()),"locator":"Source policy","trace":"evidence/source.jsonl","receipt":request["receipt"]}
                if invalid=="path":source["path"]=str(provider/"other.md")
                if invalid=="receipt":source["receipt"]="missing"
                if invalid=="trace":source["trace"]="../outside.jsonl"
                report["checks"][0]["source"]=source;(review/"report.json").write_text(json.dumps(report))
                if invalid is None:self.assertEqual(evaluation_report.check_report(review)["counts"]["observed"],1)
                else:
                    with self.assertRaises(ValueError):evaluation_report.check_report(review)

    def test_process_success_without_report_is_not_review_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = self.prepare(root)
            with patch.object(review_eval, "run_process", return_value=subprocess.CompletedProcess([], 0)):
                result = review_eval.execute_review(project)
            self.assertEqual(result["status"], "executed")
            self.assertEqual(result["report_status"], "invalid_or_missing")

    def test_runner_reviews_only_after_implementation_success(self):
        for exit_code in (0, 1):
            with self.subTest(exit_code=exit_code), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                source = root / "input"
                source.mkdir()
                (source / "README.md").write_text("Test-only task")
                with patch.object(run_eval, "run_process", return_value=subprocess.CompletedProcess([], exit_code)), \
                     patch.object(run_eval, "execute_review", return_value={"status": "executed", "report_status": "contract_verified"}) as reviewer:
                    result = run_eval.execute(source, root / "run", review=True)
                self.assertEqual(reviewer.call_count, 1 if exit_code == 0 else 0)
                self.assertEqual(result["review_status"], "contract_verified" if exit_code == 0 else "not_run")

    def test_runner_connects_separate_contexts_without_turning_findings_into_a_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "input"
            source.mkdir()
            (source / "README.md").write_text("Test-only task")
            directories = []

            def complete(command, **kwargs):
                directory = Path(command[command.index("--cd") + 1])
                directories.append(directory)
                self.assertNotIn("--model", command)
                self.assertNotIn("--ignore-user-config", command)
                self.assertFalse(any("model_reasoning_effort=" in item for item in command))
                if directory.name == "project":
                    (directory / "result.txt").write_text("First output")
                else:
                    self.report(directory, status="finding")
                return subprocess.CompletedProcess(command, 0)

            with patch.object(run_eval, "run_process", side_effect=complete), patch.object(review_eval, "run_process", side_effect=complete):
                result = run_eval.execute(source, root / "run", review=True)
            self.assertEqual([p.name for p in directories], ["project", "project-review"])
            self.assertEqual(result["status"], "executed")
            self.assertEqual(result["review"]["counts"]["finding"], 1)
            self.assertNotIn("passed", result)
            self.assertEqual((root / "run/project/result.txt").read_text(), "First output")

    def test_review_timeout_is_not_a_product_verdict(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = self.prepare(root)
            with patch.object(review_eval, "run_process", side_effect=subprocess.TimeoutExpired("codex", 1)):
                result = review_eval.execute_review(project, timeout=1)
            self.assertEqual(result["status"], "timed_out")
            self.assertNotIn("report_status", result)


if __name__ == "__main__":
    unittest.main()
