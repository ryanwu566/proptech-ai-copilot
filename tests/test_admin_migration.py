"""Wave 1C owns 022 and preserves both foundation migrations byte-for-byte."""
import json
from pathlib import Path
from scripts.migration_registry import checksum


def test_admin_migration_is_registered_without_rewriting_wave_1a_or_1b():
    registry=json.loads(Path('database/migration_registry.json').read_text())['migrations']
    entry=next(row for row in registry if row['sequence']==22)
    assert entry['filename']=='022_admin_control_plane.sql'
    assert entry['execution_policy']=='production_runner'
    assert entry['sha256']==checksum(Path('database/migrations',entry['filename']))
    for name,expected in {
        '020_consumer_account_foundation.sql':'01aa6d71588cefa8b1e4d35e9bdf08cc7944ac4280791de2f5f974a9f466dd31',
        '021_api_usage_quota_ledger.sql':'00ed7d4b78de6d92c285ab8cd87241d1477bee2ce6e97caef6bbf6e2f43b98af',
    }.items():
        assert checksum(Path('database/migrations',name))==expected
