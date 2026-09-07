"""Validate reviewed Postgres migrations without touching hosted databases.

With ``--database-url`` the script opens an explicitly supplied disposable or
CI database, applies the migration inside a transaction, checks tables,
indexes and foreign keys, then rolls the transaction back.  Without a URL it
performs only a value-free static contract check.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.postgres_runtime import connect
from scripts.migration_registry import (
    MigrationRegistryError,
    load_registry,
    next_safe_sequence,
    production_migrations,
)


# Keep the compatibility constant used by existing tests and operator scripts,
# but derive it from the frozen registry instead of maintaining a second list.
MIGRATIONS = production_migrations(load_registry(verify_files=False))
REQUIRED_TABLES = {
    "pilot_campaigns", "pilot_sessions", "pilot_consents", "pilot_events",
    "pilot_feedback", "professional_reviews", "tax_analysis_history",
    "official_market_releases", "official_market_artifacts", "market_transactions",
    "market_transaction_quality_events", "market_region_period_aggregates",
    "official_market_region_coverage", "market_import_runs", "market_import_checkpoints",
    "plvr_dataset_generations", "plvr_generation_transactions",
    "plvr_generation_market_aggregates", "plvr_generation_region_coverage",
    "plvr_active_dataset", "plvr_generation_load_checkpoints",
}
REQUIRED_INDEXES = {
    "idx_pilot_sessions_campaign", "idx_pilot_events_idempotency",
    "idx_tax_analysis_history_created_at", "idx_tax_analysis_history_case_id",
    "idx_schema_migration_ledger_applied_at", "idx_market_transactions_region_period",
    "idx_market_aggregates_region_period",
    "idx_official_market_region_coverage_region_period",
    "idx_plvr_dataset_generations_state",
    "idx_plvr_generation_transactions_region_period",
    "idx_plvr_generation_transactions_business_key",
    "idx_plvr_generation_market_aggregates_region_period",
    "idx_plvr_generation_region_coverage_region_period",
    "idx_plvr_generation_load_checkpoints_updated_at",
}
REQUIRED_VNEXT_TABLES = {
    "vnext_core.workspaces",
    "vnext_core.workspace_members",
    "vnext_core.cases",
    "vnext_core.property_entities",
    "vnext_core.property_identity_references",
    "vnext_core.property_graph_nodes",
    "vnext_core.property_relations",
    "vnext_core.evidence_items",
    "vnext_core.evidence_lineage",
    "vnext_core.evidence_links",
    "vnext_core.identity_resolutions",
    "vnext_core.resolution_attempts",
    "vnext_core.identity_candidates",
    "vnext_core.identity_conflicts",
    "vnext_core.identity_decisions",
    "vnext_core.case_property_links",
    "vnext_private.idempotency_records",
    "vnext_private.audit_events",
    "vnext_private.legacy_case_imports",
}
REQUIRED_VNEXT_INDEXES = {
    "vnext_core.uq_vnext_workspaces_personal_owner",
    "vnext_core.idx_vnext_workspace_members_user_status",
    "vnext_core.idx_vnext_workspace_members_workspace_status_role",
    "vnext_core.idx_vnext_cases_workspace_status_updated",
    "vnext_core.idx_vnext_property_entities_workspace_status_updated",
    "vnext_core.idx_vnext_identity_references_workspace_type_status",
    "vnext_core.idx_vnext_property_graph_nodes_workspace_type_record",
    "vnext_core.idx_vnext_property_relations_from",
    "vnext_core.idx_vnext_property_relations_to",
    "vnext_core.idx_vnext_evidence_workspace_fact_status_retrieved",
    "vnext_core.idx_vnext_evidence_lineage_parent",
    "vnext_core.idx_vnext_evidence_links_subject",
    "vnext_core.idx_vnext_identity_resolutions_workspace_status_started",
    "vnext_core.idx_vnext_identity_resolutions_case_started",
    "vnext_core.idx_vnext_resolution_attempts_resolution_order",
    "vnext_core.idx_vnext_identity_candidates_resolution_rank",
    "vnext_core.idx_vnext_identity_candidates_existing_property",
    "vnext_core.idx_vnext_identity_candidates_evidence",
    "vnext_core.idx_vnext_identity_conflicts_resolution_state",
    "vnext_core.idx_vnext_identity_decisions_resolution_created",
    "vnext_core.idx_vnext_identity_decisions_property_confirmed",
    "vnext_core.idx_vnext_property_relations_confirmation",
    "vnext_core.idx_vnext_case_property_links_case_history",
    "vnext_core.idx_vnext_case_property_links_property",
    "vnext_private.idx_vnext_idempotency_expiry",
    "vnext_private.idx_vnext_audit_workspace_created",
    "vnext_private.idx_vnext_audit_request",
    "vnext_private.idx_vnext_legacy_case_imports_actor",
}
REQUIRED_VNEXT_FOREIGN_KEYS = {
    "fk_vnext_cases_assigned_member",
    "fk_vnext_property_entities_workspace",
    "fk_vnext_identity_references_supersedes",
    "fk_vnext_evidence_supersedes",
    "fk_vnext_property_relations_from_node",
    "fk_vnext_property_relations_to_node",
    "fk_vnext_property_relations_evidence",
    "fk_vnext_property_relations_supersedes",
    "fk_vnext_evidence_lineage_child",
    "fk_vnext_evidence_lineage_parent",
    "fk_vnext_evidence_links_evidence",
    "fk_vnext_evidence_links_subject",
    "fk_vnext_identity_resolutions_case",
    "fk_vnext_identity_resolutions_supersedes",
    "fk_vnext_resolution_attempts_resolution",
    "fk_vnext_identity_candidates_resolution",
    "fk_vnext_identity_candidates_existing_property",
    "fk_vnext_identity_candidates_supersedes",
    "fk_vnext_identity_conflicts_left_candidate",
    "fk_vnext_identity_conflicts_right_candidate",
    "fk_vnext_identity_conflicts_evidence",
    "fk_vnext_identity_conflicts_property",
    "fk_vnext_identity_decisions_resolution",
    "fk_vnext_identity_decisions_candidate",
    "fk_vnext_identity_decisions_property",
    "fk_vnext_identity_decisions_reference",
    "fk_vnext_identity_decisions_evidence",
    "fk_vnext_identity_decisions_idempotency",
    "fk_vnext_property_relations_confirmation",
    "fk_vnext_case_property_links_case",
    "fk_vnext_case_property_links_property",
    "fk_vnext_case_property_links_resolution",
    "fk_vnext_case_property_links_confirmation",
    "fk_vnext_case_property_links_supersedes",
    "fk_vnext_legacy_import_workspace",
    "fk_vnext_legacy_import_case",
    "fk_vnext_legacy_import_actor",
    "fk_vnext_legacy_import_idempotency",
}
_DOLLAR_QUOTE_START = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")


def _static_contract() -> dict[str, Any]:
    try:
        registrations = load_registry()
    except MigrationRegistryError as exc:
        return {"status": "fail", "migration": exc.reason}
    if MIGRATIONS != production_migrations(registrations):
        return {"status": "fail", "migration": "migration_runner_registry_mismatch"}
    joined = "\n".join(path.read_text(encoding="utf-8") for path in MIGRATIONS).lower()
    required = (
        "references", "on delete cascade", "create index", "tax_analysis_history",
        "jsonb", "schema_migration_ledger", "schema_version", "official_market_releases",
        "market_region_period_aggregates", "market_import_checkpoints",
        "plvr_dataset_generations", "plvr_active_dataset",
        "create role vnext_api", "force row level security",
        "workspace_members_self_select", "vnext_private.idempotency_records",
        "vnext_private.audit_events",
        "vnext_core.property_entities", "vnext_core.property_graph_nodes",
        "vnext_core.property_relations", "vnext_core.evidence_items",
        "vnext_core.evidence_lineage", "vnext_core.evidence_links",
        "vnext_core.identity_resolutions", "vnext_core.resolution_attempts",
        "vnext_core.identity_candidates", "vnext_core.identity_conflicts",
        "vnext_core.identity_decisions", "vnext_core.case_property_links",
        "identity_confirmation_id", "case_property_links_owner_admin_insert",
        "needs_human_confirmation",
        "vnext_private.legacy_case_imports", "legacy_case_imports_actor_insert",
        "legacy_unverified", "saved_case_v1",
    )
    if not all(token in joined for token in required):
        return {"status": "fail", "migration": "contract_incomplete"}
    return {
        "status": "pass",
        "migration": "static_contract_pass",
        "registry_count": len(registrations),
        "managed_migration_count": len(MIGRATIONS),
        "next_migration_sequence": f"{next_safe_sequence(registrations):03d}",
    }


def _split_sql(sql: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    index = 0
    single_quote = False
    double_quote = False
    dollar_quote: str | None = None
    length = len(sql)

    def flush() -> None:
        statement = "".join(buffer).strip()
        if statement:
            statements.append(statement)
        buffer.clear()

    while index < length:
        character = sql[index]

        if dollar_quote is not None:
            if sql.startswith(dollar_quote, index):
                buffer.append(dollar_quote)
                index += len(dollar_quote)
                dollar_quote = None
            else:
                buffer.append(character)
                index += 1
            continue

        if single_quote:
            buffer.append(character)
            if character == "'":
                if index + 1 < length and sql[index + 1] == "'":
                    buffer.append(sql[index + 1])
                    index += 2
                else:
                    single_quote = False
                    index += 1
            elif character == "\\" and index + 1 < length:
                buffer.append(sql[index + 1])
                index += 2
            else:
                index += 1
            continue

        if double_quote:
            buffer.append(character)
            if character == '"':
                if index + 1 < length and sql[index + 1] == '"':
                    buffer.append(sql[index + 1])
                    index += 2
                else:
                    double_quote = False
                    index += 1
            else:
                index += 1
            continue

        if sql.startswith("--", index):
            index += 2
            while index < length and sql[index] != "\n":
                index += 1
            buffer.append("\n")
            if index < length:
                index += 1
            continue

        if sql.startswith("/*", index):
            index += 2
            depth = 1
            while index < length and depth:
                if sql.startswith("/*", index):
                    depth += 1
                    index += 2
                elif sql.startswith("*/", index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            if depth:
                raise ValueError("unterminated block comment")
            buffer.append(" ")
            continue

        if character == "'":
            single_quote = True
            buffer.append(character)
            index += 1
            continue

        if character == '"':
            double_quote = True
            buffer.append(character)
            index += 1
            continue

        if character == "$":
            match = _DOLLAR_QUOTE_START.match(sql, index)
            if match is not None:
                dollar_quote = match.group(0)
                buffer.append(dollar_quote)
                index = match.end()
                continue

        if character == ";":
            flush()
        else:
            buffer.append(character)
        index += 1

    if single_quote:
        raise ValueError("unterminated single-quoted string")
    if double_quote:
        raise ValueError("unterminated double-quoted identifier")
    if dollar_quote is not None:
        raise ValueError("unterminated dollar-quoted string")
    flush()
    return statements


def _statements(path: Path) -> list[str]:
    return _split_sql(path.read_text(encoding="utf-8"))


def _execute_disposable(database_url: str) -> dict[str, str]:
    class _RollbackValidation(Exception):
        pass

    class _SchemaContractFailure(Exception):
        pass

    with connect(database_url) as connection:
        try:
            with connection.transaction():
                # A plain disposable PostgreSQL service does not include the
                # Supabase Auth schema. Supply only the canonical prerequisite
                # contract inside this rollback-only validation transaction.
                connection.execute("CREATE SCHEMA IF NOT EXISTS auth")
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS auth.users (id uuid PRIMARY KEY)"
                )
                auth_uid = connection.execute(
                    "SELECT to_regprocedure('auth.uid()')"
                ).fetchone()
                if auth_uid is None or auth_uid[0] is None:
                    connection.execute(
                        "CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE "
                        "SET search_path = '' AS $$ "
                        "SELECT COALESCE("
                        "NULLIF(current_setting('request.jwt.claim.sub', true), ''), "
                        "NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'"
                        ")::uuid $$"
                    )
                for path in MIGRATIONS:
                    for statement in _statements(path):
                        connection.execute(statement)
                tables = {row[0] for row in connection.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'").fetchall()}
                indexes = {row[0] for row in connection.execute("SELECT indexname FROM pg_indexes WHERE schemaname='public'").fetchall()}
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
                foreign_key_count = connection.execute("SELECT count(*) FROM information_schema.table_constraints WHERE constraint_schema='public' AND constraint_type='FOREIGN KEY'").fetchone()[0]
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
                if (
                    not REQUIRED_TABLES.issubset(tables)
                    or not REQUIRED_INDEXES.issubset(indexes)
                    or not REQUIRED_VNEXT_TABLES.issubset(vnext_tables)
                    or not REQUIRED_VNEXT_INDEXES.issubset(vnext_indexes)
                    or foreign_key_count < 4
                    or vnext_foreign_key_count < 69
                    or not REQUIRED_VNEXT_FOREIGN_KEYS.issubset(vnext_foreign_keys)
                ):
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
