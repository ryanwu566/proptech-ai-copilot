"""Explicit admission for the new archive-snapshot target; strict ML gates survive."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import re

from services.valuation_ml.contract import TARGET, VERSION, TYPES, subject_from_record

VERSION_ADMISSION = 'plvr-archive-snapshot-admission-v1'
KNOWN_SERIAL = 'RPWNMLNKNHLGFBF78EA'
WINDOW = ('2017-01-01','2026-06-30')
SPLITS = {
    'train': {'start':'2017-01-01','end':'2024-06-30','latest_source_release':'113S2'},
    'validation': {'start':'2024-07-01','end':'2025-06-30','latest_source_release':'114S2'},
    'holdout': {'start':'2025-07-01','end':'2026-06-30','latest_source_release':'115S3'},
}


def release_ordinal(value: str) -> int:
    m = re.fullmatch(r'([0-9]{3})S([1-4])', value)
    if not m:
        raise ValueError('invalid_release_label')
    return int(m[1])*4+int(m[2])-1


def continuous_window(manifest: dict) -> dict:
    releases = sorted(release_ordinal(x['release']) for x in manifest['releases'])
    if releases != list(range(release_ordinal('105S4'),release_ordinal('115S3')+1)):
        raise ValueError('release_coverage_gap')
    return dict(start=WINDOW[0], end=WINDOW[1], release_count=40,
                rationale='First full calendar year after the first retained release through the complete '
                          'transaction quarter before the final release quarter; sparse older dates and the '
                          'incomplete 2026 Q3 tail excluded. Archive coverage, not publication evidence.',
                historical_publication_proven=False, population_completeness_proven=False)


def gate_decision(*, verified: bool) -> dict:
    return dict(version=VERSION_ADMISSION, training_authorized=bool(verified),
                authorized_target=TARGET, feature_contract=VERSION,
                historical_point_in_time_authorized=False, whole_dwelling_authorized=False,
                parking_exclusive_authorized=False,
                evaluation='Retrospective archive-snapshot temporal generalization with source-quarter '
                           'membership restrictions; not an as-of-publication historical backtest.',
                gates={
                    'historical_availability':'Required for PIT backtesting; unsatisfied. New snapshot contract '
                        'does not reconstruct past public information and cannot support PIT claims.',
                    'parking':'Unverified. Omitted from features; target is unadjusted gross consideration '
                        'per reported area. No absence or exclusive value inferred.',
                    'rights':'Unverified. Omitted from features; observed reported transfers only, '
                        'not complete dwelling interests.',
                    'identity_revision_notes':'Required. All conflicting/revised identities, note-tainted '
                        'families and ambiguous strong-fact groups excluded by immutable verified ledger.',
                    'admitted_dataset':'Independent complete verification required before fitting.'},
                strict_ml_a_b_contracts_changed=False)


def cohort_reason(row: dict) -> str | None:
    serial=row.get('official_serial','')
    if serial == KNOWN_SERIAL:
        return 'known_related_party_38652'
    if not re.fullmatch('[A-Z0-9]{8,40}',serial) or serial.startswith(('DEMO','SAMPLE','SYNTHETIC')):
        return 'sample_or_invalid_identity'
    try:
        day=date.fromisoformat(row['transaction_date']).isoformat()
    except (ValueError,KeyError,TypeError):
        return 'invalid_date'
    if day < WINDOW[0] or day > WINDOW[1]:
        return 'outside_release_supported_window'
    if row.get('ordinary_sale_status') != 'NO_REPORTED_NOTE_NOT_PROOF_OF_ARMS_LENGTH':
        return 'unresolved_note_status'
    if row.get('main_use') != '住家用':
        return 'unsupported_use'
    if row.get('geographic_unit_kind') != 'district' or not row.get('district'):
        return 'unsupported_geography'
    if row.get('building_type') not in TYPES:
        return 'unsupported_building_type'
    try:
        area=Decimal(row['area_ping'])
        if not area.is_finite() or not 5 <= area <= 200:
            return 'invalid_area'
        target=Decimal(row['gross_unit_price_ntd_ping'])
        price=Decimal(row['total_price_ntd'])
        if not target.is_finite() or not price.is_finite() or min(target,price)<=0 or target!=price/area:
            return 'invalid_target'
    except (InvalidOperation,ValueError,KeyError,TypeError):
        return 'invalid_target'
    if row.get('floor') is not None and row.get('total_floor') is not None and row['floor']>row['total_floor']:
        return 'inconsistent_floors'
    try:
        subject_from_record(row)
    except (ValueError,TypeError,KeyError):
        return 'unsupported_structure_or_geography'
    return None


def split_for(row: dict) -> str | None:
    day=row['transaction_date']
    source=release_ordinal(row['provenance']['release'])
    for key, spec in SPLITS.items():
        if spec['start'] <= day <= spec['end']:
            return key if source <= release_ordinal(spec['latest_source_release']) else None
    return None
