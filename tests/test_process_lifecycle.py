import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluation_process import run_process
from prepare_eval import prepare
from review_eval import execute_review
from run_eval import execute


@unittest.skipUnless(os.name == "posix", "Managed POSIX process groups")
class ProcessLifecycleTest(unittest.TestCase):
    def stub(self, root, body):
        directory = root / "bin"; directory.mkdir()
        executable = directory / "codex"
        executable.write_text("#!" + sys.executable + "\n" + body)
        executable.chmod(0o755)
        return {"PATH": str(directory) + os.pathsep + os.environ["PATH"]}

    def input(self, root):
        source = root / "input"; source.mkdir()
        (source / "README.md").write_text("Print ORIGINAL")
        return source

    def child_launcher(self):
        child = "from pathlib import Path;import time;Path('child-ready').write_text('ready');time.sleep(2);Path('late.txt').write_text('late')"
        return ("import subprocess,sys,time\nfrom pathlib import Path\n"
                "work=Path(sys.argv[sys.argv.index('--cd')+1])\n"
                f"subprocess.Popen([sys.executable,'-c',{child!r}],cwd=work)\n"
                "time.sleep(20)\n")

    def test_both_model_runners_stop_children_before_reporting_timeout(self):
        for runner in ("implementation", "review"):
            with self.subTest(runner=runner), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); source = self.input(root)
                env = self.stub(root, self.child_launcher())
                with patch.dict(os.environ, env):
                    if runner == "implementation":
                        result = execute(source, root / "run", timeout=1)
                        work = root / "run/project"
                    else:
                        project = root / "project"; prepare(source, project)
                        result = execute_review(project, timeout=1)
                        work = root / "project-review"
                self.assertEqual(result["status"], "timed_out")
                self.assertTrue((work / "child-ready").exists(), "Child must have started for this regression")
                time.sleep(1.3)
                self.assertFalse((work / "late.txt").exists())

    def test_normal_process_exit_also_stops_remaining_children(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            child = "from pathlib import Path;import time;Path('ready').write_text('ready');time.sleep(0.5);Path('late').write_text('late')"
            parent = (f"import subprocess,sys,time;from pathlib import Path;subprocess.Popen([sys.executable,'-c',{child!r}]);\n"
                      "while not Path('ready').exists():time.sleep(0.01)\n")
            result = run_process([sys.executable, "-c", parent], cwd=root, timeout=5)
            self.assertEqual(result.returncode, 0)
            self.assertTrue((root / "ready").exists())
            time.sleep(0.7)
            self.assertFalse((root / "late").exists())

    def test_real_dispatch_capture_and_review_chain(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = self.input(root)
            stub = '''import json,subprocess,sys
from pathlib import Path
work=Path(sys.argv[sys.argv.index('--cd')+1])
if work.name=='project':
    (work/'main.py').write_text("print('ORIGINAL')\\n")
else:
    contract=json.loads((work/'contract.json').read_text())
    (work/'probe.py').write_text("import subprocess,sys\\nprint(subprocess.check_output([sys.executable,'main.py'],text=True),end='')\\n")
    command=[sys.executable,contract['execution']['tool'],'--review',str(work),'--',sys.executable,'../probe.py']
    capture=json.loads(subprocess.check_output(command,text=True))
    stdout=next(name for name in capture['evidence'] if name.endswith('stdout.txt'))
    assert (work/stdout).read_text()=='ORIGINAL\\n'
    assert 'probe.py' in capture['test_inputs']
    report={'format':2,'scope_limits':['Synthetic dispatch, no model call'],'checks':[{
      'id':'output','source':{'kind':'input','path':'README.md','locator':'1'},
      'outcome':'Print ORIGINAL','status':'observed','method':'runtime',
      'explanation':'Executed preserved application','steps':['Run probe'],
      'execution_id':capture['id'],'evidence':[{'path':stdout,'note':'Actual output'}]}]}
    (work/'report.json').write_text(json.dumps(report))
'''
            with patch.dict(os.environ, self.stub(root, stub)):
                result = execute(source, root / "run", review=True, timeout=10, review_timeout=10)
            self.assertEqual(result["status"], "executed")
            self.assertEqual(result["review_status"], "contract_verified", result)
            self.assertEqual(result["completion"]["origin"], "runner_completion")
            self.assertEqual(result["review"]["methods"]["runtime"], 1)


if __name__ == "__main__":
    unittest.main()
