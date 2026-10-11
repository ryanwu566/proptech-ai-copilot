"""Reviewed official evidence ingestion. Structural checks never authenticate authority.

Real input requires a human data steward to inspect the retained official proof
and its precise scope. Synthetic acceptance exists only for isolated unit tests.
No public report contains transaction, object, party or address identifiers.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import re
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

from . import historical as h, lineage as l, observed_transaction as b
from . import rights_dwelling as rights, semantics as s, temporal as t
from .acquire_external_metadata import official_url
from .audit_foundation import file_sha256, read_json

VERSION = 'ml-external-evidence-v1'
SCHEMA_PATH = s.ROOT / 'docs/ml/contracts/external-evidence-v1.schema.json'
POLICY_PATH = s.ROOT / 'docs/ml/contracts/ml-b-admission-v2.json'
SCHEMA = read_json(SCHEMA_PATH)
VALIDATORS = {name:Draft202012Validator(schema, format_checker=FormatChecker())
              for name, schema in SCHEMA['$defs'].items()}
AUTHORITY_HOSTS = {
    'MOI_LAND': ('plvr.land.moi.gov.tw','lvr.land.moi.gov.tw','www.land.moi.gov.tw',
                 'www.moi.gov.tw','ws.moi.gov.tw','data.gov.tw'),
    'MODA': ('data.gov.tw','file.data.gov.tw'),
    'NLSC': ('www.nlsc.gov.tw','maps.nlsc.gov.tw','whgis-nlsc.moi.gov.tw','ws.moi.gov.tw'),
    'TAIPEI_LAND': ('land.gov.taipei','lda.land.gov.taipei','w3.land.gov.taipei'),
    'NEW_TAIPEI_LAND': ('www.land.ntpc.gov.tw','www.tamsui.land.ntpc.gov.tw',
                        'www-ws.land.ntpc.gov.tw','data.ntpc.gov.tw'),
    'TAIPEI_BUILDING': ('cmo.gov.taipei','www.dbaweb.tcg.gov.tw','service.gov.taipei'),
    'NEW_TAIPEI_BUILDING': ('service.ntpc.gov.tw','www.publicwork.ntpc.gov.tw','www.bim.ntpc.gov.tw'),
}


def hash_valid(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def retained_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or '\\' in relative or ':' in relative:
        raise ValueError('RETAINED_PATH_INVALID')
    path = Path(relative)
    root = root.resolve()
    resolved = (root / path).resolve()
    if path.is_absolute() or '..' in path.parts or not resolved.is_relative_to(root):
        raise ValueError('RETAINED_PATH_INVALID')
    if not resolved.is_file() or not 1 <= resolved.stat().st_size <= 2*1024*1024:
        raise ValueError('RETAINED_ARTIFACT_UNAVAILABLE_OR_UNBOUNDED')
    return resolved


def validate_receipt(receipt, root: Path, *, synthetic_test=False) -> dict:
    """Validate exact retained bytes and consistency; trust originates in review."""
    reasons = set()
    if not isinstance(receipt, dict) or receipt.get('receipt_type') not in VALIDATORS:
        return {'valid':False, 'reasons':['RECEIPT_TYPE_INVALID']}
    r = receipt; kind = r['receipt_type']; validator = VALIDATORS[kind]
    errors = list(validator.iter_errors(r))
    if errors:
        reasons.add('CONTRACT_SCHEMA_INVALID')
        reason_by_field = {'published_at':'PUBLICATION_TIME_REQUIRED',
            'effective_at':'EFFECTIVE_TIME_REQUIRED','evidence_sha256':'EVIDENCE_HASH_INVALID',
            'license':'LICENSE_UNPROVEN','verification':'AUTHORITY_UNREVIEWED',
            'scope':'SCOPE_INVALID','privacy':'PERSONAL_DATA_FORBIDDEN',
            'proof_class':'HISTORICAL_PUBLICATION_UNPROVEN',
            'exact_byte_publication_binding':'HISTORICAL_PUBLICATION_UNPROVEN'}
        for error in errors:
            if error.path and error.path[0] in reason_by_field:
                reasons.add(reason_by_field[error.path[0]])
    if set(r) - set(SCHEMA['$defs'][kind]['properties']):
        reasons.add('UNDECLARED_FIELDS')
    if errors:
        return {'valid':False,'reasons':sorted(reasons)}
    if r.get('synthetic') is not False and not (synthetic_test is True and r.get('synthetic') is True):
        reasons.add('SYNTHETIC_NOT_REAL_EVIDENCE')
    if r.get('privacy') != 'NON_PERSONAL':
        reasons.add('PERSONAL_DATA_FORBIDDEN')
    url = r.get('official_url', '')
    if (not official_url(url) or urlsplit(url).hostname not in AUTHORITY_HOSTS.get(r.get('source_authority'), ())):
        reasons.add('OFFICIAL_SOURCE_INVALID')
    license_ = r.get('license')
    if (not isinstance(license_, dict) or license_.get('status') != 'RESEARCH_ALLOWED'
            or license_.get('reuse_scope') not in {'RESEARCH_ONLY','OPEN_DATA_V1'}
            or not official_url(license_.get('terms_url'))):
        reasons.add('LICENSE_UNPROVEN')
    review = r.get('verification')
    if (not isinstance(review, dict) or review.get('status') != 'REVIEWED_AUTHORITY'
            or not review.get('reviewer_role') or not review.get('basis')):
        reasons.add('AUTHORITY_UNREVIEWED')
    scope = r.get('scope')
    if (not isinstance(scope, dict) or scope.get('dataset_id') != s.SOURCE_DATASET_ID
            or not isinstance(scope.get('county_codes'),list) or not scope['county_codes']
            or not set(scope['county_codes']) <= {'a','f'}
            or not isinstance(scope.get('release_ids'),list) or not scope['release_ids']):
        reasons.add('SCOPE_INVALID')
    retrieved = l.timestamp(r.get('retrieved_at'))
    published = l.timestamp(r.get('published_at'))
    effective = l.timestamp(r.get('effective_at'))
    if published is None:
        reasons.add('PUBLICATION_TIME_REQUIRED')
    if effective is None:
        reasons.add('EFFECTIVE_TIME_REQUIRED')
    if retrieved is None or (published is not None and published > retrieved):
        reasons.add('RETRIEVAL_TIME_INVALID')
    if not hash_valid(r.get('evidence_sha256')):
        reasons.add('EVIDENCE_HASH_INVALID')
    try:
        proof = retained_file(root, r.get('retained_path'))
        if proof.stat().st_size != r.get('evidence_bytes') or file_sha256(proof) != r.get('evidence_sha256'):
            reasons.add('RETAINED_BYTES_MISMATCH')
    except (ValueError, OSError) as exc:
        reasons.add(str(exc) if isinstance(exc,ValueError) else 'RETAINED_ARTIFACT_UNAVAILABLE_OR_UNBOUNDED')
    if kind == 'HistoricalPublicationReceipt':
        if (r.get('proof_class') not in {'AUTHENTICATED_HISTORICAL','SUPPORTED_HISTORICAL'}
                or r.get('exact_byte_publication_binding') is not True):
            reasons.add('HISTORICAL_PUBLICATION_UNPROVEN')
        if isinstance(scope,dict) and r.get('release_id') not in scope.get('release_ids',[]):
            reasons.add('RELEASE_SCOPE_MISMATCH')
    elif kind == 'TransactionLineageReceipt' and not errors:
        for event in r['events']:
            if (event['later_version_id'] != event['version_id']
                    or event['release_id'] not in r['scope']['release_ids']
                    or event['cancelled'] != (event['event_kind']=='CANCELLATION')
                    or (event['event_kind']=='ORIGINAL' and event['previous_version_id'] is not None)
                    or (event['event_kind'] in {'REVISION','CANCELLATION','REPLACEMENT'}
                        and not event['previous_version_id'])
                    or ((event['event_kind']=='DUPLICATE_RELEASE') != bool(event['duplicate_of_occurrence_id']))
                    or (event['event_kind']=='REPLACEMENT' and not event['replaces_family_id'])
                    or (event['event_kind']!='REPLACEMENT' and event['replaces_family_id'] is not None)
                    or l.timestamp(event['effective_at']) > l.timestamp(event['published_at'])
                    or l.timestamp(event['published_at']) > retrieved):
                reasons.add('EVENT_RELATION_INVALID')
    elif kind == 'RightsUnitMappingReceipt' and not errors:
        objects = r['building_objects']
        if (len({x['object_id'] for x in objects}) != len(objects)
                or sum(x['dwelling_units'] for x in objects) != r['registered_unit_count']
                or any(rights.fraction(x['transferred_fraction']) is None
                       or rights.fraction(x['required_fraction']) is None for x in objects)):
            reasons.add('RIGHTS_OBJECT_MAPPING_INVALID')
    return {'valid':not reasons, 'reasons':sorted(reasons)}


def reference(r):
    return {'sha256':r['evidence_sha256'],'locator':r['official_url']+'#'+r['receipt_id'], 'version':r['version']}


def in_scope(r, x):
    return (x.get('source_dataset_id') == r['scope']['dataset_id']
            and x.get('release_id') in r['scope']['release_ids']
            and x.get('member_name','')[:1] in r['scope']['county_codes'])


def ingest(items: list[dict], receipts: list[dict], root: Path, *, synthetic_test=False):
    """Only reviewed receipts can supply authority to the unfiltered source ledger.

    An invalid or conflicting bundle revokes all authority for this refresh; it
    cannot quietly drop a cancellation and resurrect an earlier sale.
    """
    if not isinstance(receipts,list) or len(receipts)>1024 or len(items)>100000:
        raise ValueError('bounded_ingestion_required')
    xs = deepcopy(items)
    # Staged claims cannot bypass the receipt boundary.
    for x in xs:
        for key in ('historical_proof_record','publication_evidence','revision_kind','revision_evidence',
                    'replaces_family_id','rights_supplement'):
            x.pop(key,None)
        x.update(identity_evidence=None, cancellation_state_evidenced=False,
                 supersedes_version_id=None, cancelled=False, source_release_available_at=None,
                 availability_evidence=None)
        x.setdefault('required_source_dependencies', [])
        x['context'].update(full_rights=None,one_dwelling=None,rights_evidence=None)
        scope={'archive_sha256':x['archive_sha256'],'member_name':x['member_name'],
               'physical_row_number':x['physical_row_number'],
               'schema_sha256':x['context'].get('schema_evidence',{}).get('sha256')}
        native = rights.classify(x['raw'],x['details']['build'],x['details']['land'],
                                complete=x['details_complete'],unique=x['main_key_unique'],scope=scope)
        x['semantic'] = {**x.get('semantic',{}),**native}
    diagnostics = {'supplied_receipts':len(receipts),'accepted_receipts':0,
                   'rejected_receipts':0,'rejection_reasons':{},'history_certificates':0,
                   'identifier_kind':'DERIVED_RESEARCH_TRANSACTION_ID'}
    reasons = Counter()
    if any(not isinstance(x['required_source_dependencies'],list) or x['required_source_dependencies'] for x in xs):
        reasons['UNREVIEWED_STAGED_EXTERNAL_DEPENDENCIES'] += 1
    ids = [r.get('receipt_id') if isinstance(r,dict) else None for r in receipts]
    for r in receipts:
        validation = validate_receipt(r,root,synthetic_test=synthetic_test)
        if not validation['valid']:
            diagnostics['rejected_receipts'] += 1
            reasons.update(validation['reasons'])
    if len(set(ids)) != len(ids):
        reasons['DUPLICATE_RECEIPT_ID'] += 1
    def blocked(reason=None):
        if reason:
            reasons[reason] += 1
        diagnostics.update(accepted_receipts=0,rejection_reasons=dict(sorted(reasons.items())))
        # Restart from the untrusted ledger with no receipts to revoke enrichment.
        empty = ingest(items,[],root)[0] if receipts else xs
        return empty,None,None,diagnostics
    if reasons:
        return blocked()
    groups=defaultdict(list)
    for r in receipts:
        groups[r['receipt_type']].append(r)
    pubs=groups['HistoricalPublicationReceipt']; namespaces=groups['TransactionNamespaceAuthority']
    lineages=groups['TransactionLineageReceipt']; mappings=groups['RightsUnitMappingReceipt']
    for x in xs:
        matches=[r for r in pubs if in_scope(r,x) and r['archive_sha256']==x['archive_sha256']]
        if len(matches)>1:
            return blocked('CONFLICTING_PUBLICATION_RECEIPTS')
        if matches:
            r=matches[0]
            x['historical_proof_record']={'source_id':r['release_id'],'hash':r['archive_sha256'],
                'official_url':r['official_url'],'publication_timestamp':r['published_at'],
                'retrieval_timestamp':r['retrieved_at'],'proof_class':r['proof_class'],
                'proof_basis':r['verification']['basis'],'exact_byte_publication_binding':True,
                'time_quality':r['time_quality'],'evidence':reference(r)}
        namespace_matches=[r for r in namespaces if in_scope(r,x)]
        if len(namespace_matches)>1:
            return blocked('CONFLICTING_NAMESPACE_RECEIPTS')
        if namespace_matches:
            x['identity_evidence']=reference(namespace_matches[0])
    events={}
    for r in lineages:
        for event in r['events']:
            oid=event['occurrence_id']
            if oid in events and events[oid][0] != event:
                return blocked('CONFLICTING_LINEAGE_EVENTS')
            events[oid]=(event,r)
    # Duplicate occurrence linkage never creates a semantic supersession edge.
    for event,_ in events.values():
        if event['event_kind']=='DUPLICATE_RELEASE':
            original=events.get(event['duplicate_of_occurrence_id'])
            if (original is None or original[0]['event_kind']=='DUPLICATE_RELEASE'
                    or original[0]['version_id']!=event['version_id']
                    or original[0]['previous_version_id']!=event['previous_version_id']
                    or original[0]['cancelled']!=event['cancelled']
                    or l.timestamp(original[0]['published_at'])>l.timestamp(event['published_at'])):
                return blocked('DUPLICATE_OCCURRENCE_BINDING_INVALID')
    applied=set()
    for x in xs:
        oid=l.identify(x)['occurrence_id']
        if oid in events:
            event,r=events[oid]
            if not in_scope(r,x) or event['archive_sha256']!=x['archive_sha256'] or event['release_id']!=x['release_id']:
                return blocked('EVENT_BYTE_SCOPE_MISMATCH')
            x['cancelled']=event['cancelled']
            if event['version_id']!=l.identify(x)['version_id']:
                return blocked('EVENT_VERSION_BINDING_MISMATCH')
            when=l.timestamp(h.publication(x).get('available_at'))
            if when is None or l.timestamp(event['published_at'])>when:
                return blocked('EVENT_PUBLICATION_BINDING_MISMATCH')
            x['supersedes_version_id']=event['previous_version_id']
            x['cancellation_state_evidenced']=True
            semantic_event=events[event['duplicate_of_occurrence_id']][0] if event['event_kind']=='DUPLICATE_RELEASE' else event
            kind=semantic_event['event_kind']
            if kind in {'REVISION','CANCELLATION','REPLACEMENT'}:
                x['revision_kind']={'REVISION':'CORRECTION','CANCELLATION':'CANCELLATION','REPLACEMENT':'SUPERSESSION'}[kind]
                x['revision_evidence']=reference(r)
            if kind=='REPLACEMENT':
                x['replaces_family_id']=semantic_event['replaces_family_id']
            applied.add(oid)
        matched=[r for r in mappings if r['occurrence_id']==oid]
        if len(matched)>1:
            return blocked('CONFLICTING_RIGHTS_RECEIPTS')
        if matched:
            r=matched[0]
            mapping_scope={'archive_sha256':x['archive_sha256'],'member_name':x['member_name'],
                'physical_row_number':x['physical_row_number'],
                'schema_sha256':x['context'].get('schema_evidence',{}).get('sha256')}
            if not in_scope(r,x) or r['mapping_scope']!=mapping_scope:
                return blocked('RIGHTS_SCOPE_MISMATCH')
            supplement={k:r[k] for k in ('main_sha256','build_sha256','land_sha256','building_objects','land_interests')}
            supplement.update(scope=r['mapping_scope'],evidence=reference(r))
            result=rights.classify(x['raw'],x['details']['build'],x['details']['land'],
                complete=x['details_complete'],unique=x['main_key_unique'],scope=mapping_scope,supplement=supplement)
            if not result['supplement_valid']:
                return blocked('RIGHTS_PAYLOAD_OR_ROLE_MISMATCH')
            x['semantic'].update(result)
            x['context'].update(full_rights=result['rights']=='FULL_RIGHTS_CONFIRMED',
                one_dwelling=result['dwelling']=='SINGLE_DWELLING_CONFIRMED',rights_evidence=reference(r))
            x['required_source_dependencies'].append({'source_id':r['receipt_id'],'sha256':r['evidence_sha256'],
                'publication_evidence':{'classification':'AUTHENTICATED','release_id':r['receipt_id'],
                    'archive_sha256':r['evidence_sha256'],'quality':'EXACT_PUBLICATION_TIME',
                    'value':max(l.timestamp(r['published_at']),l.timestamp(r['effective_at'])).isoformat(),
                    'evidence':reference(r)}})
    if set(events)!=applied:
        return blocked('EVENT_LOCATOR_NOT_IN_FULL_LEDGER')
    certificates=[]
    for r in lineages:
        cutoff=l.timestamp(r['cutoff'])
        visible=[x for x in xs if t.available_by(h.publication(x),r['cutoff'])]
        if (r['visible_ledger_sha256']!=h.ledger_digest(visible)
                or any(not in_scope(r,x) or not x['identity_evidence']
                       or not x['cancellation_state_evidenced'] for x in visible)
                or len({e['occurrence_id'] for e in r['events'] if l.timestamp(e['published_at'])<=cutoff})
                   != len(visible)):
            return blocked('COMPLETE_VISIBLE_LEDGER_BINDING_MISMATCH')
        certificates.append({'classification':'AUTHENTICATED','evidence':reference(r),
            'cutoff':r['cutoff'],'source_dataset_id':s.SOURCE_DATASET_ID,
            'visible_ledger_sha256':r['visible_ledger_sha256'],'stable_namespace':True,
            'complete_revision_cancellation_history':True,'replacement_links_complete':True})
    if len({l.timestamp(c['cutoff']) for c in certificates})!=len(certificates):
        return blocked('DUPLICATE_HISTORY_CUTOFF')
    diagnostics.update(accepted_receipts=len(receipts),history_certificates=len(certificates))
    # Coverage remains subject to the existing per-freeze and full-ledger gate.
    coverage=reference(lineages[0]) if lineages else None
    return xs, {'certificates':certificates} if certificates else None, coverage, diagnostics


def admission_policy():
    return read_json(POLICY_PATH)


def admission(pit: list[dict], gate: dict, *, privacy: bool, deterministic: bool) -> dict:
    policy=admission_policy(); months=Counter(); cities=Counter()
    for x in pit:
        effective=s.parse_roc_date(x['raw'].get('交易年月日'))
        city=s.source_county(x['member_name'])
        if effective:
            month=effective['value'][:7]; months[month]+=1; cities[(month,city)]+=1
    keys=sorted(months)
    numbers=[int(m[:4])*12+int(m[5:]) for m in keys]
    conditions={'minimum_pit_rows':len(pit)>=policy['minimum_pit_rows'],
        'usable_months':len(keys)>=policy['minimum_usable_months'],
        'contiguous_months':len(keys)>=policy['minimum_contiguous_months']
            and all(y==x+1 for x,y in zip(numbers,numbers[1:])),
        'city_month_representation':bool(keys) and all(cities[(m,c)]>=policy['minimum_city_month_rows']
            for m in keys for c in policy['required_cities']),
        'existing_complete_history_and_chronology':gate['chronology']['viable'] is True,
        'privacy':privacy is True,'independent_determinism':deterministic is True,
        'target_contracts_frozen':b.TARGET_VERSION==policy['target_b_contract']
            and s.TARGET_VERSION==policy['target_a_contract']}
    passed=all(conditions.values())
    return {'version':policy['version'],'may_begin':passed,'result':'PASS' if passed else 'BLOCKED',
            'conditions':conditions,'blockers':sorted(k for k,v in conditions.items() if not v),
            'usable_months':len(keys),'pit_rows':len(pit)}
