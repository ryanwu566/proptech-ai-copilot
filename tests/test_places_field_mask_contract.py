"""Places cost and Location contracts, with no network or worker pools."""

from concurrent.futures import Future
from pathlib import Path

import httpx
import pytest

from services import map_service
from services.adapters import google_places_adapter
from services.adapters.google_places_adapter import CATEGORY_TYPES, GooglePlacesAdapter
from services.location_insight_service import analyze_location


MINIMAL_FIELDS = {"places.id", "places.displayName", "places.location", "places.types"}
ORIGIN = (25.033, 121.5654)
ENRICHMENT = {
    "formattedAddress": "台北市信義區",
    "rating": 4.9,
    "userRatingCount": 900,
    "businessStatus": "OPERATIONAL",
    "currentOpeningHours": {"openNow": True},
    "regularOpeningHours": {"periods": [{"open": {"day": 0, "hour": 0}}]},
}


class InlineExecutor:
    """Exercise service fan-out synchronously while heavy acceptance runs."""

    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def submit(self, action, *args):
        future = Future()
        try:
            future.set_result(action(*args))
        except Exception as exc:
            future.set_exception(exc)
        return future


def places_transport(request: httpx.Request) -> httpx.Response:
    """Model Google's field projection instead of returning unrequested data."""
    import json

    included_type = json.loads(request.content)["includedTypes"][0]
    row = {
        "id": f"poi-{included_type}",
        "displayName": {"text": f"設施 {included_type}"},
        "location": {"latitude": ORIGIN[0] + 0.001, "longitude": ORIGIN[1]},
        "types": [included_type],
        **ENRICHMENT,
    }
    fields = {field.split(".")[1] for field in request.headers["X-Goog-FieldMask"].split(",")}
    return httpx.Response(200, json={"places": [{key: value for key, value in row.items() if key in fields}]})


@pytest.mark.parametrize("category", CATEGORY_TYPES)
def test_outgoing_mask_preserves_poi_contract_without_enrichment_or_extra_calls(category):
    requests = []

    def respond(request):
        requests.append(request)
        return places_transport(request)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = GooglePlacesAdapter(api_key="test", client=client)
        places = adapter.nearby(*ORIGIN, 800, category)
        assert adapter.nearby(*ORIGIN, 800, category) == places

    assert len(requests) == 1
    assert str(requests[0].url) == "https://places.googleapis.com/v1/places:searchNearby"
    mask = requests[0].headers["X-Goog-FieldMask"].split(",")
    assert set(mask) == MINIMAL_FIELDS
    assert len(mask) == len(MINIMAL_FIELDS)
    place = places[0]
    assert place["place_id"] == f"poi-{CATEGORY_TYPES[category][0]}"
    assert place["name"] == f"設施 {CATEGORY_TYPES[category][0]}"
    assert place["types"] == [CATEGORY_TYPES[category][0]]
    assert place["category"] == category
    assert place["source"] == "google_places"
    assert 100 <= place["distance_m"] <= 120
    assert (place["lat"], place["lng"]) == (ORIGIN[0] + 0.001, ORIGIN[1])
    assert place["rating"] is None
    assert place["user_rating_count"] == 0
    assert place["address"] == ""
    assert place["business_status"] == "UNKNOWN"
    assert place["opening_status"] == "unknown"
    assert place["opening_status_label"] == "營業狀態未知"


@pytest.mark.parametrize("quality", ["high", "partial", "fallback"])
def test_livability_scores_and_nearest_evidence_ignore_removed_enrichment(quality):
    rows = [
        {"id": f"p{index}", "displayName": {"text": f"咖啡 {index}"},
         "location": {"latitude": ORIGIN[0] + offset, "longitude": ORIGIN[1]}, "types": ["cafe"]}
        for index, offset in enumerate([0.001, 0.005, 0.009])
    ]

    def score(enrichment):
        places = [GooglePlacesAdapter._normalize({**row, **enrichment}, *ORIGIN, "food") for row in rows]
        return map_service.build_livability_scoring([{"category": "food", "places": places}], 1000, quality)

    before, after = score(ENRICHMENT), score({})
    nearest_before, nearest_after = before.pop("nearest_places"), after.pop("nearest_places")
    assert before == after
    assert before["category_scores"][0]["category"] == "transport"
    food = next(item for item in after["category_scores"] if item["category"] == "food")
    assert food["poi_count"] == 2  # >800m remains excluded even with a 1000m search.
    assert food["score"] == round(39 * {"high": 0.95, "partial": 0.78, "fallback": 0.65}[quality])
    evidence_fields = ("place_id", "name", "category", "distance_m", "lat", "lng", "types", "source")
    assert [{key: place[key] for key in evidence_fields} for place in nearest_before] == [
        {key: place[key] for key in evidence_fields} for place in nearest_after
    ]


def test_modern_location_retains_rendered_counts_evidence_and_six_call_budget(monkeypatch):
    requests = []

    def respond(request):
        requests.append(request)
        assert set(request.headers["X-Goog-FieldMask"].split(",")) == MINIMAL_FIELDS
        return places_transport(request)

    class VillageResolver:
        def resolve(self, **kwargs):
            return {"location": {"status": "unavailable"}, "demographics": {"status": "no_data"}}

    monkeypatch.setattr(map_service, "ThreadPoolExecutor", InlineExecutor)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = GooglePlacesAdapter(api_key="test", client=client)
        monkeypatch.setattr(map_service, "DEFAULT_GOOGLE_PLACES_ADAPTER", adapter)
        result = analyze_location(latitude=ORIGIN[0], longitude=ORIGIN[1], village_resolver=VillageResolver())
        repeated = analyze_location(latitude=ORIGIN[0], longitude=ORIGIN[1], village_resolver=VillageResolver())

    # Observation time and evidence are cached; per-request durations are not.
    for insight in (result, repeated):
        for status in insight["data_quality"]["category_status"].values():
            assert status.pop("timing_ms") >= 0
    assert repeated == result
    assert len(requests) == 6
    assert {str(request.url) for request in requests} == {"https://places.googleapis.com/v1/places:searchNearby"}
    assert result["poi_summary"] == {
        "transit_count": 1, "convenience_count": 2, "school_count": 1,
        "park_count": 1, "medical_count": 1, "risk_facility_count": None,
    }
    assert result["data_quality"]["source"] == "google_places"
    assert result["data_quality"]["status"] == "good"
    assert result["data_quality"]["coverage"] == {"requested": 6, "successful": 6, "failed": 0}
    assert result["data_quality"]["checked_at"]
    assert result["category_scores"]["transit_score"] == 24
    assert result["location_score"] is None  # Missing risk source is still unknown.
    assert len(result["nearest_pois"]) == 3
    for poi in result["nearest_pois"]:
        assert set(poi) == {"category", "name", "distance_m", "source"}
        assert poi["name"] == f"設施 {CATEGORY_TYPES[poi['category']][0]}"
        assert 100 <= poi["distance_m"] <= 120
        assert poi["source"] == "google_places"


def test_modern_location_renders_summary_without_legacy_poi_enrichment():
    view = (Path(__file__).resolve().parents[1] / "frontend_next/components/workspace/location/location-view.tsx").read_text(encoding="utf-8")
    assert "snapshot.poiSummary" in view
    assert "categories={[]}" in view
    for field in ("transit_count", "convenience_count", "school_count", "park_count", "medical_count", "risk_facility_count"):
        assert field in view
    for field in (".rating", ".user_rating_count", ".business_status", ".opening_status", ".opening_hours_source"):
        assert field not in view


@pytest.mark.parametrize("category,types,name", [
    ("food", ["cafe"], "山林步道咖啡"),
    ("food", ["restaurant", "hiking_area"], "山景餐廳"),
    ("medical", ["corporate_office"], "一般公司"),
    ("park", ["park"], "登山步道"),
])
def test_minimal_named_rows_still_reject_category_and_trail_contamination(category, types, name):
    def respond(request):
        assert set(request.headers["X-Goog-FieldMask"].split(",")) == MINIMAL_FIELDS
        return httpx.Response(200, json={"places": [{
            "id": "contaminated", "displayName": {"text": name},
            "location": {"latitude": ORIGIN[0], "longitude": ORIGIN[1]}, "types": types,
        }]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert GooglePlacesAdapter(api_key="test", client=client).nearby(*ORIGIN, 800, category) == []


def test_before_after_masks_preserve_counts_scores_deduplication_and_call_volume(monkeypatch):
    """Compare physical requests using both real masks with identical POIs."""
    monkeypatch.setattr(map_service, "ThreadPoolExecutor", InlineExecutor)
    original_mask = ",".join([
        "places.id", "places.displayName", "places.location", "places.formattedAddress",
        "places.rating", "places.userRatingCount", "places.businessStatus",
        "places.currentOpeningHours.openNow", "places.regularOpeningHours.periods", "places.types",
    ])
    minimal_mask = google_places_adapter.FIELD_MASK
    snapshots = []
    for mask in (original_mask, minimal_mask):
        requests = []

        def respond(request):
            requests.append(request)
            assert request.headers["X-Goog-FieldMask"] == mask
            row = places_transport(request).json()["places"][0]
            # Exact duplicate IDs must not inflate category counts or scores.
            return httpx.Response(200, json={"places": [row, row]})

        monkeypatch.setattr(google_places_adapter, "FIELD_MASK", mask)
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            adapter = GooglePlacesAdapter(api_key="test", client=client)
            first = map_service.get_nearby_places(*ORIGIN, 800, list(CATEGORY_TYPES), adapter=adapter)
            assert len(requests) == 6
            repeated = map_service.get_nearby_places(*ORIGIN, 800, list(CATEGORY_TYPES), adapter=adapter)
            assert len(requests) == 6
            assert first["checked_at"] == repeated["checked_at"]
        assert first["source"] == "google_places"
        assert first["checked_at"]
        assert first["evidence_quality"]["deduplicated_count"] == 6
        assert [group["count"] for group in first["categories"]] == [1] * 6
        snapshot = {key: first[key] for key in (
            "livability_score", "livability_level", "category_scores", "category_score_map",
            "evidence_quality", "scoring_criteria", "score_summary", "score_explanation", "summary",
            "recommendation_text", "source", "partial", "fallback", "failed_categories",
        )}
        snapshot["nearest"] = [{key: place[key] for key in ("place_id", "name", "distance_m", "source")}
                               for place in first["nearest_places"]]
        snapshots.append(snapshot)
    assert snapshots[0] == snapshots[1]
