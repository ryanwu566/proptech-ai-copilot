from __future__ import annotations

import pytest

from services.performance_telemetry import validate_metric_payload


def test_performance_telemetry_is_allowlisted_and_bounded() -> None:
    result = validate_metric_payload({"metric": "LCP", "value": 1200, "route": "/", "viewport_class": "mobile", "device_class": "unknown", "sampled": True})
    assert result["metric"] == "LCP"
    assert "address" not in result and "price" not in result and "token" not in result


@pytest.mark.parametrize("payload", [
    {"metric": "SQL", "value": 1, "route": "/"},
    {"metric": "LCP", "value": 1, "route": "/?token=secret"},
    {"metric": "LCP", "value": 1, "route": "/", "viewport_class": "wide"},
])
def test_performance_telemetry_rejects_unsafe_shapes(payload) -> None:
    with pytest.raises(ValueError):
        validate_metric_payload(payload)
