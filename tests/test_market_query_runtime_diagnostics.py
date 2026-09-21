"""Safe, zero-network diagnostics coverage for Market Insight queries."""

from __future__ import annotations

import re
from datetime import date
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


class _RoadRepository(_DirectRepository):
    def __init__(self, rows: list[dict[str, Any]], failure: bool = False) -> None:
        super().__init__()
        self.rows = rows
        self.failure = failure
        self.summary_called = False

    def summary(self, county: str, district: str, _period: str | None = None) -> dict[str, Any] | None:
        self.summary_called = True
        return super().summary(county, district, _period)

    def road_evidence(self, _county: str, _district: str) -> dict[str, Any]:
        if self.failure:
            raise RuntimeError("private road query detail")
        return {
            "rows": self.rows,
            "latest_import_status": "completed",
            "latest_imported_at": "2026-09-15T00:00:00+00:00",
        }


def _road_row(index: int, road: str = "和平東路二段") -> dict[str, Any]:
    return {
        "source": "official_plvr_opendata",
        "transaction_period": "2026-09",
        "city": "台北市",
        "district": "大安區",
        "road": road,
        "unit_price_per_ping": 60 + index,
        "total_price": (60 + index) * 30,
        "area_ping": 30,
        "imported_at": "2026-09-15T00:00:00+00:00",
    }


def test_service_road_query_uses_road_evidence_without_legacy_summary() -> None:
    """Calling the legacy summary would make road scope impossible to prove."""

    repository = _RoadRepository([_road_row(index) for index in range(10)])

    result = get_market_summary(
        "台北市",
        "大安區",
        road="和平東路2段",
        repository=repository,
        as_of=date(2026, 9, 21),
    )

    assert repository.summary_called is False
    assert result["effective_analysis_level"] == "ROAD"
    assert result["normalized_road"] == "和平東路二段"
    assert result["road_sample_count"] == 10
    assert result["support_reference"]


def test_service_road_query_failure_is_safe_and_bounded() -> None:
    """A provider exception must not leak through the road branch."""

    result = get_market_summary(
        "台北市",
        "大安區",
        road="和平東路二段",
        repository=_RoadRepository([], failure=True),
        as_of=date(2026, 9, 21),
    )

    assert result["data_status"] == "unavailable"
    assert result["reason_code"] == "market_road_query_unavailable"
    assert result["requested_scope"] == "ROAD"
    assert result["requested_road"] == "和平東路二段"
    assert result["normalized_road"] == "和平東路二段"
    assert result["effective_analysis_level"] == "NOT_AVAILABLE"
    assert result["fallback_reason"] == "market_road_unknown"
    assert result["monthly_series"] == []
    assert result["yearly_series"] == []
    assert result["median_unit_price_per_ping"] is None
    assert SUPPORT_REFERENCE_PATTERN.fullmatch(result["support_reference"])
    assert "private" not in str(result)


def test_service_road_runtime_missing_preserves_requested_scope(monkeypatch) -> None:
    from services import plvr_market_aggregate_service

    monkeypatch.setattr(plvr_market_aggregate_service, "_repository_from_env", lambda: None)

    result = get_market_summary(
        "台北市",
        "大安區",
        road="和平東路2段",
        as_of=date(2026, 9, 21),
    )

    assert result["reason_code"] == "market_runtime_not_configured"
    assert result["requested_road"] == "和平東路2段"
    assert result["normalized_road"] == "和平東路二段"
    assert result["effective_analysis_level"] == "NOT_AVAILABLE"
    assert result["monthly_series"] == []
    assert result["yearly_series"] == []


def test_service_road_unconfirmed_coverage_preserves_requested_scope() -> None:
    repository = _RoadRepository([])
    repository.coverage = lambda _county, _district: {  # type: ignore[method-assign]
        "coverage_status": "not_covered",
        "valid_market_candidate_count": 0,
    }

    result = get_market_summary(
        "台北市",
        "大安區",
        road="和平東路二段",
        repository=repository,
        as_of=date(2026, 9, 21),
    )

    assert result["reason_code"] == "market_coverage_not_confirmed"
    assert result["requested_scope"] == "ROAD"
    assert result["requested_road"] == "和平東路二段"
    assert result["effective_analysis_level"] == "NOT_AVAILABLE"
    assert result["fallback_reason"] == "market_road_unknown"


class _RoadEvidenceCursor:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.active = ""

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def execute(self, statement: str, _params: Any = None) -> None:
        self.statements.append(statement)
        if "from real_price_transactions" in statement:
            self.active = "evidence"
        elif "from valuation_import_runs" in statement:
            self.active = "metadata"

    def fetchall(self) -> list[dict[str, Any]]:
        if self.active != "evidence":
            return []
        return [_road_row(0)]

    def fetchone(self) -> dict[str, Any] | None:
        if self.active == "metadata":
            return {
                "latest_import_status": "completed",
                "latest_imported_at": "2026-09-15T00:00:00+00:00",
            }
        return None


class _RoadEvidenceConnection:
    def __init__(self) -> None:
        self.road_cursor = _RoadEvidenceCursor()

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def cursor(self) -> _RoadEvidenceCursor:
        return self.road_cursor


class _RoadEvidencePostgresRepository(PostgresMarketReadModelRepository):
    def __init__(self) -> None:
        super().__init__(database_url="unused")
        object.__setattr__(self, "connection", _RoadEvidenceConnection())

    def _connect(self) -> _RoadEvidenceConnection:
        return self.connection


def test_postgres_road_evidence_query_is_address_free_and_untruncated() -> None:
    """A LIMIT or sensitive selected column could make counts false or leak data."""

    repository = _RoadEvidencePostgresRepository()

    evidence = repository.road_evidence("台北市", "大安區")

    assert evidence["rows"] == [_road_row(0)]
    evidence_sql = next(
        statement for statement in repository.connection.road_cursor.statements
        if "from real_price_transactions" in statement
    ).lower()
    for forbidden in ("address_text", " lat", " lng", "raw_note", "select id", "limit"):
        assert forbidden not in evidence_sql
    assert "source = 'official_plvr_opendata'" in evidence_sql


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
