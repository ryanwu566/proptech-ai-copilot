"""Runtime contracts for production-QA geocoding and POI quality findings."""

from __future__ import annotations

import pytest

from services.adapters.google_places_adapter import GooglePlacesAdapter
from services.geocoding_acceptance import (
    AMBIGUOUS,
    EXACT_OR_ACCEPTABLE,
    INSUFFICIENT_SPECIFICITY,
    MISMATCH,
    PARTIAL_MATCH,
    evaluate_geocoding_acceptance,
)
from services.location_insight_service import analyze_location
from services.map_service import get_nearby_places
from services.terrain_risk_service import TerrainRiskLocationError, analyze_terrain_risk


def _region(address: str, *, city: str = "臺北市", district: str = "大安區", road: str = "和平東路二段", metadata: dict | None = None) -> dict:
    return {
        "formatted_address": address,
        "city": city,
        "district": district,
        "road": road,
        "center": {"lat": 25.026, "lng": 121.543},
        "geocoding_metadata": metadata or {"provider_types": ["street_address"], "location_type": "ROOFTOP", "route": road},
    }


def test_exact_property_address_is_accepted() -> None:
    acceptance = evaluate_geocoding_acceptance(
        "臺北市大安區和平東路二段100號",
        _region("臺北市大安區和平東路二段100號"),
        "google_geocoding",
    )

    assert acceptance["match_quality"] == EXACT_OR_ACCEPTABLE
    assert acceptance["accepted_for_analysis"] is True
    assert acceptance["original_query"].endswith("100號")
    assert acceptance["normalized_address"].endswith("100號")
    assert acceptance["resolved_lat"] == 25.026
    assert acceptance["geocoding_source"] == "google_geocoding"


@pytest.mark.parametrize(
    ("query", "region", "reason"),
    [
        (
            "花蓮 富世291號",
            _region("花蓮縣秀林鄉富世135號", city="花蓮縣", district="秀林鄉", road="富世"),
            "house_number_mismatch",
        ),
        (
            "臺北市大安區和平東路100號",
            _region("臺北市大安區復興南路100號", road="復興南路"),
            "street_mismatch",
        ),
        (
            "臺北市大安區和平東路100號",
            _region("臺北市信義區和平東路100號", district="信義區", road="和平東路"),
            "district_mismatch",
        ),
    ],
)
def test_material_address_mismatches_are_blocked(query: str, region: dict, reason: str) -> None:
    acceptance = evaluate_geocoding_acceptance(query, region, "google_geocoding")

    assert acceptance["match_quality"] == MISMATCH
    assert acceptance["accepted_for_analysis"] is False
    assert acceptance["requires_confirmation"] is True
    assert reason in acceptance["mismatch_reasons"]


def test_city_only_landmark_resolution_is_insufficient() -> None:
    acceptance = evaluate_geocoding_acceptance(
        "Taipei Main Station",
        _region(
            "臺北市",
            district="",
            road="",
            metadata={"provider_types": ["locality", "political"], "location_type": "APPROXIMATE"},
        ),
        "google_geocoding",
    )

    assert acceptance["match_quality"] == INSUFFICIENT_SPECIFICITY
    assert acceptance["accepted_for_analysis"] is False
    assert "city_only_resolution" in acceptance["mismatch_reasons"]


def test_provider_partial_and_ambiguous_matches_remain_unaccepted() -> None:
    partial = evaluate_geocoding_acceptance(
        "臺北市大安區",
        _region("臺北市大安區", road="", metadata={"provider_types": ["administrative_area_level_2"], "location_type": "", "partial_match": True}),
        "google_geocoding",
    )
    ambiguous = evaluate_geocoding_acceptance(
        "Central Mountain Trailhead",
        _region("Unrelated Visitor Center", city="", district="", road="", metadata={"provider_types": ["point_of_interest"], "location_type": "ROOFTOP"}),
        "google_geocoding",
    )

    assert partial["match_quality"] == PARTIAL_MATCH
    assert partial["accepted_for_analysis"] is False
    assert ambiguous["match_quality"] == AMBIGUOUS
    assert ambiguous["accepted_for_analysis"] is False


def test_location_insight_does_not_fetch_pois_for_rejected_geocode() -> None:
    acceptance = evaluate_geocoding_acceptance(
        "花蓮 富世291號",
        _region("花蓮縣秀林鄉富世135號", city="花蓮縣", district="秀林鄉", road="富世"),
        "tgos_geocoding",
    )
    nearby_calls = 0

    def nearby(*_args):
        nonlocal nearby_calls
        nearby_calls += 1
        raise AssertionError("POIs must remain blocked")

    result = analyze_location(
        address="花蓮 富世291號",
        searcher=lambda _query: {
            "matched": True,
            "center": {"lat": 24.15, "lng": 121.62},
            "formatted_address": "花蓮縣秀林鄉富世135號",
            "confidence": "low",
            "geocoding_acceptance": acceptance,
        },
        nearby_fetcher=nearby,
    )

    assert nearby_calls == 0
    assert result["resolved_location"] is None
    assert result["location_score"] is None
    assert result["data_quality"]["status"] == "unavailable"
    assert result["geocoding_acceptance"]["match_quality"] == MISMATCH


def test_terrain_providers_do_not_run_for_rejected_geocode() -> None:
    acceptance = evaluate_geocoding_acceptance(
        "花蓮 富世291號",
        _region("花蓮縣秀林鄉富世135號", city="花蓮縣", district="秀林鄉", road="富世"),
        "tgos_geocoding",
    )

    with pytest.raises(TerrainRiskLocationError):
        analyze_terrain_risk(
            address="花蓮 富世291號",
            searcher=lambda _query: {
                "matched": True,
                "center": {"lat": 24.15, "lng": 121.62},
                "formatted_address": "花蓮縣秀林鄉富世135號",
                "confidence": "low",
                "geocoding_acceptance": acceptance,
            },
            providers={"must_not_be_read": object()},
        )


def _place(place_id: str, name: str, category_type: str, *, lat: float, lng: float) -> dict:
    return {
        "place_id": place_id,
        "name": name,
        "lat": lat,
        "lng": lng,
        "address": "臺北市測試地址",
        "rating": None,
        "user_rating_count": 0,
        "business_status": "OPERATIONAL",
        "opening_status": "unknown",
        "opening_status_label": "未知",
        "opening_hours_source": "businessStatus",
        "distance_m": 100,
        "types": [category_type],
        "source": "google_places",
    }


def test_google_adapter_rejects_obvious_category_type_mismatches() -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "places": [
                    {"id": "company", "displayName": {"text": "服飾公司"}, "location": {"latitude": 25.026, "longitude": 121.543}, "types": ["clothing_store", "corporate_office"]},
                    {"id": "hospital", "displayName": {"text": "市立醫院"}, "location": {"latitude": 25.027, "longitude": 121.544}, "types": ["hospital"]},
                ]
            }

    class Client:
        def post(self, *_args, **_kwargs):
            return Response()

    places = GooglePlacesAdapter(api_key="test", client=Client()).nearby(25.026, 121.543, 800, "medical")

    assert [place["place_id"] for place in places] == ["hospital"]
    assert places[0]["types"] == ["hospital"]


def test_poi_validation_and_deduplication_are_deterministic_across_categories() -> None:
    shared = _place("shared-station", "共構站點", "transit_station", lat=25.0261, lng=121.5431)
    school_no_id = _place("", "測試學校", "school", lat=25.027, lng=121.544)

    class Adapter:
        available = True

        def nearby(self, _lat, _lng, _radius, category, _language):
            if category == "transport":
                return [shared, {**shared}]
            if category == "school":
                return [
                    {**shared, "types": ["school"]},
                    school_no_id,
                    {**school_no_id, "name": "測試學校分站"},
                    _place("clothes-as-school", "服飾企業", "clothing_store", lat=25.028, lng=121.545),
                ]
            return [
                _place("company-as-medical", "一般公司", "corporate_office", lat=25.029, lng=121.546),
                _place("real-hospital", "市立醫院", "hospital", lat=25.03, lng=121.547),
            ]

    result = get_nearby_places(25.026, 121.543, 800, ["transport", "school", "medical"], adapter=Adapter())

    assert [group["category"] for group in result["categories"]] == ["transport", "school", "medical"]
    assert [group["count"] for group in result["categories"]] == [1, 1, 1]
    assert result["evidence_quality"]["input_place_count"] == 8
    assert result["evidence_quality"]["accepted_place_count"] == 3
    assert result["evidence_quality"]["rejected_type_count"] == 2
    assert result["evidence_quality"]["deduplicated_count"] == 3
    assert result["evidence_quality"]["status"] == "partial"
    assert result["livability_score"] <= 78
    assert [place["place_id"] for place in result["nearest_places"]] == ["shared-station", "", "real-hospital"]


def test_dense_valid_google_results_do_not_automatically_reach_100() -> None:
    accepted_type = {
        "transport": "transit_station",
        "school": "school",
        "park": "park",
        "medical": "hospital",
        "shopping": "shopping_mall",
        "food": "restaurant",
    }
    category_offset = {category: index for index, category in enumerate(accepted_type)}

    class DenseAdapter:
        available = True

        def nearby(self, _lat, _lng, _radius, category, _language):
            return [
                _place(
                    f"{category}-{index}",
                    f"{category}-{index}",
                    accepted_type[category],
                    lat=25.0 + index / 10000,
                    lng=121.0 + category_offset[category] / 10000,
                )
                for index in range(10)
            ]

    result = get_nearby_places(25.0, 121.0, 800, list(accepted_type), adapter=DenseAdapter())

    assert result["evidence_quality"]["status"] == "high"
    assert result["evidence_quality"]["score_ceiling"] == 95
    assert result["livability_score"] == 95
    assert result["livability_score"] < 100
