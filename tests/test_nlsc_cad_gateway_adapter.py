"""Offline contract tests for the two fixed NLSC CAD gateway operations."""

from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest


FIXTURES = Path(__file__).parent / "fixtures" / "nlsc"
NOW = datetime(2026, 9, 19, 8, 30, tzinfo=timezone.utc)
TOKEN = "backend-only-cad-client-token-123"
CONFIG = {
    "APP_ENV": "test",
    "NLSC_GATEWAY_BASE_URL": "https://gateway.example.tw",
    "NLSC_GATEWAY_CLIENT_TOKEN": TOKEN,
}
PRODUCTION_CONFIG = {**CONFIG, "APP_ENV": "production"}


def _adapter_class():
    from services.adapters.nlsc_cad_gateway_adapter import NlscCadGatewayAdapter

    return NlscCadGatewayAdapter


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


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


def _xml_response(name: str, *, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        content=_fixture(name),
        headers={"Content-Type": "application/xml; charset=utf-8"},
    )


def test_unconfigured_cad_operations_make_zero_egress() -> None:
    client, requests = _client(lambda _request: _xml_response("cad_009_multiple.xml"))
    with client:
        adapter = _adapter_class()(
            client=client,
            environ={"APP_ENV": "production"},
            clock=lambda: NOW,
        )
        address = adapter.cad_009_address_query_land("臺中市南屯區黎明路二段497號", max_results=2)
        position = adapter.cad_001_cadas_map_position("B", "0012", "00010000")

    assert address["status"] == "unavailable"
    assert position["status"] == "unavailable"
    assert address["error_code"] == position["error_code"] == "not_configured"
    assert requests == []


@pytest.mark.parametrize(
    "base_url",
    [
        "https://gateway.example.tw",
        "https://93.184.216.34",
        "https://unapproved-gateway.example.com",
    ],
)
def test_production_like_runtime_disables_cad_egress_until_gateway_is_approved(
    base_url: str,
) -> None:
    client, requests = _client(lambda _request: _xml_response("cad_009_multiple.xml"))
    with client:
        adapter = _adapter_class()(
            client=client,
            environ={**PRODUCTION_CONFIG, "NLSC_GATEWAY_BASE_URL": base_url},
            clock=lambda: NOW,
        )
        address = adapter.cad_009_address_query_land("test address", max_results=2)
        position = adapter.cad_001_cadas_map_position("B", "0012", "00010000")

    assert adapter.available is False
    assert address["error_code"] == position["error_code"] == "production_disabled"
    assert requests == []


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.nlsc.gov.tw",
        "https://maps.nlsc.gov.tw",
        "https://wmts.nlsc.gov.tw",
    ],
)
def test_official_nlsc_hosts_cannot_bypass_the_taiwan_gateway(
    base_url: str,
) -> None:
    client, requests = _client(lambda _request: _xml_response("cad_009_multiple.xml"))
    with client:
        adapter = _adapter_class()(
            client=client,
            environ={**CONFIG, "NLSC_GATEWAY_BASE_URL": base_url},
            clock=lambda: NOW,
        )
        result = adapter.cad_009_address_query_land("臺中市南屯區黎明路二段497號")

    assert adapter.configuration_status == "malformed"
    assert result["status"] == "unavailable"
    assert requests == []


def test_cad_009_uses_only_its_fixed_operation_and_normalizes_documented_fields() -> None:
    client, requests = _client(lambda _request: _xml_response("cad_009_multiple.xml"))
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).cad_009_address_query_land("臺中市南屯區黎明路二段497號", max_results=2)

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://gateway.example.tw/nlsc/cad/CAD_009"
    assert json.loads(request.content) == {
        "query": "臺中市南屯區黎明路二段497號",
        "max_results": 2,
    }
    assert request.headers["authorization"] == f"Bearer {TOKEN}"
    assert request.headers["accept"] == "application/xml"
    assert request.headers["accept-encoding"] == "identity"
    assert request.extensions["timeout"]["read"] == 4.0
    assert result == {
        "status": "available",
        "source": "NLSC",
        "service_code": "CAD_009",
        "retrieved_at": "2026-09-19T08:30:00+00:00",
        "coverage": "unknown",
        "source_record_id": None,
        "raw_confidence": None,
        "observations": [
            {
                "content": "臺中市南屯區黎明里００１鄰黎明路二段４９７號",
                "location": "120.634421,24.153412",
                "office_code": "BC",
                "section_code": "2013",
                "land_number": "03420000",
            },
            {
                "content": "臺中市南屯區黎明里黎明路二段４９７號",
                "location": "120.634500,24.153500",
                "office_code": "BC",
                "section_code": "2013",
                "land_number": "03430000",
            },
        ],
        "error_code": None,
    }


def test_cad_001_uses_only_its_fixed_operation_and_keeps_position_as_georeference() -> None:
    client, requests = _client(lambda _request: _xml_response("cad_001_position.xml"))
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).cad_001_cadas_map_position("B", "0012", "00010000", crs="4326")

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://gateway.example.tw/nlsc/cad/CAD_001"
    assert json.loads(request.content) == {
        "county_code": "B",
        "section_code": "0012",
        "land_number": "00010000",
        "crs": "4326",
    }
    assert result == {
        "status": "available",
        "source": "NLSC",
        "service_code": "CAD_001",
        "retrieved_at": "2026-09-19T08:30:00+00:00",
        "coverage": "unknown",
        "source_record_id": None,
        "raw_confidence": None,
        "observations": [
            {
                "representative_point": {
                    "x": 120.683552,
                    "y": 24.142313,
                    "crs": "EPSG:4326",
                },
                "bounds": {
                    "lower_left": {"x": 120.683471, "y": 24.142235},
                    "upper_right": {"x": 120.683633, "y": 24.142389},
                    "crs": "EPSG:4326",
                },
            }
        ],
        "error_code": None,
    }


@pytest.mark.parametrize(
    ("operation", "arguments"),
    [
        ("cad_009_address_query_land", ("",)),
        ("cad_009_address_query_land", ("x" * 513,)),
        ("cad_009_address_query_land", ("address\x00secret",)),
        ("cad_009_address_query_land", ("address", 0)),
        ("cad_009_address_query_land", ("address", 9)),
        ("cad_009_address_query_land", ("address", True)),
        ("cad_001_cadas_map_position", ("", "0012", "00010000")),
        ("cad_001_cadas_map_position", ("B/escape", "0012", "00010000")),
        ("cad_001_cadas_map_position", ("B", "", "00010000")),
        ("cad_001_cadas_map_position", ("B", "../0012", "00010000")),
        ("cad_001_cadas_map_position", ("B", "0012", "1")),
        ("cad_001_cadas_map_position", ("B", "0012", "０００１００００")),
        ("cad_001_cadas_map_position", ("B", "0012", "00010000", "3857")),
    ],
)
def test_malformed_operation_input_is_rejected_before_egress(
    operation: str,
    arguments: tuple[object, ...],
) -> None:
    client, requests = _client(lambda _request: _xml_response("cad_009_multiple.xml"))
    with client:
        adapter = _adapter_class()(client=client, environ=CONFIG, clock=lambda: NOW)
        result = getattr(adapter, operation)(*arguments)

    assert result["status"] == "unavailable"
    assert result["error_code"] == "invalid_input"
    assert requests == []


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        ("timeout", "timeout"),
        ("redirect", "redirect_rejected"),
        ("non_2xx", "upstream_rejected"),
        ("oversized", "response_too_large"),
        ("malformed_xml", "invalid_response"),
        ("unexpected_root", "invalid_response"),
        ("entity", "invalid_response"),
        ("compressed_xml", "invalid_response"),
    ],
)
def test_cad_009_transport_and_xml_failures_are_closed(
    failure: str,
    expected_code: str,
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if failure == "timeout":
            raise httpx.ReadTimeout(f"timeout {TOKEN}", request=request)
        if failure == "redirect":
            return httpx.Response(302, headers={"Location": "https://attacker.example/"})
        if failure == "non_2xx":
            return httpx.Response(503, content=TOKEN.encode("utf-8"))
        if failure == "oversized":
            return httpx.Response(
                200,
                content=b"x" * 131_073,
                headers={"Content-Type": "application/xml"},
            )
        if failure == "compressed_xml":
            return httpx.Response(
                200,
                content=gzip.compress(_fixture("cad_009_multiple.xml")),
                headers={
                    "Content-Type": "application/xml",
                    "Content-Encoding": "gzip",
                },
            )
        if failure == "malformed_xml":
            payload = b"<addressItems>"
        elif failure == "unexpected_root":
            payload = b"<otherRoot/>"
        else:
            payload = b'<!DOCTYPE x [<!ENTITY leaked "secret">]><addressItems>&leaked;</addressItems>'
        return httpx.Response(200, content=payload, headers={"Content-Type": "application/xml"})

    client, requests = _client(respond, follow_redirects=True)
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).cad_009_address_query_land("臺中市南屯區黎明路二段497號", max_results=2)

    assert len(requests) == 1
    assert result["status"] == "unavailable"
    assert result["error_code"] == expected_code
    assert result["observations"] == []
    serialized = json.dumps(result, ensure_ascii=False)
    assert TOKEN not in serialized
    assert "<addressItems" not in serialized


@pytest.mark.parametrize(
    "payload",
    [
        b"<cadsPositionItem><repX>120</repX></cadsPositionItem>",
        b"<addressItems/>",
        (
            b"<cadsPositionItem><repX>999</repX><repY>24</repY>"
            b"<ldX>120</ldX><ldY>23</ldY><rtX>121</rtX><rtY>25</rtY>"
            b"</cadsPositionItem>"
        ),
    ],
)
def test_cad_001_unexpected_schema_or_coordinates_fail_closed(payload: bytes) -> None:
    client, _ = _client(
        lambda _request: httpx.Response(
            200,
            content=payload,
            headers={"Content-Type": "application/xml"},
        )
    )
    with client:
        result = _adapter_class()(
            client=client,
            environ=CONFIG,
            clock=lambda: NOW,
        ).cad_001_cadas_map_position("B", "0012", "00010000")

    assert result["status"] == "unavailable"
    assert result["error_code"] == "invalid_response"
    assert result["observations"] == []


def test_normalization_is_deterministic_and_does_not_retain_raw_xml() -> None:
    def normalized() -> dict[str, object]:
        client, _ = _client(lambda _request: _xml_response("cad_009_multiple.xml"))
        with client:
            return _adapter_class()(
                client=client,
                environ=CONFIG,
                clock=lambda: NOW,
            ).cad_009_address_query_land("臺中市南屯區黎明路二段497號", max_results=2)

    first = normalized()
    second = normalized()
    assert first == second
    assert first["coverage"] == "unknown"
    assert first["source_record_id"] is None
    assert first["raw_confidence"] is None
    assert "<?xml" not in json.dumps(first, ensure_ascii=False)


def test_gateway_credential_never_reaches_results_or_logs(caplog: pytest.LogCaptureFixture) -> None:
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
        ).cad_009_address_query_land("臺中市南屯區黎明路二段497號")

    assert TOKEN not in json.dumps(result)
    assert TOKEN not in caplog.text
