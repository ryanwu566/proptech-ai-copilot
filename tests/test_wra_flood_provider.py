"""Phase 3B tests: WraFloodProvider wired to the WRA flood R2 runtime.

These tests inject a fake ``query_point`` (matching the runtime signature) or a
fake R2 client through the real runtime, so nothing contacts R2 or the network.
They verify the provider maps runtime results onto the terrain-risk hazard
contract correctly, preserves scenario metadata, never turns failures into a
miss, keeps matched=true visible, and reuses the process cache on warm calls.
"""

from __future__ import annotations

import io
import json
import zipfile

import pytest
import shapefile  # pyshp
from pyproj import CRS

from services.terrain_risk_providers.wra_flood_provider import (
    DEFAULT_SCENARIO,
    SCENARIO_LABEL,
    WraFloodProvider,
)
from services.wra_flood_artifact import build_processed_artifact
from services.wra_flood_runtime import (
    RELEASE_PREFIX,
    ArtifactInvalidError,
    ChecksumMismatchError,
    InvalidScenarioError,
    SourceUnavailableError,
    WraFloodRuntime,
)

BEITOU = (25.128805040872507, 121.4648045853475)  # (lat, lon) — provider takes lat, lon


# ---------------------------------------------------------------------------
# Fake query_point helpers (runtime signature: (scenario, lon, lat) -> dict)
# ---------------------------------------------------------------------------


def _matched_result(scenario: str, *, class_value: int, count: int = 1) -> dict:
    depths = {1: "0.3-0.5 m", 2: "0.5-1.0 m", 3: "1.0-2.0 m", 4: "2.0-3.0 m", 5: ">3.0 m"}
    return {
        "status": "loaded",
        "scenario": scenario,
        "matched": True,
        "matched_count": count,
        "class": class_value,
        "canonical_depth": depths[class_value],
        "flood_dept_raw": "0.3-0.5",
        "flood_dept_malformed": False,
        "city_name": "臺北市",
        "town_name": "北投區",
    }


def _no_match_result(scenario: str) -> dict:
    return {"status": "no_match", "scenario": scenario, "matched": False, "matched_count": 0}


# ===========================================================================
# 7. provider uses default 24h-350mm scenario  + 8. scenario metadata surfaced
# ===========================================================================


def test_provider_uses_default_scenario_and_surfaces_metadata() -> None:
    seen = {}

    def fake_qp(scenario, lon, lat):
        seen["scenario"] = scenario
        seen["lon"] = lon
        seen["lat"] = lat
        return _matched_result(scenario, class_value=1)

    provider = WraFloodProvider(query_point=fake_qp)
    result = provider.analyze(*BEITOU, 500)

    assert DEFAULT_SCENARIO == "24h-350mm"
    assert seen["scenario"] == "24h-350mm"
    # provider.analyze(lat, lon) must call runtime with (scenario, lon, lat).
    assert seen["lon"] == BEITOU[1]
    assert seen["lat"] == BEITOU[0]
    # Scenario metadata surfaced in both source and value.
    assert result["source"]["scenario"] == "24h-350mm"
    assert result["source"]["scenario_label"] == SCENARIO_LABEL
    assert result["value"]["scenario"] == "24h-350mm"


# ===========================================================================
# 1. matched Class 1
# ===========================================================================


def test_matched_class_1() -> None:
    provider = WraFloodProvider(query_point=lambda s, lon, lat: _matched_result(s, class_value=1))
    result = provider.analyze(*BEITOU, 500)

    assert result["status"] == "available"
    assert result["matched"] is True
    assert result["level"] == "medium"  # Class 1 -> medium (never low)
    assert result["value"]["class"] == 1
    assert result["value"]["canonical_depth"] == "0.3-0.5 m"
    assert result["value"]["city_name"] == "臺北市"
    assert result["value"]["town_name"] == "北投區"
    assert result["value"]["flood_dept_raw"] == "0.3-0.5"
    assert result["value"]["flood_dept_malformed"] is False


# ===========================================================================
# 2. deepest class wins through provider  (runtime already picks deepest;
#    provider must faithfully map the deepest Class + level)
# ===========================================================================


def test_deepest_class_wins_through_provider() -> None:
    # Runtime reports Class 4 as the deepest match among 2 hits.
    provider = WraFloodProvider(query_point=lambda s, lon, lat: _matched_result(s, class_value=4, count=2))
    result = provider.analyze(*BEITOU, 500)

    assert result["matched"] is True
    assert result["value"]["class"] == 4
    assert result["value"]["canonical_depth"] == "2.0-3.0 m"
    assert result["value"]["matched_count"] == 2
    assert result["level"] == "high"  # Class 3-5 -> high


# ===========================================================================
# 3. no_match remains no_match, not safe / low-risk
# ===========================================================================


def test_no_match_is_not_safe_or_low_risk() -> None:
    provider = WraFloodProvider(query_point=lambda s, lon, lat: _no_match_result(s))
    result = provider.analyze(*BEITOU, 500)

    assert result["status"] == "available"  # source loaded successfully
    assert result["matched"] is False
    assert result["level"] == "unknown"  # never "low"
    assert result["level"] != "low"
    # Scenario context preserved.
    assert result["value"]["scenario"] == "24h-350mm"
    # Explanation must not claim safe / low-risk / no risk.
    text = result["explanation"]
    assert "不代表無淹水風險或低風險" in text
    payload = json.dumps(result, ensure_ascii=False)
    assert "\"level\": \"low\"" not in payload


# ===========================================================================
# 4. checksum mismatch -> error, not no_match  (and never hidden)
# ===========================================================================


def test_checksum_mismatch_becomes_error_not_no_match() -> None:
    def raise_checksum(s, lon, lat):
        raise ChecksumMismatchError("artifact checksum mismatch", scenario=s)

    provider = WraFloodProvider(query_point=raise_checksum)
    result = provider.analyze(*BEITOU, 500)

    assert result["status"] == "error"
    assert result["matched"] is False
    assert result["level"] == "unknown"
    # Must not be presented as a plain miss.
    assert "checksum" in result["explanation"] or "完整性驗證失敗" in result["explanation"]


# ===========================================================================
# 5. source unavailable -> unavailable, not no_match
# ===========================================================================


def test_source_unavailable_becomes_unavailable() -> None:
    def raise_unavailable(s, lon, lat):
        raise SourceUnavailableError("R2 GET failed", scenario=s)

    provider = WraFloodProvider(query_point=raise_unavailable)
    result = provider.analyze(*BEITOU, 500)

    assert result["status"] == "unavailable"
    assert result["matched"] is False
    assert result["level"] == "unknown"
    assert result["source"]["scenario"] == "24h-350mm"


# ===========================================================================
# 6. invalid artifact -> error, not no_match
# ===========================================================================


def test_invalid_artifact_becomes_error() -> None:
    def raise_invalid(s, lon, lat):
        raise ArtifactInvalidError("artifact decode failed", scenario=s)

    provider = WraFloodProvider(query_point=raise_invalid)
    result = provider.analyze(*BEITOU, 500)

    assert result["status"] == "error"
    assert result["matched"] is False
    assert result["level"] == "unknown"


def test_invalid_scenario_becomes_error() -> None:
    def raise_invalid_scenario(s, lon, lat):
        raise InvalidScenarioError("unknown scenario", scenario=s)

    provider = WraFloodProvider(query_point=raise_invalid_scenario)
    result = provider.analyze(*BEITOU, 500)
    assert result["status"] == "error"
    assert result["matched"] is False


# ===========================================================================
# Defensive: matched runtime result with an illegal Class must fail closed
# ===========================================================================


def test_matched_with_invalid_class_fails_closed() -> None:
    def matched_bad_class(scenario, lon, lat):
        return {
            "status": "loaded",
            "scenario": scenario,
            "matched": True,
            "matched_count": 1,
            "class": 9,  # illegal: only 1..5 are valid
            "canonical_depth": "???",
            "flood_dept_raw": "x",
            "flood_dept_malformed": True,
            "city_name": "臺北市",
            "town_name": "北投區",
        }

    provider = WraFloodProvider(query_point=matched_bad_class)
    result = provider.analyze(*BEITOU, 500)

    # Must NOT return available/medium/high and must NOT become a miss.
    assert result["status"] == "error"
    assert result["matched"] is False
    assert result["level"] == "unknown"
    assert result["level"] not in {"medium", "high", "low"}
    assert result["status"] != "available"


# ===========================================================================
# 9. warm repeated provider calls do not re-download artifact
#    (drive the REAL runtime through the provider with a counting fake client)
# ===========================================================================

_BASE_X = 250000.0
_BASE_Y = 2770000.0


def _epsg3826_wkt() -> str:
    return CRS.from_epsg(3826).to_wkt()


def _square(x0, y0, size):
    return [[x0, y0], [x0, y0 + size], [x0 + size, y0 + size], [x0 + size, y0], [x0, y0]]


def _build_zip():
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    writer = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYGON)
    writer.field("Class", "N", size=2)
    writer.field("flood_dept", "C", size=32)
    writer.field("City", "C", size=16)
    writer.field("CityName", "C", size=32)
    writer.field("Town", "C", size=16)
    writer.field("TownName", "C", size=32)
    writer.poly([_square(_BASE_X, _BASE_Y, 4000)])
    writer.record(1, "0.3-0.5", "63000", "臺北市", "63000010", "北投區")
    writer.close()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("flood.shp", shp.getvalue())
        archive.writestr("flood.shx", shx.getvalue())
        archive.writestr("flood.dbf", dbf.getvalue())
        archive.writestr("flood.prj", _epsg3826_wkt().encode("utf-8"))
    return buffer.getvalue()


class _FakeBody:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return self._payload


class CountingR2Client:
    def __init__(self, objects):
        self._objects = objects
        self.get_counts = {}

    def get_object(self, *, Bucket, Key):
        self.get_counts[Key] = self.get_counts.get(Key, 0) + 1
        if Key not in self._objects:
            raise RuntimeError(f"NoSuchKey: {Key}")
        return {"Body": _FakeBody(self._objects[Key])}


def _runtime_backed_provider():
    scenario = DEFAULT_SCENARIO
    result = build_processed_artifact(_build_zip(), scenario=scenario, source_url="https://example.invalid")
    manifest_bytes = json.dumps(result.manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")
    objects = {
        f"{RELEASE_PREFIX}/{scenario}/manifest.json": manifest_bytes,
        f"{RELEASE_PREFIX}/{scenario}/features.json.gz": result.artifact_bytes,
    }
    client = CountingR2Client(objects)
    runtime = WraFloodRuntime(client_factory=lambda: client, bucket="test-bucket")
    provider = WraFloodProvider(query_point=runtime.query_point)
    # A WGS84 point inside the class-1 square.
    centroid = result.features[0].geometry_wgs84.centroid
    return provider, runtime, client, scenario, (centroid.y, centroid.x)  # (lat, lon)


def test_warm_provider_calls_do_not_redownload_artifact() -> None:
    provider, runtime, client, scenario, (lat, lon) = _runtime_backed_provider()
    akey = f"{RELEASE_PREFIX}/{scenario}/features.json.gz"
    mkey = f"{RELEASE_PREFIX}/{scenario}/manifest.json"

    first = provider.analyze(lat, lon, 500)
    assert first["matched"] is True
    assert first["value"]["class"] == 1
    assert client.get_counts[akey] == 1
    assert client.get_counts[mkey] == 1
    assert runtime.cold_load_count == 1

    for _ in range(5):
        provider.analyze(lat, lon, 500)
    # Warm calls: no additional R2 GETs.
    assert client.get_counts[akey] == 1
    assert client.get_counts[mkey] == 1
    assert runtime.cold_load_count == 1


# ===========================================================================
# 8/11. scenario metadata + limited/matched visibility through the service
# 12. no ARDSWC / GeologyCloud regression when flood is injected
# ===========================================================================


def test_matched_flood_visible_in_terrain_service_and_no_other_regression() -> None:
    from services.terrain_risk_service import analyze_terrain_risk

    # Import fixtures from the service test module for the OTHER providers so we
    # exercise the real aggregation without external calls.
    from tests.test_terrain_risk_service import providers as service_providers

    # Real WraFloodProvider, but with an injected matched runtime result.
    flood_provider = WraFloodProvider(query_point=lambda s, lon, lat: _matched_result(s, class_value=3))
    provider_map = service_providers(flood=flood_provider)

    def searcher(query):
        return {"matched": True, "center": {"lat": 25.026, "lng": 121.543},
                "formatted_address": query, "confidence": "mock", "source": "mock"}

    report = analyze_terrain_risk(
        address="台北市測試", latitude=25.026, longitude=121.543, radius_m=500,
        searcher=searcher, providers=provider_map,
    )

    flood = report["hazards"]["flood"]
    assert flood["matched"] is True
    assert flood["status"] == "available"
    assert flood["value"]["scenario"] == "24h-350mm"

    # Matched flood must appear as a visible risk factor (PR #141: matched risk
    # stays visible even with partial/limited metadata).
    flood_factor = next((f for f in report["risk_factors"] if f["key"] == "flood"), None)
    assert flood_factor is not None
    assert flood_factor["level"] == "high"

    # No regression: the injected default fixtures for the other providers keep
    # their statuses in the aggregated report.
    assert report["hazards"]["landslide"]["status"] == "available"
    assert report["hazards"]["debris_flow"]["status"] == "available"
    assert report["hazards"]["liquefaction"]["status"] == "available"
    assert report["hazards"]["active_fault"]["status"] == "available"


def test_limited_but_matched_flood_still_visible() -> None:
    """Regression guard for PR #141: matched=true must remain a visible risk
    factor even if the provider marks the layer status as 'limited'."""
    from services.terrain_risk_service import analyze_terrain_risk
    from tests.test_terrain_risk_service import providers as service_providers

    class LimitedMatchedFloodProvider:
        def analyze(self, latitude, longitude, radius_m):
            return {
                "key": "flood",
                "label": "淹水潛勢",
                "status": "limited",
                "matched": True,
                "level": "high",
                "distance_m": 0,
                "value": {"scenario": DEFAULT_SCENARIO, "class": 5},
                "explanation": "matched but limited metadata",
                "source": {"name": "flood", "agency": "WRA", "source_url": "", "status": "limited"},
            }

    provider_map = service_providers(flood=LimitedMatchedFloodProvider())

    def searcher(query):
        return {"matched": True, "center": {"lat": 25.026, "lng": 121.543},
                "formatted_address": query, "confidence": "mock", "source": "mock"}

    report = analyze_terrain_risk(
        latitude=25.026, longitude=121.543, radius_m=500, searcher=searcher, providers=provider_map,
    )
    flood_factor = next((f for f in report["risk_factors"] if f["key"] == "flood"), None)
    assert flood_factor is not None  # matched risk not hidden by 'limited'
    assert flood_factor["level"] == "high"
