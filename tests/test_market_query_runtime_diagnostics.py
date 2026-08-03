"""Safe, zero-network diagnostics coverage for Market Insight queries."""

from __future__ import annotations

import re
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.api_main import app
from backend.api.routes_market import MARKET_QUERY_SAFE_FIELDS
from services.plvr_market_aggregate_service import (
    PostgresMarketReadModelRepository,
    get_market_summary,
    iter_taiwan_regions,
    safe_market_query_reason_code,
)


SUPPORT_REFERENCE_PATTERN = re.compile(r"[0-9a-f]{16}")


def test_query_reason_code_allowlist_never_accepts_raw_error() -> None:
    assert safe_market_query_reason_code("market_summary_query_unavailable") == "market_summary_query_unavailable"
    assert safe_market_query_reason_code("private psycopg error") == "market_unknown_safe_failure"


def test_api_query_exposes_only_safe_diagnostics(monkeypatch) -> None:
    from services import market_insight_service

    monkeypatch.setattr(
        market_insight_service,
        "get_market_summary",
        lambda *_args, **_kwargs: {
            "city": "Demo County",
            "district": "Demo District",
            "data_status": "unavailable",
            "coverage_status": "coverage_unknown",
            "reason_code": "market_summary_query_unavailable",
            "support_reference": "0123456789abcdef",
            "raw_error": "private SQL detail",
            "database_url": "must not leak",
        },
    )

    with TestClient(app) as client:
        response = client.post("/market-insights/query", json={"county": "Demo County", "district": "Demo District"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["reason_code"] == "market_summary_query_unavailable"
    assert payload["support_reference"] == "0123456789abcdef"
    assert "raw_error" not in payload
    assert "database_url" not in payload
    assert "private SQL detail" not in str(payload)
    assert set(payload).issubset(set(MARKET_QUERY_SAFE_FIELDS))


def test_api_unexpected_query_exception_returns_safe_reference(monkeypatch) -> None:
    from services import market_insight_service

    def fail(*_args, **_kwargs):
        raise RuntimeError("private raw exception")

    monkeypatch.setattr(market_insight_service, "get_market_summary", fail)

    with TestClient(app) as client:
        payload = client.post("/market-insights/query", json={"county": "Demo County"}).json()

    assert payload["reason_code"] == "market_unknown_safe_failure"
    assert SUPPORT_REFERENCE_PATTERN.fullmatch(payload["support_reference"])
    assert "private raw exception" not in str(payload)


class _PhaseCursor:
    def __init__(self, failure: str) -> None:
        self.failure = failure

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def execute(self, statement: str, _params: Any = None) -> None:
        if self.failure == "read_only" and statement == "set transaction read only":
            raise RuntimeError("private SQL and connection details")

    def fetchone(self) -> dict[str, Any] | None:
        return {"coverage_status": "covered", "valid_market_candidate_count": 2}

    def fetchall(self) -> list[dict[str, Any]]:
        return []


class _PhaseConnection:
    def __init__(self, failure: str) -> None:
        self.failure = failure

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def cursor(self) -> _PhaseCursor:
        return _PhaseCursor(self.failure)


class _PhaseRepository(PostgresMarketReadModelRepository):
    def __init__(self, failure: str) -> None:
        super().__init__(database_url="unused")
        self.failure = failure

    def _connect(self) -> _PhaseConnection:
        return _PhaseConnection(self.failure)


class _DirectRepository:
    def __init__(self, failure: str | None = None, invalid_metrics: bool = False) -> None:
        self.failure = failure
        self.invalid_metrics = invalid_metrics

    def coverage(self, _county: str, _district: str) -> dict[str, Any]:
        return {"coverage_status": "covered", "valid_market_candidate_count": 2}

    def summary(self, county: str, district: str, _period: str | None = None) -> dict[str, Any] | None:
        if self.failure == "summary":
            raise RuntimeError("private summary detail")
        return {
            "county": county,
            "district": district,
            "period": "2025-02",
            "average_unit_price": None if self.invalid_metrics else 70.0,
            "transaction_count": 2,
            "record_count": 2,
            "source_name": "Official PLVR OpenData aggregate",
            "data_status": "available",
            "coverage_status": "covered",
        }

    def history(self, _county: str, _district: str, limit: int = 6) -> list[dict[str, Any]]:
        del limit
        if self.failure == "history":
            raise RuntimeError("private history detail")
        return [{"period": "2025-02", "average_unit_price": 70.0, "transaction_count": 2}]


@pytest.mark.parametrize(
    ("failure", "reason_code"),
    (
        ("summary", "market_summary_query_unavailable"),
        ("history", "market_history_query_unavailable"),
    ),
)
def test_service_query_phase_failures_have_safe_reason_codes(failure: str, reason_code: str) -> None:
    region = next(iter(iter_taiwan_regions()))

    result = get_market_summary(region.county, region.district, repository=_DirectRepository(failure=failure))

    assert result["data_status"] == "unavailable"
    assert result["reason_code"] == reason_code
    assert SUPPORT_REFERENCE_PATTERN.fullmatch(result["support_reference"])
    assert "private" not in str(result)


def test_service_result_contract_failure_is_not_presented_as_available() -> None:
    region = next(iter(iter_taiwan_regions()))

    result = get_market_summary(
        region.county,
        region.district,
        repository=_DirectRepository(invalid_metrics=True),
    )

    assert result["data_status"] == "no_data"
    assert result["reason_code"] == "market_result_contract_invalid"
    assert result.get("average_unit_price") is None


def test_postgres_query_phase_failure_is_logged_without_public_raw_error(caplog) -> None:
    region = next(iter(iter_taiwan_regions()))
    with caplog.at_level("INFO", logger="proptech.market"):
        result = get_market_summary(region.county, region.district, repository=_PhaseRepository("read_only"))

    assert result["data_status"] == "unavailable"
    assert result["reason_code"] == "market_coverage_query_unavailable"
    assert SUPPORT_REFERENCE_PATTERN.fullmatch(result["support_reference"])
    messages = " ".join(record.getMessage() for record in caplog.records)
    assert '"event":"coverage_started"' in messages
    assert '"phase":"transaction_read_only"' in messages
    assert '"exception_class":"RuntimeError"' in messages
    assert "private SQL" not in messages
