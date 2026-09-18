"""Offline contract tests for the authenticated Property Identity smoke runner."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping

import pytest

from scripts import authenticated_identity_smoke as smoke


WORKSPACE_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
PROPERTY_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
BODY_SECRET = "private-response-body-with-pii"


def token_for(role: str | None = "authenticated") -> str:
    claims = {"role": role} if role is not None else {"sub": "synthetic-user"}
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"eyJhbGciOiJIUzI1NiJ9.{payload}.synthetic-signature"


def environment(**overrides: str) -> dict[str, str]:
    return {
        "SMOKE_API_BASE_URL": "https://api.example.test/",
        "SMOKE_USER_BEARER_TOKEN": token_for(),
        "SMOKE_WORKSPACE_ID": WORKSPACE_ID,
        "SMOKE_PROPERTY_ENTITY_ID": PROPERTY_ID,
        **overrides,
    }


def response_headers(correlation_id: str) -> dict[str, str]:
    return {
        "X-Correlation-ID": correlation_id,
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        "Permissions-Policy": "camera=(), geolocation=(), payment=(), usb=(), serial=(), bluetooth=(), microphone=(self)",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-site",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    }


class FakeClient:
    def __init__(self, *, missing_header: str | None = None, changed_header: tuple[str, str] | None = None, control_code: str = "authentication_required", redirect: bool = False, error: str | None = None):
        self.calls: list[tuple[str, str, dict[str, str], float, int]] = []
        self.missing_header = missing_header
        self.changed_header = changed_header
        self.control_code = control_code
        self.redirect = redirect
        self.error = error

    def request(self, method: str, url: str, *, headers: Mapping[str, str], timeout: float, max_body_bytes: int) -> smoke.HttpResponse:
        self.calls.append((method, url, dict(headers), timeout, max_body_bytes))
        if self.error:
            raise RuntimeError(self.error)
        response_headers_map = response_headers(headers["X-Correlation-ID"])
        if self.changed_header:
            response_headers_map[self.changed_header[0]] = self.changed_header[1]
        if self.redirect and len(self.calls) == 1:
            response_headers_map["Location"] = "https://foreign.example.test/collect"
            return smoke.HttpResponse(302, response_headers_map, b"")
        if "Authorization" not in headers:
            response_headers_map["WWW-Authenticate"] = "Bearer"
            if self.missing_header:
                response_headers_map.pop(self.missing_header, None)
            body = json.dumps({"error": {"code": self.control_code, "message": BODY_SECRET}}).encode()
            return smoke.HttpResponse(401, response_headers_map, body)
        if self.missing_header:
            response_headers_map.pop(self.missing_header, None)
        return smoke.HttpResponse(200, response_headers_map, BODY_SECRET.encode())


@pytest.mark.parametrize("base_url", [
    "http://api.example.test", "http://localhost.example.test", "http://127.0.0.2",
    "https://user:password@api.example.test", "https://api.example.test/path",
    "https://api.example.test/?secret=1", "https://api.example.test/#fragment",
    "https://api.example.test?", "https://api.example.test#",
])
def test_base_url_rejects_unsafe_origin(base_url: str) -> None:
    with pytest.raises(ValueError) as error:
        smoke.validate_base_url(base_url)
    assert base_url not in str(error.value)


def test_local_http_is_allowed_and_trailing_slash_is_normalized() -> None:
    assert smoke.validate_base_url("http://localhost:8000/") == "http://localhost:8000"
    assert smoke.validate_base_url("http://127.0.0.1/") == "http://127.0.0.1"
    assert smoke.validate_base_url("https://api.example.test/") == "https://api.example.test"


def test_service_role_is_refused_before_any_request_and_token_is_redacted(capsys: pytest.CaptureFixture[str]) -> None:
    token = token_for("service_role")
    fake = FakeClient()
    code = smoke.main(environ=environment(SMOKE_USER_BEARER_TOKEN=token), client=fake)
    output = capsys.readouterr()
    assert code == 1
    assert fake.calls == []
    assert "service_role_refused" in output.out
    assert token not in output.out + output.err
    assert "Authorization" not in output.out + output.err


def test_token_without_role_is_left_to_api_authentication() -> None:
    fake = FakeClient()
    assert smoke.main(
        environ=environment(SMOKE_USER_BEARER_TOKEN=token_for(None)),
        client=fake,
    ) == 0
    assert len(fake.calls) == 5


def test_default_run_is_read_only_and_checks_authenticated_and_control_routes(capsys: pytest.CaptureFixture[str]) -> None:
    fake = FakeClient()
    env = environment()
    assert smoke.main(environ=env, client=fake) == 0
    assert [call[0] for call in fake.calls] == ["GET"] * 5
    assert [call[1] for call in fake.calls] == [
        "https://api.example.test/v1",
        f"https://api.example.test/v1/properties/{PROPERTY_ID}",
        f"https://api.example.test/v1/properties/{PROPERTY_ID}/graph",
        f"https://api.example.test/v1/properties/{PROPERTY_ID}/evidence",
        "https://api.example.test/v1",
    ]
    assert all(call[2]["Authorization"] == f"Bearer {env['SMOKE_USER_BEARER_TOKEN']}" for call in fake.calls[:4])
    assert "Authorization" not in fake.calls[4][2]
    assert all(0 < call[3] <= 30 for call in fake.calls)
    assert [call[4] for call in fake.calls] == [0, 0, 0, 0, 4096]
    assert len({call[2]["X-Correlation-ID"] for call in fake.calls}) == 5
    output = capsys.readouterr()
    assert output.out.count("PASS status=") == 5
    assert "status=401" in output.out
    for secret in (env["SMOKE_USER_BEARER_TOKEN"], BODY_SECRET, PROPERTY_ID, WORKSPACE_ID, "Authorization"):
        assert secret not in output.out + output.err


@pytest.mark.parametrize("missing_header", ["X-Correlation-ID", "Cache-Control", "X-Content-Type-Options", "Strict-Transport-Security"])
def test_missing_correlation_or_security_header_fails_without_body_logging(missing_header: str, capsys: pytest.CaptureFixture[str]) -> None:
    fake = FakeClient(missing_header=missing_header)
    assert smoke.main(environ=environment(), client=fake) == 1
    output = capsys.readouterr().out
    assert "FAIL status=" in output
    assert BODY_SECRET not in output


def test_remote_host_containing_localhost_still_requires_hsts() -> None:
    fake = FakeClient(missing_header="Strict-Transport-Security")
    assert smoke.main(
        environ=environment(SMOKE_API_BASE_URL="https://api.localhost.example.test"),
        client=fake,
    ) == 1


@pytest.mark.parametrize("header,value", [
    ("Content-Security-Policy", "default-src *"),
    ("Permissions-Policy", "camera=*"),
    ("Strict-Transport-Security", "max-age=0"),
])
def test_weakened_security_header_fails(header: str, value: str) -> None:
    fake = FakeClient(changed_header=(header, value))
    assert smoke.main(environ=environment(), client=fake) == 1


def test_unauthenticated_control_requires_authentication_required_code(capsys: pytest.CaptureFixture[str]) -> None:
    fake = FakeClient(control_code="permission_denied")
    assert smoke.main(environ=environment(), client=fake) == 1
    output = capsys.readouterr().out
    assert "FAIL status=401" in output
    assert BODY_SECRET not in output


def test_unauthenticated_control_requires_bearer_challenge() -> None:
    fake = FakeClient(missing_header="WWW-Authenticate")
    assert smoke.main(environ=environment(), client=fake) == 1


def test_redirect_is_failed_without_forwarding_bearer_to_foreign_origin(capsys: pytest.CaptureFixture[str]) -> None:
    fake = FakeClient(redirect=True)
    assert smoke.main(environ=environment(), client=fake) == 1
    assert len(fake.calls) == 5
    assert all(call[1].startswith("https://api.example.test/") for call in fake.calls)
    assert "foreign.example.test" not in capsys.readouterr().out


def test_default_transport_disables_redirects_without_network() -> None:
    client = smoke.UrllibSmokeClient()
    handler = next(item for item in client._opener.handlers if isinstance(item, smoke._NoRedirect))
    assert handler.redirect_request(None, None, 302, "redirect", {}, "https://foreign.example.test") is None


@pytest.mark.parametrize("overrides", [
    {"SMOKE_WRITE_MODE": "true"},
    {"SMOKE_WRITE_MODE": "true", "SMOKE_TEST_WORKSPACE_ID": "cccccccc-cccc-4ccc-8ccc-cccccccccccc"},
    {"SMOKE_WRITE_MODE": "yes", "SMOKE_TEST_WORKSPACE_ID": WORKSPACE_ID},
])
def test_write_mode_refuses_without_exact_explicit_dedicated_workspace(overrides: dict[str, str], capsys: pytest.CaptureFixture[str]) -> None:
    fake = FakeClient()
    assert smoke.main(environ=environment(**overrides), client=fake) == 1
    assert fake.calls == []
    assert "FAIL" in capsys.readouterr().out


def test_explicit_dedicated_write_mode_reports_unsupported_without_post(capsys: pytest.CaptureFixture[str]) -> None:
    fake = FakeClient()
    assert smoke.main(environ=environment(SMOKE_WRITE_MODE="true", SMOKE_TEST_WORKSPACE_ID=WORKSPACE_ID), client=fake) == 1
    assert fake.calls == []
    assert "WRITE_MODE_UNSUPPORTED" in capsys.readouterr().out


def test_client_exception_is_sanitized(capsys: pytest.CaptureFixture[str]) -> None:
    token = token_for()
    fake = FakeClient(error=f"Authorization: Bearer {token} {BODY_SECRET}")
    assert smoke.main(environ=environment(SMOKE_USER_BEARER_TOKEN=token), client=fake) == 1
    output = capsys.readouterr()
    assert "FAIL status=0" in output.out
    assert token not in output.out + output.err
    assert BODY_SECRET not in output.out + output.err
    assert "Authorization" not in output.out + output.err


def test_result_structure_never_renders_untrusted_fields() -> None:
    token = token_for()
    line = smoke.CheckResult(f"Authorization {token}", False, 999, token).line()
    assert line == "FAIL status=0 correlation_id=- check=runtime"


def test_config_requires_uuid_ids_without_echoing_values(capsys: pytest.CaptureFixture[str]) -> None:
    fake = FakeClient()
    assert smoke.main(environ=environment(SMOKE_PROPERTY_ENTITY_ID="private@example.test"), client=fake) == 1
    assert fake.calls == []
    assert "private@example.test" not in capsys.readouterr().out
