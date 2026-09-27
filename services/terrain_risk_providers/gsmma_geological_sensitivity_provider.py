"""Terrain Risk adapter for immutable GSMMA geological-sensitivity evidence."""

from __future__ import annotations

from typing import Any

from services.gsmma_geological_sensitivity_runtime import (
    RELEASE_PREFIX,
    ArtifactInvalidError,
    ChecksumMismatchError,
    CrsInvalidRuntimeError,
    GeologicalSensitivityRuntimeError,
    GsmmaGeologicalSensitivityRuntime,
    QueryError,
    SourceUnavailableError,
    UnsupportedDatasetRuntimeError,
    get_runtime,
)

from .base import source_meta


SOURCE_URL = "https://data.gov.tw/dataset/27744"
SOURCE_NAME = "地質敏感區範圍數值檔"
AGENCY = "經濟部地質調查及礦業管理中心"


class GsmmaGeologicalSensitivityProvider:
    source_url = SOURCE_URL

    def __init__(self, runtime: GsmmaGeologicalSensitivityRuntime | None = None) -> None:
        self.runtime = runtime or get_runtime()

    def _configured_version(self, error: Exception | None = None) -> str:
        if isinstance(error, GeologicalSensitivityRuntimeError) and error.dataset_version:
            return error.dataset_version
        try:
            value = self.runtime.configured_dataset_version_or_none()
        except Exception:
            value = None
        return value or "not_configured"

    def _source(
        self,
        status: str,
        *,
        dataset_version: str,
        artifact_sha256: str | None = None,
        source_vintage: str | None = None,
        failure_status: str | None = None,
    ) -> dict[str, str]:
        extra = {
            "dataset_version": dataset_version,
            "immutable_artifact_prefix": f"{RELEASE_PREFIX}/{dataset_version}",
            "coverage_limitation": "僅涵蓋已載入版本中的官方公告地質敏感區多邊形，不是全國連續地質風險分類。",
        }
        if artifact_sha256:
            extra["artifact_sha256"] = artifact_sha256
        if source_vintage:
            extra["data_vintage"] = source_vintage
        if failure_status:
            extra["failure_status"] = failure_status
        return source_meta(SOURCE_NAME, AGENCY, SOURCE_URL, status, **extra)

    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict[str, Any]:
        del radius_m  # The official operation is exact point intersection.
        try:
            result = self.runtime.query_point(longitude, latitude)
            version = result["dataset_version"]
            source = self._source(
                "available",
                dataset_version=version,
                artifact_sha256=result.get("artifact_sha256"),
                source_vintage=result.get("source_vintage"),
            )
            if result.get("matched"):
                matches = result.get("matches")
                if not isinstance(matches, list) or not matches:
                    raise ArtifactInvalidError(
                        "matched runtime result contains no evidence", dataset_version=version
                    )
                explanation = (
                    f"此座標交集 {len(matches)} 項官方公告地質敏感區；"
                    "命中表示位於公告範圍內，不代表高、中或低地質風險分級。"
                )
                distance_m = 0
            else:
                matches = []
                explanation = (
                    "此座標未與已載入版本的官方公告地質敏感區多邊形相交；"
                    "這不代表地質安全，也不代表沒有其他地質災害。"
                )
                distance_m = None
            return {
                "key": "geological_sensitivity",
                "label": "地質敏感區",
                "status": "available",
                "level": "unknown",
                "matched": bool(result.get("matched")),
                "distance_m": distance_m,
                "value": {
                    "dataset_version": version,
                    "artifact_sha256": result.get("artifact_sha256"),
                    "source_vintage": result.get("source_vintage"),
                    "matched_count": len(matches),
                    "matches": matches,
                },
                "explanation": explanation,
                "source": source,
            }
        except SourceUnavailableError as exc:
            return self._failure("unavailable", exc)
        except (
            ChecksumMismatchError,
            ArtifactInvalidError,
            UnsupportedDatasetRuntimeError,
            CrsInvalidRuntimeError,
            QueryError,
        ) as exc:
            return self._failure("error", exc)
        except Exception as exc:
            wrapped = ArtifactInvalidError(
                f"unexpected geological-sensitivity provider failure: {type(exc).__name__}",
                dataset_version=self._configured_version(),
            )
            return self._failure("error", wrapped)

    def _failure(self, status: str, error: GeologicalSensitivityRuntimeError) -> dict[str, Any]:
        version = self._configured_version(error)
        source = self._source(
            status,
            dataset_version=version,
            failure_status=error.status,
        )
        return {
            "key": "geological_sensitivity",
            "label": "地質敏感區",
            "status": status,
            "level": "unknown",
            "matched": False,
            "distance_m": None,
            "value": {
                "dataset_version": version,
                "matched_count": 0,
                "matches": [],
                "failure_status": error.status,
            },
            "explanation": (
                "官方地質敏感區證據目前無法完成驗證或查詢；"
                "此失敗不得解讀為未命中、地質安全或沒有地質風險。"
            ),
            "source": source,
        }
