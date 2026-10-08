"""Bounded passive observations from actual analysis results, per process."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from typing import Any

from services.provider_config_contract import REQUIREMENTS, SOURCES, configuration_status, exact_version

STATUSES = {"available", "partial", "limited", "no_data", "no_match", "unavailable", "error", "unaccepted", "resolved", "unresolved", "demo"}
REASONS = {"success", "partial", "provider_timeout", "provider_error", "provider_rejected", "malformed_response", "provider_query_failed", "provider_unavailable", "configuration_required", "configuration_error", "official_result_available", "official_data_missing", "official_comparables_insufficient", "no_match", "geocoding_unaccepted", "source_unavailable", "source_not_configured", "not_matched_in_loaded_layer", "matched", "route_not_found", "unknown"}
SOURCE_VALUES = set(SOURCES.values()) | {"blue", "green", "google_geocoding", "tgos_geocoding", "google_routes", "google_places", "mock", "postgres", "compact_green", "none", "unknown"}


class ProviderObservations:
    def __init__(self) -> None:
        self._lock = Lock()
        self._results: dict[str, dict[str, Any]] = {}

    def record(self, capability: str, *, status: str, reason_code: str, source: str, dataset_version: str | None = None, freshness: str = "unknown") -> None:
        if capability not in REQUIREMENTS:
            return
        status = status if status in STATUSES else "unavailable"
        now = datetime.now(UTC).isoformat()
        with self._lock:
            previous = self._results.get(capability, {})
            success = status in {"available", "resolved", "no_data", "no_match"} and source not in {"mock", "none", "unknown"}
            self._results[capability] = {"capability": capability, "status": status, "reason_code": reason_code if reason_code in REASONS else "unknown", "source": source if source in SOURCE_VALUES else "unknown", "dataset_version": dataset_version if dataset_version and exact_version(dataset_version) else "unknown", "freshness": freshness if freshness in {"current", "fresh", "stale", "unknown", "unavailable"} else "unknown", "checked_at": now, "last_success": now if success else previous.get("last_success"), "last_failure": previous.get("last_failure") if success else now}

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {capability: dict(value) for capability, value in self._results.items()}


provider_observations = ProviderObservations()


def observe_response(capability: str, result: dict[str, Any]) -> dict[str, Any]:
    """Record a completed response without retaining its property or payload."""
    status_field = {"valuation": "valuation_status", "finder": "search_status", "trend": "trend_status", "market": "data_status"}.get(capability, "status")
    reason_field = {"valuation": "valuation_reason_code", "finder": "search_reason_code", "trend": "trend_reason_code"}.get(capability, "reason_code")
    details = result.get("source_details") or {}
    source = details.get("backend") or result.get("source")
    if not isinstance(source, str):
        source = SOURCES.get(capability, "unknown")
    data_status = result.get("data_status")
    nested_freshness = data_status.get("freshness_status", "unknown") if isinstance(data_status, dict) else "unknown"
    provider_observations.record(capability, status=result.get(status_field, "unavailable"), reason_code=result.get(reason_field, "unknown"), source=source, dataset_version=result.get("dataset_version"), freshness=result.get("freshness_status", nested_freshness))
    return result


def provider_status(environ) -> dict[str, Any]:
    recent = provider_observations.snapshot()
    return {"observation_scope": "process_local", "observation_retention": "last_result_per_capability_until_process_restart", "external_provider_called": False, "capabilities": [{"capability": capability, "configuration": configuration_status(capability, environ), "recent_result": recent.get(capability), "provider_status": "not_checked" if capability not in recent else recent[capability]["status"]} for capability in REQUIREMENTS]}
