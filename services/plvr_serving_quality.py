"""Conservative, disk-backed PLVR strong-fact reconciliation.

Raw addresses are hashed, never persisted to this evidence index. Repeated
releases collapse into identity/fact groups. Revisions, missing official IDs,
multiple serving rows and multiple official IDs sharing facts block automation.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any, Iterator

OFFICIAL_SOURCE = 'official_plvr_opendata'


def serving_relation() -> str:
    """Only operator configuration selects the reviewed exclusion view.

    False/absent preserves compatibility until migration and reconciliation.
    True never falls back to raw data if the view or SELECT grant is missing.
    """
    value = os.environ.get('PLVR_SERVING_EXCLUSIONS_ENABLED', 'false').strip().lower()
    if value not in {'true', 'false'}:
        raise ValueError('invalid PLVR serving exclusion configuration')
    return 'market_serving_transactions' if value == 'true' else 'real_price_transactions'


def serving_sql(statement: str) -> str:
    """Rewrite only the fixed internal BLUE source relation, never parameters."""
    relation = serving_relation()
    rewritten = statement.replace('from real_price_transactions', f'from {relation}')
    if relation == 'market_serving_transactions':
        rewritten = rewritten.replace('from market_district_period_aggregates', 'from market_serving_district_periods')
    return rewritten


def _text(value: Any) -> str:
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', str(value or ''))).replace('臺', '台')


def fact_fingerprint(row: dict[str, Any]) -> str | None:
    values = {key: _text(row.get(key)) for key in (
        'city', 'district', 'transaction_period', 'road', 'address_text', 'building_type',
    )}
    if not all(values.values()) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', values['transaction_period']):
        return None
    try:
        for key in ('area_ping', 'total_price', 'unit_price_per_ping'):
            number = Decimal(str(row.get(key)))
            if not number.is_finite() or number <= 0:
                return None
            values[key] = str(number.quantize(Decimal('0.01')))
        floor = Decimal(str(row.get('floor', 0) or 0))
        if not floor.is_finite() or floor != floor.to_integral_value():
            return None
        values['floor'] = str(int(floor))
    except (ValueError, TypeError, InvalidOperation):
        return None
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


class PlvrQualityReconciler:
    def __init__(self, index_path: Path, *, as_of: str) -> None:
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', as_of):
            raise ValueError('as_of must be a calendar month')
        # Never overwrite a prior reconciliation index.
        with index_path.open('xb'):
            pass
        index_path.chmod(0o600)
        self.as_of = as_of
        self.db = sqlite3.connect(index_path)
        self.db.executescript('''
            pragma journal_mode=DELETE;
            create table serving (id integer primary key, fact_key text not null);
            create index serving_fact on serving(fact_key);
            create table evidence (
                official_id text not null, fact_key text not null,
                occurrences integer not null, has_note integer not null,
                has_blank integer not null, missing_id integer not null,
                source_file text not null, source_row integer not null,
                primary key (official_id, fact_key)
            );
            create index evidence_fact on evidence(fact_key, official_id);
            create table blocked_identities (official_id text primary key, reason text not null);
            create table identity_counts (official_id text primary key, n integer not null);
            create table fact_counts (fact_key text primary key, n integer not null);
            create table serving_counts (fact_key text primary key, n integer not null, serving_id integer not null);
        ''')

    def add_serving(self, row: dict[str, Any]) -> None:
        key = fact_fingerprint(row)
        if row.get('source') != OFFICIAL_SOURCE or not key or str(row['transaction_period']) > self.as_of:
            return
        self.db.execute('insert into serving values (?,?)', (int(row['id']), key))

    def block_identity(self, official_id: str, reason: str = 'unparseable_source_revision') -> None:
        serial = _text(official_id)
        if serial:
            self.db.execute('insert or ignore into blocked_identities values (?,?)', (serial, reason))

    def add_raw(self, row: dict[str, Any], *, official_id: str, has_note: bool,
                floor_reliable: bool = True, source_file: str = '', source_row: int = 0) -> None:
        key = fact_fingerprint(row)
        if not key:
            self.block_identity(official_id)
            return
        if not floor_reliable or not _text(row.get('floor')) or _text(row.get('floor')) in {'0', '0.0', '0.00'}:
            self.block_identity(official_id, 'floor_not_reliable')
        serial = _text(official_id)
        missing = not serial
        if missing:
            serial = 'missing:' + hashlib.sha256(f'{source_file}:{source_row}'.encode()).hexdigest()
        self.db.execute('''insert into evidence values (?,?,1,?,?,?,?,?)
            on conflict(official_id,fact_key) do update set
              occurrences=occurrences+1,
              has_note=max(has_note,excluded.has_note),
              has_blank=max(has_blank,excluded.has_blank)
            ''', (serial, key, int(has_note), int(not has_note), int(missing), source_file, source_row))

    def classifications(self) -> Iterator[dict[str, Any]]:
        self.db.commit()
        # Explicit indexed summaries prevent SQLite choosing a Cartesian
        # identities×facts co-routine plan at nationwide cardinality. These
        # derived tables belong only to this private reconciliation index.
        with self.db:
            self.db.execute('delete from identity_counts')
            self.db.execute('delete from fact_counts')
            self.db.execute('delete from serving_counts')
            self.db.execute('insert into identity_counts select official_id,count(*) from evidence group by official_id')
            self.db.execute('insert into fact_counts select fact_key,count(*) from evidence group by fact_key')
            self.db.execute('insert into serving_counts select fact_key,count(*),min(id) from serving group by fact_key')
        cursor = self.db.execute('''
            select e.*,i.n identity_versions,f.n official_id_count,
                   coalesce(m.n,0) serving_matches,m.serving_id,b.reason blocked_reason
            from evidence e left join identity_counts i on i.official_id=e.official_id
            left join fact_counts f on f.fact_key=e.fact_key
            left join serving_counts m on m.fact_key=e.fact_key
            left join blocked_identities b on b.official_id=e.official_id
            where e.has_note=1 order by e.official_id,e.fact_key
        ''')
        columns = [item[0] for item in cursor.description]
        for values in cursor:
            row = dict(zip(columns, values))
            unique = (row['serving_matches'] == 1 and row['identity_versions'] == 1
                      and row['official_id_count'] == 1 and not row['has_blank'] and not row['missing_id'] and not row['blocked_reason'])
            classification = ('NO_MATCH' if not row['serving_matches'] else
                              'UNIQUE_MATCH' if unique else 'MULTIPLE_MATCH')
            yield {
                'classification': classification,
                'official_id': None if row['missing_id'] else row['official_id'],
                'fact_sha256': row['fact_key'],
                'serving_transaction_id': row['serving_id'] if unique else None,
                'serving_matches': row['serving_matches'],
                'identity_versions': row['identity_versions'],
                'official_id_count': row['official_id_count'],
                'note_removed_in_other_release': bool(row['has_blank']),
                'blocked_identity_reason': row['blocked_reason'],
                'occurrences': row['occurrences'],
                'source_file': row['source_file'], 'source_row': row['source_row'],
            }

    def close(self) -> None:
        self.db.close()
