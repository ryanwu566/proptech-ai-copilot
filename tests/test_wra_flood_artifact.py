"""Phase 2 tests for the WRA flood processed-artifact builder.

These tests build tiny synthetic SHP ZIPs entirely in memory with ``pyshp``
and a ``pyproj``-generated ``.prj``.  No official WRA SHP/ZIP is committed or
read here; the real official-data smoke test is run manually by the operator
against a local ZIP (documented in the build script), never in CI.

Coverage:
* zip-slip / unsafe member rejection and archive size/entry limits,
* CRS validation via pyproj (never from the filename),
* missing / ambiguous SHP component rejection,
* SHP parsing into normalized WGS84 features,
* artifact round-trip (WKB+base64 inside gzip JSON, never pickle),
* deterministic artifact bytes and stable SHA256,
* manifest field completeness,
* source checksum verification,
* area conservation measurement before/after make_valid.
"""

from __future__ import annotations

import base64
import gzip
import io
import json
import zipfile

import pytest
from pyproj import CRS
from shapely.geometry import Point

from services.wra_flood_artifact import (
    ArtifactBuildError,
    build_processed_artifact,
    extract_shp_components,
    load_artifact,
    serialize_artifact,
    sha256_bytes,
    validate_source_crs,
    verify_point_against_features,
)

import shapefile  # pyshp


# ---------------------------------------------------------------------------
# Synthetic SHP/ZIP fixtures (in-memory, no official data)
# ---------------------------------------------------------------------------

# A source-CRS (EPSG:3826, metres) square near northern Taiwan.  Two default
# features: a valid class-1 square and a self-intersecting class-3 "bowtie"
# that must be repaired by make_valid.
_BASE_X = 250000.0
_BASE_Y = 2770000.0


def _epsg3826_wkt() -> str:
    return CRS.from_epsg(3826).to_wkt()


def _default_records() -> list[dict]:
    valid_square = [
        [_BASE_X, _BASE_Y],
        [_BASE_X, _BASE_Y + 2000],
        [_BASE_X + 2000, _BASE_Y + 2000],
        [_BASE_X + 2000, _BASE_Y],
        [_BASE_X, _BASE_Y],
    ]
    # A self-touching "hourglass at a shared vertex": two squares that meet at a
    # single point.  This ring is invalid (self-intersection at the shared
    # vertex) until make_valid splits it into an equal-area MultiPolygon, so it
    # exercises geometry repair WITHOUT losing area -- mirroring the near-valid
    # ring-orientation defects seen in the real WRA SHP.
    bx, by = _BASE_X + 10000, _BASE_Y + 10000
    self_touching = [
        [bx, by],
        [bx + 1000, by + 1000],  # shared touch vertex
        [bx + 2000, by],
        [bx + 2000, by + 2000],
        [bx + 1000, by + 1000],  # touch again -> self-intersection
        [bx, by + 2000],
        [bx, by],
    ]
    return [
        {
            "poly": [valid_square],
            "Class": 1,
            "flood_dept": "0.3-0.5",
            "City": "63000",
            "CityName": "臺北市",
            "Town": "63000010",
            "TownName": "測試一區",
        },
        {
            "poly": [self_touching],
            "Class": 3,
            "flood_dept": "0.3-0.>3.0",  # malformed on purpose
            "City": "65000",
            "CityName": "新北市",
            "Town": "65000020",
            "TownName": "測試二區",
        },
    ]


def _write_shp_components(records: list[dict]) -> dict[str, bytes]:
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
        writer.record(
            rec["Class"], rec["flood_dept"], rec["City"], rec["CityName"], rec["Town"], rec["TownName"]
        )
    writer.close()
    return {"shp": shp.getvalue(), "shx": shx.getvalue(), "dbf": dbf.getvalue()}


def _build_zip(
    records: list[dict] | None = None,
    *,
    base_name: str = "flood",
    prj_wkt: str | None = None,
    include: tuple[str, ...] = ("shp", "shx", "dbf", "prj"),
    extra_members: dict[str, bytes] | None = None,
    cpg: str | None = None,
) -> bytes:
    if records is None:
        records = _default_records()
    parts = _write_shp_components(records)
    if prj_wkt is None:
        prj_wkt = _epsg3826_wkt()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        if "shp" in include:
            archive.writestr(f"{base_name}.shp", parts["shp"])
        if "shx" in include:
            archive.writestr(f"{base_name}.shx", parts["shx"])
        if "dbf" in include:
            archive.writestr(f"{base_name}.dbf", parts["dbf"])
        if "prj" in include:
            archive.writestr(f"{base_name}.prj", prj_wkt.encode("utf-8"))
        if cpg is not None:
            archive.writestr(f"{base_name}.cpg", cpg.encode("ascii"))
        for name, payload in (extra_members or {}).items():
            archive.writestr(name, payload)
    return buffer.getvalue()


_SOURCE_URL = "https://example.invalid/wra/flood/test"


def _build(zip_bytes: bytes, **kwargs):
    return build_processed_artifact(
        zip_bytes, scenario="test-scenario", source_url=_SOURCE_URL, **kwargs
    )


# ---------------------------------------------------------------------------
# 1. zip-slip and archive limits
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "evil_name",
    [
        "../evil.txt",
        "../../etc/passwd",
        "sub/../../escape.txt",
        "/abs/evil.txt",
        "C:/windows/system32/evil.txt",
    ],
)
def test_zip_slip_member_rejected(evil_name: str) -> None:
    zip_bytes = _build_zip(extra_members={evil_name: b"payload"})
    with pytest.raises(ArtifactBuildError) as exc:
        extract_shp_components(zip_bytes)
    assert "unsafe" in str(exc.value).lower()


def test_too_many_entries_rejected() -> None:
    filler = {f"junk/file_{i}.txt": b"x" for i in range(200)}
    zip_bytes = _build_zip(extra_members=filler)
    with pytest.raises(ArtifactBuildError) as exc:
        extract_shp_components(zip_bytes)
    assert "too many entries" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# 2. CRS validation (never from filename)
# ---------------------------------------------------------------------------


def test_crs_validation_accepts_epsg3826() -> None:
    crs = validate_source_crs(_epsg3826_wkt())
    assert crs.to_epsg() == 3826


def test_crs_validation_rejects_wgs84() -> None:
    with pytest.raises(ArtifactBuildError):
        validate_source_crs(CRS.from_epsg(4326).to_wkt())


def test_crs_validation_rejects_empty_prj() -> None:
    with pytest.raises(ArtifactBuildError):
        validate_source_crs("")


def test_crs_validation_ignores_filename_and_uses_wkt() -> None:
    # A ZIP whose .prj actually holds WGS84 must be rejected even though the
    # SHP components look normal; the CRS decision comes from the WKT, not names.
    zip_bytes = _build_zip(prj_wkt=CRS.from_epsg(4326).to_wkt())
    with pytest.raises(ArtifactBuildError):
        _build(zip_bytes)


# ---------------------------------------------------------------------------
# 3. missing / ambiguous SHP component
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing", ["shp", "shx", "dbf", "prj"])
def test_missing_component_rejected(missing: str) -> None:
    include = tuple(c for c in ("shp", "shx", "dbf", "prj") if c != missing)
    zip_bytes = _build_zip(include=include)
    with pytest.raises(ArtifactBuildError) as exc:
        extract_shp_components(zip_bytes)
    assert "missing required shp component" in str(exc.value).lower()


def test_ambiguous_component_rejected() -> None:
    # Two .shp files (different stems) -> ambiguous.
    parts = _write_shp_components(_default_records())
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for ext in ("shp", "shx", "dbf"):
            archive.writestr(f"flood.{ext}", parts[ext])
        archive.writestr("flood.prj", _epsg3826_wkt().encode("utf-8"))
        archive.writestr("other.shp", parts["shp"])  # second, ambiguous .shp
    with pytest.raises(ArtifactBuildError) as exc:
        extract_shp_components(buffer.getvalue())
    assert "ambiguous" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# 4. SHP parsing / normalization
# ---------------------------------------------------------------------------


def test_shp_parsing_and_normalization() -> None:
    result = _build(_build_zip())
    stats = result.stats
    assert stats.feature_count == 2
    assert stats.accepted_count == 2
    assert stats.rejected_count == 0
    # The class-3 bowtie is invalid and must be repaired.
    assert stats.repaired_geometry_count == 1
    # The class-3 record carries a malformed flood_dept string.
    assert stats.malformed_flood_dept_count == 1
    assert stats.class_distribution == {1: 1, 3: 1}
    # Canonical depth comes from Class, not the (malformed) flood_dept.
    depths = {f.class_value: f.canonical_depth for f in result.features}
    assert depths == {1: "0.3-0.5 m", 3: "1.0-2.0 m"}
    # City/town attributes survive normalization.
    cities = {f.city_name for f in result.features}
    assert cities == {"臺北市", "新北市"}


def test_features_are_reprojected_to_wgs84() -> None:
    result = _build(_build_zip())
    for feature in result.features:
        minx, miny, maxx, maxy = feature.geometry_wgs84.bounds
        assert 119.0 < minx < 122.5
        assert 21.5 < miny < 25.9
        assert feature.geometry_wgs84.geom_type in {"Polygon", "MultiPolygon"}
        assert feature.geometry_wgs84.is_valid


def test_invalid_class_record_rejected() -> None:
    records = _default_records()
    records.append(
        {
            "poly": [[[_BASE_X, _BASE_Y], [_BASE_X, _BASE_Y + 500], [_BASE_X + 500, _BASE_Y + 500], [_BASE_X + 500, _BASE_Y], [_BASE_X, _BASE_Y]]],
            "Class": 9,  # invalid
            "flood_dept": "x",
            "City": "10000",
            "CityName": "測試縣",
            "Town": "10000010",
            "TownName": "測試鄉",
        }
    )
    result = _build(_build_zip(records))
    assert result.stats.feature_count == 3
    assert result.stats.accepted_count == 2
    assert result.stats.rejected_count == 1
    assert result.stats.invalid_class_count == 1


# ---------------------------------------------------------------------------
# 5. artifact round-trip (no pickle)
# ---------------------------------------------------------------------------


def test_artifact_roundtrip_preserves_features() -> None:
    result = _build(_build_zip())
    document, features = load_artifact(result.artifact_bytes)
    assert document["schema"] == "wra_flood_processed_v1"
    assert document["geometry_encoding"] == "wkb_base64"
    assert len(features) == len(result.features)
    # Class / canonical depth / malformed flag survive the round-trip.
    by_class = {f.class_value: f for f in features}
    assert by_class[1].canonical_depth == "0.3-0.5 m"
    assert by_class[3].canonical_depth == "1.0-2.0 m"
    assert by_class[3].flood_dept_malformed is True
    assert by_class[3].properties["city_name"] == "新北市"


def test_artifact_is_gzip_json_with_wkb_base64_not_pickle() -> None:
    result = _build(_build_zip())
    raw = gzip.decompress(result.artifact_bytes)
    document = json.loads(raw.decode("utf-8"))  # parses as JSON -> not pickle
    record = document["features"][0]
    assert "geometry_wkb_base64" in record
    # Value must be valid base64-encoded WKB.
    decoded = base64.b64decode(record["geometry_wkb_base64"])
    assert decoded[:1] in (b"\x00", b"\x01")  # WKB byte-order marker
    # Pickle opcodes must never appear at the artifact head.
    assert raw[:2] != b"\x80\x04"


def test_roundtrip_geometry_matches_point() -> None:
    result = _build(_build_zip())
    _, features = load_artifact(result.artifact_bytes)
    # Reproject the class-1 square centroid via the same features and confirm a hit.
    from services.wra_flood_offline_dataset import match_point

    # Centroid of the class-1 square in WGS84.
    class1 = next(f for f in result.features if f.class_value == 1)
    c = class1.geometry_wgs84.centroid
    match = match_point(c.x, c.y, features)
    assert match.matched is True
    assert match.matched_feature["class"] == 1


# ---------------------------------------------------------------------------
# 6. deterministic artifact + checksum
# ---------------------------------------------------------------------------


def test_artifact_bytes_are_deterministic() -> None:
    zip_bytes = _build_zip()
    r1 = _build(zip_bytes)
    r2 = _build(zip_bytes)
    assert r1.artifact_bytes == r2.artifact_bytes
    assert sha256_bytes(r1.artifact_bytes) == sha256_bytes(r2.artifact_bytes)
    assert r1.manifest["artifact_sha256"] == r2.manifest["artifact_sha256"]


def test_serialize_artifact_is_stable_regardless_of_mtime() -> None:
    result = _build(_build_zip())
    reserialized = serialize_artifact(result.features, scenario="test-scenario")
    # gzip mtime=0 makes output byte-for-byte reproducible.
    assert reserialized == result.artifact_bytes


def test_manifest_artifact_sha256_matches_bytes() -> None:
    result = _build(_build_zip())
    assert result.manifest["artifact_sha256"] == sha256_bytes(result.artifact_bytes)


def test_source_sha256_verification() -> None:
    zip_bytes = _build_zip()
    good = sha256_bytes(zip_bytes)
    # Correct expected hash passes.
    result = _build(zip_bytes, expected_source_sha256=good)
    assert result.manifest["source_sha256"] == good
    # Wrong expected hash fails fast.
    with pytest.raises(ArtifactBuildError) as exc:
        _build(zip_bytes, expected_source_sha256="0" * 64)
    assert "sha256 mismatch" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# 7. manifest field completeness
# ---------------------------------------------------------------------------


def test_manifest_has_all_required_fields() -> None:
    result = _build(_build_zip())
    manifest = result.manifest
    required = {
        "scenario",
        "source_url",
        "source_sha256",
        "artifact_sha256",
        "source_crs",
        "target_crs",
        "feature_count",
        "accepted_count",
        "rejected_count",
        "repaired_geometry_count",
        "malformed_flood_dept_count",
        "class_distribution",
        "geometry_type_distribution",
        "area_before_m2",
        "area_after_m2",
        "area_difference_pct",
        "city_count",
        "town_count",
        "quality_status",
    }
    assert required.issubset(manifest.keys())
    assert manifest["source_crs"] == "EPSG:3826"
    assert manifest["target_crs"] == "EPSG:4326"
    assert manifest["scenario"] == "test-scenario"
    assert manifest["city_count"] == 2
    assert manifest["town_count"] == 2
    assert manifest["quality_status"] == "verified"


# ---------------------------------------------------------------------------
# 8. area conservation
# ---------------------------------------------------------------------------


def test_area_conservation_measured_and_small() -> None:
    result = _build(_build_zip())
    manifest = result.manifest
    # Area is actually measured in the source CRS (metres), not assumed 0.
    assert manifest["area_before_m2"] > 0
    assert manifest["area_after_m2"] > 0
    # make_valid should conserve area to well under the tolerance.
    assert manifest["area_difference_pct"] < 0.01


def test_area_before_reflects_original_ring_area() -> None:
    # Single clean 2000m x 2000m square -> 4,000,000 m^2 before make_valid.
    records = [_default_records()[0]]
    result = _build(_build_zip(records))
    assert result.stats.repaired_geometry_count == 0
    assert result.manifest["area_before_m2"] == pytest.approx(4_000_000.0, rel=1e-6)
    assert result.manifest["area_after_m2"] == pytest.approx(4_000_000.0, rel=1e-6)


# ---------------------------------------------------------------------------
# 9. no-hit is a plain miss, never a low-risk claim
# ---------------------------------------------------------------------------


def test_point_verification_hit_and_miss() -> None:
    result = _build(_build_zip())
    class1 = next(f for f in result.features if f.class_value == 1)
    c = class1.geometry_wgs84.centroid
    hit = verify_point_against_features(c.x, c.y, result.features)
    assert hit["matched"] is True
    assert hit["primary"]["class"] == 1
    assert hit["primary"]["canonical_depth"] == "0.3-0.5 m"

    # A far-away point misses; the result is a plain miss with no risk verdict.
    miss = verify_point_against_features(121.9, 25.9, result.features)
    assert miss["matched"] is False
    assert miss["matched_count"] == 0
    assert miss["primary"] is None
    # The miss payload must not assert anything about "safe" / "low risk".
    assert "risk" not in json.dumps(miss).lower()
    assert "safe" not in json.dumps(miss).lower()
