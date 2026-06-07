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
    assert "district = %s" in district_sql and "road = %s" not in district_sql.split("order by")[0]
    assert "city = %s" in city_sql and "district = %s" not in city_sql.split("order by")[0]
