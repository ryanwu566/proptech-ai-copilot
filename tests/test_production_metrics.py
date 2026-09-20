"""Production metrics security and cardinality contracts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import logging
import re

from fastapi.testclient import TestClient
import pytest

from backend.api_main import app
from services.metrics import BoundedMetricsRegistry
from services.production_config import (
    assert_startup_configuration,
    load_runtime_configuration,
)


client = TestClient(app)
SCRAPE_TOKEN = "metrics-scrape-token-with-at-least-32-characters"


def _valid_production_environment() -> dict[str, str]:
    return {
        "APP_ENV": "production",
        "APP_RUNTIME": "standard",
        "DATABASE_URL": "postgresql://db.example.invalid/app",
        "PILOT_SESSION_SIGNING_KEY": "s" * 32,
        "CORS_ALLOWED_ORIGINS": "https://frontend.example.invalid",
        "PUBLIC_APP_BASE_URL": "https://frontend.example.invalid",
    }


def _sample_value(rendered: str, sample: str) -> float:
    for line in rendered.splitlines():
        if line.startswith(sample + " "):
            return float(line.rsplit(" ", 1)[1])
    return 0.0


def _scrape(token: str = SCRAPE_TOKEN):
    return client.get("/metrics", headers={"X-Metrics-Scrape-Token": token})


def test_registry_records_request_total_and_status_class() -> None:
    registry = BoundedMetricsRegistry({"/health"})

    registry.observe_http_request(
        method="GET",
        route_template="/health",
        status_code=204,
        duration_seconds=0.01,
    )

    assert (
        'proptech_http_requests_total{method="GET",route="/health",status_class="2xx"} 1'
        in registry.render_prometheus()
    )


def test_registry_records_dedicated_429_and_5xx_totals() -> None:
    registry = BoundedMetricsRegistry({"/limited", "/failed"})

    registry.observe_http_request(
        method="POST",
        route_template="/limited",
        status_code=429,
        duration_seconds=0.02,
    )
    registry.observe_http_request(
        method="GET",
        route_template="/failed",
        status_code=503,
        duration_seconds=0.03,
    )

    rendered = registry.render_prometheus()
    assert "proptech_http_responses_429_total 1" in rendered
    assert "proptech_http_responses_5xx_total 1" in rendered


def test_registry_records_request_latency_in_fixed_buckets() -> None:
    registry = BoundedMetricsRegistry({"/slow"})

    registry.observe_http_request(
        method="GET",
        route_template="/slow",
        status_code=200,
        duration_seconds=0.2,
    )

    rendered = registry.render_prometheus()
    assert (
        'proptech_http_request_duration_seconds_bucket{method="GET",route="/slow",le="0.25"} 1'
        in rendered
    )
    assert (
        'proptech_http_request_duration_seconds_count{method="GET",route="/slow"} 1'
        in rendered
    )
    assert re.search(
        r'proptech_http_request_duration_seconds_sum\{method="GET",route="/slow"\} 0\.2(?:0+)?$',
        rendered,
        re.MULTILINE,
    )


def test_registry_collapses_unregistered_paths_and_dynamic_ids() -> None:
    registry = BoundedMetricsRegistry(
        {"/v1/workspaces/{workspace_id}/properties/{property_id}"}
    )
    sensitive_values = (
        "/v1/workspaces/workspace-secret/properties/property-secret",
        "/unknown/user-123?email=owner@example.com",
        "/coordinates/25.033/121.5654",
    )

    registry.observe_http_request(
        method="GET",
        route_template="/v1/workspaces/{workspace_id}/properties/{property_id}",
        status_code=200,
        duration_seconds=0.01,
    )
    for index in range(1000):
        registry.observe_http_request(
            method=f"CUSTOM-{index}",
            route_template=sensitive_values[index % len(sensitive_values)],
            status_code=799,
            duration_seconds=0.01,
        )

    rendered = registry.render_prometheus()
    route_labels = set(re.findall(r'route="([^"]+)"', rendered))
    method_labels = set(re.findall(r'method="([^"]+)"', rendered))
    status_labels = set(re.findall(r'status_class="([^"]+)"', rendered))
    assert route_labels == {
        "/v1/workspaces/{param}/properties/{param}",
        "/__unmatched__",
    }
    assert method_labels == {"GET", "OTHER"}
    assert status_labels == {"2xx", "other"}
    for value in (
        "workspace-secret",
        "property-secret",
        "user-123",
        "owner@example.com",
        "25.033",
        "121.5654",
        "?",
    ):
        assert value not in rendered


def test_registry_observe_and_render_are_safe_under_concurrency() -> None:
    registry = BoundedMetricsRegistry({"/health"})

    def write_batch() -> None:
        for _ in range(250):
            registry.observe_http_request(
                method="GET",
                route_template="/health",
                status_code=200,
                duration_seconds=0.01,
            )

    def render_batch() -> None:
        for _ in range(50):
            rendered = registry.render_prometheus()
            assert "proptech_http_requests_total" in rendered

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(write_batch) for _ in range(8)]
        futures.extend(pool.submit(render_batch) for _ in range(8))
        for future in futures:
            future.result(timeout=10)

    rendered = registry.render_prometheus()
    assert _sample_value(
        rendered,
        'proptech_http_requests_total{method="GET",route="/health",status_class="2xx"}',
    ) == 2000
    assert _sample_value(
        rendered,
        'proptech_http_request_duration_seconds_count{method="GET",route="/health"}',
    ) == 2000


def test_metrics_endpoint_is_hidden_when_scrape_token_is_not_configured(
    monkeypatch,
) -> None:
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    assert _scrape().status_code == 200
    monkeypatch.delenv("METRICS_SCRAPE_TOKEN", raising=False)

    response = _scrape()

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_metrics_endpoint_rejects_missing_request_token_with_generic_404(
    monkeypatch,
) -> None:
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    assert _scrape().status_code == 200

    response = client.get("/metrics")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_metrics_endpoint_rejects_wrong_token_without_reflection(
    monkeypatch,
    caplog,
) -> None:
    wrong_token = "wrong-token-that-must-never-be-reflected"
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    caplog.set_level(logging.INFO, logger="proptech.observability")
    assert _scrape().status_code == 200

    response = _scrape(wrong_token)

    captured_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
    assert wrong_token not in response.text
    assert wrong_token not in captured_logs
    assert SCRAPE_TOKEN not in response.text
    assert SCRAPE_TOKEN not in captured_logs


def test_all_denied_scrape_cases_have_the_same_external_response(monkeypatch) -> None:
    denied_responses = []

    monkeypatch.delenv("METRICS_SCRAPE_TOKEN", raising=False)
    denied_responses.append(_scrape())

    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    denied_responses.append(client.get("/metrics"))
    denied_responses.append(_scrape("x" * 32))

    observable_responses = {
        (
            response.status_code,
            response.content,
            response.headers.get("content-type"),
        )
        for response in denied_responses
    }
    assert observable_responses == {
        (404, b'{"detail":"Not Found"}', "application/json")
    }


def test_metrics_endpoint_uses_constant_time_token_comparison(monkeypatch) -> None:
    from backend.api import routes_metrics

    wrong_token = "x" * 32
    comparisons: list[tuple[str, str]] = []

    def reject(provided: str, expected: str) -> bool:
        comparisons.append((provided, expected))
        return False

    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    monkeypatch.setattr(routes_metrics.secrets, "compare_digest", reject)

    response = _scrape(wrong_token)

    assert response.status_code == 404
    assert comparisons == [(wrong_token, SCRAPE_TOKEN)]


def test_metrics_endpoint_accepts_correct_token(monkeypatch) -> None:
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)

    response = _scrape()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "proptech_http_requests_total" in response.text
    assert SCRAPE_TOKEN not in response.text


def test_http_request_count_increments(monkeypatch) -> None:
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    sample = (
        'proptech_http_requests_total{method="GET",route="/health",'
        'status_class="2xx"}'
    )
    before = _sample_value(_scrape().text, sample)

    response = client.get("/health")

    after = _sample_value(_scrape().text, sample)
    assert response.status_code == 200
    assert after == before + 1


def test_http_429_count_increments(monkeypatch) -> None:
    from backend.api import routes_performance

    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    routes_performance._buckets.clear()
    before = _sample_value(
        _scrape().text, "proptech_http_responses_429_total"
    )
    payload = {
        "metric": "LCP",
        "value": 1,
        "route": "/",
        "viewport_class": "mobile",
        "device_class": "unknown",
    }

    try:
        for _ in range(60):
            assert client.post("/performance/metrics", json=payload).status_code == 202
        limited = client.post("/performance/metrics", json=payload)
    finally:
        routes_performance._buckets.clear()

    after = _sample_value(_scrape().text, "proptech_http_responses_429_total")
    assert limited.status_code == 429
    assert after == before + 1


def test_http_5xx_count_increments_without_exception_text(
    monkeypatch,
    caplog,
) -> None:
    from backend.api import routes_loan_calculator

    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    exception_text = "private-exception owner@example.com property-123"

    def fail_calculation(**_kwargs):
        raise RuntimeError(exception_text)

    monkeypatch.setattr(routes_loan_calculator, "calculate_loan", fail_calculation)
    caplog.set_level(logging.WARNING, logger="proptech.observability")
    before = _sample_value(
        _scrape().text, "proptech_http_responses_5xx_total"
    )

    response = client.post("/loan/calculate", json={"property_price": 10_000_000})

    rendered = _scrape().text
    after = _sample_value(rendered, "proptech_http_responses_5xx_total")
    captured_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert response.status_code == 500
    assert after == before + 1
    assert exception_text not in response.text
    assert exception_text not in rendered
    assert exception_text not in captured_logs


def test_http_request_latency_is_recorded(monkeypatch) -> None:
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    sample = (
        'proptech_http_request_duration_seconds_count{method="GET",route="/health"}'
    )
    before = _sample_value(_scrape().text, sample)

    client.get("/health")

    after = _sample_value(_scrape().text, sample)
    assert after == before + 1


def test_body_limit_early_response_is_counted_as_unmatched(monkeypatch) -> None:
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    sample = (
        'proptech_http_requests_total{method="POST",route="/__unmatched__",'
        'status_class="4xx"}'
    )
    before = _sample_value(_scrape().text, sample)

    response = client.post(
        "/loan/calculate",
        content=b"",
        headers={"Content-Length": "1000001"},
    )

    after = _sample_value(_scrape().text, sample)
    assert response.status_code == 413
    assert after == before + 1


def test_rejected_origin_early_response_is_counted_as_unmatched(monkeypatch) -> None:
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    sample = (
        'proptech_http_requests_total{method="POST",route="/__unmatched__",'
        'status_class="4xx"}'
    )
    before = _sample_value(_scrape().text, sample)

    response = client.post(
        "/loan/calculate",
        json={"property_price": 10_000_000},
        headers={"Origin": "https://attacker.invalid"},
    )

    after = _sample_value(_scrape().text, sample)
    assert response.status_code == 403
    assert after == before + 1


def test_maintenance_early_response_is_counted_as_unmatched(monkeypatch) -> None:
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    monkeypatch.setenv("MAINTENANCE_MODE", "true")
    sample = (
        'proptech_http_requests_total{method="POST",route="/__unmatched__",'
        'status_class="5xx"}'
    )
    before = _sample_value(_scrape().text, sample)

    response = client.post(
        "/loan/calculate",
        json={"property_price": 10_000_000},
    )

    after = _sample_value(_scrape().text, sample)
    assert response.status_code == 503
    assert after == before + 1


def test_cors_preflight_response_is_counted_as_unmatched(monkeypatch) -> None:
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    sample = (
        'proptech_http_requests_total{method="OPTIONS",route="/__unmatched__",'
        'status_class="2xx"}'
    )
    before = _sample_value(_scrape().text, sample)

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    after = _sample_value(_scrape().text, sample)
    assert response.status_code == 200
    assert after == before + 1


def test_route_labels_use_templates_and_exclude_ids_and_queries(
    monkeypatch,
    caplog,
) -> None:
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    dynamic_id = "987654321"
    query_secret = "owner@example.com"
    caplog.set_level(logging.INFO, logger="proptech.observability")

    templated = client.get(f"/history/{dynamic_id}?email={query_secret}")
    unmatched = client.get(f"/not-a-route/{dynamic_id}?email={query_secret}")

    rendered = _scrape().text
    captured_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert templated.status_code == 404
    assert unmatched.status_code == 404
    assert 'route="/history/{param}"' in rendered
    assert 'route="/__unmatched__"' in rendered
    for value in (dynamic_id, query_secret, "?email="):
        assert value not in rendered
        assert value not in captured_logs


def test_health_response_stays_value_free(monkeypatch) -> None:
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)

    payload = client.get("/health").json()
    serialized = json.dumps(payload, sort_keys=True)

    assert SCRAPE_TOKEN not in serialized
    assert "metrics_scrape_token" not in serialized


def test_metrics_and_request_log_exclude_secret_and_pii_values(
    monkeypatch,
    caplog,
) -> None:
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", SCRAPE_TOKEN)
    sensitive_values = {
        "authorization": "authorization-secret-123",
        "cookie": "session-cookie-secret-456",
        "jwt": "eyJhbGciOiJIUzI1NiJ9.secret.signature",
        "api_key": "api-key-secret-789",
        "email": "owner@example.com",
        "user_id": "user-sensitive-123",
        "workspace_id": "workspace-sensitive-456",
        "property_id": "property-sensitive-789",
        "address": "100 Sensitive Address Road",
        "latitude": "25.033000",
        "longitude": "121.565400",
    }
    caplog.set_level(logging.INFO, logger="proptech.observability")
    response = client.get(
        f'/v1/workspaces/{sensitive_values["workspace_id"]}/context',
        params={
            "email": sensitive_values["email"],
            "user": sensitive_values["user_id"],
            "property": sensitive_values["property_id"],
            "address": sensitive_values["address"],
            "lat": sensitive_values["latitude"],
            "lng": sensitive_values["longitude"],
        },
        headers={
            "Authorization": (
                f'Bearer {sensitive_values["authorization"]}.'
                f'{sensitive_values["jwt"]}'
            ),
            "Cookie": f'session={sensitive_values["cookie"]}',
            "X-API-Key": sensitive_values["api_key"],
        },
    )

    rendered = _scrape().text
    request_logs = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name == "proptech.observability"
    )
    combined = "\n".join((response.text, rendered, request_logs))
    assert 'route="/v1/workspaces/{param}/context"' in rendered
    for value in sensitive_values.values():
        assert value not in combined


def test_production_allows_an_absent_scrape_token_as_disabled() -> None:
    config = assert_startup_configuration(_valid_production_environment())

    assert config.ready is True
    assert config.metrics_scrape_token_status == "not_configured"


def test_production_rejects_a_malformed_configured_scrape_token() -> None:
    values = {
        **_valid_production_environment(),
        "METRICS_SCRAPE_TOKEN": "too-short",
    }

    with pytest.raises(
        RuntimeError,
        match="Required production configuration is unavailable",
    ):
        assert_startup_configuration(values)


def test_production_reports_scrape_token_status_without_its_value() -> None:
    values = {
        **_valid_production_environment(),
        "METRICS_SCRAPE_TOKEN": SCRAPE_TOKEN,
    }

    config = load_runtime_configuration(values)
    serialized = json.dumps(config.safe_report(), sort_keys=True)

    assert config.metrics_scrape_token_status == "configured"
    assert SCRAPE_TOKEN not in serialized
