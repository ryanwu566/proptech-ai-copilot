"""Allowlisted, privacy-safe first-party performance telemetry validation."""

from __future__ import annotations

from typing import Any


ALLOWED_METRICS = frozenset({"LCP", "CLS", "INP", "TTFB"})
ALLOWED_VIEWPORTS = frozenset({"mobile", "tablet", "desktop"})
ALLOWED_DEVICE_CLASSES = frozenset({"coarse", "unknown"})


def validate_metric_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) - {"metric", "value", "route", "viewport_class", "release_version", "locale", "pilot_mode", "device_class", "sampled"}:
        raise ValueError("unsupported telemetry field")
    metric = str(payload.get("metric", ""))
    if metric not in ALLOWED_METRICS:
        raise ValueError("unsupported telemetry metric")
    value = payload.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0 or value > 120000:
        raise ValueError("telemetry value is out of range")
    route = str(payload.get("route", ""))
    if not route.startswith("/") or len(route) > 120 or "?" in route or "#" in route:
        raise ValueError("telemetry route is invalid")
    viewport = str(payload.get("viewport_class", "unknown"))
    device = str(payload.get("device_class", "unknown"))
    if viewport not in ALLOWED_VIEWPORTS or device not in ALLOWED_DEVICE_CLASSES:
        raise ValueError("telemetry classification is invalid")
    return {"metric": metric, "value": round(float(value), 2), "route": route[:120], "viewport_class": viewport, "release_version": str(payload.get("release_version", "unknown"))[:40], "locale": str(payload.get("locale", "unknown"))[:12], "pilot_mode": str(payload.get("pilot_mode", "normal"))[:40], "device_class": device, "sampled": bool(payload.get("sampled", False))}
