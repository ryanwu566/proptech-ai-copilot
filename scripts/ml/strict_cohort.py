"""Strict target guard and conserving offline cohort selection."""
from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal, localcontext

from . import lineage as l, semantics as s, temporal as t

VERSION='residential-semantic-temporal-cohort-v1'


def strict_target(raw: dict, context: dict, verdict: dict) -> dict:
    reasons=[]
    conditions={'rights':('FULL_RIGHTS_CONFIRMED','RIGHTS_UNCONFIRMED'),
                'dwelling':('SINGLE_DWELLING_CONFIRMED','DWELLING_UNCONFIRMED'),
                'parking':('NO_PARKING_CONFIRMED','PARKING_UNCONFIRMED'),
                'area_unit':('m²','AREA_UNIT_UNPROVEN'),
                'area_field':('建物移轉總面積平方公尺','AREA_FIELD_UNPROVEN')}
    for key,(want,reason) in conditions.items():
        if verdict.get(key)!=want:
            reasons.append(reason)
    for key in ('source_valid','revision_valid','availability_valid'):
        if verdict.get(key) is not True:
            reasons.append(key.upper()+'_UNPROVEN')
    if raw.get('交易標的')!='房地(土地+建物)': reasons.append('UNSUPPORTED_TARGET')
    if raw.get('主要用途')!='住家用': reasons.append('NON_RESIDENTIAL_USE')
    if s.text(raw.get('建物型態')) not in s.TYPES: reasons.append('UNSUPPORTED_BUILDING_TYPE')
    counts=s.parse_counts(raw.get('交易筆棟數'))
    if not counts or counts[0]<1 or counts[1]!=1:
        reasons.append('RAW_OBJECT_COUNT_UNPROVEN')
    if (context.get('full_rights') is not True or context.get('one_dwelling') is not True
            or not s.evidence_valid(context.get('rights_evidence'))):
        reasons.append('RIGHTS_CONTEXT_UNPROVEN')
    if reasons:
        return {'valid':False,'reasons':reasons}
    return s.construct_target(raw,context)


def numeric_diagnostic(raw: dict) -> dict:
    """Reconcile raw NTD/m² without generating a label for an ineligible row."""
    area=s.number(raw.get('建物移轉總面積平方公尺'))
    price=s.number(raw.get('總價元'))
    if area is None or area<=0: return {'reason':'INVALID_AREA','reconciliation':'NOT_COMPUTABLE'}
    if price is None or price<=0: return {'reason':'INVALID_PRICE','reconciliation':'NOT_COMPUTABLE'}
    with localcontext() as ctx:
        ctx.prec=28
        ping=area*Decimal('0.3025')
        unit=price/ping
        if not Decimal(5)<=ping<=Decimal(150):
            return {'reason':'AREA_OUTSIDE_V1_SCOPE','reconciliation':'NOT_COMPUTED_OUTSIDE_SCOPE'}
        if not Decimal(10000)<=unit<=Decimal(5000000):
            return {'reason':'PRICE_OUTSIDE_V1_SCOPE','reconciliation':'NOT_COMPUTED_OUTSIDE_SCOPE'}
        supplied=s.text(raw.get('單價元平方公尺'))
        if not supplied: return {'reason':None,'reconciliation':'OFFICIAL_UNIT_PRICE_ABSENT'}
        official=s.number(supplied)
        if official is None or official<=0:
            return {'reason':'TARGET_RECONCILIATION_FAILED','reconciliation':'INVALID_OFFICIAL_UNIT_PRICE'}
        derived=price/area
        difference=abs(official-derived)
        tolerance=max(Decimal(1),Decimal('0.001')*derived)
        mismatch=difference>tolerance
        return {'reason':'TARGET_RECONCILIATION_FAILED' if mismatch else None,
                'reconciliation':'MISMATCH' if mismatch else 'WITHIN_TOLERANCE',
                'relative_difference':str(difference/derived)}


STAGES=('schema','source_identity','geography','transaction_target','residential_use','building_type',
        'rights','dwelling','parking','price_area','physical','revision','availability')


def build_cohort(items: list[dict], cutoff: str) -> dict:
    if len(items)>100000: raise ValueError('bounded_main_rows_exceeded')
    boundary=l.timestamp(cutoff)
    if boundary is None: raise ValueError('cutoff_requires_timezone')
    ordered=sorted(items,key=lambda x:l.canonical_bytes(l.identify(x)))
    occurrences=[l.identify(x)['occurrence_id'] for x in ordered]
    if len(set(occurrences))!=len(occurrences): raise ValueError('duplicate_physical_occurrence_input')
    selection=l.select_as_of(ordered,cutoff)
    dispositions={x['occurrence_id']:x for x in selection['dispositions']}
    evaluations=[]
    for item in ordered:
        raw,context=item['raw'],item['context']
        semantic=item.get('semantic',{})
        geo=s.normalize_geography(raw.get('縣市',''),raw.get('鄉鎮市區',''),item['member_name'])
        effective=s.parse_roc_date(raw.get('交易年月日'))
        available=l.timestamp(item.get('source_release_available_at'))
        numeric=numeric_diagnostic(raw)
        floor,total=s.parse_floor(raw.get('移轉層次')),s.parse_floor(raw.get('總樓層數'))
        reasons={stage:None for stage in STAGES}
        if item.get('parse_error'): reasons['schema']='CSV_FIELD_COUNT'
        elif not effective: reasons['schema']='INVALID_DATE'
        elif effective['precision']!='day': reasons['schema']='TRANSACTION_DAY_REQUIRED'
        elif (date.fromisoformat(effective['value'])>boundary.astimezone(t.TAIPEI).date()
              or (available and date.fromisoformat(effective['value'])>available.astimezone(t.TAIPEI).date())):
            reasons['schema']='EFFECTIVE_AFTER_AVAILABILITY_OR_CUTOFF'
        if not s.evidence_valid(context.get('schema_evidence')) or not s.text(raw.get('編號')):
            reasons['source_identity']='UNKNOWN_SOURCE_IDENTITY'
        if not geo['source_proven']: reasons['geography']='INVALID_GEOGRAPHY'
        if raw.get('交易標的')!='房地(土地+建物)': reasons['transaction_target']='UNSUPPORTED_TARGET'
        if raw.get('主要用途')!='住家用': reasons['residential_use']='NON_RESIDENTIAL_USE'
        if s.text(raw.get('建物型態')) not in s.TYPES: reasons['building_type']='UNSUPPORTED_BUILDING_TYPE'
        if semantic.get('rights')!='FULL_RIGHTS_CONFIRMED':
            reasons['rights']=semantic.get('rights') if semantic.get('rights') in {'PARTIAL_RIGHTS','RIGHTS_AMBIGUOUS'} else 'RIGHTS_UNKNOWN'
        elif context.get('full_rights') is not True or not s.evidence_valid(context.get('rights_evidence')):
            reasons['rights']='RIGHTS_CONTEXT_UNPROVEN'
        counts=s.parse_counts(raw.get('交易筆棟數'))
        if semantic.get('dwelling')!='SINGLE_DWELLING_CONFIRMED':
            reasons['dwelling']=semantic.get('dwelling') if semantic.get('dwelling') in {'MULTI_DWELLING','DWELLING_AMBIGUOUS'} else 'DWELLING_UNKNOWN'
        elif not counts or counts[0]<1 or counts[1]!=1:
            reasons['dwelling']='RAW_OBJECT_COUNT_UNPROVEN'
        elif context.get('one_dwelling') is not True:
            reasons['dwelling']='DWELLING_CONTEXT_UNPROVEN'
        if semantic.get('parking')!='NO_PARKING_CONFIRMED':
            reasons['parking']=semantic.get('parking') if semantic.get('parking') in {'PARKING_PRESENT','PARKING_SEMANTICS_AMBIGUOUS'} else 'PARKING_UNKNOWN'
        elif s.classify_parking(raw,context)!='NO_PARKING_CONFIRMED':
            reasons['parking']='PARKING_CONTEXT_UNPROVEN'
        reasons['price_area']=numeric['reason']
        area_contract=item.get('area_contract',{})
        if (area_contract!={'field':'建物移轉總面積平方公尺','unit':'m²'}
                or context.get('area_basis')!=s.AREA_VERSION or not s.evidence_valid(context.get('area_evidence'))):
            reasons['price_area']=reasons['price_area'] or 'AREA_CONTRACT_UNPROVEN'
        if (floor is None or total is None or floor>total): reasons['physical']='FLOOR_AMBIGUOUS'
        elif '備註' not in raw or s.text(raw['備註']): reasons['physical']='SPECIAL_NOTE_REQUIRES_REVIEW'
        elif context.get('special_transaction') is not False: reasons['physical']='SPECIAL_STATUS_UNPROVEN'
        mark=dispositions[l.identify(item)['occurrence_id']]
        if mark['reason']:
            stage='availability' if mark['reason'] in {'availability_unknown','after_availability_cutoff'} else 'revision'
            reasons[stage]=mark['reason']
        evaluations.append((item,geo,effective,floor,reasons,numeric))
    active=list(range(len(evaluations))); first={}; funnel=[]
    for stage in STAGES:
        rejected=[i for i in active if evaluations[i][4][stage]]
        counts=Counter(evaluations[i][4][stage] for i in rejected)
        first.update({i:evaluations[i][4][stage] for i in rejected})
        rejected_set=set(rejected)
        remaining=[i for i in active if i not in rejected_set]
        funnel.append({'stage':stage,'input_count':len(active),'accepted_count':len(remaining),
                       'excluded_count':len(rejected),'reason_breakdown':dict(sorted(counts.items()))})
        active=remaining
    membership=[];targets=[];features=[];exclusions=[];rows=[]
    for i,(item,geo,effective,floor,reasons,numeric) in enumerate(evaluations):
        ids=l.identify(item)
        identity={'transaction_family_id':ids['transaction_family_id'],
                  'source_record_version_id':ids['version_id'],'physical_occurrence_id':ids['occurrence_id']}
        if i in first:
            exclusions.append({**identity,'release_id':item['release_id'],'first_reason':first[i],
                               'all_reasons':sorted({x for x in reasons.values() if x}),
                               'geography':geo,'effective_period':effective})
            continue
        verdict={**item['semantic'],'source_valid':True,'revision_valid':True,'availability_valid':True,
                 'area_field':item['area_contract']['field'],'area_unit':item['area_contract']['unit']}
        target=strict_target(item['raw'],item['context'],verdict)
        if not target['valid']:
            # Failure at this boundary means the conserving stage predicates are incomplete.
            raise ValueError('target_guard_disagrees_with_funnel')
        membership.append({**identity,'release_id':item['release_id'],
                           'release_available_at':item['source_release_available_at'],
                           'selected_as_of_cutoff':cutoff,'effective_period':effective,'cohort_version':VERSION})
        targets.append({**identity,'values':target})
        features.append({**identity,'values':{'county_district':geo['city']+'/'+geo['district'],
                         'building_type':s.TYPES[s.text(item['raw']['建物型態'])],
                         'area_ping':target['area_ping'],'floor':floor,
                         'prediction_year':int(effective['value'][:4]),'prediction_month':int(effective['value'][5:7])}})
        rows.append({**item,**ids})
    assert len(items)==len(membership)+len(exclusions)
    assert len({x['transaction_family_id'] for x in membership})==len(membership)
    return {'membership':membership,'targets':targets,'features':features,'exclusions':exclusions,
            'funnel':funnel,'revision_dispositions':selection['dispositions'],'relations':selection['relations'],
            'selected_rows':rows,'reconciliation_counts':dict(sorted(Counter(x[5]['reconciliation'] for x in evaluations).items()))}
