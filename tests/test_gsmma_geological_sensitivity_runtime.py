from __future__ import annotations

from collections import defaultdict
import gzip
import hashlib
import io
import json
import threading
import time
import zipfile

import pytest
import shapefile
from pyproj import CRS, Transformer

from services.gsmma_geological_sensitivity_artifact import PackageInput, build_processed_artifact
from services.gsmma_geological_sensitivity_runtime import (
    ArtifactInvalidError,
    ChecksumMismatchError,
    CrsInvalidRuntimeError,
    GsmmaGeologicalSensitivityRuntime,
    QueryError,
    SourceUnavailableError,
    UnsupportedDatasetRuntimeError,
    artifact_key,
    manifest_key,
    validate_dataset_version,
)


VERSION = "2024-06-27"


def _polygon_parts(polygons: list[list[list[float]]]) -> dict[str, bytes]:
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    writer = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYGON, encoding="utf-8")
    writer.field("OBJECTID", "N", size=8)
    for index, polygon in enumerate(polygons, start=1):
        writer.poly([polygon])
        writer.record(index)
    writer.close()
    return {
        "area.shp": shp.getvalue(),
        "area.shx": shx.getvalue(),
        "area.dbf": dbf.getvalue(),
        "area.prj": CRS.from_epsg(3826).to_wkt().encode(),
        "area.cpg": b"UTF-8",
    }


def _zip(parts: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in parts.items():
            archive.writestr(name, payload)
    return output.getvalue()


def _square(x: float, y: float, size: float = 100.0) -> list[list[float]]:
    return [[x, y], [x, y + size], [x + size, y + size], [x + size, y], [x, y]]


def _build_objects(tmp_path, *, two_designations: bool = False, fragments: bool = False):
    rows = [
        "1,活動斷層地質敏感區,F0001,測試斷層,2024-06-27,文號1,TWD97 TM2 121,,https://example.gov.tw/1.zip"
    ]
    inputs = []
    first_polygons = [_square(250000, 2770000)]
    if fragments:
        first_polygons.append(_square(250020, 2770020))
    first = tmp_path / "first.zip"
    first.write_bytes(_zip(_polygon_parts(first_polygons)))
    inputs.append(PackageInput("1", first))
    if two_designations:
        rows.append(
            "2,山崩與地滑地質敏感區,L0001,測試山崩區,2024-06-28,文號2,TWD97 TM2 121,,https://example.gov.tw/2.zip"
        )
        second = tmp_path / "second.zip"
        second.write_bytes(_zip(_polygon_parts([_square(250010, 2770010)])))
        inputs.append(PackageInput("2", second))
    index = (
        "No.,地質敏感區類型,地質敏感區編號,地質敏感區名稱,公告日期,文號,座標系統1,座標系統2,下載連結\n"
        + "\n".join(rows)
        + "\n"
    ).encode()
    result = build_processed_artifact(
        index, inputs, dataset_version=VERSION, source_vintage="2024-06-27"
    )
    return {
        manifest_key(VERSION): result.manifest_bytes,
        artifact_key(VERSION): result.artifact_bytes,
    }


class _Body:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


class FakeClient:
    def __init__(self, objects: dict[str, bytes], delay: float = 0):
        self.objects = objects
        self.delay = delay
        self.calls = defaultdict(int)

    def get_object(self, *, Bucket: str, Key: str):
        self.calls[Key] += 1
        if self.delay:
            time.sleep(self.delay)
        if Key not in self.objects:
            raise RuntimeError("NoSuchKey")
        return {"Body": _Body(self.objects[Key])}


def _runtime(objects: dict[str, bytes], *, delay: float = 0, version: str | None = VERSION):
    client = FakeClient(objects, delay=delay)
    runtime = GsmmaGeologicalSensitivityRuntime(
        client_factory=lambda: client, bucket="test-bucket", dataset_version=version
    )
    return runtime, client


def _inside_point() -> tuple[float, float]:
    return Transformer.from_crs(3826, 4326, always_xy=True).transform(250050, 2770050)


def test_runtime_requires_explicit_version(monkeypatch) -> None:
    monkeypatch.delenv("GSMMA_GEOLOGICAL_SENSITIVITY_DATASET_VERSION", raising=False)
    runtime, _ = _runtime({}, version=None)
    with pytest.raises(SourceUnavailableError, match="DATASET_VERSION"):
        runtime.load_dataset()


@pytest.mark.parametrize("version", ["latest", "../escape", "a/b", "C:drive", ""])
def test_runtime_rejects_mutable_or_unsafe_versions(version: str) -> None:
    with pytest.raises(UnsupportedDatasetRuntimeError):
        validate_dataset_version(version)


def test_runtime_constructs_only_immutable_versioned_keys() -> None:
    assert manifest_key(VERSION) == f"processed/gsmma/geological-sensitivity/v1/{VERSION}/manifest.json"
    assert artifact_key(VERSION) == f"processed/gsmma/geological-sensitivity/v1/{VERSION}/features.json.gz"


def test_missing_object_is_source_unavailable() -> None:
    runtime, _ = _runtime({})
    with pytest.raises(SourceUnavailableError):
        runtime.load_dataset()


def test_manifest_version_mismatch_is_unsupported(tmp_path) -> None:
    objects = _build_objects(tmp_path)
    manifest = json.loads(objects[manifest_key(VERSION)])
    manifest["dataset_version"] = "other-version"
    objects[manifest_key(VERSION)] = json.dumps(manifest).encode()
    runtime, _ = _runtime(objects)
    with pytest.raises(UnsupportedDatasetRuntimeError, match="version"):
        runtime.load_dataset()


def test_review_required_manifest_is_not_queryable(tmp_path) -> None:
    objects = _build_objects(tmp_path)
    manifest = json.loads(objects[manifest_key(VERSION)])
    manifest["quality_status"] = "review_required"
    objects[manifest_key(VERSION)] = json.dumps(manifest).encode()
    runtime, _ = _runtime(objects)
    with pytest.raises(UnsupportedDatasetRuntimeError, match="quality"):
        runtime.load_dataset()


def test_manifest_target_crs_must_be_wgs84(tmp_path) -> None:
    objects = _build_objects(tmp_path)
    manifest = json.loads(objects[manifest_key(VERSION)])
    manifest["target_crs"] = "EPSG:3826"
    objects[manifest_key(VERSION)] = json.dumps(manifest).encode()
    runtime, _ = _runtime(objects)
    with pytest.raises(CrsInvalidRuntimeError):
        runtime.load_dataset()


def test_checksum_is_verified_before_decode(tmp_path) -> None:
    objects = _build_objects(tmp_path)
    objects[artifact_key(VERSION)] += b"corrupt"
    runtime, _ = _runtime(objects)
    with pytest.raises(ChecksumMismatchError):
        runtime.load_dataset()


def test_invalid_manifest_and_artifact_are_distinct(tmp_path) -> None:
    runtime, _ = _runtime({manifest_key(VERSION): b"not-json"})
    with pytest.raises(ArtifactInvalidError, match="manifest"):
        runtime.load_dataset()

    objects = _build_objects(tmp_path)
    manifest = json.loads(objects[manifest_key(VERSION)])
    bad = b"not-gzip"
    manifest["artifact_sha256"] = hashlib.sha256(bad).hexdigest()
    objects[manifest_key(VERSION)] = json.dumps(manifest).encode()
    objects[artifact_key(VERSION)] = bad
    runtime, _ = _runtime(objects)
    with pytest.raises(ArtifactInvalidError, match="artifact"):
        runtime.load_dataset()


def test_accepted_empty_artifact_is_rejected(tmp_path) -> None:
    objects = _build_objects(tmp_path)
    document = json.loads(gzip.decompress(objects[artifact_key(VERSION)]).decode("utf-8"))
    document["features"] = []
    artifact = gzip.compress(
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        mtime=0,
    )
    manifest = json.loads(objects[manifest_key(VERSION)])
    manifest["feature_count"] = 0
    manifest["artifact_sha256"] = hashlib.sha256(artifact).hexdigest()
    objects[manifest_key(VERSION)] = json.dumps(manifest).encode()
    objects[artifact_key(VERSION)] = artifact

    runtime, _ = _runtime(objects)
    with pytest.raises(ArtifactInvalidError, match="feature count"):
        runtime.load_dataset()

def test_cold_load_warm_cache_and_clear(tmp_path) -> None:
    objects = _build_objects(tmp_path)
    runtime, client = _runtime(objects)
    first = runtime.load_dataset()
    second = runtime.load_dataset()
    assert first is second
    assert client.calls[manifest_key(VERSION)] == 1
    assert client.calls[artifact_key(VERSION)] == 1
    runtime.clear_cache()
    runtime.load_dataset()
    assert client.calls[manifest_key(VERSION)] == 2


def test_concurrent_cold_load_is_single_flight(tmp_path) -> None:
    runtime, client = _runtime(_build_objects(tmp_path), delay=0.02)
    barrier = threading.Barrier(6)
    results = []

    def worker():
        barrier.wait()
        results.append(runtime.load_dataset())

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(results) == 6
    assert all(result is results[0] for result in results)
    assert client.calls[artifact_key(VERSION)] == 1


def test_query_returns_all_overlapping_designations(tmp_path) -> None:
    runtime, _ = _runtime(_build_objects(tmp_path, two_designations=True))
    lon, lat = _inside_point()
    result = runtime.query_point(lon, lat)
    assert result["matched"] is True
    assert result["matched_count"] == 2
    assert [match["canonical_category"] for match in result["matches"]] == [
        "active_fault_sensitive_area",
        "landslide_sensitive_area",
    ]
    assert result["dataset_version"] == VERSION


def test_query_consolidates_fragments_of_same_designation(tmp_path) -> None:
    runtime, _ = _runtime(_build_objects(tmp_path, fragments=True))
    lon, lat = _inside_point()
    result = runtime.query_point(lon, lat)
    assert result["matched_count"] == 1
    assert result["matches"][0]["matched_fragment_count"] == 2


def test_successful_no_match_contains_no_safety_or_risk_level(tmp_path) -> None:
    runtime, _ = _runtime(_build_objects(tmp_path))
    result = runtime.query_point(123.0, 20.0)
    assert result == {
        "status": "no_match",
        "matched": False,
        "matched_count": 0,
        "matches": [],
        "dataset_version": VERSION,
        "artifact_sha256": runtime.load_dataset().artifact_sha256,
        "source_vintage": "2024-06-27",
    }


@pytest.mark.parametrize(("lon", "lat"), [(181, 25), (121, 91), (float("nan"), 25)])
def test_invalid_query_coordinates_fail_closed(tmp_path, lon: float, lat: float) -> None:
    runtime, _ = _runtime(_build_objects(tmp_path))
    with pytest.raises(QueryError):
        runtime.query_point(lon, lat)


def test_match_limit_errors_instead_of_truncating(tmp_path, monkeypatch) -> None:
    import services.gsmma_geological_sensitivity_runtime as runtime_module

    monkeypatch.setattr(runtime_module, "MAX_MATCHED_FEATURES", 1)
    runtime, _ = _runtime(_build_objects(tmp_path, two_designations=True))
    with pytest.raises(QueryError, match="limit"):
        runtime.query_point(*_inside_point())
