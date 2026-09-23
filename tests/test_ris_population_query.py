from __future__ import annotations

from contextlib import contextmanager
from datetime import date

import pytest


FIELDS = (
    "statistic_yyymm",
    "statistic_month",
    "district_code",
    "site_id",
    "village",
    "household_count",
    "total_population",
    "male_population",
    "female_population",
    "age_0_14",
    "age_15_64",
    "age_65_plus",
    "child_ratio",
    "working_age_ratio",
    "elderly_ratio",
    "average_household_size",
    "audit_reasons",
    "source_provider",
    "source_dataset",
)


def _row(
    yyymm: str,
    district_code: str = "65000010001",
    *,
    total_population: int = 20,
    child_ratio: float | None = 0.1,
    audit_reasons: list[str] | None = None,
) -> tuple[object, ...]:
    year = int(yyymm[:-2]) + 1911
    month = int(yyymm[-2:])
    values = {
        "statistic_yyymm": yyymm,
        "statistic_month": date(year, month, 1),
        "district_code": district_code,
        "site_id": "臺北市大安區",
        "village": "測試里",
        "household_count": 8,
        "total_population": total_population,
        "male_population": 10,
        "female_population": 10,
        "age_0_14": 2,
        "age_15_64": 16,
        "age_65_plus": 2,
        "child_ratio": child_ratio,
        "working_age_ratio": 0.8 if child_ratio is not None else None,
        "elderly_ratio": 0.1 if child_ratio is not None else None,
        "average_household_size": 2.5 if child_ratio is not None else None,
        "audit_reasons": list(audit_reasons or []),
        "source_provider": "RIS",
        "source_dataset": "ODRP014",
    }
    return tuple(values[field] for field in FIELDS)


class Result:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows

    def fetchone(self) -> tuple[object, ...] | None:
        return self.rows[0] if self.rows else None

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows


class FakeConnection:
    def __init__(self, rows: list[tuple[object, ...]], *, fail: Exception | None = None) -> None:
        self.rows = rows
        self.fail = fail
        self.events: list[tuple[str, object]] = []

    def __enter__(self) -> "FakeConnection":
        self.events.append(("connection_enter", None))
        return self

    def __exit__(self, *args: object) -> None:
        self.events.append(("connection_exit", None))

    @contextmanager
    def transaction(self):
        self.events.append(("transaction_enter", None))
        try:
            yield
        finally:
            self.events.append(("transaction_exit", None))

    def execute(self, sql: str, params: tuple[object, ...] | None = None) -> Result:
        normalized = " ".join(sql.lower().split())
        self.events.append((normalized, params))
        if normalized == "set transaction read only":
            return Result([])
        assert normalized.startswith("select "), f"write or DDL reached read service: {normalized}"
        assert params is not None, "business SELECT must be parameterized"
        if self.fail is not None:
            raise self.fail
        return Result(self.rows)


def _service(connection: FakeConnection, *, url: str = "postgresql://safe-test"):
    from services.ris_population_query import RisPopulationQueryService

    requested_urls: list[str] = []

    def connect(database_url: str) -> FakeConnection:
        requested_urls.append(database_url)
        return connection

    service = RisPopulationQueryService(
        database_url_provider=lambda: url,
        connection_factory=connect,
    )
    return service, requested_urls


def test_latest_uses_descending_database_month_and_preserves_audit_metadata() -> None:
    connection = FakeConnection([_row("11507", audit_reasons=["sex_total_mismatch"])])
    service, requested_urls = _service(connection)

    result = service.latest("65000010001")

    assert result["statistic_yyymm"] == "11507"
    assert result["audit_reasons"] == ["sex_total_mismatch"]
    select_sql, params = next(event for event in connection.events if str(event[0]).startswith("select "))
    assert "where district_code = %s" in select_sql
    assert "order by statistic_month desc" in select_sql
    assert "limit 1" in select_sql
    assert params == ("65000010001",)
    assert requested_urls == ["postgresql://safe-test"]


def test_exact_month_uses_composite_business_key_and_isolates_district() -> None:
    connection = FakeConnection([_row("11504", "65000010002")])
    service, _ = _service(connection)

    result = service.exact_month("65000010002", "11504")

    assert result["district_code"] == "65000010002"
    select_sql, params = next(event for event in connection.events if str(event[0]).startswith("select "))
    assert "statistic_yyymm = %s" in select_sql
    assert "district_code = %s" in select_sql
    assert params == ("11504", "65000010002")


def test_history_selects_recent_limit_then_returns_ascending_months() -> None:
    connection = FakeConnection([_row("11407"), _row("11504"), _row("11507")])
    service, _ = _service(connection)

    result = service.history("65000010001", limit=13)

    assert [row["statistic_yyymm"] for row in result] == ["11407", "11504", "11507"]
    select_sql, params = next(event for event in connection.events if str(event[0]).startswith("select "))
    assert "order by statistic_month desc" in select_sql
    assert "limit %s" in select_sql
    assert select_sql.endswith("order by statistic_month asc")
    assert params == ("65000010001", 13)


def test_zero_and_null_values_are_not_rewritten() -> None:
    connection = FakeConnection([_row("11507", total_population=0, child_ratio=None)])
    service, _ = _service(connection)

    result = service.latest("65000010001")

    assert result["total_population"] == 0
    assert result["child_ratio"] is None
    assert result["working_age_ratio"] is None
    assert result["average_household_size"] is None


def test_read_only_transaction_is_set_before_parameterized_select() -> None:
    connection = FakeConnection([_row("11507")])
    service, _ = _service(connection)

    service.latest("65000010001")

    names = [event[0] for event in connection.events]
    assert names.index("transaction_enter") < names.index("set transaction read only")
    select_index = next(index for index, name in enumerate(names) if str(name).startswith("select "))
    assert names.index("set transaction read only") < select_index < names.index("transaction_exit")


def test_missing_database_configuration_is_unavailable_without_connecting() -> None:
    from services.ris_population_query import RisPopulationQueryUnavailable, RisPopulationQueryService

    connected = False

    def forbidden_connect(_url: str):
        nonlocal connected
        connected = True
        raise AssertionError("must not connect")

    service = RisPopulationQueryService(
        database_url_provider=lambda: "",
        connection_factory=forbidden_connect,
    )

    with pytest.raises(RisPopulationQueryUnavailable):
        service.latest("65000010001")
    assert connected is False


def test_database_exception_is_replaced_with_safe_unavailable_error() -> None:
    from services.ris_population_query import RisPopulationQueryUnavailable

    connection = FakeConnection([], fail=RuntimeError("postgresql://secret-host SELECT private"))
    service, _ = _service(connection)

    with pytest.raises(RisPopulationQueryUnavailable) as error:
        service.latest("65000010001")

    assert "secret-host" not in str(error.value)
    assert "select" not in str(error.value).lower()


def test_malformed_database_row_is_replaced_with_safe_unavailable_error() -> None:
    from services.ris_population_query import RisPopulationQueryUnavailable

    connection = FakeConnection([("11507",)])
    service, _ = _service(connection)

    with pytest.raises(RisPopulationQueryUnavailable):
        service.latest("65000010001")


def test_query_path_never_calls_r2_or_live_ris(monkeypatch) -> None:
    from services import ris_population_archive, ris_population_provider

    def forbidden(*_args, **_kwargs):
        raise AssertionError("request-time external source call")

    monkeypatch.setattr(ris_population_archive, "verify_object", forbidden)
    monkeypatch.setattr(ris_population_provider, "fetch_population_pages", forbidden)
    connection = FakeConnection([_row("11507")])
    service, _ = _service(connection)

    assert service.latest("65000010001")["source_provider"] == "RIS"


def test_default_service_uses_production_config_database_url(monkeypatch) -> None:
    from services import production_config
    from services.ris_population_query import RisPopulationQueryService

    connection = FakeConnection([_row("11507")])
    requested_urls: list[str] = []
    monkeypatch.setattr(production_config, "database_url", lambda: "postgresql://production-contract")

    def connect(url: str) -> FakeConnection:
        requested_urls.append(url)
        return connection

    service = RisPopulationQueryService(connection_factory=connect)

    service.latest("65000010001")

    assert requested_urls == ["postgresql://production-contract"]
