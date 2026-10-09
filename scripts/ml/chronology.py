"""Conservative four-block proposals and leakage-safe inputs for future baselines."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from . import lineage as l, semantics as s, temporal as t
from .strict_cohort import build_cohort

VERSION='plvr-contiguous-four-block-maturity-v1'


def _month_number(month):
    year,value=map(int,month.split('-'))
    return year*12+value-1


def _month_start(month):
    return datetime.fromisoformat(month+'-01T00:00:00+08:00')


def split_rows_from_items(items: list[dict]) -> list[dict]:
    rows=[]
    for item in items:
        geo=s.normalize_geography(item['raw'].get('縣市',''),item['raw'].get('鄉鎮市區',''),item['member_name'])
        effective=s.parse_roc_date(item['raw']['交易年月日'])
        rows.append({'family_id':item['transaction_family_id'],'effective_date':effective['value'],
            'precision':effective['precision'],'available_at':item['source_release_available_at'],
            'source_record_version_id':item['version_id'],'physical_occurrence_id':item['occurrence_id'],
            'county_district':geo['city']+'/'+geo['district'],'building_type':s.TYPES[s.text(item['raw']['建物型態'])]})
    return rows


def design_splits(rows: list[dict], *, coverage_evidence: dict | None,
                  ledger_items: list[dict] | None = None,
                  label_observation_cutoff: str | None = None,
                  min_month_rows: int = 20, min_block_subgroup_rows: int = 20,
                  cohort_selector=build_cohort) -> dict:
    blockers=[]; blocks={}; assignments=[]
    months=Counter(x['effective_date'][:7] for x in rows)
    keys=sorted(months)
    if not rows: blockers.append('EMPTY_COHORT')
    if not isinstance(ledger_items,list): blockers.append('HISTORICAL_MEMBERSHIP_UNPROVEN')
    if not s.evidence_valid(coverage_evidence): blockers.append('COMPLETE_MATURE_COVERAGE_UNPROVEN')
    if len(keys)<21: blockers.append('INSUFFICIENT_CHRONOLOGICAL_MONTHS')
    if any(months[x]<min_month_rows for x in keys): blockers.append('INSUFFICIENT_MONTH_VOLUME')
    if any(_month_number(b)!=_month_number(a)+1 for a,b in zip(keys,keys[1:])):
        blockers.append('DISCONTINUOUS_MONTHS')
    if any(x.get('precision')!='day' for x in rows): blockers.append('TRANSACTION_DAY_REQUIRED')
    if len({x['family_id'] for x in rows})!=len(rows): blockers.append('DUPLICATE_FAMILY')
    label_boundary=l.timestamp(label_observation_cutoff)
    if label_boundary is None: blockers.append('LABEL_OBSERVATION_CUTOFF_UNPROVEN')
    elif keys:
        next_month_number=_month_number(keys[-1])+1
        test_month_end=_month_start(f'{next_month_number//12:04d}-{next_month_number%12+1:02d}')
        if label_boundary<test_month_end:
            blockers.append('INCOMPLETE_TEST_OBSERVATION_PERIOD')
    if any(not s.text(x.get('source_record_version_id')) or not s.text(x.get('physical_occurrence_id')) for x in rows):
        blockers.append('FROZEN_VERSION_PROVENANCE_MISSING')
    if not blockers:
        ledger_hash=l.digest(ledger_items)
        ranges={'TRAIN':keys[:-9],'VALIDATION':keys[-9:-6],'CALIBRATION':keys[-6:-3],'TEST':keys[-3:]}
        # Scoring labels may mature after the test prediction period, under an
        # explicit separate observation cutoff; this never grants fitting access.
        freezes={'TRAIN':_month_start(ranges['VALIDATION'][0]),
                 'VALIDATION':_month_start(ranges['CALIBRATION'][0]),
                 'CALIBRATION':_month_start(ranges['TEST'][0]),'TEST':label_boundary}
        for name,periods in ranges.items():
            selected=[x for x in rows if x['effective_date'][:7] in periods]
            # Re-select the complete supplied ledger at each block freeze.
            # Later cancellations/corrections must not silently change an earlier
            # population. Reject a global-cutoff proposal that differs; callers
            # must supply historical populations before any positive handoff.
            cutoff=freezes[name] if name=='TEST' else freezes[name]-timedelta(microseconds=1)
            frozen=cohort_selector(ledger_items,cutoff.isoformat())
            historical=[x for x in split_rows_from_items(frozen['selected_rows'])
                        if x['effective_date'][:7] in periods]
            if sorted(map(l.canonical_bytes,selected))!=sorted(map(l.canonical_bytes,historical)):
                blockers.append('HISTORICAL_MEMBERSHIP_DIFFERS')
            if any(l.timestamp(x.get('available_at')) is None
                   or (l.timestamp(x['available_at'])>freezes[name] if name=='TEST' else
                       l.timestamp(x['available_at'])>=freezes[name]) for x in selected):
                blockers.append('RELEASE_LAG_AT_FREEZE')
            subgroups=Counter((x['county_district'],x['building_type']) for x in selected)
            all_subgroups={(x['county_district'],x['building_type']) for x in rows}
            if any(subgroups[g]<min_block_subgroup_rows for g in all_subgroups):
                blockers.append('INSUFFICIENT_BLOCK_SUBGROUP_VOLUME')
            blocks[name]=[periods[0],periods[-1]]
            assignments.extend({'family_id':x['family_id'],'split':name,
                'source_record_version_id':x['source_record_version_id'],
                'physical_occurrence_id':x['physical_occurrence_id'],
                'release_available_at':x['available_at'],'effective_date':x['effective_date'],
                'block_freeze_at':freezes[name].isoformat(),
                'selection_cutoff':cutoff.isoformat(),'full_ledger_sha256':ledger_hash,
                'label_observation_cutoff':label_boundary.isoformat()} for x in selected)
    return {'viable':not blockers,'blockers':sorted(set(blockers)),
            'blocks':blocks if not blockers else {},
            'assignments':sorted(assignments,key=l.canonical_bytes) if not blockers else [],
            'monthly_counts':dict(sorted(months.items())), 'version':VERSION,
            'maturity_rule':'Availability strictly before next block freeze; calendar dates never imply publication.',
            'calibration_policy':'Never used for model fitting or model selection.'}


def baseline_history(items: list[dict], *, prediction_at: str, fitting_cutoff: str,
                     subject_family: str, fitting_families: set[str] | None) -> list[dict]:
    prediction,boundary=l.timestamp(prediction_at),l.timestamp(fitting_cutoff)
    if prediction is None or boundary is None: raise ValueError('explicit_timezone_instants_required')
    if not isinstance(fitting_families,(set,frozenset)):
        raise ValueError('frozen_fit_membership_required')
    cutoff=min(prediction,boundary).isoformat()
    # Full ledger first, including future corrections and cancellations. Never
    # prefilter to qualifying versions or to fitting membership before selection.
    cohort=build_cohort(items,cutoff)
    result=[]
    for item in cohort['selected_rows']:
        family=item['transaction_family_id']
        effective=s.parse_roc_date(item['raw'].get('交易年月日'))
        if (family!=subject_family and family in fitting_families
                and effective and effective['precision']=='day'
                and datetime.fromisoformat(effective['value']+'T00:00:00+08:00')<prediction):
            result.append(item)
    return sorted(result,key=lambda x:(x['transaction_family_id'],x['version_id']))
