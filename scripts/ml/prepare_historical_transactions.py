#!/usr/bin/env python3
"""Prepare/verify existing local PLVR history only. No network or serving DB."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
from services.plvr_historical_dataset import build_dataset,verify_artifact,verify_source


def guard_storage(path):
    p=Path(path)
    while not p.exists():p=p.parent
    result=subprocess.run(['findmnt','-rn','-o','SOURCE','--target',str(p)],capture_output=True,text=True,check=True)
    device=result.stdout.strip().split('[',1)[0]
    if not device or device.startswith('/dev/sda') or (device.startswith('/dev/') and os.path.realpath(device).startswith('/dev/sda')):
        raise ValueError('forbidden_storage')
    return device


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    build=sub.add_parser('build');build.add_argument('--source-root',type=Path,default=Path('/srv/proptech-data/DB/實價登錄 PLVR'))
    build.add_argument('--output-parent',type=Path,required=True);build.add_argument('--as-of',required=True)
    verify=sub.add_parser('verify');verify.add_argument('--artifact',type=Path,required=True)
    source=sub.add_parser('verify-source');source.add_argument('--artifact',type=Path,required=True)
    source.add_argument('--source-root',type=Path,default=Path('/srv/proptech-data/DB/實價登錄 PLVR'))
    args=p.parse_args()
    try:
        os.nice(15)
        if args.command=='build':
            destination=args.output_parent.resolve()
            if not any(destination.is_relative_to(p) for p in (Path('/home/andy/proptech-ml-data'),Path('/srv/proptech-ml'))):
                raise ValueError('unreviewed_output_root')
            guard_storage(args.source_root)
            if guard_storage(args.output_parent)!=guard_storage(Path('/home/andy')):
                raise ValueError('output_must_use_internal_home_filesystem')
            result=build_dataset(args.source_root,args.output_parent,as_of=args.as_of,progress=lambda x:print(json.dumps(x),flush=True))
        else:
            guard_storage(args.artifact)
            if args.command=='verify-source':guard_storage(args.source_root);result=verify_source(args.artifact,args.source_root)
            else:result=verify_artifact(args.artifact)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True),flush=True);return 0
    except Exception as e:
        # No raw values, addresses, credentials or arbitrary exception messages.
        safe=str(e) if isinstance(e,ValueError) and str(e).replace('_','').isalnum() and str(e).isascii() else 'build_or_verification_failed'
        print(json.dumps({'status':'BLOCKED','reason_code':safe,'error_class':type(e).__name__}),flush=True);return 1


if __name__=='__main__':raise SystemExit(main())
