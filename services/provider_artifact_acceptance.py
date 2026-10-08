"""Offline acceptance of immutable risk artifacts; never performs R2 access."""

from __future__ import annotations

import io
import math
from typing import Any, Iterable

from services import wra_flood_runtime as wra
from services import gsmma_geological_sensitivity_runtime as gsmma


class _SavedObjects:
    def __init__(self, objects: dict[str, bytes]):
        self.objects = objects

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        return {"Body": io.BytesIO(self.objects[Key])}


def _check_fixtures(query, fixtures: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(fixtures)
    if len(rows) > 3:
        raise ValueError("fixture count exceeds bounded acceptance limit of three")
    results = []
    for position, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("matched"), bool):
            raise ValueError("fixture requires an explicit boolean matched expectation")
        try:
            lon, lat = float(row["lon"]), float(row["lat"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("fixture coordinates must be numeric") from exc
        if not math.isfinite(lon) or not math.isfinite(lat) or not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise ValueError("fixture coordinates are outside WGS84 bounds")
        result = query(lon, lat)
        if result.get("matched") is not row["matched"]:
            raise ValueError(f"fixture {position + 1} did not match its declared expectation")
        results.append({"label": str(row.get("label") or f"fixture-{position + 1}"), "matched": result["matched"],
                        "status": result["status"]})
    return results


def _summary(loaded, version: str, vintage: str, fixture_results: list[dict[str, Any]]) -> dict[str, Any]:
    return {"status": "accepted", "dataset_version": version, "source_vintage": vintage,
            "artifact_sha256": loaded.artifact_sha256, "feature_count": len(loaded.features),
            "fixture_results": fixture_results, "fixtures_verified": bool(fixture_results),
            "network_requests": 0, "production_readiness": "unproven"}


def validate_wra_artifact(manifest_bytes: bytes, artifact_bytes: bytes, *, scenario: str = "24h-350mm",
                          fixtures: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    scenario = wra.validate_scenario(scenario)
    client = _SavedObjects({wra.manifest_key(scenario): manifest_bytes, wra.artifact_key(scenario): artifact_bytes})
    runtime = wra.WraFloodRuntime(client_factory=lambda: client, bucket="offline-acceptance")
    loaded = runtime.load_scenario(scenario)
    vintage = loaded.manifest.get("source_vintage")
    if not isinstance(vintage, str) or not vintage.strip() or vintage.casefold() == "unknown":
        raise ValueError("WRA acceptance requires explicit official source vintage")
    results = _check_fixtures(lambda lon, lat: runtime.query_point(scenario, lon, lat), fixtures)
    return {**_summary(loaded, "v1", vintage, results), "scenario": scenario}


def validate_gsmma_artifact(manifest_bytes: bytes, artifact_bytes: bytes, *, dataset_version: str,
                            fixtures: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    version = gsmma.validate_dataset_version(dataset_version)
    client = _SavedObjects({gsmma.manifest_key(version): manifest_bytes, gsmma.artifact_key(version): artifact_bytes})
    runtime = gsmma.GsmmaGeologicalSensitivityRuntime(client_factory=lambda: client, bucket="offline-acceptance", dataset_version=version)
    loaded = runtime.load_dataset()
    results = _check_fixtures(runtime.query_point, fixtures)
    return _summary(loaded, version, loaded.source_vintage, results)
