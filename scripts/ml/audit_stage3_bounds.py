#!/usr/bin/env python3
"""Read-only exact-byte lineage/parking/rights audit. No fitting or data rebuild."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import sqlite3
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from services.plvr_ml_admissibility import VERSION, public_scope, rights_eligibility
from services.valuation_ml.admission import cohort_reason, continuous_window, split_for


def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def verify_inputs(folder,verification,admission):
    summary=json.loads((folder/'summary.json').read_text())
    if (verification.get('status')!='PASS' or
        verification.get('dataset_fingerprint')!=summary['dataset_fingerprint'] or
        verification.get('clean_transactions')!=summary['counts']['clean_transactions'] or
        verification.get('logical_dataset_sha256')!=summary['logical_dataset_sha256']):
        raise ValueError('prior_full_verification_binding_required')
    complete=json.loads((folder/'COMPLETE.json').read_text())
    if (complete['dataset_fingerprint']!=summary['dataset_fingerprint'] or
        digest(folder/'summary.json')!=complete['summary_sha256']):
        raise ValueError('summary_checksum_mismatch')
    names={'coverage.json','lineage.sqlite','provenance-manifest.json','schema.json','transactions.jsonl.gz'}
    if set(summary['artifact_hashes'])!=names:raise ValueError('artifact_file_contract')
    # Current declarations cannot rebind altered bytes to a historical PASS.
    # These expected digests come from the previously committed admission.
    if (admission.get('dataset_fingerprint')!=summary['dataset_fingerprint'] or
        admission.get('source_summary_sha256')!=digest(folder/'summary.json') or
        admission.get('source_artifact_hashes')!=summary['artifact_hashes']):
        raise ValueError('prior_admission_checksum_binding_mismatch')
    for name,expected in summary['artifact_hashes'].items():
        if digest(folder/name)!=expected or expected!=admission['source_artifact_hashes'][name]:
            raise ValueError('artifact_checksum_mismatch')
    return summary,json.loads((folder/'provenance-manifest.json').read_text())


def audit(folder,verification,admission):
    started=time.monotonic();summary,manifest=verify_inputs(folder,verification,admission)
    if admission['dataset_fingerprint']!=summary['dataset_fingerprint']:
        raise ValueError('admission_fingerprint_mismatch')
    continuous_window(manifest)
    schema=json.loads((folder/'schema.json').read_text())
    per_release=defaultdict(Counter);parking=Counter();rights=Counter();basis=Counter();excluded=Counter()
    split_counts=Counter();split_hashes={s:hashlib.sha256() for s in ('train','validation','holdout')}
    n=0;admitted=0;bad_rights=0;pub=Counter();known_clean=0
    with gzip.open(folder/'transactions.jsonl.gz','rt',encoding='utf-8') as stream:
        for line in stream:
            row=json.loads(line);n+=1;release=row['provenance']['release'];profile=per_release[release]
            count=row['parking_count_reported'];key='missing' if count is None else 'reported_zero' if count==0 else 'reported_positive'
            profile['canonical_rows']+=1;profile['parking_'+key]+=1;parking[key]+=1
            basis[row['parking_basis']]+=1;rights[row['rights_status']]+=1
            pub['historical_publication_proven']+=row['historical_publication_proven'] is True
            pub['nonnull_source_release_available_at']+=row['source_release_available_at'] is not None
            known_clean+=row['official_serial']=='RPWNMLNKNHLGFBF78EA'
            reason=cohort_reason(row)
            part=None if reason else split_for(row)
            if reason or part is None:
                excluded[reason or 'source_release_later_than_split_freeze']+=1;continue
            admitted+=1;profile['admitted_rows']+=1;profile['admitted_parking_'+key]+=1
            profile['admitted_rights_'+row['rights_status']]+=1
            bad_rights+=not rights_eligibility(row['rights_status'],'reported_transfer')['eligible']
            split_counts[part]+=1;split_hashes[part].update((row['canonical_id']+'\n').encode())
    actual_split_hashes={s:h.hexdigest() for s,h in split_hashes.items()}
    if (n!=summary['counts']['clean_transactions'] or admitted!=admission['admitted_rows'] or
        dict(split_counts)!=admission['split_counts'] or actual_split_hashes!=admission['split_identity_sha256'] or
        dict(excluded)!=admission['excluded_from_v1'] or known_clean or bad_rights or any(pub.values())):
        raise ValueError('bounded_audit_cohort_or_contract_changed')
    with sqlite3.connect((folder/'lineage.sqlite').resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        db.execute('pragma query_only=ON');db.execute('pragma cache_size=-16384')
        tables=sorted(r[0] for r in db.execute("select name from sqlite_master where type='table'"))
        conflicting=list(db.execute('select official_id from identity_stats where versions<>1'))
        conflicting_clean=sum(db.execute('select count(*) from clean_transactions where official_id=?',r).fetchone()[0] for r in conflicting)
        serial='RPWNMLNKNHLGFBF78EA'
        known={'legacy_serving_row':38652,
            'raw_occurrences':db.execute('select count(*) from occurrences where official_id=?',(serial,)).fetchone()[0],
            'clean_occurrences':db.execute('select count(*) from clean_transactions where official_id=?',(serial,)).fetchone()[0],
            'admitted_occurrences':known_clean,
            'disposition':db.execute('select reason from dispositions where official_id=?',(serial,)).fetchone()[0]}
        disposition_counts=dict(db.execute('select reason,count(*) from dispositions where reason is not null group by reason'))
        schemas={}
        for release,sha,count in db.execute("select release,schema_sha256,count(*) from source_files where role='sale_main' group by release,schema_sha256 order by release"):
            schemas.setdefault(release,[]).append({'schema_sha256':sha,'sale_main_files':count})
        if conflicting_clean or len(conflicting)!=summary['counts']['conflicting_identity_groups']:
            raise ValueError('observed_conflicting_family_entered_clean')
        if known['raw_occurrences']!=1 or known['clean_occurrences'] or known['disposition']!='known_related_party_serial':
            raise ValueError('known_related_party_invariant')
        if disposition_counts!=summary['exclusions_by_reason']:raise ValueError('exclusion_disposition_mismatch')
    members=manifest['members'];cancel_members=[m['member'] for m in members if any(k in m['member'].casefold() for k in ('cancel','supersed','撤銷','解約'))]
    fields=set(schema['record_json_schema']['properties'])
    return dict(status='PASS',evidence_contract_version=VERSION,dataset_fingerprint=summary['dataset_fingerprint'],
        verification_basis='All artifact hashes rechecked and bound to prior complete row/lineage verifier; no archive rebuild.',
        verified_artifact_hashes=summary['artifact_hashes'],prior_full_verification=verification,
        publication={'decision':'BOUNDED','manifest_publication_proven':manifest['source_publication_times_proven'],
            'row_publication_profile':dict(pub),'release_count':len(manifest['releases']),
            'release_range':[manifest['releases'][0]['release'],manifest['releases'][-1]['release']],
            'sqlite_tables':tables,'cancellation_named_inventory_members':cancel_members,
            'known_revision_conflict_families':len(conflicting),'known_conflict_clean_rows':conflicting_clean,
            'exclusion_counts':disposition_counts,'main_schemas_by_release':schemas,
            'handling':'Quarantine all observed semantic-version conflicts, identity/fact ambiguity and note-tainted families. '
                'No latest-release-wins selection or disappearance-as-cancellation inference.',
            'residual_risk':'Unreported cancellation, supersession under a changed serial/fact key, or events outside retained '
                'archives may remain. Neither absence from a later release nor a build timestamp certifies current active '
                'legal state. Evaluation concerns frozen reported observations, not a cancellation-complete transaction register.'},
        parking={'decision':'EXCLUDED FROM V1','canonical_count_profile':dict(parking),
            'basis_profile':dict(basis),'retained_parking_fields':sorted(fields & {'parking_count_reported','parking_basis'}),
            'parking_price_area_retained':False,'inference_parking_fields_accepted':False,
            'interpretation':'Reported count distributions describe source values only. Missing/zero never proves absence; '
                'no parking price/area adjustment or count feature is used. Stable semantic price/area basis is unproved.'},
        rights={'decision':'RESTRICTED','canonical_rights_profile':dict(rights),'known_partial_admitted_rows':bad_rights,
            'whole_dwelling_proof_fields_retained':False,
            'interpretation':'Blank notes, residential use, building type and counts do not prove complete dwelling rights. '
                'Land ownership fractions are not dwelling transfer fractions. Unknown rights are reported-transfer '
                'observations only; explicit partial-right requests and whole-value scaling are unsupported.'},
        by_release={k:dict(v) for k,v in sorted(per_release.items())},
        impact={'canonical_rows':n,'admitted_rows':admitted,'split_counts':dict(split_counts),
            'split_identity_sha256':actual_split_hashes,'cohort_changed':False,'features_changed':False,
            'retraining_required':False,'model_artifact_regeneration_required':False,
            'reason':'Every admitted identity, split membership and existing model feature remains unchanged; only evidence '
                'and API claim boundaries are made explicit. No parameter search or holdout reuse for model selection.'},
        known_related_party=known,public_scope=public_scope(),
        resource_usage={'seconds':time.monotonic()-started,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                        'workers':1,'sqlite_cache_bytes':16*1024**2,'nice':os.getpriority(0,0)})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--artifact',type=Path,required=True)
    p.add_argument('--verification',type=Path,required=True);p.add_argument('--admission',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args();os.nice(15)
    if args.output.resolve().is_relative_to(args.artifact.resolve()):raise ValueError('immutable_source_output_forbidden')
    result=audit(args.artifact,json.loads(args.verification.read_text()),json.loads(args.admission.read_text()))
    args.output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':result['status'],'impact':result['impact'],'resource_usage':result['resource_usage']}))
