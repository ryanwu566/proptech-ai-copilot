"""Phase 3A tests for the WRA flood R2 runtime loader.

These tests never contact Cloudflare R2 or the network.  A small in-memory
``FakeR2Client`` serves synthetic manifest + artifact objects.  Artifacts are
built with the existing :mod:`services.wra_flood_artifact` builder (real WKB +
gzip + JSON), so the WKB decode path and STRtree are exercised end-to-end.

Covered cases (spec section 9):
 1. valid scenario load
 2. invalid scenario rejected
 3. manifest missing
 4. artifact missing
 5. checksum mismatch fail closed
 6. invalid gzip/json artifact
 7. WKB load
 8. STRtree hit
 9. STRtree no-hit
10. deepest Class wins
11. no-hit has no safe/low-risk interpretation
12. second query does not re-download R2
13. cache clear causes reload
14. concurrent cold-load only downloads once
15. malformed manifest
16. canonical scenario key construction
"""

from __future__ import annotations

import io
import json
import threading
import time
import zipfile

import pytest
import shapefile  # pyshp
from pyproj import CRS

from services.wra_flood_artifact import build_processed_artifact, sha256_bytes
from services.wra_flood_runtime import (
    CANONICAL_SCENARIOS,
    RELEASE_PREFIX,
    ArtifactInvalidError,
    ChecksumMismatchError,
    InvalidScenarioError,
    SourceUnavailableError,
    WraFloodRuntime,
    artifact_key,
    manifest_key,
)

# ---------------------------------------------------------------------------
# Synthetic SHP/ZIP -> processed artifact (in-memory, no official data)
# ---------------------------------------------------------------------------

_BASE_X = 250000.0
_BASE_Y = 2770000.0


def _epsg3826_wkt() -> str:
    return CRS.from_epsg(3826).to_wkt()


def _square(x0: float, y0: float, size: float) -> list[list[float]]:
    return [
        [x0, y0],
        [x0, y0 + size],
        [x0 + size, y0 + size],
        [x0 + size, y0],
        [x0, y0],
    ]


def _overlapping_records() -> list[dict]:
    """Two overlapping squares (Class 1 and Class 4) plus a distant Class 2.

    The Class 1 and Class 4 squares overlap in a shared region so a point there
    hits two features -> exercises deepest-Class-wins (Class 4).
    """

    big = _square(_BASE_X, _BASE_Y, 4000)  # Class 1
    small_overlap = _square(_BASE_X + 1000, _BASE_Y + 1000, 1500)  # Class 4, overlaps big
    distant = _square(_BASE_X + 50000, _BASE_Y + 50000, 1000)  # Class 2, far away
    return [
        {"poly": [big], "Class": 1, "flood_dept": "0.3-0.5", "City": "63000",
         "CityName": "臺北市", "Town": "63000010", "TownName": "北投區"},
        {"poly": [small_overlap], "Class": 4, "flood_dept": "2.0-3.0", "City": "63000",
         "CityName": "臺北市", "Town": "63000020", "TownName": "士林區"},
        {"poly": [distant], "Class": 2, "flood_dept": "0.5-1.0", "City": "65000",
         "CityName": "新北市", "Town": "65000030", "TownName": "板橋區"},
    ]


def _write_shp(records: list[dict]) -> dict[str, bytes]:
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    writer = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYGON)
    writer.field("Class", "N", size=2)
    writer.field("flood_dept", "C", size=32)
    writer.field("City", "C", size=16)
    writer.field("CityName", "C", size=32)
    writer.field("Town", "C", size=16)
    writer.field("TownName", "C", size=32)
    for rec in records:
        writer.poly(rec["poly"])
        writer.record(rec["Class"], rec["flood_dept"], rec["City"], rec["CityName"], rec["Town"], rec["TownName"])
    writer.close()
    return {"shp": shp.getvalue(), "shx": shx.getvalue(), "dbf": dbf.getvalue()}


def _build_zip(records: list[dict]) -> bytes:
    parts = _write_shp(records)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("flood.shp", parts["shp"])
        archive.writestr("flood.shx", parts["shx"])
        archive.writestr("flood.dbf", parts["dbf"])
        archive.writestr("flood.prj", _epsg3826_wkt().encode("utf-8"))
    return buffer.getvalue()


def _make_artifact(scenario: str, records: list[dict] | None = None):
    """Return (manifest_bytes, artifact_bytes, features) for a scenario."""

    if records is None:
        records = _overlapping_records()
    result = build_processed_artifact(
        _build_zip(records), scenario=scenario, source_url="https://example.invalid/wra"
    )
    manifest_bytes = json.dumps(result.manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return manifest_bytes, result.artifact_bytes, result.features


def _wgs84_point_in(feature) -> tuple[float, float]:
    c = feature.geometry_wgs84.centroid
    return c.x, c.y


# ---------------------------------------------------------------------------
# Fake R2 client
# ---------------------------------------------------------------------------


class _FakeBody:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


class FakeR2Error(Exception):
    """Stand-in for a boto3 ClientError (e.g. NoSuchKey)."""


class FakeR2Client:
    """Minimal S3-like client backed by an in-memory {key: bytes} store."""

    def __init__(self, objects: dict[str, bytes], *, delay: float = 0.0) -> None:
        self._objects = dict(objects)
        self.get_counts: dict[str, int] = {}
        self._delay = delay
        self._lock = threading.Lock()

    def get_object(self, *, Bucket: str, Key: str) -> dict:  # noqa: N803
        with self._lock:
            self.get_counts[Key] = self.get_counts.get(Key, 0) + 1
        if self._delay:
            time.sleep(self._delay)
        if Key not in self._objects:
            raise FakeR2Error(f"NoSuchKey: {Key}")
        return {"Body": _FakeBody(self._objects[Key])}


def _runtime_with(objects: dict[str, bytes], *, delay: float = 0.0) -> tuple[WraFloodRuntime, FakeR2Client]:
    client = FakeR2Client(objects, delay=delay)
    runtime = WraFloodRuntime(client_factory=lambda: client, bucket="test-bucket")
    return runtime, client


def _objects_for(scenario: str, records: list[dict] | None = None):
    manifest_bytes, artifact_bytes, features = _make_artifact(scenario, records)
    objects = {
        f"{RELEASE_PREFIX}/{scenario}/manifest.json": manifest_bytes,
        f"{RELEASE_PREFIX}/{scenario}/features.json.gz": artifact_bytes,
    }
    return objects, manifest_bytes, artifact_bytes, features


# ===========================================================================
# 16. canonical scenario key construction
# ===========================================================================


def test_canonical_key_construction() -> None:
    assert manifest_key("24h-350mm") == "processed/wra/flood/v1/24h-350mm/manifest.json"
    assert artifact_key("24h-350mm") == "processed/wra/flood/v1/24h-350mm/features.json.gz"
    # All 10 canonical scenarios build the expected keys.
    for scenario in CANONICAL_SCENARIOS:
        assert manifest_key(scenario) == f"{RELEASE_PREFIX}/{scenario}/manifest.json"
        assert artifact_key(scenario) == f"{RELEASE_PREFIX}/{scenario}/features.json.gz"
    assert len(CANONICAL_SCENARIOS) == 10


def test_key_construction_rejects_unknown_scenario() -> None:
    with pytest.raises(InvalidScenarioError):
        manifest_key("../evil")
    with pytest.raises(InvalidScenarioError):
        artifact_key("99h-999mm")


# ===========================================================================
# 2. invalid scenario rejected (fail closed, never no_match)
# ===========================================================================


def test_invalid_scenario_rejected() -> None:
    runtime, client = _runtime_with({})
    with pytest.raises(InvalidScenarioError):
        runtime.load_scenario("not-a-scenario")
    with pytest.raises(InvalidScenarioError):
        runtime.query_point("not-a-scenario", 121.5, 25.0)
    # An invalid scenario must never trigger any R2 GET.
    assert client.get_counts == {}


# ===========================================================================
# 1. valid scenario load  + 7. WKB load
# ===========================================================================


def test_valid_scenario_load_decodes_wkb() -> None:
    scenario = "24h-350mm"
    objects, _mb, artifact_bytes, features = _objects_for(scenario)
    runtime, client = _runtime_with(objects)

    loaded = runtime.load_scenario(scenario)
    assert loaded.scenario == scenario
    assert loaded.feature_count == len(features) == 3
    # Checksum recorded equals the artifact sha256.
    assert loaded.artifact_sha256 == sha256_bytes(artifact_bytes)
    # WKB decode produced valid Shapely polygons.
    for geom in loaded.geometries:
        assert geom.geom_type in {"Polygon", "MultiPolygon"}
        assert geom.is_valid
    # STRtree built over all geometries.
    assert loaded.tree is not None


# ===========================================================================
# 3. manifest missing
# ===========================================================================


def test_manifest_missing_source_unavailable() -> None:
    scenario = "24h-350mm"
    objects, _mb, artifact_bytes, _f = _objects_for(scenario)
    del objects[f"{RELEASE_PREFIX}/{scenario}/manifest.json"]
    runtime, _client = _runtime_with(objects)
    with pytest.raises(SourceUnavailableError):
        runtime.load_scenario(scenario)


# ===========================================================================
# 4. artifact missing
# ===========================================================================


def test_artifact_missing_source_unavailable() -> None:
    scenario = "24h-350mm"
    objects, _mb, _ab, _f = _objects_for(scenario)
    del objects[f"{RELEASE_PREFIX}/{scenario}/features.json.gz"]
    runtime, _client = _runtime_with(objects)
    with pytest.raises(SourceUnavailableError):
        runtime.load_scenario(scenario)


# ===========================================================================
# 5. checksum mismatch fail closed
# ===========================================================================


def test_checksum_mismatch_fails_closed() -> None:
    scenario = "24h-350mm"
    objects, manifest_bytes, artifact_bytes, _f = _objects_for(scenario)
    # Corrupt the artifact bytes so the recomputed sha256 no longer matches the
    # manifest's artifact_sha256. Keep it a valid gzip so we prove the checksum
    # gate fires BEFORE decoding.
    corrupted = artifact_bytes[:-1] + bytes([artifact_bytes[-1] ^ 0xFF])
    objects[f"{RELEASE_PREFIX}/{scenario}/features.json.gz"] = corrupted
    runtime, _client = _runtime_with(objects)
    with pytest.raises(ChecksumMismatchError):
        runtime.load_scenario(scenario)


# ===========================================================================
# 6. invalid gzip/json artifact  (checksum passes, decode fails)
# ===========================================================================


def test_invalid_artifact_bytes_artifact_invalid() -> None:
    scenario = "24h-350mm"
    # Build a manifest whose artifact_sha256 matches a non-gzip payload so the
    # checksum passes but the decode fails -> ArtifactInvalidError.
    garbage = b"this is not gzip"
    manifest = {
        "scenario": scenario,
        "artifact_sha256": sha256_bytes(garbage),
        "dataset": "wra_flood_potential",
    }
    objects = {
        f"{RELEASE_PREFIX}/{scenario}/manifest.json": json.dumps(manifest).encode("utf-8"),
        f"{RELEASE_PREFIX}/{scenario}/features.json.gz": garbage,
    }
    runtime, _client = _runtime_with(objects)
    with pytest.raises(ArtifactInvalidError):
        runtime.load_scenario(scenario)


# ===========================================================================
# 15. malformed manifest (not JSON / missing artifact_sha256)
# ===========================================================================


def test_malformed_manifest_not_json() -> None:
    scenario = "24h-350mm"
    objects, _mb, artifact_bytes, _f = _objects_for(scenario)
    objects[f"{RELEASE_PREFIX}/{scenario}/manifest.json"] = b"{not valid json"
    runtime, _client = _runtime_with(objects)
    with pytest.raises(ArtifactInvalidError):
        runtime.load_scenario(scenario)


def test_malformed_manifest_missing_sha256() -> None:
    scenario = "24h-350mm"
    objects, _mb, artifact_bytes, _f = _objects_for(scenario)
    manifest = {"scenario": scenario, "dataset": "wra_flood_potential"}  # no artifact_sha256
    objects[f"{RELEASE_PREFIX}/{scenario}/manifest.json"] = json.dumps(manifest).encode("utf-8")
    runtime, _client = _runtime_with(objects)
    with pytest.raises(ArtifactInvalidError):
        runtime.load_scenario(scenario)


# ===========================================================================
# 8. STRtree hit  + 10. deepest Class wins
# ===========================================================================


def test_query_hit_deepest_class_wins() -> None:
    scenario = "24h-350mm"
    objects, _mb, _ab, features = _objects_for(scenario)
    runtime, _client = _runtime_with(objects)

    # Point inside the overlap region of Class 1 (big) and Class 4 (small).
    class4 = next(f for f in features if f.class_value == 4)
    lon, lat = _wgs84_point_in(class4)
    result = runtime.query_point(scenario, lon, lat)

    assert result["matched"] is True
    assert result["status"] == "loaded"
    assert result["matched_count"] == 2  # both Class 1 and Class 4 intersect
    assert result["class"] == 4  # deepest wins
    assert result["canonical_depth"] == "2.0-3.0 m"
    assert result["city_name"] == "臺北市"
    assert result["town_name"] == "士林區"
    assert result["flood_dept_malformed"] is False


# ===========================================================================
# 9. STRtree no-hit  + 11. no safe/low-risk interpretation
# ===========================================================================


def test_query_miss_has_no_risk_interpretation() -> None:
    scenario = "24h-350mm"
    objects, _mb, _ab, _f = _objects_for(scenario)
    runtime, _client = _runtime_with(objects)

    # A far-away point (Pacific) that misses every polygon.
    result = runtime.query_point(scenario, 123.9, 24.0)
    assert result["matched"] is False
    assert result["matched_count"] == 0
    assert result["status"] == "no_match"

    payload = json.dumps(result).lower()
    assert "safe" not in payload
    assert "low_risk" not in payload
    assert "\"risk\"" not in payload
    assert "risk" not in result  # no bare 'risk' key


# ===========================================================================
# 12. second query does not re-download R2
# ===========================================================================


def test_warm_cache_no_redownload() -> None:
    scenario = "24h-350mm"
    objects, _mb, _ab, features = _objects_for(scenario)
    runtime, client = _runtime_with(objects)

    mkey = f"{RELEASE_PREFIX}/{scenario}/manifest.json"
    akey = f"{RELEASE_PREFIX}/{scenario}/features.json.gz"

    class1 = next(f for f in features if f.class_value == 1)
    lon, lat = _wgs84_point_in(class1)

    runtime.query_point(scenario, lon, lat)
    assert client.get_counts[mkey] == 1
    assert client.get_counts[akey] == 1
    assert runtime.cold_load_count == 1

    # Repeated queries must not re-GET from R2.
    for _ in range(5):
        runtime.query_point(scenario, lon, lat)
    assert client.get_counts[mkey] == 1
    assert client.get_counts[akey] == 1
    assert runtime.cold_load_count == 1


# ===========================================================================
# 13. cache clear causes reload
# ===========================================================================


def test_clear_cache_causes_reload() -> None:
    scenario = "24h-350mm"
    objects, _mb, _ab, _f = _objects_for(scenario)
    runtime, client = _runtime_with(objects)
    akey = f"{RELEASE_PREFIX}/{scenario}/features.json.gz"

    runtime.load_scenario(scenario)
    assert client.get_counts[akey] == 1
    assert runtime.is_cached(scenario) is True

    runtime.clear_cache()
    assert runtime.is_cached(scenario) is False

    runtime.load_scenario(scenario)
    assert client.get_counts[akey] == 2  # re-downloaded after clear
    assert runtime.cold_load_count == 2


# ===========================================================================
# 14. concurrent cold-load only downloads once (single-flight)
# ===========================================================================


def test_concurrent_cold_load_single_flight() -> None:
    scenario = "24h-350mm"
    objects, _mb, _ab, _f = _objects_for(scenario)
    # Add latency to widen the race window.
    runtime, client = _runtime_with(objects, delay=0.05)
    akey = f"{RELEASE_PREFIX}/{scenario}/features.json.gz"

    results: list = []
    barrier = threading.Barrier(8)

    def worker() -> None:
        barrier.wait()
        results.append(runtime.load_scenario(scenario))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Despite 8 concurrent threads, the artifact is downloaded exactly once.
    assert client.get_counts[akey] == 1
    assert runtime.cold_load_count == 1
    assert len(results) == 8
    # All threads observe the same cached object.
    assert all(r is results[0] for r in results)


# ===========================================================================
# Failure states are never downgraded to no_match
# ===========================================================================


def test_failures_never_become_no_match() -> None:
    scenario = "24h-350mm"
    # Missing everything -> source_unavailable, not a miss.
    runtime, _client = _runtime_with({})
    with pytest.raises(SourceUnavailableError):
        runtime.query_point(scenario, 121.5, 25.0)
