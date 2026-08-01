"""Apply the reviewed PostgreSQL migrations with a bounded safe summary.

The database URL is explicit input so this command never reads dotenv files or
prints connection details. Use a managed or disposable PostgreSQL database,
never SQLite, and take the documented backup checkpoint before production use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.postgres_runtime import connect
from scripts.validate_postgres_migration import MIGRATIONS, REQUIRED_INDEXES, REQUIRED_TABLES, _statements

SAFE_RELEASE = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify(connection) -> dict[str, str]:
    tables = {row[0] for row in connection.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'").fetchall()}
    indexes = {row[0] for row in connection.execute("SELECT indexname FROM pg_indexes WHERE schemaname='public'").fetchall()}
    foreign_key_count = connection.execute("SELECT count(*) FROM information_schema.table_constraints WHERE constraint_schema='public' AND constraint_type='FOREIGN KEY'").fetchone()[0]
    if not REQUIRED_TABLES.issubset(tables):
        return {"status": "failed", "check": "tables"}
    if not REQUIRED_INDEXES.issubset(indexes):
        return {"status": "failed", "check": "indexes"}
    if foreign_key_count < 4:
        return {"status": "failed", "check": "foreign_keys"}
    return {"status": "pass", "check": "tables_indexes_foreign_keys"}


def apply(database_url: str | None, *, release_version: str = "unconfigured", dry_run: bool = False) -> dict[str, object]:
    if not all(path.is_file() for path in MIGRATIONS):
        return {"status": "failed", "reason": "migration_files_missing"}
    if not SAFE_RELEASE.fullmatch(release_version):
        return {"status": "failed", "reason": "release_version_invalid"}
    if dry_run or not database_url:
        return {"status": "ready", "migration_count": len(MIGRATIONS), "mode": "dry_run" if dry_run else "database_required"}
    try:
        with connect(database_url) as connection:
            connection.execute("BEGIN")
            for path in MIGRATIONS:
                for statement in _statements(path):
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migration_ledger (migration_id, schema_version, release_version, checksum) VALUES (%s, %s, %s, %s) ON CONFLICT (migration_id) DO UPDATE SET schema_version = EXCLUDED.schema_version, release_version = EXCLUDED.release_version, checksum = EXCLUDED.checksum",
                    (path.stem, "schema-007", release_version, _checksum(path)),
                )
            verification = _verify(connection)
            if verification["status"] != "pass":
                connection.rollback()
                return {"status": "failed", "reason": "schema_verification_failed"}
            connection.commit()
            return {"status": "pass", "migration_count": len(MIGRATIONS), "ledger": "applied", "verification": verification["check"]}
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
