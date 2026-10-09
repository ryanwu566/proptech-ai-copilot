"""Target B: observed transferred-area transaction labels, never dwelling proof.

Candidate extraction tolerates explicitly unresolved dwelling rights because its
estimand is the recorded transfer. PIT selection reuses the complete, strict
revision ledger. Neither this module nor a positive candidate count approves ML.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal, localcontext
import re

from . import lineage as l, plvr_raw_parser as p, semantics as s, temporal as t
from .strict_cohort import numeric_diagnostic

VERSION = 'plvr-observed-residential-transaction-v1'
TARGET_VERSION = 'observed-residential-transfer-ntd-ping-v1'
AREA_VERSION = 'reported-registered-transferred-building-no-parking-v1'
FEATURE_COLUMNS = ('county_district', 'building_type', 'area_ping', 'floor', 'prediction_year', 'prediction_month')
DETAIL_USES = {'住家用', '共有部分', '共有部份'}
STAGES = ('schema', 'source', 'geography', 'transaction', 'use', 'type', 'objects', 'details',
          'parking', 'target', 'physical')


def classify(item: dict, cutoff: str) -> dict:
    boundary = l.timestamp(cutoff)
    if boundary is None:
        raise ValueError('cutoff_requires_timezone')
    raw, context = item['raw'], item['context']
    details = item.get('details', {})
    builds, lands, parks = (details.get(k, []) for k in ('build', 'land', 'park'))
    complete, unique = item.get('details_complete') is True, item.get('main_key_unique') is True
    geo = s.normalize_geography(raw.get('縣市', ''), raw.get('鄉鎮市區', ''), item['member_name'])
    effective = s.parse_roc_date(raw.get('交易年月日'))
    available = l.timestamp(item.get('source_release_available_at'))
    reasons = {k: [] for k in STAGES}
    def add(stage, condition, reason):
        if condition:
            reasons[stage].append(reason)
    add('schema', bool(item.get('parse_error')), 'CSV_FIELD_COUNT')
    add('schema', effective is None, 'INVALID_DATE')
    add('schema', bool(effective and effective['precision'] != 'day'), 'TRANSACTION_DAY_REQUIRED')
    if effective and effective['precision'] == 'day':
        day = date.fromisoformat(effective['value'])
        add('schema', day > boundary.astimezone(t.TAIPEI).date()
            or bool(available and day > available.astimezone(t.TAIPEI).date()), 'EFFECTIVE_AFTER_AVAILABILITY_OR_CUTOFF')
    add('source', item.get('source_dataset_id') != s.SOURCE_DATASET_ID
        or not s.text(raw.get('編號')) or context.get('member_name') != item['member_name']
        or type(item.get('physical_row_number')) is not int or item['physical_row_number'] < 1
        or not all(isinstance(item.get(k), str) and re.fullmatch('[0-9a-f]{64}', item[k])
                   for k in ('archive_sha256', 'member_sha256'))
        or not s.evidence_valid(context.get('schema_evidence'))
        or not s.text(context.get('source_schema_version')), 'UNKNOWN_SOURCE_IDENTITY')
    add('geography', not geo['source_proven'], 'INVALID_GEOGRAPHY')
    add('transaction', raw.get('交易標的') != '房地(土地+建物)', 'UNSUPPORTED_TRANSACTION_TYPE')
    add('use', raw.get('主要用途') != '住家用', 'NON_RESIDENTIAL_USE')
    add('type', s.text(raw.get('建物型態')) not in s.TYPES, 'UNSUPPORTED_BUILDING_TYPE')
    counts = s.parse_counts(raw.get('交易筆棟數'))
    add('objects', counts is None, 'OBJECT_COUNTS_UNPARSEABLE')
    if counts:
        add('objects', counts[0] < 1, 'NO_REPORTED_LAND')
        add('objects', counts[1] != 1, 'REPORTED_BUILDING_COUNT_NOT_ONE')
    add('details', not complete or not unique or not builds or not lands, 'INCOMPLETE_OR_AMBIGUOUS_DETAIL_JOIN')
    add('details', any(s.text(x.get('主要用途')) not in DETAIL_USES for x in builds)
        or not any(x.get('主要用途') == '住家用' for x in builds), 'UNSUPPORTED_OR_MIXED_DETAIL_USE')
    add('details', any(len({l.digest(x) for x in rows}) != len(rows) for rows in (builds, lands, parks)), 'DUPLICATE_DETAIL_PAYLOAD')
    area = s.number(raw.get('建物移轉總面積平方公尺'))
    portions = [s.number(x.get('建物移轉面積平方公尺')) for x in builds]
    with localcontext() as ctx:
        ctx.prec = 28
        add('details', not portions or any(x is None or x <= 0 for x in portions)
            or area is None or area <= 0
            or abs(sum(x for x in portions if x is not None)-area) > max(Decimal('0.01'), Decimal('0.001')*area),
            'TRANSFERRED_AREA_DETAIL_MISMATCH')
    parking = p.parking_state(raw, parks, builds, complete, unique, context=context)
    add('parking', parking != 'NO_PARKING_CONFIRMED', parking if parking != 'UNKNOWN' else 'PARKING_UNKNOWN')
    numeric = numeric_diagnostic(raw)
    add('target', bool(numeric['reason']), numeric['reason'])
    add('target', not s.text(raw.get('單價元平方公尺')), 'OFFICIAL_UNIT_PRICE_REQUIRED')
    add('target', item.get('area_contract') != {'field': '建物移轉總面積平方公尺', 'unit': 'm²'}
        or context.get('area_basis') != s.AREA_VERSION or not s.evidence_valid(context.get('area_evidence')), 'AREA_CONTRACT_UNPROVEN')
    floor, total = s.parse_floor(raw.get('移轉層次')), s.parse_floor(raw.get('總樓層數'))
    add('physical', floor is None or total is None or floor > total, 'FLOOR_AMBIGUOUS')
    add('physical', '備註' not in raw or bool(s.text(raw.get('備註'))), 'REPORTED_NOTE_REQUIRES_REVIEW')
    all_reasons = [v for stage in STAGES for v in reasons[stage]]
    target = None
    if not all_reasons:
        # Existing arithmetic proves only field/unit/no-parking semantics. No
        # rights or single-dwelling claim is added to its numerical result.
        target = s.construct_target(raw, context)
        if not target['valid']:
            raise ValueError('target_guard_disagrees_with_candidate_predicates')
        target.update(target_version=TARGET_VERSION, area_version=AREA_VERSION,
                      target_method='recorded_gross_consideration_over_reported_transferred_area')
    return {'structurally_valid': not any(reasons[k] for k in ('schema', 'source', 'geography')),
            'target_valid': not all_reasons, 'first_reason': all_reasons[0] if all_reasons else None,
            'all_reasons': all_reasons, 'stage_reasons': reasons, 'geography': geo,
            'effective_period': effective, 'parking': parking, 'target': target,
            'observation_unit': 'reported_transaction_occurrence',
            'rights_status': 'UNVERIFIED_COMPLETE_DWELLING_RIGHTS',
            'dwelling_status': 'UNVERIFIED_REGISTERED_UNIT_COUNT',
            'special_status': 'NO_REPORTED_NOTE_NOT_PROOF_OF_ORDINARY_SALE',
            'detail_composition': 'MULTIPLE_REGISTERED_PORTIONS_UNIT_ROLES_UNVERIFIED' if len(builds) > 1
                                  else 'SINGLE_DETAIL_PORTION_UNIT_COUNT_UNVERIFIED',
            'building_detail_rows': len(builds), 'land_detail_rows': len(lands), 'version': VERSION}


def feature_values(item: dict, target: dict) -> dict:
    raw = item['raw']
    geo = s.normalize_geography(raw.get('縣市', ''), raw.get('鄉鎮市區', ''), item['member_name'])
    effective = s.parse_roc_date(raw['交易年月日'])
    return {'county_district': geo['city']+'/'+geo['district'],
            'building_type': s.TYPES[s.text(raw['建物型態'])], 'area_ping': target['area_ping'],
            'floor': s.parse_floor(raw['移轉層次']), 'prediction_year': int(effective['value'][:4]),
            'prediction_month': int(effective['value'][5:7])}


def build_candidates(items: list[dict], cutoff: str) -> dict:
    if len(items) > 100000:
        raise ValueError('bounded_main_rows_exceeded')
    ordered = sorted(items, key=lambda x: l.canonical_bytes(l.identify(x)))
    occurrence_ids = [l.identify(x)['occurrence_id'] for x in ordered]
    if len(set(occurrence_ids)) != len(occurrence_ids):
        raise ValueError('duplicate_physical_occurrence_input')
    # Resolve identity and revisions over ALL records before eligibility.
    selected = l.select_as_of(ordered, cutoff)
    dispositions = {x['occurrence_id']: x for x in selected['dispositions']}
    ledger, candidates, exclusions, rows = [], [], [], []
    evaluations = []
    for item in ordered:
        identity = l.identify(item)
        verdict = classify(item, cutoff)
        pit_reason = dispositions[identity['occurrence_id']]['reason']
        pit_valid = verdict['target_valid'] and pit_reason is None
        entry = {**identity, 'release_id': item['release_id'], **verdict,
                 'point_in_time_valid': pit_valid, 'pit_reason': pit_reason,
                 'chronologically_evaluable': False, 'approved_training': False}
        ledger.append(entry); evaluations.append(verdict)
        if verdict['target_valid']:
            candidates.append({**identity, 'release_id': item['release_id'],
                               'release_available_at': item.get('source_release_available_at'),
                               'effective_period': verdict['effective_period'], 'target': verdict['target'],
                               'features': feature_values(item, verdict['target']),
                               'rights_status': verdict['rights_status'], 'dwelling_status': verdict['dwelling_status'],
                               'detail_composition': verdict['detail_composition'],
                               'point_in_time_valid': pit_valid, 'approved_training': False})
        else:
            exclusions.append({**identity, 'first_reason': verdict['first_reason'], 'all_reasons': verdict['all_reasons']})
        if pit_valid:
            rows.append({**item, **identity})
    active = list(range(len(evaluations))); funnel = []
    for stage in STAGES:
        rejected = [i for i in active if evaluations[i]['stage_reasons'][stage]]
        reasons = Counter(evaluations[i]['stage_reasons'][stage][0] for i in rejected)
        blocked = set(rejected)
        remaining = [i for i in active if i not in blocked]
        funnel.append({'stage': stage, 'input_count': len(active), 'accepted_count': len(remaining),
                       'excluded_count': len(rejected), 'reason_breakdown': dict(sorted(reasons.items()))})
        active = remaining
    assert len(items) == len(candidates)+len(exclusions) == len(ledger)
    assert len(candidates) == len(active)
    assert len({x['transaction_family_id'] for x in rows}) == len(rows)
    return {'ledger': ledger, 'candidates': candidates, 'candidate_exclusions': exclusions,
            'selected_rows': rows, 'funnel': funnel, 'revision_dispositions': selected['dispositions'],
            'relations': selected['relations'],
            'counts': {'raw_observations': len(items),
                       'structurally_valid_observations': sum(x['structurally_valid'] for x in ledger),
                       'target_valid_candidates': len(candidates), 'point_in_time_valid_observations': len(rows)}}


def baseline_history(items: list[dict], *, prediction_at: str, fitting_cutoff: str,
                     subject_family: str, fitting_versions: dict[str, str] | None) -> list[dict]:
    prediction, boundary = l.timestamp(prediction_at), l.timestamp(fitting_cutoff)
    if prediction is None or boundary is None:
        raise ValueError('explicit_timezone_instants_required')
    if not isinstance(fitting_versions, dict):
        raise ValueError('frozen_fit_versions_required')
    # Selector is inclusive; baseline use is strictly before either freeze.
    cutoff = (min(prediction, boundary)-timedelta(microseconds=1)).isoformat()
    cohort = build_candidates(items, cutoff)
    result = []
    for row in cohort['selected_rows']:
        family = row['transaction_family_id']
        effective = s.parse_roc_date(row['raw'].get('交易年月日'))
        if (family != subject_family and fitting_versions.get(family) == row['version_id']
                and datetime.fromisoformat(effective['value']+'T00:00:00+08:00') < prediction):
            result.append(row)
    return sorted(result, key=lambda x: (x['transaction_family_id'], x['version_id']))
