"""Validate reviewed Postgres migrations without touching hosted databases.

With ``--database-url`` the script opens an explicitly supplied disposable or
CI database, applies the migration inside a transaction, checks tables,
indexes and foreign keys, then rolls the transaction back.  Without a URL it
performs only a value-free static contract check.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.postgres_runtime import connect


MIGRATIONS = (
    ROOT / "database" / "migrations" / "004_add_pilot_evidence.sql",
    ROOT / "database" / "migrations" / "005_add_pilot_security_indexes.sql",
    ROOT / "database" / "migrations" / "006_add_tax_analysis_history.sql",
    ROOT / "database" / "migrations" / "007_add_schema_migration_ledger.sql",
    ROOT / "database" / "migrations" / "008_add_official_market_pipeline.sql",
    ROOT / "database" / "migrations" / "009_separate_official_market_region_coverage.sql",
)
REQUIRED_TABLES = {"pilot_campaigns", "pilot_sessions", "pilot_consents", "pilot_events", "pilot_feedback", "professional_reviews", "tax_analysis_history", "official_market_releases", "official_market_artifacts", "market_transactions", "market_transaction_quality_events", "market_region_period_aggregates", "official_market_region_coverage", "market_import_runs", "market_import_checkpoints"}
REQUIRED_INDEXES = {"idx_pilot_sessions_campaign", "idx_pilot_events_idempotency", "idx_tax_analysis_history_created_at", "idx_tax_analysis_history_case_id", "idx_schema_migration_ledger_applied_at", "idx_market_transactions_region_period", "idx_market_aggregates_region_period", "idx_official_market_region_coverage_region_period"}


def _static_contract() -> dict[str, str]:
    if not all(path.is_file() for path in MIGRATIONS):
        return {"status": "fail", "migration": "missing"}
    joined = "\n".join(path.read_text(encoding="utf-8") for path in MIGRATIONS).lower()
    required = ("references", "on delete cascade", "create index", "tax_analysis_history", "jsonb", "schema_migration_ledger", "schema_version", "official_market_releases", "market_region_period_aggregates", "market_import_checkpoints")
    if not all(token in joined for token in required):
        return {"status": "fail", "migration": "contract_incomplete"}
    return {"status": "pass", "migration": "static_contract_pass"}


def _statements(path: Path) -> list[str]:
    sql = "\n".join(line for line in path.read_text(encoding="utf-8").splitlines() if not line.strip().startswith("--"))
    return [part.strip() for part in sql.split(";") if part.strip()]


def _execute_disposable(database_url: str) -> dict[str, str]:
    class _RollbackValidation(Exception):
        pass

    class _SchemaContractFailure(Exception):
        pass

    with connect(database_url) as connection:
        try:
            with connection.transaction():
                for path in MIGRATIONS:
                    for statement in _statements(path):
                        connection.execute(statement)
                tables = {row[0] for row in connection.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'").fetchall()}
                indexes = {row[0] for row in connection.execute("SELECT indexname FROM pg_indexes WHERE schemaname='public'").fetchall()}
                foreign_key_count = connection.execute("SELECT count(*) FROM information_schema.table_constraints WHERE constraint_schema='public' AND constraint_type='FOREIGN KEY'").fetchone()[0]
                if not REQUIRED_TABLES.issubset(tables) or not REQUIRED_INDEXES.issubset(indexes) or foreign_key_count < 4:
                    raise _SchemaContractFailure
                raise _RollbackValidation
        except _RollbackValidation:
            return {"status": "pass", "migration": "postgres_transaction_rolled_back", "foreign_keys": "pass", "indexes": "pass", "ledger": "pass"}
        except _SchemaContractFailure:
            return {"status": "fail", "migration": "schema_contract_failed"}


def validate(database_url: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = _static_contract()
    if result["status"] == "fail":
        return result
    if not database_url:
        result["database"] = "not_run"
        result["operator_note"] = "Provide a disposable Postgres URL for transactional application validation."
        return result
    try:
        result.update({"database": "validated", **_execute_disposable(database_url)})
    except Exception:
        return {"status": "unavailable", "migration": "database_validation_unavailable", "database": "unavailable"}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=None, help="Explicit disposable Postgres URL; never read from environment.")
    args = parser.parse_args()
    result = validate(args.database_url)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
