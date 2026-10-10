"""Read-only byte equality, hash integrity and privacy audit for ML-A2 outputs."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

from .audit_foundation import file_sha256

FILES = {'evidence.json', 'data-gate.json', 'source-inventory.json', 'build-manifest.json', 'output-hashes.json'}
PRIVATE_KEYS = {'occurrence_id', 'physical_occurrence_id', 'transaction_family_id', 'source_record_version_id',
                'version_id', 'raw_payload_sha256', '編號', '土地位置建物門牌', '建物門牌', '土地位置',
                '姓名', '電話', '手機', '身分證字號', '統一編號', 'address', 'phone', 'email',
                'notes', '備註', 'target', 'features', 'records', 'rows'}
PRIVATE_KEYS |= {'name', 'phone_number', 'owner_identity', 'owner_name', 'personal_identifier',
                 '身分證號', '所有權人', '權利人姓名', '聯絡電話'}


def check_privacy(value) -> None:
    """Reject transaction-level fields; a 'raw' aggregate must contain only counts."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in PRIVATE_KEYS:
                raise ValueError('privacy_row_field')
            if key == 'raw' and (not isinstance(child, dict)
                                 or not all(type(x) is int and x >= 0 for x in child.values())):
                raise ValueError('privacy_raw_payload')
            check_privacy(key)
            check_privacy(child)
    elif isinstance(value, list):
        for child in value:
            check_privacy(child)
    elif isinstance(value, str):
        if re.search(r'(?:^|\s)[A-Za-z]:[/\\]|/(?:Users|home)/', value):
            raise ValueError('privacy_absolute_machine_path')
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError('privacy_nonfinite_value')


def compare(first: Path, second: Path) -> dict:
    directories = [first.resolve(), second.resolve()]
    if directories[0] == directories[1]:
        raise ValueError('independent_build_directories_required')
    hashes = {}
    for destination in directories:
        if not destination.is_dir() or {x.name for x in destination.iterdir()} != FILES:
            raise ValueError('exact_aggregate_artifact_set_required')
        parsed = {}
        for name in sorted(FILES):
            path = destination/name
            if not path.is_file() or path.stat().st_size > 2*1024*1024:
                raise ValueError('bounded_aggregate_artifact_required')
            parsed[name] = json.loads(path.read_text(encoding='utf-8'))
            check_privacy(parsed[name])
        manifest = parsed['output-hashes.json']
        if not isinstance(manifest, dict) or set(manifest) != FILES-{'output-hashes.json'}:
            raise ValueError('output_hash_manifest_scope_invalid')
        for name, expected in manifest.items():
            if file_sha256(destination/name) != expected:
                raise ValueError('output_hash_mismatch')
    for name in sorted(FILES):
        if (directories[0]/name).read_bytes() != (directories[1]/name).read_bytes():
            raise ValueError('deterministic_artifact_bytes_differ')
        hashes[name] = file_sha256(directories[0]/name)
    return {'status': 'PASS', 'matched_files': len(FILES), 'byte_identical': True,
            'privacy': 'PASS', 'output_sha256': hashes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--first', required=True, type=Path)
    parser.add_argument('--second', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.first, args.second)
    except (OSError, ValueError, TypeError):
        parser.exit(2, 'history_build_verification_failed: byte/hash/privacy contract\n')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
