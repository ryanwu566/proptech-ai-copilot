"""Whole-dwelling rights require object roles and the dwelling's required interests.

Native PLVR ownership fractions are not transfer fractions of a dwelling. The
recovered build schema omits object IDs/roles and building rights fractions.
Supplemental evidence is a reviewed input, bound to exact main/detail content;
this module validates consistency, not the authority of an external attestation.
"""
from __future__ import annotations

from fractions import Fraction
import re

from . import lineage as l, semantics as s

VERSION = 'plvr-whole-dwelling-interests-v1'


def fraction(values) -> Fraction | None:
    if not isinstance(values, (list, tuple)) or len(values) != 2:
        return None
    if not all(isinstance(x,str) and re.fullmatch(r'[0-9]{1,30}',x) for x in values):
        return None
    n,d=map(int,values)
    return Fraction(n,d) if 0 < n <= d else None


def classify(raw: dict, builds: list[dict], lands: list[dict], *, complete: bool,
             unique: bool, supplement: dict | None = None, scope: dict | None = None) -> dict:
    result={'rights':'RIGHTS_UNKNOWN','dwelling':'DWELLING_UNKNOWN',
            'rights_reason':'OBJECT_RIGHTS_EVIDENCE_ABSENT',
            'dwelling_reason':'REGISTERED_UNIT_EVIDENCE_ABSENT','version':VERSION,
            'supplement_valid':False}
    def uncertain(reason):
        result.update(rights='RIGHTS_AMBIGUOUS',dwelling='DWELLING_AMBIGUOUS',
                      rights_reason=reason,dwelling_reason=reason)
        return result
    if not unique or not complete:
        return uncertain('AMBIGUOUS_DETAIL_JOIN' if not unique else 'INCOMPLETE_DETAILS')
    counts=s.parse_counts(raw.get('交易筆棟數'))
    if not counts or not builds or not lands:
        return result
    if counts[1]>1:
        result.update(dwelling='MULTI_DWELLING',dwelling_reason='DECLARED_MULTIPLE_BUILDINGS')
    elif counts[1]!=1 or s.text(raw.get('交易標的'))!='房地(土地+建物)':
        return uncertain('UNSUPPORTED_OBJECT_STRUCTURE')
    if len({l.digest(x) for x in builds})!=len(builds) or len({l.digest(x) for x in lands})!=len(lands):
        return uncertain('REPEATED_DETAIL_OBJECT_IDENTITY_UNRESOLVED')
    if len(lands)!=counts[0]:
        return uncertain('MAIN_LAND_DETAIL_COUNT_DISAGREEMENT')
    areas=[s.number(x.get('建物移轉面積平方公尺')) for x in builds]
    total=s.number(raw.get('建物移轉總面積平方公尺'))
    if total is None or any(x is None or x<=0 for x in areas) or sum(areas)!=total:
        return uncertain('MAIN_BUILD_DETAIL_AREA_DISAGREEMENT')
    land_fractions=[fraction([s.text(x.get('權利人持分分子')),s.text(x.get('權利人持分分母'))]) for x in lands]
    if any(s.number(x.get('權利人持分分子')) is not None
           and s.number(x.get('權利人持分分母')) is not None
           and s.number(x.get('權利人持分分母'))>0
           and s.number(x.get('權利人持分分子'))>s.number(x.get('權利人持分分母')) for x in lands):
        return uncertain('LAND_FRACTION_EXCEEDS_WHOLE')
    if any(x is None for x in land_fractions):
        result['rights_reason']='LAND_FRACTION_UNKNOWN_OR_INVALID'
        return result
    statuses=[s.text(x.get('移轉情形')) for x in builds+lands]
    if any(x not in {'全筆移轉','持分移轉'} for x in statuses):
        result['rights_reason']='TRANSFER_STATUS_UNKNOWN'
        return result
    if any((s.text(x.get('移轉情形'))=='全筆移轉')!=(share==1) for x,share in zip(lands,land_fractions)):
        return uncertain('LAND_WHOLE_STATUS_FRACTION_DISAGREEMENT')
    if supplement is None:
        if '持分移轉' in statuses:
            result.update(rights='RIGHTS_AMBIGUOUS',rights_reason='FRACTIONAL_INTEREST_ROLE_UNRESOLVED')
        if len(builds)>1 and counts[1]==1:
            result.update(dwelling='DWELLING_AMBIGUOUS',dwelling_reason='MULTIPLE_DETAIL_ROLES_UNRESOLVED')
        return result
    if (not isinstance(supplement,dict) or not s.evidence_valid(supplement.get('evidence'))
            or not isinstance(scope,dict) or supplement.get('scope')!=scope
            or set(scope)!={'archive_sha256','member_name','physical_row_number','schema_sha256'}
            or not re.fullmatch(r'[0-9a-f]{64}',s.text(scope.get('archive_sha256')))
            or not re.fullmatch(r'[0-9a-f]{64}',s.text(scope.get('schema_sha256')))
            or s.source_county(scope.get('member_name','')) is None
            or type(scope.get('physical_row_number')) is not int or scope['physical_row_number']<1
            or supplement.get('main_sha256')!=l.digest(raw)
            or supplement.get('build_sha256')!=l.digest(builds)
            or supplement.get('land_sha256')!=l.digest(lands)):
        return uncertain('SUPPLEMENT_BINDING_INVALID')
    objects=supplement.get('building_objects')
    interests=supplement.get('land_interests')
    if (not isinstance(objects,list) or len(objects)!=len(builds)
            or not isinstance(interests,list) or len(interests)!=len(lands)
            or any(not isinstance(x,dict) for x in objects+interests)):
        return uncertain('OBJECT_MAPPING_CARDINALITY')
    private=[x for x in objects if x.get('role')=='PRIVATE_DWELLING']
    if (any(not isinstance(x.get('role'),str)
            or x['role'] not in {'PRIVATE_DWELLING','COMMON_ANCILLARY'}
            or not isinstance(x.get('object_id'),str) or not s.text(x['object_id'])
            or type(x.get('dwelling_units')) is not int for x in objects)
            or len({x['object_id'] for x in objects})!=len(objects) or not private):
        return uncertain('OBJECT_ROLE_IDENTITY_INVALID')
    units=sum(x['dwelling_units'] for x in private)
    if units>1 or len(private)>1 or counts[1]>1:
        result.update(dwelling='MULTI_DWELLING',dwelling_reason='MULTIPLE_REGISTERED_DWELLINGS')
    elif units==1 and counts[1]==1:
        result.update(dwelling='SINGLE_DWELLING_CONFIRMED',dwelling_reason=None)
    else:
        return uncertain('UNIT_COUNT_INVALID')
    unit_ids={x['object_id'] for x in private}
    partial=False
    for native,obj in zip(builds,objects):
        transferred=fraction(obj.get('transferred_fraction'))
        required=fraction(obj.get('required_fraction'))
        if transferred is None or required is None:
            return uncertain('BUILDING_TRANSFER_FRACTION_INVALID')
        if obj['role']=='PRIVATE_DWELLING':
            if required!=1 or s.text(native.get('主要用途'))!='住家用':
                return uncertain('PRIVATE_DWELLING_BASIS_INVALID')
            native_floor=s.parse_floor(native.get('建物分層'))
            if native_floor is None or native_floor!=s.parse_floor(raw.get('移轉層次')):
                return uncertain('PRIVATE_DWELLING_FLOOR_DISAGREEMENT')
        elif (not isinstance(obj.get('unit_id'),str) or obj['unit_id'] not in unit_ids or obj['dwelling_units']!=0):
            return uncertain('COMMON_INTEREST_UNIT_LINK_INVALID')
        elif s.text(native.get('主要用途'))!='共有部分':
            return uncertain('COMMON_ROLE_NATIVE_USE_DISAGREEMENT')
        if (s.text(native.get('移轉情形'))=='全筆移轉')!=(transferred==1):
            return uncertain('BUILDING_STATUS_FRACTION_DISAGREEMENT')
        if transferred>required:
            return uncertain('EXCESS_BUILDING_INTEREST')
        partial |= transferred<required
    for transferred,interest in zip(land_fractions,interests):
        required=fraction(interest.get('required_fraction'))
        if required is None or not isinstance(interest.get('unit_id'),str) or interest['unit_id'] not in unit_ids:
            return uncertain('LAND_REQUIRED_INTEREST_UNRESOLVED')
        if transferred>required:
            return uncertain('EXCESS_LAND_INTEREST')
        partial |= transferred<required
    result.update(rights='PARTIAL_RIGHTS' if partial else 'FULL_RIGHTS_CONFIRMED',
                  rights_reason='LESS_THAN_REQUIRED_DWELLING_INTEREST' if partial else None,
                  supplement_valid=True)
    return result
