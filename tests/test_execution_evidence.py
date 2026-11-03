import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_eval import prepare
from review_eval import prepare_review
from evaluation_execution import execute, prepare_runtime
from evaluation_report import check_report
from review_eval import freeze_completion
import os
import subprocess


class ExecutionEvidenceTest(unittest.TestCase):
    def prepare(self, root, code="print('ORIGINAL')\n"):
        source = root / "input"
        source.mkdir()
        (source / "README.md").write_text("The program must print ORIGINAL.\n")
        project = root / "project"
        prepare(source, project)
        (project / "main.py").write_text(code)
        return prepare_review(project)

    def report(self, review, execution, *, status="observed"):
        output = next(name for name in execution["evidence"] if name.endswith("stdout.txt"))
        report = {"format": 2, "checks": [{
            "id": "output", "source": {"kind":"input","path":"README.md","locator":"line 1"},
            "outcome": "Print ORIGINAL", "status": status, "method": "runtime",
            "explanation": "Compared captured stdout with the required output", "steps": ["Run main.py"],
            "execution_id": execution["id"], "evidence": [{"path":output,"note":"Captured stdout"}],
        }], "scope_limits": ["Local interpreter and fixture only"]}
        (review / "report.json").write_text(json.dumps(report))
        return report

    def test_runtime_observation_binds_command_revision_and_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            review = self.prepare(Path(temp))
            record = execute(review, [sys.executable, "main.py"])
            self.assertEqual(record["status"], "completed")
            self.assertTrue(record["source_revision_verified"])
            self.report(review, record)
            result = check_report(review)
            self.assertEqual(result["methods"]["runtime"], 1)
            self.assertIn(record["id"], result["executions"])

    def test_repaired_runtime_cannot_be_executed_as_the_first_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            review = self.prepare(Path(temp), "print('BROKEN')\n")
            runtime = prepare_runtime(review)
            (runtime / "main.py").write_text("print('ORIGINAL')\n")
            with self.assertRaisesRegex(ValueError, "no longer matches"):
                execute(review, [sys.executable, "main.py"])
            self.assertEqual((review / "subject/main.py").read_text(), "print('BROKEN')\n")

    def test_source_mutation_during_execution_invalidates_runtime_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            review = self.prepare(Path(temp), "from pathlib import Path\nPath('main.py').write_text(\"print('ORIGINAL')\\n\")\nprint('ORIGINAL')\n")
            record = execute(review, [sys.executable, "main.py"])
            self.assertFalse(record["source_revision_verified"])
            self.report(review, record)
            with self.assertRaisesRegex(ValueError, "first artifact"):
                check_report(review)

    def test_added_runtime_code_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            review = self.prepare(Path(temp))
            runtime = prepare_runtime(review)
            (runtime / "replacement.py").write_text("print('ORIGINAL')\n")
            with self.assertRaises(ValueError):
                execute(review, [sys.executable, "replacement.py"])

    def test_runtime_report_cannot_use_uncaptured_or_modified_evidence(self):
        for mode in ("changed", "not-captured", "unknown-execution"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                review = self.prepare(Path(temp))
                record = execute(review, [sys.executable, "main.py"])
                report = self.report(review, record)
                item = report["checks"][0]
                if mode == "changed":
                    (review / item["evidence"][0]["path"]).write_text("Different output")
                elif mode == "not-captured":
                    (review / "evidence/other.txt").write_text("Unrelated output")
                    item["evidence"][0]["path"] = "evidence/other.txt"
                else:
                    item["execution_id"] = "0" * 32
                (review / "report.json").write_text(json.dumps(report))
                with self.assertRaises((ValueError, OSError)):
                    check_report(review)

    def test_relative_test_script_cannot_change_after_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            review = self.prepare(Path(temp))
            script = review / "check.py"
            script.write_text("import subprocess,sys\nprint(subprocess.check_output([sys.executable,'main.py'],text=True),end='')\n")
            record = execute(review, [sys.executable, "../check.py"])
            self.assertIn("check.py", record["test_inputs"])
            self.report(review, record)
            check_report(review)
            script.write_text("print('REPLACED')\n")
            with self.assertRaisesRegex(ValueError, "test input changed"):
                check_report(review)

    def test_test_input_symlink_binding_is_rechecked(self):
        with tempfile.TemporaryDirectory() as temp:
            review = self.prepare(Path(temp))
            first = review / "first.py"; first.write_text("print('ORIGINAL')\n")
            other = review / "other.py"; other.write_text("print('CHANGED')\n")
            link = review / "check.py"; link.symlink_to(first)
            record = execute(review, [sys.executable, "../check.py"])
            self.report(review, record)
            link.unlink(); link.symlink_to(other)
            with self.assertRaisesRegex(ValueError, "test input changed"):
                check_report(review)

    def test_relative_input_outside_review_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            review = self.prepare(Path(temp))
            (review.parent / "outside.py").write_text("print('ORIGINAL')\n")
            with self.assertRaisesRegex(ValueError, "inside the review workspace"):
                execute(review, [sys.executable, "../../outside.py"])

    def test_captured_test_script_cannot_change_after_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            review = self.prepare(Path(temp))
            script = review / "evidence/test.py"
            script.write_text("import subprocess,sys\nprint(subprocess.check_output([sys.executable,'main.py'],text=True),end='')\n")
            record = execute(review, [sys.executable, str(script)])
            self.report(review, record)
            check_report(review)
            script.write_text("print('ORIGINAL')\n")
            with self.assertRaisesRegex(ValueError, "test input changed"):
                check_report(review)

    def test_evidence_can_be_written_outside_runtime_and_is_hashed(self):
        with tempfile.TemporaryDirectory() as temp:
            review = self.prepare(Path(temp))
            script = review / "test.py"
            script.write_text("from pathlib import Path\nPath('../evidence/result.json').write_text('{\"ok\":true}')\n")
            record = execute(review, [sys.executable,str(script)], evidence_paths=["evidence/result.json"])
            self.assertTrue(record["source_revision_verified"])
            self.assertIn("evidence/result.json", record["evidence"])

    def test_existing_evidence_cannot_be_reattributed_to_a_new_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            review = self.prepare(Path(temp))
            (review / "evidence/prior.txt").write_text("from an earlier run")
            with self.assertRaisesRegex(ValueError, "new evidence path"):
                execute(review, [sys.executable,"-c","pass"], evidence_paths=["evidence/prior.txt"])
            self.assertEqual((review / "evidence/prior.txt").read_text(), "from an earlier run")

    def test_concurrent_processes_cannot_share_one_evidence_output(self):
        with tempfile.TemporaryDirectory() as temp:
            review=self.prepare(Path(temp))
            tool=review.parent/"project-harness/evaluation_execution.py"
            base=[sys.executable,str(tool),"--review",str(review),"--evidence","evidence/shared.txt","--",sys.executable,"-c"]
            def command(value):
                return base+[f"from pathlib import Path; import time; Path('../evidence/shared.txt').write_text('{value}'); time.sleep(0.1); print('{value}')"]
            first=subprocess.Popen(command("A"),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            second=subprocess.Popen(command("B"),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            first_out,first_error=first.communicate(timeout=10);second_out,second_error=second.communicate(timeout=10)
            self.assertCountEqual([first.returncode,second.returncode],[0,1])
            successful=json.loads(first_out if first.returncode==0 else second_out)
            self.assertTrue(successful["source_revision_verified"])
            self.assertIn("new evidence path",second_error if first.returncode==0 else first_error)

    def test_execution_from_another_review_cannot_be_reattributed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);one=root/"one";two=root/"two";one.mkdir();two.mkdir()
            first=self.prepare(one);second=self.prepare(two)
            record=execute(first,[sys.executable,"main.py"])
            destination=second/".harness/executions";destination.mkdir(parents=True)
            shutil.copy2(first/".harness/executions"/f"{record['id']}.json",destination/f"{record['id']}.json")
            for name in record["evidence"]:
                target=second/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(first/name,target)
            self.report(second,record)
            with self.assertRaisesRegex(ValueError,"preserved first artifact"):
                check_report(second)

    @unittest.skipIf(os.name == "nt", "POSIX executable bits")
    def test_executable_permission_repair_changes_the_artifact_revision(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "input"; source.mkdir(); (source / "README.md").write_text("Run the script")
            project = root / "project"; prepare(source, project)
            script = project / "run.sh";script.write_text("#!/bin/sh\necho working\n");script.chmod(0o644)
            review = prepare_review(project); runtime = prepare_runtime(review)
            (runtime / "run.sh").chmod(0o755)
            with self.assertRaisesRegex(ValueError, "no longer matches"):
                execute(review,["./run.sh"])

    def test_completed_snapshot_survives_later_project_edits(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);source=root/"input";source.mkdir();(source/"README.md").write_text("Original requirement")
            project=root/"project";prepare(source,project);(project/"result.txt").write_text("first output")
            frozen, receipt=freeze_completion(project,origin="runner_completion")
            (project/"result.txt").write_text("later repair")
            review=prepare_review(project)
            self.assertEqual((review/"subject/result.txt").read_text(),"first output")
            self.assertEqual(receipt["origin"],"runner_completion")

    def test_manual_capture_does_not_claim_an_earlier_model_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            review=self.prepare(Path(temp))
            baseline=json.loads(review.with_name(review.name+"-baseline.json").read_text())
            self.assertEqual(baseline["completion"]["origin"],"manual_capture")

    def test_missing_execution_does_not_become_a_runtime_observation(self):
        with tempfile.TemporaryDirectory() as temp:
            review = self.prepare(Path(temp))
            record = execute(review, [str(review / "nonexistent-program")])
            self.assertEqual(record["status"], "unavailable")
            (review / "evidence/manual.log").write_text("manual assertion")
            report = {"format":2,"checks":[{"id":"x","source":{"kind":"input","path":"README.md","locator":"1"},"outcome":"Output","status":"observed","method":"runtime","explanation":"assertion","steps":["attempt"],"execution_id":record["id"],"evidence":[{"path":"evidence/manual.log","note":"manual"}]}],"scope_limits":[]}
            (review / "report.json").write_text(json.dumps(report))
            with self.assertRaises(ValueError):
                check_report(review)

    def test_timeout_can_support_a_finding_but_not_a_completed_outcome(self):
        with tempfile.TemporaryDirectory() as temp:
            review = self.prepare(Path(temp), "import time\nprint('started',flush=True)\ntime.sleep(10)\n")
            record = execute(review, [sys.executable,"main.py"], timeout=0.1)
            self.assertEqual(record["status"], "timed_out")
            self.report(review, record)
            with self.assertRaisesRegex(ValueError, "Timed-out"):
                check_report(review)
            self.report(review, record, status="finding")
            self.assertEqual(check_report(review)["counts"]["finding"], 1)

    def test_harness_and_contract_changes_are_detected(self):
        for name in ("contract.json", "../project-harness/evaluation_execution.py"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                review = self.prepare(Path(temp))
                (review / name).write_text("changed contract or harness")
                with self.assertRaises(ValueError):
                    prepare_runtime(review)


if __name__ == "__main__":
    unittest.main()
