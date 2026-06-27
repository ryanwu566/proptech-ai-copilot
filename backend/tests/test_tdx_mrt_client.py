from __future__ import annotations

import httpx
import pytest

from app.services import tdx_mrt_client
from app.services.tdx_mrt_client import TdxMrtClient, TdxMrtClientError


class MockResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


def test_tdx_client_fetches_token_station_and_line_records_once(monkeypatch) -> None:
    calls: list[str] = []

    def fake_post(url: str, data=None, timeout=None):  # noqa: ANN001, ARG001
        calls.append("token")
        return MockResponse(200, {"access_token": "test-token"})

    def fake_get(url: str, params=None, headers=None, timeout=None):  # noqa: ANN001, ARG001
        assert headers == {"Authorization": "Bearer test-token"}
        assert params == {"$format": "JSON"}
        if url == tdx_mrt_client.TDX_STATION_URL:
            calls.append("station")
            return MockResponse(200, [{"StationUID": "S001"}])
        if url == tdx_mrt_client.TDX_STATION_OF_LINE_URL:
            calls.append("line")
            return MockResponse(200, [{"LineID": "L1"}])
        raise AssertionError("unexpected url")

    monkeypatch.setattr(tdx_mrt_client.httpx, "post", fake_post)
    monkeypatch.setattr(tdx_mrt_client.httpx, "get", fake_get)

    station_records, line_records = TdxMrtClient("client", "secret").fetch_station_and_line_records()

    assert calls == ["token", "station", "line"]
    assert station_records == [{"StationUID": "S001"}]
    assert line_records == [{"LineID": "L1"}]


def test_missing_credentials_fail_before_network(monkeypatch) -> None:
    def fail_post(*args, **kwargs):  # noqa: ANN001, ARG001
        raise AssertionError("network should not be called")

    monkeypatch.setattr(tdx_mrt_client.httpx, "post", fail_post)

    with pytest.raises(TdxMrtClientError) as error:
        TdxMrtClient(None, "secret").fetch_station_and_line_records()

    assert error.value.failure_class == "credentials_unavailable"


def test_authentication_failure_is_classified_without_secret_leak(monkeypatch) -> None:
    def fake_post(url: str, data=None, timeout=None):  # noqa: ANN001, ARG001
        return MockResponse(401, {})

    monkeypatch.setattr(tdx_mrt_client.httpx, "post", fake_post)

    with pytest.raises(TdxMrtClientError) as error:
        TdxMrtClient("client", "secret").fetch_station_and_line_records()

    assert error.value.failure_class == "authentication_failed"
    assert "secret" not in str(error.value)
    assert "client" not in str(error.value)


def test_invalid_token_payload_is_invalid_response(monkeypatch) -> None:
    def fake_post(url: str, data=None, timeout=None):  # noqa: ANN001, ARG001
        return MockResponse(200, {"not_access_token": "missing"})

    monkeypatch.setattr(tdx_mrt_client.httpx, "post", fake_post)

    with pytest.raises(TdxMrtClientError) as error:
        TdxMrtClient("client", "secret").fetch_station_and_line_records()

    assert error.value.failure_class == "invalid_response"


def test_station_response_must_be_list(monkeypatch) -> None:
    def fake_post(url: str, data=None, timeout=None):  # noqa: ANN001, ARG001
        return MockResponse(200, {"access_token": "test-token"})

    def fake_get(url: str, params=None, headers=None, timeout=None):  # noqa: ANN001, ARG001
        return MockResponse(200, {"unexpected": "shape"})

    monkeypatch.setattr(tdx_mrt_client.httpx, "post", fake_post)
    monkeypatch.setattr(tdx_mrt_client.httpx, "get", fake_get)

    with pytest.raises(TdxMrtClientError) as error:
        TdxMrtClient("client", "secret").fetch_station_and_line_records()

    assert error.value.failure_class == "invalid_response"


def test_transport_error_is_service_unavailable(monkeypatch) -> None:
    def fake_post(url: str, data=None, timeout=None):  # noqa: ANN001, ARG001
        raise httpx.ConnectError("connection failed")

    monkeypatch.setattr(tdx_mrt_client.httpx, "post", fake_post)

    with pytest.raises(TdxMrtClientError) as error:
        TdxMrtClient("client", "secret").fetch_station_and_line_records()

    assert error.value.failure_class == "service_unavailable"
