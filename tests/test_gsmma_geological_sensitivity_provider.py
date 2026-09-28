from __future__ import annotations

import pytest

from services.gsmma_geological_sensitivity_runtime import (
    ArtifactInvalidError,
    ChecksumMismatchError,
    CrsInvalidRuntimeError,
    QueryError,
    SourceUnavailableError,
    UnsupportedDatasetRuntimeError,
)
from services.terrain_risk_providers.gsmma_geological_sensitivity_provider import (
    GsmmaGeologicalSensitivityProvider,
)
from services.terrain_risk_providers.gsmma_geology_provider import GsmmaGeologyProvider


VERSION = "2024-06-27"


class FakeRuntime:
    def __init__(self, result=None, error: Exception | None = None, version: str | None = VERSION):
        self.result = result
        self.error = error
        self.version = version
        self.calls = []

    def query_point(self, lon: float, lat: float):
        self.calls.append((lon, lat))
        if self.error:
            raise self.error
        return self.result

    def configured_dataset_version_or_none(self):
        return self.version


def _match_result():
    return {
        "status": "loaded",
        "matched": True,
        "matched_count": 2,
        "matches": [
            {
                "official_category": "活動斷層地質敏感區",
                "canonical_category": "active_fault_sensitive_area",
                "official_name": "測試斷層",
                "sensitivity_area_no": "F0001",
                "announcement_no": "文號1",
                "announcement_date": "2024-06-27",
                "source_agency": "經濟部地質調查及礦業管理中心",
                "source_url": "https://example.gov.tw/1.zip",
                "source_crs": "EPSG:3826",
                "matched_fragment_count": 1,
            },
            {
                "official_category": "山崩與地滑地質敏感區",
                "canonical_category": "landslide_sensitive_area",
                "official_name": "測試山崩區",
                "sensitivity_area_no": "L0001",
                "announcement_no": "文號2",
                "announcement_date": "2024-06-28",
                "source_agency": "經濟部地質調查及礦業管理中心",
                "source_url": "https://example.gov.tw/2.zip",
                "source_crs": "EPSG:3826",
                "matched_fragment_count": 1,
            },
        ],
        "dataset_version": VERSION,
        "artifact_sha256": "a" * 64,
        "source_vintage": "2024-06-27",
    }


def _no_match_result():
    return {
        "status": "no_match",
        "matched": False,
        "matched_count": 0,
        "matches": [],
        "dataset_version": VERSION,
        "artifact_sha256": "a" * 64,
        "source_vintage": "2024-06-27",
    }


def test_matched_provider_preserves_all_evidence_without_severity() -> None:
    runtime = FakeRuntime(_match_result())
    result = GsmmaGeologicalSensitivityProvider(runtime=runtime).analyze(25.0, 121.0, 500)

    assert runtime.calls == [(121.0, 25.0)]
    assert result["key"] == "geological_sensitivity"
    assert result["status"] == "available"
    assert result["matched"] is True
    assert result["level"] == "unknown"
    assert result["distance_m"] == 0
    assert result["value"]["matched_count"] == 2
    assert len(result["value"]["matches"]) == 2
    assert result["source"]["dataset_version"] == VERSION
    assert result["source"]["immutable_artifact_prefix"].endswith(f"/{VERSION}")


def test_true_no_match_is_available_unknown_and_not_safe() -> None:
    result = GsmmaGeologicalSensitivityProvider(runtime=FakeRuntime(_no_match_result())).analyze(
        25.0, 121.0, 500
    )
    assert result["status"] == "available"
    assert result["matched"] is False
    assert result["level"] == "unknown"
    assert "不代表" in result["explanation"]
    assert "低風險" not in result["explanation"]


@pytest.mark.parametrize(
    ("error", "expected_status", "failure_status"),
    [
        (SourceUnavailableError("missing", dataset_version=VERSION), "unavailable", "source_unavailable"),
        (ChecksumMismatchError("bad", dataset_version=VERSION), "error", "checksum_mismatch"),
        (ArtifactInvalidError("bad", dataset_version=VERSION), "error", "artifact_invalid"),
        (UnsupportedDatasetRuntimeError("bad", dataset_version=VERSION), "error", "unsupported_dataset"),
        (CrsInvalidRuntimeError("bad", dataset_version=VERSION), "error", "crs_invalid"),
        (QueryError("bad", dataset_version=VERSION), "error", "query_error"),
    ],
)
def test_runtime_failures_never_become_no_match(error, expected_status: str, failure_status: str) -> None:
    result = GsmmaGeologicalSensitivityProvider(runtime=FakeRuntime(error=error)).analyze(
        25.0, 121.0, 500
    )
    assert result["status"] == expected_status
    assert result["matched"] is False
    assert result["level"] == "unknown"
    assert result["value"]["failure_status"] == failure_status
    assert result["source"]["dataset_version"] == VERSION


class FakeSensitivityProvider:
    def __init__(self, result=None):
        self.result = result or GsmmaGeologicalSensitivityProvider(runtime=FakeRuntime(_no_match_result())).analyze(25, 121, 500)
        self.calls = 0

    def analyze(self, latitude, longitude, radius_m):
        self.calls += 1
        return self.result


class FakeGeologyCloudProvider:
    def __init__(self):
        self.calls = []

    def analyze(self, latitude, longitude, radius_m, area_hint=None, include_layers=None):
        self.calls.append((area_hint, tuple(include_layers or ())))
        return {
            "geological_sensitivity": {"key": "geological_sensitivity", "status": "unavailable"},
            "liquefaction": {
                "key": "liquefaction", "label": "土壤液化潛勢", "status": "available",
                "level": "high", "matched": True, "distance_m": 0, "value": {"official_classification": "高潛勢"},
                "explanation": "existing liquefaction", "source": {"name": "liquefaction"},
            },
            "active_fault": {
                "key": "active_fault", "label": "活動斷層", "status": "unavailable",
                "level": "unknown", "matched": False, "distance_m": None, "value": None,
                "explanation": "existing incomplete path", "source": {"name": "geology cloud"},
            },
        }


class RaisingGeologyCloudProvider:
    def analyze(self, *args, **kwargs):
        raise RuntimeError("cloud unavailable")


def test_composite_routes_sensitivity_without_touching_geologycloud() -> None:
    sensitivity = FakeSensitivityProvider()
    cloud = FakeGeologyCloudProvider()
    result = GsmmaGeologyProvider(sensitivity_provider=sensitivity, geologycloud_provider=cloud).analyze(
        25, 121, 500, include_layers=["geological_sensitivity"]
    )
    assert sensitivity.calls == 1
    assert cloud.calls == []
    assert result["geological_sensitivity"]["status"] == "available"


def test_composite_routes_liquefaction_without_touching_r2_provider() -> None:
    sensitivity = FakeSensitivityProvider()
    cloud = FakeGeologyCloudProvider()
    result = GsmmaGeologyProvider(sensitivity_provider=sensitivity, geologycloud_provider=cloud).analyze(
        25, 121, 500, area_hint="臺北市", include_layers=["liquefaction"]
    )
    assert sensitivity.calls == 0
    assert cloud.calls == [("臺北市", ("liquefaction",))]
    assert result["liquefaction"]["level"] == "high"


def test_composite_keeps_active_fault_on_existing_unavailable_path() -> None:
    cloud = FakeGeologyCloudProvider()
    result = GsmmaGeologyProvider(
        sensitivity_provider=FakeSensitivityProvider(), geologycloud_provider=cloud
    ).analyze(25, 121, 500, include_layers=["active_fault"])
    assert result["active_fault"]["status"] == "unavailable"
    assert result["active_fault"]["level"] == "unknown"
    assert result["active_fault"]["explanation"] == "existing incomplete path"


def test_composite_isolates_sensitivity_failure_from_other_layers() -> None:
    failed = GsmmaGeologicalSensitivityProvider(
        runtime=FakeRuntime(error=ChecksumMismatchError("bad", dataset_version=VERSION))
    ).analyze(25, 121, 500)
    cloud = FakeGeologyCloudProvider()
    result = GsmmaGeologyProvider(
        sensitivity_provider=FakeSensitivityProvider(failed), geologycloud_provider=cloud
    ).analyze(25, 121, 500, area_hint="臺北市")
    assert result["geological_sensitivity"]["status"] == "error"
    assert result["liquefaction"]["status"] == "available"
    assert result["active_fault"]["status"] == "unavailable"


def test_composite_isolates_cloud_failure_from_sensitivity_layer() -> None:
    sensitivity = FakeSensitivityProvider()
    result = GsmmaGeologyProvider(
        sensitivity_provider=sensitivity,
        geologycloud_provider=RaisingGeologyCloudProvider(),
    ).analyze(25, 121, 500)

    assert sensitivity.calls == 1
    assert result["geological_sensitivity"]["status"] == "available"
    assert result["liquefaction"]["status"] == "error"
    assert result["active_fault"]["status"] == "error"
