"""TDX MRT client tests with fake HTTP only."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from services.tdx_mrt_client import TdxMrtClient, TdxMrtClientError


class FakeResponse:
    def __init__(self, payload: Any, *, fail: bool = False) -> None:
        self.payload = payload
        self.fail = fail

    def raise_for_status(self) -> None:
        if self.fail:
            raise httpx.HTTPStatusError("raw provider detail", request=httpx.Request("GET", "https://example.test"), response=httpx.Response(500))

    def json(self) -> Any:
        return self.payload


def test_client_fetches_token_then_station_and_line_payload(monkeypatch) -> None:
    posts: list[dict[str, Any]] = []
    gets: list[dict[str, Any]] = []

    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:
        posts.append(kwargs)
        return FakeResponse({"access_token": "fake-access-token"})

    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:
        gets.append(kwargs)
        if len(gets) == 1:
            return FakeResponse([{"StationUID": "ST-A"}])
        return FakeResponse([{"LineID": "L1", "Stations": [{"StationUID": "ST-A"}]}])

    monkeypatch.setattr("services.tdx_mrt_client.httpx.post", fake_post)
    monkeypatch.setattr("services.tdx_mrt_client.httpx.get", fake_get)

    payload = TdxMrtClient(client_id="configured", client_secret="configured").refresh_payload()

    assert payload.station_records == [{"StationUID": "ST-A"}]
    assert payload.line_records == [{"LineID": "L1", "Stations": [{"StationUID": "ST-A"}]}]
    assert len(posts) == 1
    assert len(gets) == 2
    assert "fake-access-token" in gets[0]["headers"]["authorization"]


def test_client_requires_credentials() -> None:
    with pytest.raises(TdxMrtClientError) as exc:
        TdxMrtClient(client_id="", client_secret="").refresh_payload()

    assert "credential" in str(exc.value).lower()
    assert "token" not in str(exc.value).lower()


def test_client_sanitizes_provider_errors(monkeypatch) -> None:
    monkeypatch.setattr("services.tdx_mrt_client.httpx.post", lambda *args, **kwargs: FakeResponse({"error": "raw secret detail"}, fail=True))

    with pytest.raises(TdxMrtClientError) as exc:
        TdxMrtClient(client_id="configured", client_secret="configured").refresh_payload()

    assert "raw provider detail" not in str(exc.value)
    assert "raw secret detail" not in str(exc.value)


def test_client_rejects_unexpected_payload_shape(monkeypatch) -> None:
    monkeypatch.setattr("services.tdx_mrt_client.httpx.post", lambda *args, **kwargs: FakeResponse({"access_token": "fake-access-token"}))
    monkeypatch.setattr("services.tdx_mrt_client.httpx.get", lambda *args, **kwargs: FakeResponse({"unexpected": "shape"}))

    with pytest.raises(TdxMrtClientError) as exc:
        TdxMrtClient(client_id="configured", client_secret="configured").refresh_payload()

    assert "payload" in str(exc.value)
