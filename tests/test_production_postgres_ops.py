from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts.backup_pilot_evidence import backup
from scripts.restore_pilot_evidence import restore
from scripts.validate_postgres_migration import validate


def _sqlite_source(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("create table pilot_events (event_id text primary key, event_type text not null)")
        connection.execute("insert into pilot_events values ('event-1', 'pilot_started')")


def test_postgres_migration_static_contract_is_value_free_without_database() -> None:
    result = validate()
    assert result["status"] == "pass"
    assert result["database"] == "not_run"


def test_local_backup_and_restore_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite"
    backup_path = tmp_path / "backup.sqlite"
    restored = tmp_path / "restored.sqlite"
    _sqlite_source(source)
    assert backup(source, backup_path)["status"] == "pass"
    assert restore(backup_path, restored, confirm=True)["status"] == "pass"
    with sqlite3.connect(restored) as connection:
        assert connection.execute("select count(*) from pilot_events").fetchone()[0] == 1


def test_backup_and_restore_refuse_production_mode(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite"
    destination = tmp_path / "destination.sqlite"
    _sqlite_source(source)
    assert backup(source, destination, mode="production")["status"] == "blocked"
    assert restore(source, destination, mode="production", confirm=True)["status"] == "blocked"
