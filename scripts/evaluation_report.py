"""독립 검토 보고서의 원천·증거·실행 리비전 계약을 검사한다."""

import json
from pathlib import Path

from evaluation_execution import verify_baseline, verify_execution
from evaluation_sources import verify_reference_source


STATUSES = {"observed", "finding", "unverified", "not_applicable"}
METHODS = {"runtime", "inspection", "scope"}


def check_report(review):
    review = Path(review).resolve()
    baseline = verify_baseline(review)
    report = json.loads((review / "report.json").read_text())
    if not isinstance(report, dict) or report.get("format") != 2:
        raise ValueError("Expected review report format 2")
    checks = report.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("A nonempty checks array is required")
    if not isinstance(report.get("scope_limits"), list) or not all(isinstance(v, str) and v.strip() for v in report["scope_limits"]):
        raise ValueError("scope_limits must be explicit")
    counts = dict.fromkeys(sorted(STATUSES), 0)
    methods = dict.fromkeys(sorted(METHODS), 0)
    seen, executions = set(), {}
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("Each check must be an object")
        for field in ("id", "outcome", "status", "method", "explanation"):
            if not isinstance(check.get(field), str) or not check[field].strip():
                raise ValueError(f"Check requires {field}")
        if check["id"] in seen or check["status"] not in STATUSES or check["method"] not in METHODS:
            raise ValueError("Duplicate check ID or unsupported status/method")
        seen.add(check["id"])
        source = check.get("source", {})
        if not isinstance(source, dict) or source.get("kind") not in {"input", "package", "reference"}:
            raise ValueError("Source must declare input, package or recorded reference ownership")
        if not all(isinstance(source.get(k), str) and source[k].strip() for k in ("path", "locator")):
            raise ValueError("Source needs a path and locator")
        if source["kind"] == "reference":
            verify_reference_source(review,source,baseline["package_path"])
        else:
            owner = review / "input" if source["kind"] == "input" else Path(baseline["package_path"])
            source_path = (owner / source["path"]).resolve()
            if not source_path.is_relative_to(owner) or not source_path.is_file():
                raise ValueError("Check source escapes its declared owner or does not exist")
        if check["status"] in {"observed", "finding"}:
            if check["method"] == "scope":
                raise ValueError("Scope statements are not observed behavior")
            steps, evidence = check.get("steps"), check.get("evidence")
            if not isinstance(steps, list) or not steps or not all(isinstance(v, str) and v.strip() for v in steps):
                raise ValueError("Observed results and findings require reproduction steps")
            if not isinstance(evidence, list) or not evidence:
                raise ValueError("Observed results and findings require evidence")
            for item in evidence:
                if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k].strip() for k in ("path", "note")):
                    raise ValueError("Evidence needs a path and explanatory note")
                path = (review / item["path"]).resolve()
                if not path.is_relative_to(review / "evidence") or not path.is_file() or not path.stat().st_size:
                    raise ValueError("Evidence must be a nonempty local review artifact")
            if check["method"] == "runtime":
                execution = verify_execution(review, check.get("execution_id"), evidence)
                if execution["status"] == "timed_out" and check["status"] == "observed":
                    raise ValueError("Timed-out execution does not establish a completed outcome")
                executions[execution["id"]] = {"runtime_additions": execution["runtime_additions"], "exit_code": execution["exit_code"]}
        counts[check["status"]] += 1
        methods[check["method"]] += 1
    return {"report_status": "contract_verified", "counts": counts, "methods": methods, "executions": executions,
            "meaning": "Source/evidence ownership and captured execution revision verified. Not a product pass or proof of coverage/evidence truth."}
