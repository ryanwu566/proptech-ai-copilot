from pathlib import Path

from services.valuation_providers.postgres_provider import PostgresValuationProvider, _comparable_query
from services.valuation_service import SampleValuationProvider, get_valuation_provider


def test_postgres_provider_connection_failure_is_safe(monkeypatch) -> None:
    PostgresValuationProvider._availability_cache.clear()
    monkeypatch.setattr(PostgresValuationProvider, "_connect", lambda self: (_ for _ in ()).throw(ConnectionError("offline")))
    provider = PostgresValuationProvider("postgresql://unavailable")
    assert provider.available() is False
    assert provider.query_comparables({"city": "台北市"}) == []


def test_configured_but_failed_postgres_falls_back_to_sample(monkeypatch) -> None:
    PostgresValuationProvider._availability_cache.clear()
    monkeypatch.setattr(PostgresValuationProvider, "_connect", lambda self: (_ for _ in ()).throw(ConnectionError("offline")))
    provider = get_valuation_provider(database_url="postgresql://unavailable", sqlite_path=Path("missing.sqlite"))
    assert isinstance(provider, SampleValuationProvider)


def test_postgres_failed_status_is_user_safe(monkeypatch) -> None:
    monkeypatch.setattr(PostgresValuationProvider, "_connect", lambda self: (_ for _ in ()).throw(ConnectionError("offline")))
    status = PostgresValuationProvider("postgresql://unavailable").data_status()
    assert status["active_source"] == "postgres"
    assert status["coverage"]["records_count"] == 0
    assert "password" not in str(status).lower()


def test_postgres_query_scopes_relax_from_road_to_city() -> None:
    request = {"city": "台北市", "district": "大安區", "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30, "building_age_years": 10}
    road_sql, _ = _comparable_query(request, "road", 50)
    district_sql, _ = _comparable_query(request, "district", 50)
    city_sql, _ = _comparable_query(request, "city", 50)
    assert "road = %s" in road_sql
    assert "trim(district) = %s" in district_sql and "road = %s" not in district_sql.split("order by")[0]
    assert "replace(trim(city), '臺', '台') = %s" in city_sql and "trim(district) = %s" not in city_sql.split("order by")[0]
    assert "transaction_period <= %s" in road_sql


class _ScopeCursor:
    def __init__(self) -> None:
        self.query = ""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query, _params=None) -> None:
        self.query = " ".join(query.split())

    def fetchall(self):
        return []


class _ScopeConnection:
    def __init__(self) -> None:
        self.cursor_instance = _ScopeCursor()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def cursor(self):
        return self.cursor_instance


def test_postgres_provider_fetches_district_pool_for_service_grouping(monkeypatch) -> None:
    connection = _ScopeConnection()
    monkeypatch.setattr(PostgresValuationProvider, "_connect", lambda self: connection)
    provider = PostgresValuationProvider("postgresql://test")
    assert provider.query_comparables({"city": "台北市", "district": "大安區", "road": "和平東路二段"}) == []
    where_clause = connection.cursor_instance.query.split("order by")[0]
    assert "replace(trim(city), '臺', '台') = %s" in where_clause
    assert "trim(district) = %s" in where_clause
    assert "road = %s" not in where_clause
    assert "limit 200" in connection.cursor_instance.query
    assert provider.last_query_metadata["query_scope"] == "district_pool"
    assert provider.last_query_metadata["candidate_pool_size"] == 0


def test_postgres_provider_disables_prepared_statements(monkeypatch) -> None:
    import psycopg

    captured = {}
    sentinel = object()

    def fake_connect(*_args, **kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(psycopg, "connect", fake_connect)
    connection = PostgresValuationProvider("postgresql://test")._connect()
    assert connection is sentinel
    assert captured["prepare_threshold"] is None
