from pathlib import Path
from scripts.migration_registry import checksum, load_registry, next_safe_sequence
from scripts.apply_production_migrations import MIGRATIONS

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "database/migrations/020_consumer_account_foundation.sql"


def test_additive_account_migration_is_registered_and_default_only():
    registrations = load_registry()
    rows = [r for r in registrations if r.sequence == 20]
    assert len(rows) == 1
    assert rows[0].sha256 == checksum(PATH)
    assert PATH in MIGRATIONS
    assert next_safe_sequence(registrations) == 22
    sql = PATH.read_text().lower()
    assert "force row level security" in sql
    assert "grant insert (user_id)" in sql
    assert "grant update" not in sql
    assert "security definer" not in sql
    assert "as restrictive for select" in sql
    assert "user_metadata" not in sql
