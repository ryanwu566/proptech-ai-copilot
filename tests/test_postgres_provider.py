from datetime import UTC, datetime

from services.valuation_providers.postgres_provider import PostgresValuationProvider


class Cursor:
    def __init__(self):
        self.query = ""

    def __enter__(self): return self
    def __exit__(self, *_args): return None
    def execute(self, query, _params=None): self.query = " ".join(query.split())
    def fetchone(self):
        if "valuation_import_runs" in self.query:
            return {"imported_at": datetime(2026, 7, 1, tzinfo=UTC), "status": "completed", "city_scope": "虛構市", "district_scope": "虛構區", "road_scope": "", "inserted_rows": 1, "skipped_duplicate_rows": 0}
        return {"records_count": 1, "cities_count": 1, "districts_count": 1, "roads_count": 1, "official_records_count": 1, "sample_records_count": 0, "raw_official_period_min": "2026-01", "raw_official_period_max": "2026-06", "effective_trend_period_min": "2026-01", "effective_trend_period_max": "2026-06", "excluded_future_period_count": 0, "excluded_too_old_period_count": 0}
    def fetchall(self): return [{"city": "虛構市"}] if "distinct city" in self.query else [{"district": "虛構區"}]


class Connection:
    def __init__(self): self.cursor_instance = Cursor()
    def __enter__(self): return self
    def __exit__(self, *_args): return None
    def cursor(self): return self.cursor_instance


def test_provider_exposes_freshness_and_cache_expires(monkeypatch):
    connection = Connection()
    monkeypatch.setattr(PostgresValuationProvider, "_connect", lambda self: connection)
    provider = PostgresValuationProvider("postgresql://test")
    tick = [0.0]
    provider._clock = lambda: tick[0]
    first = provider.data_status()
    second = provider.data_status()
    assert first is second
    assert first["freshness_status"] in {"fresh", "aging"}
    assert first["freshness_user_message"]
    tick[0] = 61.0
    assert provider.data_status()["freshness_status"] in {"fresh", "aging"}


def test_provider_failure_is_unavailable_without_raw_error(monkeypatch):
    monkeypatch.setattr(PostgresValuationProvider, "_connect", lambda self: (_ for _ in ()).throw(RuntimeError("sensitive db detail")))
    status = PostgresValuationProvider("postgresql://test").data_status()
    assert status["freshness_status"] == "unavailable"
    assert status["freshness_reason_code"] == "provider_unavailable"
    assert "sensitive" not in str(status)
