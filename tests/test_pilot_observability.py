from __future__ import annotations

from services.observability import build_observation, normalize_correlation_id, sanitize_client_error


def test_correlation_id_accepts_bounded_safe_value_and_rejects_header_injection() -> None:
    assert normalize_correlation_id("pilot-abc_123") == "pilot-abc_123"
    generated = normalize_correlation_id("bad value\r\nX-Leak: yes")
    assert len(generated) == 32
    assert "\r" not in generated and "\n" not in generated


def test_observation_allowlist_excludes_secrets_and_raw_payloads() -> None:
    observation = build_observation(correlation_id="pilot-abc_123", route="/pilot/access", method="POST", status_code=503, duration_ms=999999, pilot_mode="closed_pilot", error_code="not-allowlisted")
    assert observation["status_class"] == "5xx"
    assert observation["duration_ms"] == 120000
    assert observation["error_code"] == "client_error"
    assert set(observation) == {"correlation_id", "route", "method", "status_class", "duration_ms", "release_version", "pilot_mode", "environment", "dependency_status", "error_code"}
    assert "token" not in str(observation).lower()


def test_client_error_payload_is_categorical_only() -> None:
    safe = sanitize_client_error("render_failure", "/pilot", "boundary")
    assert safe == {"error_code": "render_failure", "route": "/pilot", "boundary": "boundary"}
