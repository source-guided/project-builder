#!/usr/bin/env python3
"""참조 발견, 관리자 작업, 세션 실행을 연결하는 Project Builder CLI."""

import argparse
import json
from pathlib import Path
import sys

# 이동한 패키지에서도 같은 패키지의 모듈만 로드한다.
SCRIPT_DIRECTORY = str(Path(__file__).resolve().parent)
if SCRIPT_DIRECTORY not in sys.path:
    sys.path.insert(0, SCRIPT_DIRECTORY)

from reference_registry import change, initialize
from document_stores import Stores, load_config
from reference_session import Session
from reference_workflow import Workflow


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--index",required=True)
    listing = commands.add_parser("list")
    listing.add_argument("--index", required=True)
    listing.add_argument("--index-access", choices=("file", "web", "connector"))
    for name in ("walk", "discover"):
        item = commands.add_parser(name)
        item.add_argument("--index", nargs="+", required=True)
        item.add_argument("--max-indexes", type=int, default=128)
        item.add_argument("--index-access", choices=("file", "web", "connector"))
        if name == "discover":
            item.add_argument("--query", default="")
            item.add_argument("--limit", type=int, default=20)
    for name in ("resolve", "prepare-read", "read", "metadata-review", "metadata-status"):
        item = commands.add_parser(name)
        item.add_argument("--index", required=True)
        item.add_argument("--id", required=True)
        item.add_argument("--index-access", choices=("file", "web", "connector"))
        if name != "resolve":
            item.add_argument("--trace", type=Path, required=True)
            item.add_argument("--scope", default="local")
            item.add_argument("--source-root", type=Path, action="append", default=[])
        if name == "metadata-review":
            item.add_argument("--receipt", required=True)
        if name == "metadata-status":
            item.add_argument("--refresh", action="store_true", help="Read the source through the workflow before comparing observations")
    batch = commands.add_parser("read-many")
    batch.add_argument("--requests", type=Path, required=True)
    batch.add_argument("--workers", type=int, default=4)
    batch.add_argument("--trace", type=Path, required=True)
    batch.add_argument("--scope", default="local")
    batch.add_argument("--source-root", type=Path, action="append", default=[])
    record = commands.add_parser("record")
    record.add_argument("--trace", type=Path, required=True)
    record.add_argument("--scope", default="local")
    record.add_argument("--receipt", required=True)
    record.add_argument("--status", choices=("read", "unavailable", "reused-from-current-context"), default="read")
    record.add_argument("--sha256")
    record.add_argument("--based-on")
    record.add_argument("--error")
    audit = commands.add_parser("audit")
    audit.add_argument("--trace", type=Path, required=True)
    audit.add_argument("--scope", default="local")
    for name in ("add", "update", "remove"):
        item = commands.add_parser(name)
        item.add_argument("--index", required=True)
        item.add_argument("--id", required=True)
        item.add_argument("--expected-digest", required=name != "add")
        if name == "add":
            item.add_argument("--label", required=True)
            item.add_argument("--description", default="")
            item.add_argument("--locator", required=True)
            item.add_argument("--kind", choices=("source", "reference"), default="source")
            item.add_argument("--access", choices=("file", "web", "connector", "relative"), required=True)
            item.add_argument("--topics", nargs="*", default=[])
        if name == "update":
            item.add_argument("--patch", type=Path, required=True)
    for command in commands.choices.values():
        command.add_argument("--store-config",type=Path)
    args = parser.parse_args(argv)
    stores = Stores(load_config(args.store_config))
    requests = None
    if args.command == "read-many":
        requests = json.loads(args.requests.read_text())
        if not isinstance(requests, list) or not all(isinstance(r, dict) and {"index", "id"} <= set(r) <= {"index", "id", "access"} for r in requests):
            raise ValueError("Batch requests need index/id and optional index access")
    method = getattr(args, "index_access", None)
    roots = requests if requests is not None else args.index if isinstance(getattr(args, "index", None), list) else [args.index] if getattr(args, "index", None) else []
    if method:
        roots=[{"index":root,"access":method} for root in roots]
    catalog = stores.catalog(roots)
    if args.command == "init":
        result = initialize(args.index,stores=stores)
    elif args.command == "list":
        observed = catalog.read_index(args.index, access=method)
        result = {**observed["document"], "index_digest": observed["digest"], "index_revision": observed.get("revision")}
    elif args.command == "walk":
        result = catalog.walk([{"index": p, "access": method} for p in args.index] if method else args.index, max_indexes=args.max_indexes)
    elif args.command == "discover":
        result = catalog.discover([{"index": p, "access": method} for p in args.index] if method else args.index, args.query, max_indexes=args.max_indexes, limit=args.limit)
    elif args.command == "resolve":
        result = catalog.resolve(args.index, args.id, access=method)
    elif args.command in {"add", "update", "remove"}:
        entry = None
        if args.command == "add":
            entry = {"id": args.id, "label": args.label, "description": args.description,
                     "kind": args.kind, "access": args.access, "locator": args.locator, "topics": args.topics}
        result = change(args.index, args.id, operation=args.command, entry=entry,
                        patch=json.loads(args.patch.read_text()) if args.command == "update" else None,
                        expected_digest=args.expected_digest,stores=stores)
    else:
        workflow = Workflow(args.trace, scope=args.scope, catalog=catalog, source_roots=getattr(args,"source_root",[]))
        if args.command == "read":
            result = workflow.read(args.index, args.id, access=method)
        elif args.command == "prepare-read":
            result = workflow.prepare(args.index, args.id, access=method)
        elif args.command == "read-many":
            result = workflow.read_many(requests, workers=args.workers)
        elif args.command == "record":
            result = workflow.session.record(args.receipt, status=args.status, digest=args.sha256,
                                             error=args.error, based_on=args.based_on)
        elif args.command == "audit":
            result = workflow.audit()
        elif args.command == "metadata-review":
            result = workflow.session.review_metadata(args.receipt, catalog.resolve(args.index, args.id, access=method))
        else:
            if args.refresh:
                before_count = len(workflow.session.events())
                try:
                    workflow.read(args.index, args.id, access=method)
                except (OSError, ValueError):
                    # 실제 조회 실패만 관측으로 반환하고 초기화·요청 오류는 전파한다.
                    if len(workflow.session.events()) <= before_count:
                        raise
            result = workflow.session.metadata_status(catalog.resolve(args.index, args.id, access=method))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(json.dumps({"error": type(error).__name__, "message": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
