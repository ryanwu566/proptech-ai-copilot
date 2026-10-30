#!/usr/bin/env python3
"""Read-only raw-to-BLUE reconciliation from a private current serving export.

No database writes, provider calls, credentials or source transformations.
Output is a private NEW directory. Full classifications contain hashed facts,
not raw addresses; only UNIQUE_MATCH records are eligible for reviewed apply.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import sys
import re
import unicodedata
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plvr_import_service import FLOOR_NUMBERS, FILE_CITY_MAP, SALE_MAIN_FILENAME, normalize_row, read_csv_rows
from services.plvr_serving_quality import PlvrQualityReconciler


_INVARIANT_REASONS = {
    'output must not be inside source data': 'output_inside_source',
    'future official row in current serving export': 'future_official_row',
    'serving snapshot population does not match reviewed baseline': 'serving_snapshot_population_mismatch',
    'raw source file count does not match reviewed baseline': 'raw_source_file_count_mismatch',
    'source symlink is not permitted': 'source_symlink_disallowed',
    'as_of must be a calendar month': 'invalid_as_of',
}
_SQLITE_ERRORS = {
    sqlite3.SQLITE_CANTOPEN: ('SQLITE_CANTOPEN','sqlite_cannot_open'),
    sqlite3.SQLITE_READONLY: ('SQLITE_READONLY','sqlite_readonly'),
    sqlite3.SQLITE_FULL: ('SQLITE_FULL','sqlite_full'),
    sqlite3.SQLITE_IOERR: ('SQLITE_IOERR','sqlite_io_error'),
    sqlite3.SQLITE_NOMEM: ('SQLITE_NOMEM','sqlite_memory_limit'),
    sqlite3.SQLITE_INTERRUPT: ('SQLITE_INTERRUPT','sqlite_interrupted'),
    sqlite3.SQLITE_CORRUPT: ('SQLITE_CORRUPT','sqlite_corrupt'),
    sqlite3.SQLITE_BUSY: ('SQLITE_BUSY','sqlite_busy'),
    sqlite3.SQLITE_LOCKED: ('SQLITE_LOCKED','sqlite_locked'),
}
_SAFE_REASONS = set(_INVARIANT_REASONS.values()) | {v[1] for v in _SQLITE_ERRORS.values()} | {
    'reconciliation_failed','reconciliation_io_error','invalid_child_report'}
_SAFE_CLASSES = {'ValueError','PermissionError','FileNotFoundError','FileExistsError','OSError',
                 'OperationalError','IntegrityError','DatabaseError','MemoryError','UnknownError'}


def safe_reconciliation_error(error: Exception) -> dict:
    """Expose fixed reason codes, never exception text, SQL or raw records."""
    name=type(error).__name__
    result={'status':'BLOCKED','error_class':name if name in _SAFE_CLASSES else 'UnknownError',
            'reason_code':'reconciliation_failed','database_changes_applied':False}
    if isinstance(error,ValueError):
        result['reason_code']=_INVARIANT_REASONS.get(str(error),'reconciliation_failed')
    if isinstance(error,OSError):
        result['reason_code']='reconciliation_io_error'
    code=getattr(error,'sqlite_errorcode',None)
    if isinstance(code,int) and (code & 255) in _SQLITE_ERRORS:
        result['sqlite_errorcode']=code
        result['sqlite_errorname'],result['reason_code']=_SQLITE_ERRORS[code & 255]
    return result


def safe_process_report(stdout: bytes, exit_code: int) -> dict:
    """Allowlist the child JSON before including it in operator evidence."""
    result={'exit_code':exit_code,'status':'BLOCKED','reason_code':'invalid_child_report'}
    try:
        if len(stdout)>65536: return result
        value=json.loads(stdout)
        if not isinstance(value,dict) or not isinstance(value.get('status'),str) or value['status'] not in {'BLOCKED','REVIEW_REQUIRED'}: return result
    except (ValueError,UnicodeError):
        return result
    result={'exit_code':exit_code,'status':value['status']}
    if isinstance(value.get('reason_code'),str) and value['reason_code'] in _SAFE_REASONS: result['reason_code']=value['reason_code']
    if isinstance(value.get('error_class'),str) and value['error_class'] in _SAFE_CLASSES: result['error_class']=value['error_class']
    code=value.get('sqlite_errorcode')
    if type(code) is int and code>=0 and (code & 255) in _SQLITE_ERRORS:
        result['sqlite_errorcode']=code
        result['sqlite_errorname']=_SQLITE_ERRORS[code & 255][0]
    for key in ['unique_serving_rows_eligible']:
        if type(value.get(key)) is int and value[key]>=0: result[key]=value[key]
    if type(value.get('known_serial_unique_match_to_38652')) is bool:
        result['known_serial_unique_match_to_38652']=value['known_serial_unique_match_to_38652']
    for key,names in [('classifications',['UNIQUE_MATCH','MULTIPLE_MATCH','NO_MATCH']),
                      ('counts',['serving_total_rows','serving_official_rows','serving_nonofficial_rows',
                                 'raw_files','raw_rows','nonblank_note_rows','rejected_nonblank_note_rows','eligible_note_occurrences'])]:
        if isinstance(value.get(key),dict):
            result[key]={name:value[key][name] for name in names
                         if type(value[key].get(name)) is int and value[key][name]>=0}
    return result


def reliable_floor(raw_value: str, normalized_floor: int) -> bool:
    token=unicodedata.normalize('NFKC',str(raw_value)).strip()
    match=re.fullmatch(r'([一二三四五六七八九十百零〇0-9]+)[層樓]?',token)
    if not match:
        return False
    value=match.group(1)
    exact=int(value) if value.isascii() and value.isdigit() else FLOOR_NUMBERS.get(value)
    return exact is not None and exact>0 and exact==normalized_floor


def reconcile(*, serving_export: Path, raw_root: Path, output: Path, as_of: str,
              expected_official_rows: int = 451672, expected_total_rows: int = 451744,
              expected_raw_files: int = 880) -> dict:
    if any(output.resolve().is_relative_to(root) for root in [raw_root.resolve(),Path('/run/media/andy/Crucial X9/DB'),Path('/srv/proptech-data/DB')]):
        raise ValueError('output must not be inside source data')
    os.umask(0o077)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    r = PlvrQualityReconciler(output/'fact-index.sqlite', as_of=as_of)
    counters = Counter()
    classifications = Counter()
    rejected = Counter()
    unique_ids = set()
    known = []
    try:
        with serving_export.open(encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line)
                counters['serving_total_rows'] += 1
                if row['source'] == 'official_plvr_opendata':
                    counters['serving_official_rows'] += 1
                    if str(row['transaction_period']) > as_of:
                        raise ValueError('future official row in current serving export')
                else:
                    counters['serving_nonofficial_rows'] += 1
                r.add_serving(row)
        if (counters['serving_total_rows'] != expected_total_rows
                or counters['serving_official_rows'] != expected_official_rows):
            raise ValueError('serving snapshot population does not match reviewed baseline')
        paths = sorted(p for p in raw_root.rglob('*') if p.is_file() and SALE_MAIN_FILENAME.fullmatch(p.name))
        if len(paths) != expected_raw_files:
            raise ValueError('raw source file count does not match reviewed baseline')
        with (output/'raw-file-sha256.jsonl').open('x', encoding='utf-8') as manifests:
            for path in paths:
                if path.is_symlink() or not path.resolve().is_relative_to(raw_root.resolve()):
                    raise ValueError('source symlink is not permitted')
                relative = str(path.relative_to(raw_root))
                digest = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
                rows, encoding = read_csv_rows(path)
                manifests.write(json.dumps({'file':relative,'sha256':digest,'encoding':encoding})+'\n')
                counters['raw_files'] += 1
                for index, raw in enumerate(rows, start=3):
                    counters['raw_rows'] += 1
                    has_note = bool(str(raw.get('備註') or raw.get('raw_note') or '').strip())
                    counters['nonblank_note_rows'] += int(has_note)
                    serial = str(raw.get('編號') or raw.get('移轉編號') or raw.get('transaction_id') or '')
                    normalized, reason = normalize_row(raw, city_hint=FILE_CITY_MAP[path.name[0].lower()],
                        as_of=date.fromisoformat(as_of+'-01'), allow_future_forensic=True,
                        allow_official_city_level=True)
                    if normalized is None:
                        r.block_identity(serial)
                        rejected[reason or 'normalization_rejected'] += 1
                        counters['rejected_nonblank_note_rows'] += int(has_note)
                        continue
                    raw_floor=unicodedata.normalize('NFKC',str(raw.get('移轉層次') or raw.get('rps09') or raw.get('floor') or '')).strip()
                    floor_reliable=reliable_floor(raw_floor,normalized['floor'])
                    r.add_raw(normalized, official_id=serial, has_note=has_note, floor_reliable=floor_reliable,
                              source_file=relative, source_row=index)
                r.db.commit()
        with (output/'classifications.jsonl').open('x', encoding='utf-8') as stream:
            for item in r.classifications():
                classifications[item['classification']] += 1
                counters['eligible_note_occurrences'] += item['occurrences']
                if item['classification'] == 'UNIQUE_MATCH':
                    unique_ids.add(item['serving_transaction_id'])
                if item['official_id'] == 'RPWNMLNKNHLGFBF78EA':
                    known.append(item)
                stream.write(json.dumps(item,ensure_ascii=False)+'\n')
        # These are evidence-group counts, not occurrence-based serving deletions.
        with serving_export.open('rb') as stream:
            snapshot_sha = hashlib.file_digest(stream,'sha256').hexdigest()
        known_pass = len(known)==1 and known[0]['classification']=='UNIQUE_MATCH' and known[0]['serving_transaction_id']==38652
        summary = {'schema':'plvr-special-note-reconciliation-v2','as_of':as_of,
            'status':'REVIEW_REQUIRED' if known_pass else 'BLOCKED',
            'serving_snapshot_sha256':snapshot_sha, 'counts':dict(counters),
            'normalizer_rejections':dict(rejected),
            'classification_unit':'distinct official identity plus strong-fact version with note evidence',
            'classifications':{name:classifications[name] for name in ['UNIQUE_MATCH','MULTIPLE_MATCH','NO_MATCH']},
            'unique_serving_rows_eligible':len(unique_ids), 'known_serial':known,
            'known_serial_unique_match_to_38652':known_pass,'database_changes_applied':False}
        (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
        return summary
    finally:
        r.close()


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serving-export',type=Path,required=True)
    parser.add_argument('--raw-root',type=Path,default=Path('/srv/proptech-data/DB/實價登錄 PLVR/02_extracted'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--as-of',required=True)
    args=parser.parse_args()
    try:
        result=reconcile(serving_export=args.serving_export,raw_root=args.raw_root,output=args.output,as_of=args.as_of)
        print(json.dumps({k:v for k,v in result.items() if k not in {'known_serial'}},ensure_ascii=False))
    except Exception as exc:
        # Never surface database rows, URLs or arbitrary exception details.
        print(json.dumps(safe_reconciliation_error(exc)))
        raise SystemExit(1) from None


if __name__=='__main__':
    main()
