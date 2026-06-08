from datetime import UTC, datetime

from services.valuation_providers.postgres_provider import PostgresValuationProvider


class FakeCursor:
    def __init__(self, official: int, sample: int) -> None:
        self.official = official
        self.sample = sample
        self.query = ""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query, _params=None) -> None:
        self.query = " ".join(query.split())

    def fetchone(self):
        if "from valuation_import_runs" in self.query:
            return {
                "imported_at": datetime(2026, 6, 1, tzinfo=UTC),
                "status": "completed",
                "city_scope": "台北市,新北市",
                "district_scope": "大安區,板橋區",
                "road_scope": "",
                "inserted_rows": 125,
                "skipped_duplicate_rows": 5,
            }
        return {
            "records_count": self.official + self.sample,
            "cities_count": 1,
            "districts_count": 1,
            "roads_count": 2,
            "official_records_count": self.official,
            "sample_records_count": self.sample,
            "raw_official_period_min": "2016-09",
            "raw_official_period_max": "2026-10",
            "effective_trend_period_min": "2025-01",
            "effective_trend_period_max": "2026-05",
            "excluded_future_period_count": 4,
            "excluded_too_old_period_count": 8,
        }

    def fetchall(self):
        return [{"city": "台北市"}] if "distinct city" in self.query else [{"district": "大安區"}]


class FakeConnection:
    def __init__(self, official: int, sample: int) -> None:
        self.cursor_instance = FakeCursor(official, sample)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def cursor(self):
        return self.cursor_instance


def test_postgres_status_identifies_official_data(monkeypatch) -> None:
    monkeypatch.setattr(PostgresValuationProvider, "_connect", lambda self: FakeConnection(12, 0))
    status = PostgresValuationProvider("postgresql://test").data_status()
    assert status["data_composition"] == "official"
    assert status["is_demo_data"] is False
    assert status["official_records_count"] == 12
    assert status["last_updated"].startswith("2026-06-01")
    assert status["official_period_min"] == "2016-09"
    assert status["official_period_max"] == "2026-10"
    assert status["raw_official_period_min"] == "2016-09"
    assert status["raw_official_period_max"] == "2026-10"
    assert status["effective_trend_period_min"] == "2025-01"
    assert status["effective_trend_period_max"] == "2026-05"
    assert status["excluded_future_period_count"] == 4
    assert status["excluded_too_old_period_count"] == 8
    assert status["retention_policy_years"] == 3
    assert status["records_outside_retention_count"] == 8
    assert status["oldest_effective_period"] == "2025-01"
    assert status["newest_effective_period"] == "2026-05"
    assert "rolling 3 年" in status["retention_note"]
    assert "自動排除" in status["data_quality_note"]
    assert status["latest_import_inserted_rows"] == 125
    assert status["latest_import_skipped_duplicates"] == 5
    assert "台北市,新北市" in status["latest_import_scope"]
    assert status["coverage_city_count"] == 1
    assert status["coverage_district_count"] == 1
    assert status["coverage_road_count"] == 2
    assert status["coverage_summary"] == "目前官方資料涵蓋 1 縣市、1 行政區、2 路段。"
    assert len(status["official_coverage_note"]) < 80


def test_postgres_status_identifies_mixed_data(monkeypatch) -> None:
    monkeypatch.setattr(PostgresValuationProvider, "_connect", lambda self: FakeConnection(12, 3))
    status = PostgresValuationProvider("postgresql://test").data_status()
    assert status["data_composition"] == "mixed"
    assert status["is_full_taiwan"] is False
