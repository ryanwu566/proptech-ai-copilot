"""Canary safety tests; the live endpoint is never called here."""

from scripts.canary_official_data import run_canary


class Response:
    status = 200

    class Headers:
        def get(self, name: str, default: str = "") -> str:
            return "application/xml" if name == "Content-Type" else default

    headers = Headers()

    def read(self, limit: int) -> bytes:
        return b"<Capabilities xmlns='http://www.opengis.net/wmts/1.0'>WMTS</Capabilities>"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


def fake_get(request, timeout: int):
    assert timeout == 20
    assert "GetCapabilities" in request.full_url
    return Response()


def test_canary_uses_bounded_verified_schema_path() -> None:
    result = run_canary("nlsc_base_map", http_get=fake_get)
    assert result["status"] == "available"
    assert result["schema_status"] == "valid"
    assert result["response_bytes_bounded"] is True


def test_canary_does_not_print_or_return_body() -> None:
    result = run_canary("nlsc_base_map", http_get=fake_get)
    assert "body" not in result
    assert "token" not in result
