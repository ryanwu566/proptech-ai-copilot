"""Separately operated Stage 1 migration must be frozen without automatic replay."""
from scripts.migration_registry import load_registry, next_safe_sequence, checksum
from scripts.apply_production_migrations import MIGRATIONS


def test_serving_exclusion_migration_is_registered_but_never_replayed():
    registry=load_registry()
    entry=next(r for r in registry if r.filename=='023_add_market_serving_exclusions.sql')
    assert entry.execution_policy=='legacy_operator'
    assert entry.sha256==checksum(entry.path)
    assert all(m.name!='023_add_market_serving_exclusions.sql' for m in MIGRATIONS)
    assert next_safe_sequence(registry)==24
