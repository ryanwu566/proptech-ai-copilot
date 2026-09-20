"""Post-routing capture contracts for bounded observability labels."""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import pytest

from backend import api_main
from services import metrics


@pytest.mark.parametrize(
    ("registered_path", "requested_path", "expected_label"),
    (
        ("/health", "/health", "/health"),
        ("/history/{analysis_id}", "/history/987654321", "/history/{param}"),
        (
            "/v1/workspaces/{workspace_id}/context",
            "/v1/workspaces/workspace-sensitive-456/context",
            "/v1/workspaces/{param}/context",
        ),
    ),
)
def test_route_handler_capture_sees_the_resolved_registered_template(
    registered_path: str,
    requested_path: str,
    expected_label: str,
) -> None:
    test_app = FastAPI()

    @test_app.get(registered_path)
    async def captured_label(request: Request) -> dict[str, str]:
        return {"route": metrics.captured_route_label(request.scope)}

    metrics.install_route_label_capture(test_app.routes)

    response = TestClient(test_app).get(requested_path)

    assert response.status_code == 200
    assert response.json() == {"route": expected_label}


def test_metrics_and_request_log_consume_the_same_captured_route_label(
    monkeypatch,
    caplog,
) -> None:
    token = "metrics-scrape-token-with-at-least-32-characters"
    dynamic_id = "987654321"
    query_secret = "owner@example.com"
    expected_label = "/history/{param}"
    client = TestClient(api_main.app)
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", token)
    caplog.set_level(logging.INFO, logger="proptech.observability")

    response = client.get(f"/history/{dynamic_id}?email={query_secret}")
    rendered = client.get(
        "/metrics",
        headers={"X-Metrics-Scrape-Token": token},
    ).text
    completed = [
        json.loads(record.getMessage().split(" ", 1)[1])
        for record in caplog.records
        if record.name == "proptech.observability"
        and record.getMessage().startswith("request_completed ")
    ]

    assert response.status_code == 404
    assert completed[-1]["route"] == expected_label
    assert f'route="{completed[-1]["route"]}"' in rendered
    assert dynamic_id not in rendered
    assert query_secret not in rendered


def test_nested_vnext_route_keeps_inherited_prefix_in_metrics_and_log(
    monkeypatch,
    caplog,
) -> None:
    token = "metrics-scrape-token-with-at-least-32-characters"
    property_id = "00000000-0000-0000-0000-000000000001"
    expected_label = "/v1/properties/{param}"
    client = TestClient(api_main.app)
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", token)
    caplog.set_level(logging.INFO, logger="proptech.observability")

    response = client.get(f"/v1/properties/{property_id}")
    rendered = client.get(
        "/metrics",
        headers={"X-Metrics-Scrape-Token": token},
    ).text
    completed = [
        json.loads(record.getMessage().split(" ", 1)[1])
        for record in caplog.records
        if record.name == "proptech.observability"
        and record.getMessage().startswith("request_completed ")
    ]

    assert response.status_code == 401
    assert completed[-1]["route"] == expected_label
    assert f'route="{expected_label}"' in rendered
    assert property_id not in rendered
