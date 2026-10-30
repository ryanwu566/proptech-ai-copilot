#!/usr/bin/env python3
"""Run admitted Stage 3 work offline at reduced priority with bounded threads."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='2'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=('prepare','train'))
    p.add_argument('--dataset',type=Path)
    p.add_argument('--verification',type=Path)
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--output-parent',type=Path,default=Path('/home/andy/proptech-model-artifacts'))
    args=p.parse_args();os.nice(15)
    # Dedicated local roots only. Neither source storage nor the repository is writable output.
    for dest in (args.work,args.output_parent):
        dest=dest.resolve()
        if not any(dest.is_relative_to(root) for root in
                   (Path('/home/andy/proptech-ml-data/stage3'),Path('/home/andy/proptech-model-artifacts'))):
            raise ValueError('unreviewed_ml_output_root')
    from services.valuation_ml.offline import prepare,train
    if args.operation=='prepare':
        if not args.dataset or not args.verification:
            p.error('prepare requires --dataset and --verification')
        result=prepare(args.dataset,args.work,json.loads(args.verification.read_text()))
    else:
        result=train(args.work,args.output_parent)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True),flush=True)


if __name__=='__main__':
    main()
