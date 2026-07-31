"""Offline Terrain adapter and privacy contract tests."""

from services.official_terrain_data import (
    ingest_terrain_snapshot,
    match_terrain_snapshot,
    sanitize_terrain_evidence_for_case,
    validate_terrain_snapshot,
)


def snapshot() -> dict:
    return {
        "type": "FeatureCollection",
        "provider_id": "fixture_terrain_provider",
        "source_version": "fixture-v1",
        "effective_date": "2026-01-01",
        "fetched_at": "2026-01-02T00:00:00+00:00",
        "attribution": "Fixture attribution",
        "features": [{
            "type": "Feature",
            "properties": {"feature_id": "fixture-1", "layer_id": "debris_flow", "official_name": "Fixture debris-flow reference"},
            "geometry": {"type": "Polygon", "coordinates": [[[121.0, 25.0], [122.0, 25.0], [122.0, 26.0], [121.0, 26.0], [121.0, 25.0]]]},
        }],
    }


def test_snapshot_schema_and_deterministic_match() -> None:
    payload = snapshot()
    assert validate_terrain_snapshot(payload, "fixture_terrain_provider")["valid"] is True
    first = match_terrain_snapshot(payload, 25.5, 121.5, "debris_flow")
    second = match_terrain_snapshot(payload, 25.5, 121.5, "debris_flow")
    assert first == second
    assert first["query_status"] == "matched"
    assert first["match_status"] == "matched"
    assert first["matched_feature_count"] == 1


def test_no_match_is_not_safe_or_low_risk() -> None:
    result = match_terrain_snapshot(snapshot(), 24.5, 121.5, "debris_flow")
    assert result["query_status"] == "not_matched_in_loaded_layer"
    assert result["match_status"] == "not_matched_in_loaded_layer"
    assert "no risk" not in str(result["limitation"]).lower()
    assert "low" not in str(result["limitation"]).lower()


def test_missing_layer_is_outside_loaded_coverage() -> None:
    result = match_terrain_snapshot(snapshot(), 25.5, 121.5, "flood")
    assert result["query_status"] == "outside_coverage"
    assert result["coverage_status"] == "outside_coverage"


def test_invalid_snapshot_is_error_and_case_contract_is_reduced() -> None:
    result = match_terrain_snapshot({"type": "FeatureCollection", "features": []}, 25.5, 121.5, "flood")
    assert result["query_status"] == "error"
    stored = sanitize_terrain_evidence_for_case(match_terrain_snapshot(snapshot(), 25.5, 121.5, "debris_flow"))
    assert not {"latitude", "longitude", "geometry", "raw", "payload"}.intersection(stored)


def test_case_boundary_rejects_sensitive_text() -> None:
    evidence = match_terrain_snapshot(snapshot(), 25.5, 121.5, "debris_flow")
    evidence["limitation"] = "raw coordinate payload"
    try:
        sanitize_terrain_evidence_for_case(evidence)
    except ValueError as exc:
        assert "unsafe" in str(exc)
    else:
        raise AssertionError("unsafe evidence should not be stored")


def test_import_is_dry_run_and_reports_checksum(tmp_path) -> None:
    path = tmp_path / "terrain.json"
    path.write_text(__import__("json").dumps(snapshot()), encoding="utf-8")
    report = ingest_terrain_snapshot(path, "fixture_terrain_provider")
    assert report["status"] == "validated"
    assert report["dry_run"] is True
    assert report["mutation"] == "none"
    assert report["source_checksum_sha256"]
