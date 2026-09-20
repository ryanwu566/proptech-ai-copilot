"""Offline contract tests for the TEST-only NLSC TILE_001 seam."""

from __future__ import annotations

import base64
import gzip
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest


FIXTURES = Path(__file__).parent / "fixtures" / "nlsc"
NOW = datetime(2026, 9, 20, 9, 15, tzinfo=timezone.utc)
TOKEN = "backend-only-tile-client-token-123"
GATEWAY_ORIGIN = "https://gateway.example.tw"
ALLOWLIST_ENV = "NLSC_TILE001_TEST_GATEWAY_ORIGINS"
CONFIG = {
    "APP_ENV": "test",
    "NLSC_GATEWAY_BASE_URL": GATEWAY_ORIGIN,
    "NLSC_GATEWAY_CLIENT_TOKEN": TOKEN,
    ALLOWLIST_ENV: GATEWAY_ORIGIN,
}


def _adapter_class():
    from services.adapters.nlsc_tile_gateway_adapter import NlscTileGatewayAdapter

    return NlscTileGatewayAdapter


def _fixture(name: str = "tile_001_transparent_256.png.b64") -> bytes:
    encoded = (FIXTURES / name).read_text(encoding="ascii").strip()
    return base64.b64decode(encoded, validate=True)


def _client(handler, *, follow_redirects: bool = False):
    requests: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    return (
        httpx.Client(
            transport=httpx.MockTransport(record),
            follow_redirects=follow_redirects,
        ),
        requests,
    )


class _ChunkStream(httpx.SyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks
        self.yielded = 0
        self.closed = False

    def __iter__(self):
        for chunk in self._chunks:
            self.yielded += 1
            yield chunk

    def close(self) -> None:
        self.closed = True


def _png_response(
    payload: bytes | None = None,
    *,
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    selected_headers = {"Content-Type": "image/png"}
    if headers:
        selected_headers.update(headers)
    return httpx.Response(
        status,
        content=_fixture() if payload is None else payload,
        headers=selected_headers,
    )


def test_tile_001_uses_one_fixed_gateway_operation_and_normalizes_only_documented_metadata() -> None:
    client, requests = _client(lambda _request: _png_response())
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).fetch_tile(z=19, x=524287, y=0)

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert str(request.url) == (
        "https://gateway.example.tw/nlsc/tiles/TILE_001/19/0/524287"
    )
    assert request.headers["authorization"] == f"Bearer {TOKEN}"
    assert request.headers["accept"] == "image/png"
    assert request.headers["accept-encoding"] == "identity"
    assert request.headers["cache-control"] == "no-store"
    assert request.extensions["timeout"]["read"] == 4.0
    assert result.status == "available"
    assert result.content == _fixture()
    assert "content=" not in repr(result)
    assert result.error_code is None
    assert result.policy.cache_control == "no-store"
    assert result.policy.store is False
    assert result.policy.semantic_scope == "reference_imagery_only"
    assert asdict(result.observation) == {
        "source": "NLSC",
        "service_code": "TILE_001",
        "retrieved_at": "2026-09-20T09:15:00+00:00",
        "crs": "EPSG:3857",
        "layer": "DMAPS",
        "z": 19,
        "x": 524287,
        "y": 0,
        "content_type": "image/png",
        "attribution": "內政部國土測繪中心－國土測繪圖資服務雲",
        "notice": (
            "Reference imagery only. Blank or nonblank imagery does not establish "
            "parcel existence, parcel absence, a legal boundary, or current cadastral truth."
        ),
        "coverage": "unknown",
    }


@pytest.mark.parametrize(
    ("z", "x", "y"),
    [
        (-1, 0, 0),
        (20, 0, 0),
        (True, 0, 0),
        (1.0, 0, 0),
        ("1", 0, 0),
        (0, -1, 0),
        (0, 0, -1),
        (0, 1, 0),
        (0, 0, 1),
        (1, 2, 0),
        (1, 0, 2),
        (1, True, 0),
        (1, 0, False),
        (19, 524288, 0),
        (19, 0, 524288),
    ],
)
def test_invalid_tile_coordinates_are_rejected_before_egress(
    z: object,
    x: object,
    y: object,
) -> None:
    client, requests = _client(lambda _request: _png_response())
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).fetch_tile(z=z, x=x, y=y)

    assert result.status == "unavailable"
    assert result.error_code == "invalid_input"
    assert result.observation is None
    assert result.content is None
    assert requests == []


@pytest.mark.parametrize(
    "base_url",
    [
        "https://maps.nlsc.gov.tw",
        "https://wmts.nlsc.gov.tw",
        "https://api.nlsc.gov.tw",
    ],
)
def test_direct_nlsc_origins_are_rejected_even_when_listed(base_url: str) -> None:
    client, requests = _client(lambda _request: _png_response())
    with client:
        adapter = _adapter_class()(
            client=client,
            environ={
                **CONFIG,
                "NLSC_GATEWAY_BASE_URL": base_url,
                ALLOWLIST_ENV: base_url,
            },
            clock=lambda: NOW,
        )
        result = adapter.fetch_tile(z=0, x=0, y=0)

    assert adapter.configuration_status == "direct_origin_rejected"
    assert result.error_code == "not_configured"
    assert requests == []


@pytest.mark.parametrize(
    ("base_url", "allowlist"),
    [
        (GATEWAY_ORIGIN, ""),
        (GATEWAY_ORIGIN, "https://other.example.tw"),
        (GATEWAY_ORIGIN, "https://*.example.tw"),
        ("https://gateway.example.tw.attacker.invalid", GATEWAY_ORIGIN),
        ("https://sub.gateway.example.tw", GATEWAY_ORIGIN),
    ],
)
def test_gateway_origin_requires_an_exact_non_wildcard_allowlist_match(
    base_url: str,
    allowlist: str,
) -> None:
    client, requests = _client(lambda _request: _png_response())
    with client:
        adapter = _adapter_class()(
            client=client,
            environ={
                **CONFIG,
                "NLSC_GATEWAY_BASE_URL": base_url,
                ALLOWLIST_ENV: allowlist,
            },
            clock=lambda: NOW,
        )
        result = adapter.fetch_tile(z=0, x=0, y=0)

    assert adapter.available is False
    assert result.error_code == "not_configured"
    assert requests == []


@pytest.mark.parametrize("mode", ["production", "preview"])
def test_production_like_runtime_without_approved_origin_makes_zero_egress(
    mode: str,
) -> None:
    client, requests = _client(lambda _request: _png_response())
    with client:
        adapter = _adapter_class()(
            client=client,
            environ={**CONFIG, "APP_ENV": mode, ALLOWLIST_ENV: ""},
            clock=lambda: NOW,
        )
        result = adapter.fetch_tile(z=0, x=0, y=0)

    assert adapter.configuration_status == "production_disabled"
    assert result.error_code == "production_disabled"
    assert requests == []


def test_production_like_runtime_stays_disabled_even_if_origin_is_listed() -> None:
    client, requests = _client(lambda _request: _png_response())
    with client:
        adapter = _adapter_class()(
            client=client,
            environ={**CONFIG, "APP_ENV": "production"},
            clock=lambda: NOW,
        )
        result = adapter.fetch_tile(z=0, x=0, y=0)

    assert adapter.configuration_status == "production_disabled"
    assert result.error_code == "production_disabled"
    assert requests == []


def test_serverless_runtime_never_enables_the_test_tile_seam() -> None:
    client, requests = _client(lambda _request: _png_response())
    with client:
        adapter = _adapter_class()(
            client=client,
            environ={**CONFIG, "VERCEL": "1"},
            clock=lambda: NOW,
        )
        result = adapter.fetch_tile(z=0, x=0, y=0)

    assert adapter.configuration_status == "production_disabled"
    assert result.error_code == "production_disabled"
    assert requests == []


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        ("timeout", "timeout"),
        ("redirect", "redirect_rejected"),
        ("non_2xx", "upstream_rejected"),
        ("wrong_content_type", "invalid_response"),
        ("oversized", "response_too_large"),
        ("malformed_png", "invalid_response"),
        ("truncated_png", "invalid_response"),
        ("encoded", "invalid_response"),
    ],
)
def test_transport_and_png_failures_are_closed(
    failure: str,
    expected_code: str,
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if failure == "timeout":
            raise httpx.ReadTimeout(f"timeout {TOKEN}", request=request)
        if failure == "redirect":
            return httpx.Response(302, headers={"Location": "https://attacker.invalid/"})
        if failure == "non_2xx":
            return httpx.Response(503, content=TOKEN.encode("utf-8"))
        if failure == "wrong_content_type":
            return httpx.Response(
                200,
                content=_fixture(),
                headers={"Content-Type": "image/jpeg"},
            )
        if failure == "oversized":
            return _png_response(b"x" * 524_289)
        if failure == "malformed_png":
            return _png_response(b"not a png")
        if failure == "truncated_png":
            return _png_response(_fixture()[:-8])
        return _png_response(
            gzip.compress(_fixture()),
            headers={"Content-Encoding": "gzip"},
        )

    client, requests = _client(respond, follow_redirects=True)
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).fetch_tile(z=1, x=1, y=0)

    assert len(requests) == 1
    assert result.status == "unavailable"
    assert result.error_code == expected_code
    assert result.observation is None
    assert result.content is None
    assert TOKEN not in repr(result)


def test_declared_oversized_body_is_rejected_without_streaming() -> None:
    stream = _ChunkStream([_fixture()])
    client, requests = _client(
        lambda _request: httpx.Response(
            200,
            stream=stream,
            headers={
                "Content-Type": "image/png",
                "Content-Length": "524289",
            },
        )
    )
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).fetch_tile(z=0, x=0, y=0)

    assert len(requests) == 1
    assert result.error_code == "response_too_large"
    assert stream.yielded == 0
    assert stream.closed is True


@pytest.mark.parametrize("declared_length", [None, "1"])
def test_streaming_body_cannot_bypass_response_size_limit(
    declared_length: str | None,
) -> None:
    stream = _ChunkStream([b"x" * 262_144, b"y" * 262_145])
    headers = {"Content-Type": "image/png"}
    if declared_length is not None:
        headers["Content-Length"] = declared_length
    client, requests = _client(
        lambda _request: httpx.Response(200, stream=stream, headers=headers)
    )
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).fetch_tile(z=0, x=0, y=0)

    assert len(requests) == 1
    assert result.status == "unavailable"
    assert result.error_code == "response_too_large"
    assert stream.yielded == 2
    assert stream.closed is True


def test_invalid_png_scanline_filter_is_rejected() -> None:
    client, requests = _client(
        lambda _request: _png_response(
            _fixture("tile_001_invalid_filter.png.b64")
        )
    )
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).fetch_tile(z=0, x=0, y=0)

    assert len(requests) == 1
    assert result.status == "unavailable"
    assert result.error_code == "invalid_response"
    assert result.content is None


def test_blank_or_nonblank_semantics_remain_unknown() -> None:
    client, _ = _client(lambda _request: _png_response())
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).fetch_tile(z=0, x=0, y=0)

    assert result.observation is not None
    assert result.observation.coverage == "unknown"
    assert "parcel absence" in result.observation.notice
    assert "current cadastral truth" in result.observation.notice
    serialized = json.dumps(asdict(result.observation), ensure_ascii=False)
    for invented_field in (
        "source_record_id",
        "confidence",
        "legal_boundary_status",
        "freshness",
        "parcel_identity",
    ):
        assert invented_field not in serialized


def test_repeated_fetches_are_not_cached_in_memory_or_on_disk() -> None:
    before = set(Path.cwd().iterdir())
    client, requests = _client(lambda _request: _png_response())
    with client:
        adapter = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        )
        first = adapter.fetch_tile(z=1, x=1, y=0)
        second = adapter.fetch_tile(z=1, x=1, y=0)

    assert first.status == second.status == "available"
    assert len(requests) == 2
    assert set(Path.cwd().iterdir()) == before
    assert first.policy.cache_control == second.policy.cache_control == "no-store"


def test_gateway_credential_never_reaches_results_or_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, _ = _client(
        lambda _request: httpx.Response(
            401,
            content=TOKEN.encode("utf-8"),
            headers={"Content-Type": "text/plain"},
        )
    )
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).fetch_tile(z=0, x=0, y=0)

    assert TOKEN not in repr(result)
    assert TOKEN not in caplog.text


def test_successful_png_cannot_reflect_gateway_credential(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, requests = _client(
        lambda _request: _png_response(
            _fixture("tile_001_reflected_token.png.b64")
        )
    )
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).fetch_tile(z=0, x=0, y=0)

    assert len(requests) == 1
    assert result.status == "unavailable"
    assert result.error_code == "invalid_response"
    assert result.content is None
    assert TOKEN not in repr(result)
    assert TOKEN not in caplog.text


def test_tile_fetch_cannot_mutate_property_identity_provider_state() -> None:
    from services.vnext.identity_resolution import IdentityResolutionEngine

    engine = IdentityResolutionEngine(clock=lambda: NOW)
    original_providers = engine.providers
    client, _ = _client(lambda _request: _png_response())
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).fetch_tile(z=0, x=0, y=0)

    assert result.status == "available"
    assert engine.providers is original_providers
    assert engine.providers == ()
