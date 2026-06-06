"""Google Places adapter normalization and no-key behavior tests."""

from services.adapters.google_places_adapter import GooglePlacesAdapter, distance_meters, normalize_opening_status


def test_google_places_adapter_without_key_is_safe() -> None:
    adapter = GooglePlacesAdapter(api_key="")
    assert adapter.available is False
    assert adapter.nearby(25.033, 121.5654, 800, "food") == []


def test_distance_meters_is_reasonable() -> None:
    assert distance_meters(25.033, 121.5654, 25.033, 121.5654) == 0
    assert 90 <= distance_meters(25.033, 121.5654, 25.034, 121.5654) <= 120


def test_google_place_normalization_hides_raw_response() -> None:
    normalized = GooglePlacesAdapter._normalize(
        {
            "id": "places/demo",
            "displayName": {"text": "展示咖啡"},
            "location": {"latitude": 25.034, "longitude": 121.5654},
            "formattedAddress": "台北市信義區",
            "rating": 4.5,
            "userRatingCount": 88,
            "businessStatus": "OPERATIONAL",
            "types": ["cafe"],
            "unrequested_expensive_field": "not-forwarded",
        },
        25.033,
        121.5654,
        "food",
    )
    assert normalized["place_id"] == "places/demo"
    assert normalized["category"] == "food"
    assert normalized["distance_m"] > 0
    assert normalized["opening_status_label"] == "店家正常營運"
    assert "unrequested_expensive_field" not in normalized


def test_opening_status_uses_current_hours_when_available() -> None:
    assert normalize_opening_status({"currentOpeningHours": {"openNow": True}})["opening_status_label"] == "目前營業中"
    assert normalize_opening_status({"currentOpeningHours": {"openNow": False}})["opening_status_label"] == "目前休息中"


def test_operational_is_not_claimed_as_open_now() -> None:
    result = normalize_opening_status({"businessStatus": "OPERATIONAL"})
    assert result["opening_status"] == "operational"
    assert result["opening_status_label"] == "店家正常營運"
    assert result["opening_status_label"] != "目前營業中"
