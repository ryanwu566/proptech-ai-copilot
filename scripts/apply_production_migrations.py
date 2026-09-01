"""Apply the reviewed PostgreSQL migrations with a bounded safe summary.

The database URL is explicit input so this command never reads dotenv files or
prints connection details. Use a managed or disposable PostgreSQL database,
never SQLite, and take the documented backup checkpoint before production use.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.postgres_runtime import connect
from scripts.migration_registry import (
    MigrationRegistryError,
    checksum,
    load_registry,
    next_safe_sequence,
    production_migrations,
)
from scripts.validate_postgres_migration import (
    MIGRATIONS,
    REQUIRED_INDEXES,
    REQUIRED_TABLES,
    REQUIRED_VNEXT_INDEXES,
    REQUIRED_VNEXT_FOREIGN_KEYS,
    REQUIRED_VNEXT_TABLES,
    _statements,
)

SAFE_RELEASE = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")
LEDGER_MIGRATION = next(path for path in MIGRATIONS if path.stem == "007_add_schema_migration_ledger")


class _SafeMigrationFailure(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _checksum(path: Path) -> str:
    return checksum(path)


def _schema_version(path: Path) -> str:
    match = re.match(r"^(\d+)_", path.name)
    return f"schema-{match.group(1)}" if match else "schema-unknown"


def _verify(connection) -> dict[str, str]:
    tables = {row[0] for row in connection.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'").fetchall()}
    indexes = {row[0] for row in connection.execute("SELECT indexname FROM pg_indexes WHERE schemaname='public'").fetchall()}
    foreign_key_count = connection.execute("SELECT count(*) FROM information_schema.table_constraints WHERE constraint_schema='public' AND constraint_type='FOREIGN KEY'").fetchone()[0]
    vnext_tables = {
        f"{row[0]}.{row[1]}"
        for row in connection.execute(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema IN ('vnext_core', 'vnext_private')"
        ).fetchall()
    }
    vnext_indexes = {
        f"{row[0]}.{row[1]}"
        for row in connection.execute(
            "SELECT schemaname, indexname FROM pg_indexes "
            "WHERE schemaname IN ('vnext_core', 'vnext_private')"
        ).fetchall()
    }
    vnext_foreign_key_count = connection.execute(
        "SELECT count(*) FROM information_schema.table_constraints "
        "WHERE constraint_schema IN ('vnext_core', 'vnext_private') "
        "AND constraint_type = 'FOREIGN KEY'"
    ).fetchone()[0]
    vnext_foreign_keys = {
        row[0]
        for row in connection.execute(
            "SELECT constraint_name FROM information_schema.table_constraints "
            "WHERE constraint_schema IN ('vnext_core', 'vnext_private') "
            "AND constraint_type = 'FOREIGN KEY'"
        ).fetchall()
    }
    if not REQUIRED_TABLES.issubset(tables):
        return {"status": "failed", "check": "tables"}
    if not REQUIRED_INDEXES.issubset(indexes):
        return {"status": "failed", "check": "indexes"}
    if not REQUIRED_VNEXT_TABLES.issubset(vnext_tables):
        return {"status": "failed", "check": "vnext_tables"}
    if not REQUIRED_VNEXT_INDEXES.issubset(vnext_indexes):
        return {"status": "failed", "check": "vnext_indexes"}
    if foreign_key_count < 4:
        return {"status": "failed", "check": "foreign_keys"}
    if vnext_foreign_key_count < 65 or not REQUIRED_VNEXT_FOREIGN_KEYS.issubset(vnext_foreign_keys):
        return {"status": "failed", "check": "vnext_foreign_keys"}
    return {"status": "pass", "check": "tables_indexes_foreign_keys"}


def _ensure_ledger(connection) -> None:
    for statement in _statements(LEDGER_MIGRATION):
        connection.execute(statement)
    columns = {
        row[0]
        for row in connection.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'schema_migration_ledger'"
        ).fetchall()
    }
    required_columns = {"migration_id", "schema_version", "applied_at", "release_version", "checksum"}
    if not required_columns.issubset(columns):
        raise _SafeMigrationFailure("migration_ledger_schema_invalid")
    primary_key = connection.execute(
        "SELECT constraint_name FROM information_schema.table_constraints WHERE table_schema = 'public' AND table_name = 'schema_migration_ledger' AND constraint_type = 'PRIMARY KEY'"
    ).fetchone()
    if primary_key is None:
        raise _SafeMigrationFailure("migration_ledger_schema_invalid")


def _apply_migrations(connection, *, release_version: str) -> None:
    _ensure_ledger(connection)
    for path in MIGRATIONS:
        checksum = _checksum(path)
        recorded = connection.execute(
            "SELECT checksum FROM schema_migration_ledger WHERE migration_id = %s",
            (path.stem,),
        ).fetchone()
        if recorded is not None:
            if recorded[0] != checksum:
                raise _SafeMigrationFailure("migration_checksum_drift")
            continue
        for statement in _statements(path):
            connection.execute(statement)
        connection.execute(
            "INSERT INTO schema_migration_ledger (migration_id, schema_version, release_version, checksum) VALUES (%s, %s, %s, %s)",
            (path.stem, _schema_version(path), release_version, checksum),
        )


def apply(database_url: str | None, *, release_version: str = "unconfigured", dry_run: bool = False) -> dict[str, object]:
    try:
        registrations = load_registry()
    except MigrationRegistryError as exc:
        return {"status": "failed", "reason": exc.reason}
    if MIGRATIONS != production_migrations(registrations):
        return {"status": "failed", "reason": "migration_runner_registry_mismatch"}
    if not SAFE_RELEASE.fullmatch(release_version):
        return {"status": "failed", "reason": "release_version_invalid"}
    summary = {
        "migration_count": len(MIGRATIONS),
        "registry_count": len(registrations),
        "next_migration_sequence": f"{next_safe_sequence(registrations):03d}",
    }
    if dry_run or not database_url:
        return {
            "status": "ready",
            **summary,
            "mode": "dry_run" if dry_run else "database_required",
        }
    try:
        with connect(database_url) as connection:
            with connection.transaction():
                _apply_migrations(connection, release_version=release_version)
                verification = _verify(connection)
                if verification["status"] != "pass":
                    raise _SafeMigrationFailure("schema_verification_failed")
            return {
                "status": "pass",
                **summary,
                "ledger": "applied",
                "verification": verification["check"],
            }
    except _SafeMigrationFailure as exc:
        return {"status": "unavailable", "reason": exc.reason}
    except Exception:
        return {"status": "unavailable", "reason": "database_migration_unavailable"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=None, help="Explicit managed or disposable PostgreSQL URL; never read from environment.")
    parser.add_argument("--release-version", default="unconfigured")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = apply(args.database_url, release_version=args.release_version, dry_run=args.dry_run)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in {"ready", "pass"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
