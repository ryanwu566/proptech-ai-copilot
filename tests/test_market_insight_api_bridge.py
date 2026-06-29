"""API tests for the PLVR Market Insight bridge."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api_main import app


client = TestClient(app)


def test_market_status_endpoint_uses_safe_metadata(monkeypatch) -> None:
    from services import market_insight_service

    monkeypatch.setattr(
        market_insight_service,
        "get_market_status",
        lambda: {
            "data_status": "available",
            "coverage_status": "partial",
            "source_name": "Official PLVR OpenData aggregate",
            "source_updated_at": "2025-03-05",
            "available_county_count": 1,
            "available_district_count": 2,
            "earliest_period": "2025-01",
            "latest_period": "2025-02",
            "caveat": "market caveat",
        },
    )

    response = client.get("/market-insights/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_status"] == "available"
    assert payload["available_district_count"] == 2
    assert "database_url" not in payload
    assert "raw_payload" not in payload


def test_market_regions_endpoint_filters_by_county(monkeypatch) -> None:
    from services import market_insight_service

    seen: dict[str, str] = {}

    def fake_regions(county: str = ""):
        seen["county"] = county
        return {
            "regions": [{"city": "Demo County", "county": "Demo County", "district": "North", "period": "2025-02"}],
            "data_status": "available",
            "coverage_status": "partial",
            "source_name": "Official PLVR OpenData aggregate",
            "source_updated_at": "2025-03-05",
            "available_county_count": 1,
            "available_district_count": 1,
            "earliest_period": "2025-02",
            "latest_period": "2025-02",
            "caveat": "market caveat",
        }

    monkeypatch.setattr(market_insight_service, "list_market_regions", fake_regions)

    response = client.get("/market-insights/regions?county=Demo%20County")

    assert response.status_code == 200
    assert seen == {"county": "Demo County"}
    assert response.json()["regions"][0]["district"] == "North"


def test_market_query_accepts_county_alias_and_period(monkeypatch) -> None:
    from services import market_insight_service

    seen: dict[str, str | None] = {}

    def fake_summary(city: str, district: str, period: str | None = None):
        seen.update({"city": city, "district": district, "period": period})
        return {
            "city": city,
            "county": city,
            "district": district,
            "period": period,
            "average_unit_price": 72.5,
            "avg_price_per_ping": 72.5,
            "transaction_count": 3,
            "transaction_volume": 3,
            "trend": [],
            "livability_score": None,
            "esg_lite_score": None,
            "poi_breakdown": {},
            "sdg11_note": "",
            "summary": "aggregate ready",
            "source_name": "Official PLVR OpenData aggregate",
            "source_updated_at": "2025-03-05",
            "coverage_status": "partial",
            "data_status": "available",
            "caveat": "market caveat",
            "disclaimer": "market caveat",
            "record_count": 3,
        }

    monkeypatch.setattr(market_insight_service, "get_market_summary", fake_summary)

    response = client.post(
        "/market-insights/query",
        json={"county": "Demo County", "district": "North", "period": "2025-02"},
    )

    assert response.status_code == 200
    assert seen == {"city": "Demo County", "district": "North", "period": "2025-02"}
    payload = response.json()
    assert payload["data_status"] == "available"
    assert payload["average_unit_price"] == 72.5
    assert "address_text" not in payload
    assert "raw_error" not in payload
