"""Shared helpers for terrain risk provider adapters."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


ProviderResult = dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_meta(
    name: str,
    agency: str,
    source_url: str,
    status: str,
    data_updated_at: str | None = None,
    **extra: str,
) -> dict[str, str]:
    payload = {
        "name": name,
        "agency": agency,
        "source_url": source_url,
        "fetched_at": utc_now(),
        "status": status,
    }
    if data_updated_at:
        payload["data_updated_at"] = data_updated_at
    payload.update(extra)
    return payload


def unavailable_layer(key: str, label: str, source: dict[str, str], explanation: str) -> ProviderResult:
    return {
        "key": key,
        "label": label,
        "status": "unavailable",
        "level": "unknown",
        "matched": False,
        "distance_m": None,
        "value": None,
        "explanation": explanation,
        "source": source,
    }
