"""Idempotent offline ML-0 receipt/gate refresh. No training or network access."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from . import audit_target_reframing as staging, external_evidence as e
from . import historical as h, lineage as l, semantics as s, source_recovery as recovery
from .audit_foundation import file_sha256, read_json
from .verify_authoritative_history_builds import check_privacy


def refresh(items, receipts, evidence_root: Path, cutoff: str) -> dict:
    if l.timestamp(cutoff) is None:
        raise ValueError('cutoff_requires_timezone')
    ledger,certificates,coverage,validation=e.ingest(items,receipts,evidence_root)
    gate=h.data_gate(ledger,cutoff,history_certificate=certificates,coverage_evidence=coverage,pit_v3=True)
    selected=h.select_pit_v3(ledger,cutoff,history_certificate=certificates)['selected']
    # Independent determinism cannot be asserted by a caller flag.
    admission=e.admission(selected,gate,privacy=True,deterministic=False)
    counts={**gate['counts'],'approved_training':0}
    months=Counter(s.parse_roc_date(x['raw']['交易年月日'])['value'][:7] for x in selected)
    result={'schema_version':'ml0-external-evidence-refresh-v1','cutoff':cutoff,
        'identifier_kind':'DERIVED_RESEARCH_TRANSACTION_ID','counts':counts,
        'target_a':'BLOCKED','target_b':'BLOCKED','ml_b_admission':admission,
        'receipt_validation':validation,'pit_month_profile':h.month_profile(dict(sorted(months.items()))),
        'existing_gate':{'version':gate['version'],'target_a':gate['target_a'],
            'target_b':gate['target_b'],'chronology_viable':gate['chronology']['viable'],
            'chronology_blockers':gate['chronology']['blockers'],
            'eligible_before_independent_determinism':gate['counts']['approved_training']},
        'waterfall':gate['waterfall'],
        'inputs':{'source_ledger_sha256':h.ledger_digest(items),
                  'receipt_bundle_sha256':l.digest(receipts),
                  'receipt_contract_sha256':file_sha256(e.SCHEMA_PATH),
                  'admission_policy_sha256':file_sha256(e.POLICY_PATH)},
        'limitations':['Real authority is a reviewed upstream input, not a hash/Boolean authentication.',
            'Synthetic evidence rejected; no fixture contributes to real counts.',
            'ML-B remains blocked until independent byte equality and privacy verification complete.']}
    check_privacy(result)
    return result


def verify(first: Path, second: Path, *, items=None, receipts=None, evidence_root=None,
           recovery_manifest_sha256=None) -> dict:
    if first.resolve()==second.resolve():
        raise ValueError('independent_output_files_required')
    reports=[read_json(x,2*1024*1024) for x in (first,second)]
    for report in reports: check_privacy(report)
    if first.read_bytes()!=second.read_bytes():
        raise ValueError('deterministic_bytes_differ')
    for report in reports:
        if report['inputs']['receipt_contract_sha256']!=file_sha256(e.SCHEMA_PATH) or report['inputs']['admission_policy_sha256']!=file_sha256(e.POLICY_PATH):
            raise ValueError('frozen_contract_or_policy_changed')
    fresh=None
    if items is not None and receipts is not None and evidence_root is not None:
        fresh=refresh(items,receipts,evidence_root,reports[0]['cutoff'])
        if recovery_manifest_sha256 is not None:
            if not e.hash_valid(recovery_manifest_sha256):
                raise ValueError('fresh_source_manifest_hash_invalid')
            fresh['inputs']['source_recovery_manifest_sha256']=recovery_manifest_sha256
        for key,value in fresh.items():
            if reports[0].get(key)!=value:
                raise ValueError('fresh_source_gate_report_mismatch')
    conditions={**(fresh or reports[0])['ml_b_admission']['conditions'],
                'independent_determinism':True,'fresh_sources_revalidated':fresh is not None}
    passed=fresh is not None and all(value is True for value in conditions.values())
    return {'status':'PASS','byte_identical':True,'privacy':'PASS','output_sha256':file_sha256(first),
        'conditions':conditions,'may_ml_b_begin':passed,
        'approved_cohort':fresh['existing_gate']['eligible_before_independent_determinism'] if passed else 0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    run=sub.add_parser('refresh')
    run.add_argument('--preflight',type=Path,default=recovery.ARTIFACT_ROOT/'preflight.json')
    run.add_argument('--downloads',type=Path,default=recovery.ARTIFACT_ROOT/'downloads.json')
    run.add_argument('--receipts',type=Path,default=s.ROOT/'docs/ml/external-evidence-receipts-v1.json')
    run.add_argument('--evidence-root',type=Path,default=s.ROOT/'artifacts/ml/external-evidence/receipts')
    run.add_argument('--releases',nargs='+',default=['112S3','115S2'])
    run.add_argument('--cutoff',required=True)
    run.add_argument('--observation-at',required=True)
    run.add_argument('--output',required=True,type=Path)
    compare=sub.add_parser('verify')
    compare.add_argument('--first',required=True,type=Path)
    compare.add_argument('--second',required=True,type=Path)
    compare.add_argument('--revalidate',action='store_true',help='Rebuild source/receipt gates before any positive admission.')
    compare.add_argument('--preflight',type=Path,default=recovery.ARTIFACT_ROOT/'preflight.json')
    compare.add_argument('--downloads',type=Path,default=recovery.ARTIFACT_ROOT/'downloads.json')
    compare.add_argument('--receipts',type=Path,default=s.ROOT/'docs/ml/external-evidence-receipts-v1.json')
    compare.add_argument('--evidence-root',type=Path,default=s.ROOT/'artifacts/ml/external-evidence/receipts')
    args=parser.parse_args()
    try:
        if args.action=='verify':
            kwargs={}
            if args.revalidate:
                previous=read_json(args.first,2*1024*1024)
                config=previous['configuration']
                observed=l.timestamp(config['observation_at'])
                cutoff=l.timestamp(previous['cutoff'])
                if observed is None or cutoff is None or cutoff>observed:
                    raise ValueError('explicit_ordered_cutoff_and_observation_required')
                items,manifest,_=staging.stage_sources(read_json(args.preflight),read_json(args.downloads),
                    config['observation_at'],required_releases=tuple(config['releases']))
                if l.digest(manifest)!=previous['inputs']['source_recovery_manifest_sha256']:
                    raise ValueError('fresh_source_manifest_mismatch')
                kwargs=dict(items=items,receipts=read_json(args.receipts),evidence_root=args.evidence_root,
                            recovery_manifest_sha256=l.digest(manifest))
            result=verify(args.first,args.second,**kwargs)
        else:
            cutoff=l.timestamp(args.cutoff); observed=l.timestamp(args.observation_at)
            if cutoff is None or observed is None or cutoff>observed:
                raise ValueError('explicit_ordered_cutoff_and_observation_required')
            output=args.output.resolve()
            private=(s.ROOT/'artifacts/ml/external-evidence').resolve()
            if not output.is_relative_to(private):
                raise ValueError('private_aggregate_output_required')
            receipts=read_json(args.receipts)
            items,manifest,_=staging.stage_sources(read_json(args.preflight),read_json(args.downloads),
                args.observation_at,required_releases=tuple(args.releases))
            result=refresh(items,receipts,args.evidence_root,args.cutoff)
            result['configuration']={'releases':args.releases,'observation_at':args.observation_at}
            result['source_archives']=[{'release_id':x['source_archive_id'],'official_url':x['official_url'],
                'archive_sha256':x['sha256'],'byte_size':x['byte_size'],
                'retrieved_at':x['retrieved_at'],'classification_without_receipt':'CURRENT_ONLY',
                'license_note':'Catalog Open Data v1; no inferred reuse for requested supplements.',
                'purpose':'Offline raw/schema/detail revalidation; no historical time inferred.'}
                for x in manifest['sources'] if x['checksum_status']=='EXACT_MATCH']
            result['inputs']['source_recovery_manifest_sha256']=l.digest(manifest)
            check_privacy(result)
            payload=l.canonical_bytes(result)+b'\n'
            output.parent.mkdir(parents=True,exist_ok=True)
            if output.exists() and output.read_bytes()!=payload:
                raise ValueError('output_exists_with_different_bytes')
            if not output.exists(): output.write_bytes(payload)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
    except (OSError,ValueError,KeyError,TypeError):
        parser.exit(2,'external_evidence_refresh_failed: bounded source/receipt/time/privacy contract\n')


if __name__=='__main__':
    main()
