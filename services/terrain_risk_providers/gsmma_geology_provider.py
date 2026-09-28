"""Thin composite preserving independent GSMMA geology-layer semantics."""

from __future__ import annotations

from typing import Any, Iterable

from .base import source_meta, unavailable_layer
from .geologycloud_provider import GeologyCloudProvider
from .gsmma_geological_sensitivity_provider import (
    AGENCY,
    SOURCE_NAME,
    SOURCE_URL,
    GsmmaGeologicalSensitivityProvider,
)


class GsmmaGeologyProvider:
    def __init__(
        self,
        sensitivity_provider: GsmmaGeologicalSensitivityProvider | None = None,
        geologycloud_provider: GeologyCloudProvider | None = None,
    ) -> None:
        self.sensitivity_provider = sensitivity_provider or GsmmaGeologicalSensitivityProvider()
        self.geologycloud_provider = geologycloud_provider or GeologyCloudProvider()

    @staticmethod
    def _placeholder(key: str, label: str) -> dict[str, Any]:
        return unavailable_layer(
            key,
            label,
            source_meta(SOURCE_NAME, AGENCY, SOURCE_URL, "unavailable"),
            "此圖層未在本次複合查詢中啟用。",
        )

    def analyze(
        self,
        latitude: float,
        longitude: float,
        radius_m: int,
        area_hint: str | None = None,
        include_layers: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        requested = set(
            ("geological_sensitivity", "liquefaction", "active_fault")
            if include_layers is None
            else include_layers
        )
        result = {
            "geological_sensitivity": self._placeholder(
                "geological_sensitivity", "地質敏感區"
            ),
            "liquefaction": self._placeholder("liquefaction", "土壤液化潛勢"),
            "active_fault": self._placeholder("active_fault", "活動斷層"),
        }
        cloud_layers = tuple(
            key for key in ("liquefaction", "active_fault") if key in requested
        )
        if cloud_layers:
            try:
                cloud_result = self.geologycloud_provider.analyze(
                    latitude,
                    longitude,
                    radius_m,
                    area_hint=area_hint,
                    include_layers=cloud_layers,
                )
            except Exception:
                for key in cloud_layers:
                    result[key] = {
                        **result[key],
                        "status": "error",
                        "value": {"failure_status": "query_error"},
                    }
            else:
                for key in cloud_layers:
                    if key in cloud_result:
                        result[key] = cloud_result[key]
        if "geological_sensitivity" in requested:
            try:
                result["geological_sensitivity"] = self.sensitivity_provider.analyze(
                    latitude, longitude, radius_m
                )
            except Exception:
                result["geological_sensitivity"] = {
                    **self._placeholder("geological_sensitivity", "地質敏感區"),
                    "status": "error",
                    "explanation": "地質敏感區來源發生未預期錯誤；不得解讀為未命中或安全。",
                }
        return result
