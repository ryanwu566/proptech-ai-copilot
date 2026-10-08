"""Acceptance exercises saved artifacts through the production index loaders."""
import json
import gzip
import hashlib
from shapely.geometry import box
from shapely import wkb

import pytest

from tests.test_wra_flood_runtime import _make_artifact, _wgs84_point_in
from tests.test_gsmma_geological_sensitivity_runtime import _build_objects, _inside_point, VERSION
from services import provider_artifact_acceptance as acceptance


def test_wra_acceptance_checks_positive_negative_and_checksum():
    manifest_bytes, artifact, features = _make_artifact("24h-350mm")
    manifest = json.loads(manifest_bytes)
    manifest["source_vintage"] = "official-fixture-2024"
    lon, lat = _wgs84_point_in(features[0])
    result = acceptance.validate_wra_artifact(json.dumps(manifest).encode(), artifact, fixtures=[
        {"lon": lon, "lat": lat, "matched": True, "label": "positive"},
        {"lon": 123.9, "lat": 24.0, "matched": False, "label": "negative"},
    ])
    assert result["status"] == "accepted"
    assert result["network_requests"] == 0
    assert result["source_vintage"] == "official-fixture-2024"
    assert [row["matched"] for row in result["fixture_results"]] == [True, False]
    with pytest.raises(Exception, match="checksum"):
        acceptance.validate_wra_artifact(json.dumps(manifest).encode(), artifact + b"corrupt")


def test_wra_acceptance_requires_explicit_vintage():
    manifest, artifact, _ = _make_artifact("24h-350mm")
    with pytest.raises(ValueError, match="vintage"):
        acceptance.validate_wra_artifact(manifest, artifact)


def test_gsmma_acceptance_reuses_exact_version_index_and_rejects_bad_fixture(tmp_path):
    from services.gsmma_geological_sensitivity_runtime import manifest_key, artifact_key
    objects = _build_objects(tmp_path)
    manifest, artifact = objects[manifest_key(VERSION)], objects[artifact_key(VERSION)]
    lon, lat = _inside_point()
    fixtures = [{"lon": lon, "lat": lat, "matched": True, "label": "positive"},
                {"lon": 123.9, "lat": 24.0, "matched": False, "label": "negative"}]
    result = acceptance.validate_gsmma_artifact(manifest, artifact, dataset_version=VERSION, fixtures=fixtures)
    assert result["status"] == "accepted" and result["dataset_version"] == VERSION
    assert result["network_requests"] == 0
    fixtures[0]["matched"] = False
    with pytest.raises(ValueError, match="fixture"):
        acceptance.validate_gsmma_artifact(manifest, artifact, dataset_version=VERSION, fixtures=fixtures)
    with pytest.raises(Exception, match="immutable"):
        acceptance.validate_gsmma_artifact(manifest, artifact, dataset_version="latest")


def test_gsmma_point_on_boundary_matches_existing_intersection_contract(tmp_path):
    from services.gsmma_geological_sensitivity_runtime import manifest_key, artifact_key, GsmmaGeologicalSensitivityRuntime
    from services.provider_artifact_acceptance import _SavedObjects
    objects = _build_objects(tmp_path)
    runtime = GsmmaGeologicalSensitivityRuntime(client_factory=lambda: _SavedObjects(objects), bucket="fixture", dataset_version=VERSION)
    # Use the exact saved vertex: avoid transformed-coordinate rounding turning
    # a boundary fixture into an accidental outside point.
    lon, lat = runtime.load_dataset().features[0].geometry.exterior.coords[0]
    result = acceptance.validate_gsmma_artifact(objects[manifest_key(VERSION)], objects[artifact_key(VERSION)], dataset_version=VERSION,
                                               fixtures=[{"lon": lon, "lat": lat, "matched": True, "label": "boundary"}])
    assert result["fixture_results"][0]["matched"] is True


def test_gsmma_acceptance_rejects_projected_coordinates_mislabeled_as_wgs84(tmp_path):
    from services.gsmma_geological_sensitivity_runtime import manifest_key, artifact_key, ArtifactInvalidError
    objects = _build_objects(tmp_path)
    manifest = json.loads(objects[manifest_key(VERSION)])
    document = json.loads(gzip.decompress(objects[artifact_key(VERSION)]))
    document["features"][0]["geometry_wkb_hex"] = wkb.dumps(box(250000, 2700000, 250010, 2700010), hex=True)
    artifact = gzip.compress(json.dumps(document).encode())
    manifest["artifact_sha256"] = hashlib.sha256(artifact).hexdigest()
    with pytest.raises(ArtifactInvalidError):
        acceptance.validate_gsmma_artifact(json.dumps(manifest).encode(), artifact, dataset_version=VERSION)
