"""Strict bounded PLVR CSV/detail inspection; this module does not attest rights."""
from __future__ import annotations

from collections import defaultdict
import csv
import hashlib
import io

from . import semantics as s

PARKING_WORDS = ('車位', '停車')
ENGLISH_MAIN = (
    'The villages and towns urban district', 'transaction sign',
    'land sector position building sector house number plate', 'land shifting total area square meter',
    'the use zoning or compiles and checks', 'the non-metropolis land use district', 'non-metropolis land use',
    'transaction year month and day', 'transaction pen number', 'shifting level', 'total floor number',
    'building state', 'main use', 'main building materials', 'construction to complete the years',
    'building shifting total area', 'Building present situation pattern - room',
    'building present situation pattern - hall', 'building present situation pattern - health',
    'building present situation pattern - compartmented', 'Whether there is manages the organization',
    'total price NTD', 'the unit price (NTD / square meter)', 'the berth category',
    'berth shifting total area square meter', 'the berth total price NTD', 'the note', 'serial number',
    'main building area', 'auxiliary building area', 'balcony area', 'elevator', 'transaction number')
ENGLISH_DETAILS = {
    'build': ('The serial number', 'room age', 'building shifting area square meter', 'the main use',
              'main building materials', 'construction completes the date', 'total layer', 'building lamination', ''),
    'land': ('The serial number', ' land position', 'land shifting area square meter',
             'the use zoning or compiles and checks', '', '', '', 'land parcel'),
    'park': ('Serial number', 'berth category', 'berth price', 'berth area square meter', ''),
}


def parse_csv(data: bytes, expected_header: list[str], english: tuple[str, ...] | None = None) -> dict:
    if len(data) > 32 * 1024 * 1024:
        raise ValueError('csv_byte_limit')
    try:
        decoded = data.decode('utf-8-sig', errors='strict')
    except UnicodeDecodeError as error:
        raise ValueError('csv_encoding') from error
    reader = csv.reader(io.StringIO(decoded, newline=''), strict=True)
    records = []
    blank_count = description_count = 0
    header = None
    previous_line = 0
    try:
        for record_number, cells in enumerate(reader, 1):
            start_line, end_line = previous_line + 1, reader.line_num
            previous_line = end_line
            if not cells:
                blank_count += 1
                continue
            if header is None:
                header = cells
                if header != expected_header or len(set(header)) != len(header):
                    raise ValueError('header_schema_mismatch')
                continue
            if english is not None and not records and description_count == 0 and tuple(cells) == english:
                description_count += 1
                continue
            if len(records) >= 250000:
                raise ValueError('csv_row_limit')
            valid = len(cells) == len(header)
            records.append({'raw': dict(zip(header, cells)) if valid else {}, 'cells': cells,
                            'record_number': record_number, 'start_line': start_line, 'end_line': end_line,
                            'parse_error': None if valid else 'CSV_FIELD_COUNT'})
    except csv.Error as error:
        raise ValueError('csv_syntax_no_partial_output') from error
    if header is None:
        raise ValueError('csv_header_missing')
    return {'header': header, 'records': records, 'description_record_count': description_count,
            'blank_csv_record_count': blank_count, 'sha256': hashlib.sha256(data).hexdigest()}


def detail_index(records: list[dict]) -> tuple[dict, bool]:
    groups = defaultdict(list)
    complete = True
    for record in records:
        key = s.text(record['raw'].get('編號'))
        if record['parse_error'] or not key:
            complete = False
        else:
            groups[key].append(record)
    return dict(groups), complete


def unproven_context(member: str, schema_hash: str, park_hash: str | None, detail_count: int | None) -> dict:
    def evidence(checksum, locator):
        return {'sha256':checksum, 'locator':locator, 'version':'plvr-embedded-schema-detail-audit-v1'}
    return {'member_name':member, 'source_schema_version':schema_hash,
            'schema_evidence':evidence(schema_hash, 'schema-main.csv'),
            'rights_evidence':None, 'full_rights':None, 'one_dwelling':None,
            'area_evidence':None, 'area_basis':None, 'special_transaction':None,
            'parking_evidence':evidence(park_hash, member.replace('.csv','_park.csv')) if park_hash else None,
            'parking_detail_count':detail_count, 'blank_parking_means_absent':False}


def parking_state(raw: dict, parks: list[dict], builds: list[dict], complete: bool, unique: bool,
                  *, context: dict) -> str:
    """Diagnose absence using complete within-release joins; never infer blanks.

    Building detail descriptions mentioning parking quarantine apparent zero-count
    cases, including shared portions. They do not prove separately priced spaces.
    """
    counts = s.parse_counts(raw.get('交易筆棟數'))
    if not unique:
        return 'PARKING_SEMANTICS_AMBIGUOUS'
    if counts and len(parks) and counts[2] != len(parks):
        return 'PARKING_SEMANTICS_AMBIGUOUS'
    context = dict(context)
    context['parking_detail_count'] = len(parks) if complete else None
    if not complete:
        context['parking_evidence'] = None
    initial = s.classify_parking(raw, context)
    if initial == 'PARKING_PRESENT':
        return initial
    if initial != 'NO_PARKING_CONFIRMED':
        return initial
    if not builds:
        return 'UNKNOWN'
    if any(token in s.text(raw.get('備註')) for token in PARKING_WORDS):
        return 'PARKING_SEMANTICS_AMBIGUOUS'
    if any(any(token in s.text(row.get('主要用途')) for token in PARKING_WORDS) for row in builds):
        return 'PARKING_SEMANTICS_AMBIGUOUS'
    if any(not s.text(row.get('主要用途')) for row in builds):
        return 'UNKNOWN'
    return 'NO_PARKING_CONFIRMED'
