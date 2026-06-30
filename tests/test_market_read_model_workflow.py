"""Static tests for the market read model schema, docs, and workflow."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/refresh-market-read-model.yml").read_text(encoding="utf-8")
DOCS = (ROOT / "docs/nationwide-market-read-model-v1.md").read_text(encoding="utf-8")
SCHEMA = (ROOT / "database/market_read_model_schema.sql").read_text(encoding="utf-8")


def test_market_read_model_workflow_yaml_is_parseable_when_parser_available() -> None:
    try:
        import yaml  # type: ignore[import-not-found]
    except Exception:
        yaml = None

    if yaml is not None:
        parsed = yaml.safe_load(WORKFLOW)
        assert parsed["name"] == "Refresh Market Read Model"
        trigger = parsed.get("on", parsed.get(True))
        assert trigger == {"workflow_dispatch": None}
        assert parsed["permissions"] == {}

    lines = WORKFLOW.splitlines()
    assert lines[0] == "name: Refresh Market Read Model"
    assert lines[2] == "on:"
    assert lines[3] == "  workflow_dispatch:"
    assert "          import json" in lines
    assert "          PY" in lines


def test_market_read_model_workflow_is_manual_only_and_secret_backed() -> None:
    assert "workflow_dispatch" in WORKFLOW
    assert "schedule" not in WORKFLOW
    assert "push:" not in WORKFLOW
    assert "pull_request" not in WORKFLOW
    assert "secrets.RENDER_API_BASE_URL" in WORKFLOW
    assert "secrets.MARKET_READ_MODEL_REFRESH_TOKEN" in WORKFLOW
    assert "permissions: {}" in WORKFLOW


def test_market_read_model_workflow_calls_refresh_once_safely() -> None:
    assert WORKFLOW.count("/market-insights/refresh") == 1
    assert "X-Market-Read-Model-Refresh-Token" in WORKFLOW
    assert "--connect-timeout 20" in WORKFLOW
    assert "--max-time 180" in WORKFLOW
    assert "--verbose" not in WORKFLOW
    assert "cat \"$body_file\"" not in WORKFLOW
    assert "MARKET_READ_MODEL_REFRESH=success" in WORKFLOW
    assert "MARKET_READ_MODEL_HTTP_STATUS=200" in WORKFLOW
    assert "MARKET_READ_MODEL_REASON=" in WORKFLOW


def test_market_read_model_workflow_outputs_only_allowlisted_failure_reason() -> None:
    for reason in (
        "refresh_runtime_not_configured",
        "valuation_database_unavailable",
        "read_model_initialization_unavailable",
        "read_model_refresh_unavailable",
        "unknown_safe_failure",
    ):
        assert reason in WORKFLOW
    assert "json.load" in WORKFLOW
    assert "payload.get(\"reason_code\")" in WORKFLOW
    assert "rm -f \"$body_file\"" in WORKFLOW
    assert "cat \"$body_file\"" not in WORKFLOW
    assert "echo \"$body_file\"" not in WORKFLOW
    assert "echo \"${base_url}" not in WORKFLOW
    assert "echo \"${MARKET_READ_MODEL_REFRESH_TOKEN}" not in WORKFLOW
    assert "--verbose" not in WORKFLOW
    assert "--retry" not in WORKFLOW
    assert "set -x" not in WORKFLOW
    for forbidden in ("database_url", "SQL", "raw exception", "response body", "address", "latitude", "longitude"):
        assert forbidden not in WORKFLOW


def test_market_read_model_schema_contains_indexed_aggregate_tables() -> None:
    assert "market_district_period_aggregates" in SCHEMA
    assert "market_read_model_metadata" in SCHEMA
    for field in (
        "county",
        "district",
        "period",
        "average_unit_price",
        "transaction_count",
        "record_count",
        "source_name",
        "source_updated_at",
        "coverage_status",
        "data_status",
        "aggregation_method",
        "built_at",
    ):
        assert field in SCHEMA
    assert "idx_market_read_model_county_district_period" in SCHEMA
    assert "real_price_transactions" not in SCHEMA


def test_market_read_model_docs_cover_operations_and_boundaries() -> None:
    assert "GET endpoints read only the read model tables" in DOCS
    assert "POST /market-insights/refresh" in DOCS
    assert "MARKET_READ_MODEL_REFRESH_TOKEN" in DOCS
    assert "RENDER_API_BASE_URL" in DOCS
    assert "workflow_dispatch" in DOCS
    assert "does not automatically change" in DOCS
    assert "valuation results" in DOCS
    assert "loan or credit calculations" in DOCS
    assert "purchase advice" in DOCS
