"""Deterministic TGOS adapter behavior and secret-boundary tests."""

from __future__ import annotations

import json

import httpx

from services.adapters.tgos_geocoding_adapter import TGOS_URL, TgosGeocodingAdapter


VALID_PAYLOAD = {
    "AddressList": [
        {
            "FULL_ADDR": "臺北市信義區市府路1號",
            "COUNTY": "臺北市",
            "TOWN": "信義區",
            "ROAD": "市府路1號",
            "X": "121.5645",
            "Y": "25.0375",
        }
    ]
}


class FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.request = httpx.Request("GET", TGOS_URL)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            response = httpx.Response(self.status_code, request=self.request)
            raise httpx.HTTPStatusError("TGOS request failed", request=self.request, response=response)

    def json(self) -> object:
        return self.payload


class FakeClient:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, object]] = []
        self.closed = False

    def get(self, url: str, *, params: dict[str, str]) -> FakeResponse:
        self.calls.append({"url": url, "params": params})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome  # type: ignore[return-value]

    def close(self) -> None:
        self.closed = True


def adapter_with(outcome: object) -> tuple[TgosGeocodingAdapter, FakeClient]:
    client = FakeClient([outcome])
    return TgosGeocodingAdapter(app_id="backend-app", api_key="backend-key", client=client), client  # type: ignore[arg-type]


def test_tgos_without_credentials_skips_request() -> None:
    client = FakeClient([FakeResponse(VALID_PAYLOAD)])
    adapter = TgosGeocodingAdapter(app_id="", api_key="", client=client)  # type: ignore[arg-type]

    assert adapter.available is False
    assert adapter.search("台北101", []) is None
    assert client.calls == []
    assert "backend-key" not in adapter.last_error


def test_tgos_empty_query_skips_request() -> None:
    adapter, client = adapter_with(FakeResponse(VALID_PAYLOAD))

    assert adapter.search(" \n\t ", []) is None
    assert client.calls == []
    assert adapter.last_error == "TGOS query is empty"


def test_tgos_timeout_is_safe() -> None:
    adapter, _ = adapter_with(httpx.TimeoutException("request timed out"))

    assert adapter.search("臺北市信義區市府路1號", []) is None
    assert adapter.last_error == "TGOS 暫時無法回應"


def test_tgos_http_error_is_safe() -> None:
    adapter, _ = adapter_with(FakeResponse({}, status_code=503))

    assert adapter.search("臺北市信義區市府路1號", []) is None
    assert adapter.last_error == "TGOS 暫時無法取得定位結果"


def test_tgos_empty_address_list_is_unavailable() -> None:
    adapter, _ = adapter_with(FakeResponse({"AddressList": []}))

    assert adapter.search("臺北市信義區市府路1號", []) is None
    assert adapter.last_error == "TGOS 暫時無法取得定位結果"


def test_tgos_rejects_bad_nan_and_swapped_coordinates() -> None:
    for longitude, latitude in (("nan", "25.0375"), ("25.0375", "121.5645"), ("121.5645", "90")):
        payload = {"AddressList": [{**VALID_PAYLOAD["AddressList"][0], "X": longitude, "Y": latitude}]}
        adapter, _ = adapter_with(FakeResponse(payload))
        assert adapter.search("臺北市信義區市府路1號", []) is None
        assert adapter.last_error == "TGOS 暫時無法取得定位結果"


def test_tgos_valid_response_is_normalized_and_credentials_do_not_leak() -> None:
    adapter, client = adapter_with(FakeResponse(VALID_PAYLOAD))

    result = adapter.search("臺北市信義區市府路1號", [])

    assert result is not None
    assert result["formatted_address"] == "臺北市信義區市府路1號"
    assert result["center"] == {"lat": 25.0375, "lng": 121.5645}
    assert result["city"] == "臺北市"
    assert result["district"] == "信義區"
    assert client.calls[0]["url"] == TGOS_URL
    serialized = json.dumps(result, ensure_ascii=False)
    assert "backend-app" not in serialized
    assert "backend-key" not in serialized
    assert adapter.last_error == ""


def test_tgos_reuses_one_owned_client_and_closes_it(monkeypatch) -> None:
    client = FakeClient([FakeResponse(VALID_PAYLOAD), FakeResponse(VALID_PAYLOAD)])
    created: list[FakeClient] = []

    def client_factory(*args, **kwargs):
        created.append(client)
        return client

    monkeypatch.setattr("services.adapters.tgos_geocoding_adapter.httpx.Client", client_factory)
    adapter = TgosGeocodingAdapter(app_id="backend-app", api_key="backend-key")

    assert adapter.search("臺北市信義區市府路1號", []) is not None
    assert adapter.search("臺北市信義區市府路1號", []) is not None
    assert created == [client]
    assert len(client.calls) == 2

    adapter.close()
    assert client.closed is True


def test_tgos_does_not_close_injected_client() -> None:
    adapter, client = adapter_with(FakeResponse(VALID_PAYLOAD))

    adapter.close()

    assert client.closed is False
