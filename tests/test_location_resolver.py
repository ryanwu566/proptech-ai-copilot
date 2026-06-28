"""Trusted address resolver service tests with fake provider responses."""

from __future__ import annotations

from typing import Any

import httpx

from services.location_resolver import (
    GoogleAddressProvider,
    LocationResolveResult,
    SAFE_RESPONSE_KEYS,
    TgosAddressProvider,
    resolve_address,
)


class FakeProvider:
    def __init__(self, result: LocationResolveResult, configured: bool = True) -> None:
        self.result = result
        self.configured = configured
        self.calls = 0

    def resolve(self, address: str) -> LocationResolveResult:
        self.calls += 1
        assert address == "臺北市信義區市府路1號"
        return self.result


class FakeHttpResponse:
    def __init__(self, payload: dict[str, Any], status_error: bool = False) -> None:
        self.payload = payload
        self.status_error = status_error

    def raise_for_status(self) -> None:
        if self.status_error:
            raise httpx.HTTPStatusError("provider error", request=httpx.Request("GET", "https://example.test"), response=httpx.Response(500))

    def json(self) -> dict[str, Any]:
        return self.payload


def assert_safe_response(result: dict[str, Any]) -> None:
    assert set(result) == SAFE_RESPONSE_KEYS
    serialized = str(result)
    assert "raw" not in serialized
    assert "token" not in serialized
    assert "api_key" not in serialized
    assert "provider error" not in serialized


def test_tgos_success_returns_resolved_without_raw_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.location_resolver.httpx.get",
        lambda *args, **kwargs: FakeHttpResponse(
            {
                "AddressList": [
                    {
                        "FULL_ADDR": "測試格式化地址",
                        "X": "121.56",
                        "Y": "25.03",
                        "provider_secret": "should not leak",
                    }
                ]
            }
        ),
    )
    provider = TgosAddressProvider(app_id="configured", api_key="configured")

    result = provider.resolve("臺北市信義區市府路1號").to_safe_dict()

    assert result["status"] == "resolved"
    assert result["source"] == "tgos"
    assert result["latitude"] == 25.03
    assert result["longitude"] == 121.56
    assert_safe_response(result)


def test_tgos_failure_falls_back_to_google_success() -> None:
    tgos = FakeProvider(LocationResolveResult(status="unavailable"), configured=True)
    google = FakeProvider(
        LocationResolveResult(
            status="resolved",
            source="google",
            formatted_address="測試格式化地址",
            latitude=25.03,
            longitude=121.56,
            confidence="high",
            message="已取得可信位置（Google）。",
        ),
        configured=True,
    )

    result = resolve_address("臺北市信義區市府路1號", tgos_provider=tgos, google_provider=google)

    assert result["status"] == "resolved"
    assert result["source"] == "google"
    assert tgos.calls == 1
    assert google.calls == 1
    assert_safe_response(result)


def test_google_zero_results_is_unresolved(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.location_resolver.httpx.get",
        lambda *args, **kwargs: FakeHttpResponse({"status": "ZERO_RESULTS", "results": []}),
    )
    provider = GoogleAddressProvider(api_key="configured")

    result = provider.resolve("臺北市信義區市府路1號").to_safe_dict()

    assert result["status"] == "unresolved"
    assert result["source"] == "none"
    assert result["latitude"] is None
    assert result["longitude"] is None
    assert_safe_response(result)


def test_google_non_ok_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.location_resolver.httpx.get",
        lambda *args, **kwargs: FakeHttpResponse({"status": "REQUEST_DENIED", "error_message": "secret provider detail"}),
    )
    provider = GoogleAddressProvider(api_key="configured")

    result = provider.resolve("臺北市信義區市府路1號").to_safe_dict()

    assert result["status"] == "unavailable"
    assert "secret provider detail" not in str(result)
    assert_safe_response(result)


def test_google_ok_without_coordinates_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.location_resolver.httpx.get",
        lambda *args, **kwargs: FakeHttpResponse({"status": "OK", "results": [{"geometry": {}}]}),
    )
    provider = GoogleAddressProvider(api_key="configured")

    result = provider.resolve("臺北市信義區市府路1號").to_safe_dict()

    assert result["status"] == "unavailable"
    assert result["latitude"] is None
    assert result["longitude"] is None
    assert_safe_response(result)


def test_all_unconfigured_or_unavailable_is_unavailable() -> None:
    tgos = FakeProvider(LocationResolveResult(status="unavailable"), configured=False)
    google = FakeProvider(LocationResolveResult(status="unavailable"), configured=False)

    result = resolve_address("臺北市信義區市府路1號", tgos_provider=tgos, google_provider=google)

    assert result["status"] == "unavailable"
    assert result["source"] == "none"
    assert tgos.calls == 0
    assert google.calls == 0
    assert_safe_response(result)
