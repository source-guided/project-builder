"""독립 원천의 관측 영수증을 보고서 출처에 연결한다."""

import json
from pathlib import Path
import re
import sys


def verify_reference_source(review, source, package):
    trace=(review/source.get("trace","")).resolve()
    if not trace.is_relative_to(review) or not trace.is_file():
        raise ValueError("Reference source needs a local review trace")
    sys.path.insert(0,str(Path(package)/"scripts"))
    from reference_session import audit_records
    records=[json.loads(line) for line in trace.read_text().splitlines() if line.strip()]
    audit_records(records)
    receipt=source.get("receipt")
    request=next((e for e in records if e.get("event")=="reference" and e.get("receipt")==receipt),None)
    observation=next((e for e in records if e.get("event")=="source" and e.get("receipt")==receipt),None)
    if not request or not observation or observation.get("status")!="read":
        raise ValueError("Reference source must identify an actual recorded read")
    digest=observation.get("observed_sha256","")
    if not isinstance(digest,str) or not re.fullmatch("[0-9a-f]{64}",digest) or request["resolved"]["address"]!=source["path"]:
        raise ValueError("Reference source path/revision does not match its observation")
    return {"address":source["path"],"observed_sha256":digest,"receipt":receipt}
