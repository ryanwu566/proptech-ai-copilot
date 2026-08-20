from fastapi.testclient import TestClient

from backend.api_main import app
from services.parcel_geometry import MAX_UPLOAD_BYTES


client = TestClient(app)
POLYGON = b'{"type":"Polygon","coordinates":[[[121.55,25.03],[121.55,25.031],[121.551,25.031],[121.551,25.03],[121.55,25.03]]]}'


def test_multipart_upload_returns_truthful_geometry_and_never_echoes_file() -> None:
    response = client.post(
        "/parcel-geometry/upload",
        files={"file": ("private-name.geojson", POLYGON, "application/geo+json")},
        data={"latitude": "25.0305", "longitude": "121.5505"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "user_provided"
    assert payload["source_label"] == "USER_PROVIDED_GEOMETRY"
    assert payload["legal_boundary"] is False
    assert "private-name" not in response.text
    assert "no-store" in response.headers["cache-control"]


def test_upload_errors_keep_distinct_codes() -> None:
    cases = [
        ("parcel.txt", b"not gis", "UNSUPPORTED_FORMAT", 422),
        ("parcel.geojson", b"", "PARSE_FAILED", 422),
        ("parcel.zip", b"not zip", "PARSE_FAILED", 422),
        ("parcel.geojson", b"x" * (MAX_UPLOAD_BYTES + 1), "FILE_TOO_LARGE", 413),
    ]
    for filename, body, code, status in cases:
        response = client.post("/parcel-geometry/upload", files={"file": (filename, body)})
        assert response.status_code == status
        assert response.json()["detail"]["code"] == code


def test_status_separates_disabled_vector_and_verified_landsect_context() -> None:
    payload = client.get("/parcel-geometry/status").json()
    assert payload["nlsc_vector_provider"] == "disabled_not_configured"
    assert payload["uploaded_geometry_persisted"] is False
    assert payload["landsect_context"]["status"] == "VERIFIED_PUBLIC"
    assert payload["landsect_context"]["semantics"] == "SECTION_CONTEXT_NOT_PARCEL_BOUNDARY"


def test_spatial_api_never_claims_intersection_without_hazard_geometry() -> None:
    parcel = {"type": "Polygon", "coordinates": [[[121.55, 25.03], [121.55, 25.031], [121.551, 25.031], [121.551, 25.03], [121.55, 25.03]]]}
    response = client.post("/parcel-geometry/spatial-analyze", json={"parcel_geometry": parcel, "hazard_geometry": None})
    assert response.status_code == 200
    assert response.json()["claim_type"] == "NO_GEOMETRY_AVAILABLE"
    assert "intersects" not in response.json()


def test_non_upload_routes_keep_original_one_mb_request_limit() -> None:
    response = client.post("/terrain-risk/analyze", content=b"x" * 1_000_001, headers={"content-type": "application/json"})
    assert response.status_code == 413
