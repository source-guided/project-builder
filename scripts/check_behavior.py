#!/usr/bin/env python3
"""합성 시나리오의 모델 산출물을 독립 입력으로 검증한다."""

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def check_reconciliation(project: Path):
    script = project / "reconcile.py"
    checks = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        left, right, output = (root / name for name in ("left.csv", "right.csv", "result.json"))

        def run(ltext, rtext):
            left.write_text(ltext)
            right.write_text(rtext)
            output.write_text("existing-result-sentinel")
            result = subprocess.run([sys.executable, str(script), str(left), str(right), "--output", str(output)], capture_output=True, text=True, timeout=20)
            return result, output.read_text()

        result, data = run("id,amount\nz,0\nb,9007199254740993.01\na,01.0\n", "id,amount\na,1.00\nb,9007199254740993.02\nx,3\n")
        assert result.returncode == 0, result.stderr
        assert json.loads(data) == {"matched": ["a"], "different": [{"id": "b", "left": "9007199254740993.01", "right": "9007199254740993.02"}], "leftOnly": ["z"], "rightOnly": ["x"]}
        checks.append("exact precision, equivalence, schema, and ID ordering")
        result, data = run("id,amount\n", "id,amount\n")
        assert result.returncode == 0 and json.loads(data) == {"matched": [], "different": [], "leftOnly": [], "rightOnly": []}
        checks.append("header-only input")
        invalid = ["", "amount,id\n", "id,amount\na,1\na,2\n", "id,amount\na,1e2\n", "id,amount\na,NaN\n", "id,amount\na,-1\n", "id,amount\na,1.234\n", "id,amount\na,1,extra\n", "id,amount\n,1\n"]
        for index, content in enumerate(invalid):
            for side in (0, 1):
                result, data = run(content if side == 0 else "id,amount\n", content if side else "id,amount\n")
                assert result.returncode != 0 and result.stderr.strip()
                assert data == "existing-result-sentinel"
                checks.append(f"invalid input {index + 1}, side {side + 1}: error and output preserved")
    return checks


def check_resume(project: Path):
    spec = importlib.util.spec_from_file_location("evaluated_summary", project / "summary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for value, expected in [(0, "0"), (None, "Unknown"), (1, "1"), (27, "27")]:
        assert module.display_quantity(value) == expected
    record = (project / "work-record.md").read_text()
    assert "The export format work is separate and must not be modified in this task." in record
    return ["zero is a value", "None is missing", "positive quantities preserved", "unrelated user note preserved"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("reconciliation", "resume"), required=True)
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    checks = (check_reconciliation if args.case == "reconciliation" else check_resume)(args.project.resolve())
    print(json.dumps({"case": args.case, "status": "passed", "checks": checks}, ensure_ascii=False, indent=2))
