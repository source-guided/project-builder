#!/usr/bin/env python3
"""작업별 기본·사용자·일반 방식 선택과 연결 CLI."""

import argparse
import json
from pathlib import Path
import sys

from source_connections import Connections, DEFAULTS, offers


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    offer=sub.add_parser("offers");offer.add_argument("--query",default="");offer.add_argument("--catalog",type=Path,default=DEFAULTS)
    for name in ("show","select","discover","read","prepare-read"):
        command=sub.add_parser(name);command.add_argument("--state",type=Path,required=True)
        if name!="show":command.add_argument("--intent",required=True)
        if name=="select":
            command.add_argument("--mode",choices=("default","custom","general"),required=True)
            command.add_argument("--candidate");command.add_argument("--index")
            command.add_argument("--access",choices=("file","web","connector"))
            command.add_argument("--kind",choices=("reference","source"),default="reference")
            command.add_argument("--catalog",type=Path,default=DEFAULTS);command.add_argument("--expected-digest")
        if name=="discover":command.add_argument("--query",default="")
        if name in {"read","prepare-read"}:
            command.add_argument("--reference-index");command.add_argument("--reference-access",choices=("file","web","connector"));
            command.add_argument("--id");command.add_argument("--trace",type=Path,required=True);command.add_argument("--scope",default="local")
            command.add_argument("--source-root",type=Path,action="append",default=[])
    args=parser.parse_args()
    if args.command=="offers":result={"candidates":offers(args.query,catalog=args.catalog),"connected":False,"bodies_fetched":False}
    else:
        connections=Connections(args.state)
        if args.command=="show":result=connections.show()
        elif args.command=="select":result=connections.select(args.intent,args.mode,candidate=args.candidate,index=args.index,access=args.access,kind=args.kind,catalog=args.catalog,expected_digest=args.expected_digest)
        elif args.command=="discover":result=connections.discover(args.intent,args.query)
        else:result=connections.access(args.intent,args.trace,identifier=args.id,reference_index=args.reference_index,reference_access=args.reference_access,prepare_only=args.command=="prepare-read",scope=args.scope,source_roots=args.source_root)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    try:main()
    except (ValueError,OSError) as error:
        print(json.dumps({"error":type(error).__name__,"message":str(error)}),file=sys.stderr)
        raise SystemExit(1)
