"""Regression coverage for PLVR geography and future-period containment."""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from scripts.import_plvr_to_postgres import _write_rows
from services import official_market_query
from services.official_plvr_market_pipeline import (
    NormalizedTransaction,
    aggregate_transactions,
    normalize_rows as normalize_official_rows,
    publish_release,
    score_comparables,
)
from services.plvr_data_integrity import (
    FUTURE_TRANSACTION_PERIOD,
    INVALID_CITY_DISTRICT_PAIR,
    canonical_region_storage_keys,
    current_transaction_period,
    first_day_after_current_period,
    normalized_row_integrity_reason,
)
from services.plvr_import_service import normalize_row, normalize_rows
from services.plvr_market_aggregate_service import (
    DIRECT_COVERAGE_COUNTY_SQL,
    DIRECT_COVERAGE_DISTRICT_SQL,
    DIRECT_HISTORY_COUNTY_SQL,
    DIRECT_HISTORY_DISTRICT_SQL,
    DIRECT_SUMMARY_COUNTY_LATEST_SQL,
    DIRECT_SUMMARY_DISTRICT_LATEST_SQL,
    PostgresMarketReadModelRepository,
    READ_MODEL_CATALOG_SQL,
    READ_MODEL_REGIONS_SQL,
    READ_MODEL_STATUS_SQL,
    REFRESH_TEMP_AGGREGATES_SQL,
    get_market_summary,
)
from services.taiwan_admin_registry import normalize_market_region


AS_OF = date(2026, 8, 11)


def _raw_row(
    *,
    city: str = "",
    district: str = "中正區",
    address: str = "臺北市中正區忠孝東路一段1號",
    transaction_date: str = "20260801",
) -> dict[str, str]:
    row = {
        "鄉鎮市區": district,
        "交易標的": "房地(土地+建物)",
        "土地位置建物門牌": address,
        "交易年月日": transaction_date,
        "移轉層次": "八層",
        "總樓層數": "十五層",
        "建物型態": "住宅大樓",
        "建築完成年月": "1000101",
        "建物移轉總面積平方公尺": "99.17",
        "總價元": "24000000",
        "單價元平方公尺": "242008",
    }
    if city:
        row["縣市"] = city
    return row


@pytest.mark.parametrize(
    ("county", "district", "expected_county", "expected_district"),
    [
        (" 台北市 ", " 中正區 ", "臺北市", "中正區"),
        ("臺北市", "中正區", "臺北市", "中正區"),
        ("台北市", "南港區", "臺北市", "南港區"),
        ("台中市", "北屯區", "臺中市", "北屯區"),
        ("桃園市", "中壢區", "桃園市", "中壢區"),
        ("桃園市", "平鎮區", "桃園市", "平鎮區"),
        ("台南市", "安平區", "臺南市", "安平區"),
        ("高雄市", "小港區", "高雄市", "小港區"),
        ("花蓮縣", "花蓮市", "花蓮縣", "花蓮市"),
        ("台東縣", "台東市", "臺東縣", "臺東市"),
    ],
)
def test_canonical_registry_accepts_aliases_and_golden_regions(
    county: str,
    district: str,
    expected_county: str,
    expected_district: str,
) -> None:
    result = normalize_market_region(county, district)
    assert result.valid is True
    assert (result.county, result.district) == (expected_county, expected_district)


def test_canonical_registry_fails_closed_without_cross_county_fuzzy_match() -> None:
    result = normalize_market_region("臺南市", "中壢區")
    assert result.valid is False
    assert result.reason == "unknown_district"
    assert len(canonical_region_storage_keys()) == 368


def test_filename_hint_cannot_override_an_incompatible_district() -> None:
    row, reason = normalize_row(
        _raw_row(district="中壢區", address="桃園市中壢區中正路1號"),
        city_hint="臺南市",
        as_of=AS_OF,
    )
    assert row is None
    assert reason == INVALID_CITY_DISTRICT_PAIR


@pytest.mark.parametrize(
    ("city", "district", "address"),
    [
        ("臺南市", "三民區", "臺南市三民區中正路1號"),
        ("未知市", "中正區", "未知市中正區中正路1號"),
        ("臺北市", "未知區", "臺北市未知區中正路1號"),
    ],
)
def test_normalization_rejects_noncanonical_region_pairs(
    city: str,
    district: str,
    address: str,
) -> None:
    row, reason = normalize_row(
        _raw_row(city=city, district=district, address=address),
        as_of=AS_OF,
    )
    assert row is None
    assert reason == INVALID_CITY_DISTRICT_PAIR


def test_explicit_row_city_has_precedence_over_filename_hint() -> None:
    row, reason = normalize_row(
        _raw_row(city="桃園市", district="中壢區", address="桃園市中壢區中正路1號"),
        city_hint="臺南市",
        as_of=AS_OF,
    )
    assert reason is None
    assert row is not None
    assert row["city"] == "桃園市"
    assert row["district"] == "中壢區"


def test_filename_hint_conflicting_with_address_city_fails_closed() -> None:
    row, reason = normalize_row(
        _raw_row(city="", district="東區", address="新竹市東區中央路1號"),
        city_hint="臺南市",
        as_of=AS_OF,
    )
    assert row is None
    assert reason == INVALID_CITY_DISTRICT_PAIR


def test_explicit_city_precedes_conflicting_hint_for_shared_district() -> None:
    row, reason = normalize_row(
        _raw_row(city="新竹市", district="東區", address="新竹市東區中央路1號"),
        city_hint="臺南市",
        as_of=AS_OF,
    )
    assert reason is None
    assert row is not None
    assert row["city"] == "新竹市"
    assert row["district"] == "東區"


def test_import_qc_counts_invalid_pair_and_future_period() -> None:
    valid = _raw_row()
    invalid_region = _raw_row(district="中壢區", address="桃園市中壢區中正路1號")
    future = _raw_row(transaction_date="20260901")

    accepted, report = normalize_rows(
        [valid, invalid_region, future],
        city_hint="臺北市",
        as_of=AS_OF,
    )

    assert len(accepted) == 1
    assert report["accepted_rows"] == 1
    assert report["excluded_rows"] == 2
    assert report["exclusion_reasons"] == {
        FUTURE_TRANSACTION_PERIOD: 1,
        INVALID_CITY_DISTRICT_PAIR: 1,
    }


@pytest.mark.parametrize(
    ("as_of", "expected_period", "expected_next_month"),
    [
        (date(2026, 8, 1), "2026-08", date(2026, 9, 1)),
        (date(2026, 9, 30), "2026-09", date(2026, 10, 1)),
        (date(2026, 10, 1), "2026-10", date(2026, 11, 1)),
    ],
)
def test_period_ceiling_is_injectable(
    as_of: date,
    expected_period: str,
    expected_next_month: date,
) -> None:
    assert current_transaction_period(as_of) == expected_period
    assert first_day_after_current_period(as_of) == expected_next_month


def test_period_ceiling_uses_taipei_calendar_at_utc_boundary() -> None:
    before_midnight = datetime(2026, 8, 31, 15, 59, tzinfo=timezone.utc)
    after_midnight = datetime(2026, 8, 31, 16, 0, tzinfo=timezone.utc)
    assert current_transaction_period(before_midnight) == "2026-08"
    assert current_transaction_period(after_midnight) == "2026-09"


def test_write_guard_rejects_future_rows_before_database_connection() -> None:
    row, reason = normalize_row(_raw_row(), city_hint="臺北市", as_of=AS_OF)
    assert reason is None and row is not None
    row["transaction_period"] = "2026-09"
    assert normalized_row_integrity_reason(row, as_of=AS_OF) == FUTURE_TRANSACTION_PERIOD

    with pytest.raises(ValueError, match=FUTURE_TRANSACTION_PERIOD):
        _write_rows(
            "database-must-not-be-opened",
            [row],
            {},
            SimpleNamespace(),
            ["臺北市"],
            ["中正區"],
            as_of=AS_OF,
        )


def test_write_guard_rejects_invalid_region_before_database_connection() -> None:
    row, reason = normalize_row(_raw_row(), city_hint="臺北市", as_of=AS_OF)
    assert reason is None and row is not None
    row.update({"city": "臺南市", "district": "中壢區"})
    assert normalized_row_integrity_reason(row, as_of=AS_OF) == INVALID_CITY_DISTRICT_PAIR

    with pytest.raises(ValueError, match=INVALID_CITY_DISTRICT_PAIR):
        _write_rows(
            "database-must-not-be-opened",
            [row],
            {},
            SimpleNamespace(),
            ["臺南市"],
            ["中壢區"],
            as_of=AS_OF,
        )


def test_official_pipeline_quarantines_future_period_with_qc_reason() -> None:
    accepted, summary = normalize_official_rows(
        [
            {
                "county": "臺北市",
                "district": "中正區",
                "transaction_date": "2026-09-01",
                "transaction_type": "房地",
                "total_price": "10000000",
                "area_sqm": "30",
            }
        ],
        source_id="fixture",
        release_id="release",
        as_of=AS_OF,
    )
    assert accepted == []
    assert summary.quarantined_rows == 1
    assert summary.reason_counts[FUTURE_TRANSACTION_PERIOD] == 1


def test_official_pipeline_quarantines_invalid_city_district_pair() -> None:
    accepted, summary = normalize_official_rows(
        [
            {
                "county": "臺南市",
                "district": "中壢區",
                "transaction_date": "2026-08-01",
                "transaction_type": "房地",
                "total_price": "10000000",
                "area_sqm": "30",
            }
        ],
        source_id="fixture",
        release_id="release",
        as_of=AS_OF,
    )
    assert accepted == []
    assert summary.quarantined_rows == 1
    assert summary.reason_counts[INVALID_CITY_DISTRICT_PAIR] == 1


def _transaction(period: str) -> NormalizedTransaction:
    return NormalizedTransaction(
        transaction_id=f"id-{period}",
        source_id="fixture",
        source_release_id="release",
        transaction_type="existing_sale",
        county="臺北市",
        district="中正區",
        transaction_date=date.fromisoformat(f"{period}-01"),
        area_sqm=30,
        total_price_ntd=3_000_000,
        unit_price_ntd_sqm=100_000,
        unit_price_ntd_ping=330_578.5,
        validation_status="valid",
        dedupe_fingerprint=f"fp-{period}",
    )


def test_aggregate_and_release_write_guards_reject_future_periods() -> None:
    future = _transaction("2026-09")
    assert aggregate_transactions(
        [future],
        source_name="fixture",
        source_release_id="release",
        source_updated_at=None,
        as_of=AS_OF,
    ) == []

    class NoDatabaseConnection:
        def cursor(self):
            raise AssertionError("database connection must not be used")

    with pytest.raises(ValueError, match=FUTURE_TRANSACTION_PERIOD):
        publish_release(
            NoDatabaseConnection(),
            release={"release_id": "release", "source_id": "fixture"},
            transactions=[future],
            aggregates=[],
            as_of=AS_OF,
        )


def test_future_target_and_candidates_do_not_enter_comparable_results() -> None:
    current = _transaction("2026-08")
    future = _transaction("2026-09")
    assert score_comparables(future, [current], as_of=AS_OF) == []
    assert score_comparables(current, [future], as_of=AS_OF) == []


class _AllFutureRepository:
    def coverage(self, _county: str, _district: str) -> dict[str, Any]:
        return {
            "coverage_status": "covered",
            "valid_market_candidate_count": 1,
            "source_updated_at": "2026-08-01",
        }

    def summary(self, county: str, district: str, _period: str | None = None) -> dict[str, Any]:
        return {
            "county": county,
            "district": district,
            "period": "2026-10",
            "average_unit_price": 99,
            "transaction_count": 1,
            "record_count": 1,
            "source_name": "fixture",
            "coverage_status": "covered",
            "data_status": "available",
        }

    def history(self, _county: str, _district: str, limit: int = 6) -> list[dict[str, Any]]:
        return [{"period": "2026-10", "average_unit_price": 99, "transaction_count": 1}][:limit]


def test_all_future_market_rows_are_unavailable_without_fake_zero_metrics() -> None:
    result = get_market_summary(
        "臺北市",
        "中正區",
        repository=_AllFutureRepository(),
        as_of=AS_OF,
    )
    assert result["data_status"] == "unavailable"
    assert result["coverage_status"] == "coverage_unknown"
    assert result["average_unit_price"] is None
    assert result["transaction_count"] is None
    assert result["history"] == []


def test_future_history_is_removed_without_changing_current_metrics() -> None:
    class MixedHistoryRepository(_AllFutureRepository):
        def summary(self, county: str, district: str, _period: str | None = None) -> dict[str, Any]:
            return {
                "county": county,
                "district": district,
                "period": "2026-08",
                "average_unit_price": 88,
                "transaction_count": 2,
                "record_count": 2,
                "source_name": "fixture",
                "coverage_status": "covered",
                "data_status": "available",
            }

        def history(self, _county: str, _district: str, limit: int = 6) -> list[dict[str, Any]]:
            return [
                {"period": "2026-10", "average_unit_price": 99, "transaction_count": 1},
                {"period": "2026-08", "average_unit_price": 88, "transaction_count": 2},
            ][:limit]

    result = get_market_summary(
        "臺北市",
        "中正區",
        repository=MixedHistoryRepository(),
        as_of=AS_OF,
    )
    assert result["data_status"] == "available"
    assert result["average_unit_price"] == 88
    assert result["transaction_count"] == 2
    assert [item["period"] for item in result["history"]] == ["2026-08"]


def test_market_sql_guards_canonical_pairs_and_future_periods() -> None:
    direct_sql = "\n".join(
        [
            DIRECT_SUMMARY_COUNTY_LATEST_SQL,
            DIRECT_SUMMARY_DISTRICT_LATEST_SQL,
            DIRECT_HISTORY_COUNTY_SQL,
            DIRECT_HISTORY_DISTRICT_SQL,
            DIRECT_COVERAGE_COUNTY_SQL,
            DIRECT_COVERAGE_DISTRICT_SQL,
            REFRESH_TEMP_AGGREGATES_SQL,
        ]
    )
    read_model_sql = "\n".join([READ_MODEL_STATUS_SQL, READ_MODEL_CATALOG_SQL, READ_MODEL_REGIONS_SQL])
    assert "= any(%s)" in direct_sql
    assert "transaction_period <= %s" in direct_sql
    assert "excluded_future_period_count" in direct_sql
    assert "= any(%s)" in read_model_sql
    assert "period <= %s" in read_model_sql


def test_repository_binds_canonical_keys_and_period_ceiling() -> None:
    class Cursor:
        def __init__(self) -> None:
            self.executions: list[tuple[str, list[Any]]] = []

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def execute(self, sql: str, params: list[Any] | None = None) -> None:
            self.executions.append((sql, list(params or [])))

        def fetchone(self) -> dict[str, Any]:
            return {
                "county": "台北市",
                "district": "中正區",
                "period": "2026-08",
                "average_unit_price": 90,
                "transaction_count": 1,
                "record_count": 1,
                "source_name": "fixture",
                "coverage_status": "covered",
                "data_status": "available",
            }

    class Connection:
        def __init__(self, cursor: Cursor) -> None:
            self.cursor_instance = cursor

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def cursor(self) -> Cursor:
            return self.cursor_instance

    class Repository(PostgresMarketReadModelRepository):
        def __init__(self) -> None:
            super().__init__("unused", as_of=AS_OF)
            object.__setattr__(self, "cursor_instance", Cursor())

        def _connect(self):
            return Connection(self.cursor_instance)

    repository = Repository()
    repository.summary("臺北市", "中正區")
    sql, params = repository.cursor_instance.executions[-1]
    assert sql == DIRECT_SUMMARY_DISTRICT_LATEST_SQL
    assert len(params[0]) == 368
    assert params[1:] == ["2026-08", "台北市", "中正區"]


def test_official_read_queries_bind_the_same_period_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    class Cursor:
        description: list[Any] = []

        def __init__(self) -> None:
            self.executions: list[tuple[str, list[Any]]] = []

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def execute(self, sql: str, params: list[Any] | None = None) -> None:
            self.executions.append((sql, list(params or [])))

        def fetchone(self):
            return None

        def fetchall(self):
            return []

    class Connection:
        def __init__(self) -> None:
            self.cursor_instance = Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def cursor(self) -> Cursor:
            return self.cursor_instance

        def close(self) -> None:
            return None

    aggregate_connection = Connection()
    monkeypatch.setattr(official_market_query, "_connect", lambda: aggregate_connection)
    result = official_market_query.query_aggregate(
        "臺北市",
        "中正區",
        as_of=AS_OF,
    )
    aggregate_sql, aggregate_params = aggregate_connection.cursor_instance.executions[-1]
    assert result["data_status"] == "no_data"
    assert "period <= %s" in aggregate_sql
    assert aggregate_params[3] == "2026-08"

    comparable_connection = Connection()
    monkeypatch.setattr(official_market_query, "_connect", lambda: comparable_connection)
    comparables = official_market_query.query_comparables(
        "臺北市",
        "中正區",
        as_of=AS_OF,
    )
    comparable_sql, comparable_params = comparable_connection.cursor_instance.executions[-1]
    assert comparables["comparables"] == []
    assert "transaction_date < %s" in comparable_sql
    assert comparable_params[-2] == date(2026, 9, 1)


def test_official_read_rejects_explicit_future_period_before_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        official_market_query,
        "_connect",
        lambda: (_ for _ in ()).throw(AssertionError("database connection must not be used")),
    )
    result = official_market_query.query_aggregate(
        "臺北市",
        "中正區",
        period="2026-09",
        as_of=AS_OF,
    )
    assert result == {
        "data_status": "unavailable",
        "coverage_status": "coverage_unknown",
        "reason": "future_period_excluded",
    }
