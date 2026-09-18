from __future__ import annotations

import json

from services.pilot_persistence import configured_persistence
from services.production_config import assert_startup_configuration, load_runtime_configuration


def test_development_keeps_sqlite_local_default_without_claiming_durable_readiness() -> None:
    config = load_runtime_configuration({})
    assert config.production_like is False
    assert config.ready is True
    assert config.database_status == "not_configured"


def test_production_missing_database_and_security_config_fails_closed() -> None:
    config = load_runtime_configuration({"APP_ENV": "production", "APP_RUNTIME": "standard"})
    assert config.production_like is True
    assert config.ready is False
    assert config.safe_report()["database"] == "not_configured"


def test_production_configuration_requires_safe_categories_but_not_optional_admin_tokens() -> None:
    values = {
        "APP_ENV": "production",
        "APP_RUNTIME": "standard",
        "DATABASE_URL": "postgresql://db.example.invalid/app",
        "PILOT_SESSION_SIGNING_KEY": "s" * 32,
        "CORS_ALLOWED_ORIGINS": "https://frontend.example.invalid",
        "PUBLIC_APP_BASE_URL": "https://frontend.example.invalid",
    }
    config = load_runtime_configuration(values)
    assert config.ready is True
    assert config.admin_token_status == "not_configured"
    assert configured_persistence(environ=values)["adapter"] == "postgres"
    serialized = json.dumps(config.safe_report())
    assert "db.example" not in serialized
    assert "s" * 32 not in serialized


def test_malformed_production_database_is_not_accepted() -> None:
    config = load_runtime_configuration({"APP_ENV": "production", "DATABASE_URL": "sqlite:///unsafe"})
    assert config.database_status == "malformed"
    assert config.ready is False


def test_optional_nlsc_gateway_absence_does_not_block_startup() -> None:
    values = {
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql://db.example.invalid/app",
        "PILOT_SESSION_SIGNING_KEY": "s" * 32,
        "CORS_ALLOWED_ORIGINS": "https://frontend.example.invalid",
        "PUBLIC_APP_BASE_URL": "https://frontend.example.invalid",
    }
    config = assert_startup_configuration(values)
    assert config.ready is True
    assert config.safe_report()["nlsc_gateway"] == "not_configured"


def test_nlsc_gateway_report_is_value_free_and_validates_production_destination() -> None:
    values = {
        "APP_ENV": "production",
        "NLSC_GATEWAY_BASE_URL": "https://93.184.216.34",
        "NLSC_GATEWAY_CLIENT_TOKEN": "backend-client-token-123",
    }
    config = load_runtime_configuration(values)
    assert config.safe_report()["nlsc_gateway"] == "configured"
    assert "backend-client-token-123" not in json.dumps(config.safe_report())
    assert "93.184.216.34" not in json.dumps(config.safe_report())
    values["NLSC_GATEWAY_BASE_URL"] = "https://[2606:4700:4700::1111]"
    assert load_runtime_configuration(values).safe_report()["nlsc_gateway"] == "configured"

    for url in (
        "http://gateway.example.invalid",
        "https://gateway.example.invalid",
        "https://127.0.0.1",
        "https://93.184.216.34.",
        "https://127.1",
        "https://0x7f.0.0.1",
        "https://[::1]",
        "https://10.0.0.1",
        "https://172.16.0.1",
        "https://192.168.1.1",
        "https://169.254.1.1",
        "https://gateway.local",
        "https://gateway.localdomain",
        "https://gateway.internal",
        "https://user:pass@gateway.example.invalid",
        "https://gateway.example.invalid/other/path",
        "https://gateway.example.invalid?url=https://attacker.example",
        "https://gateway.example.invalid#fragment",
    ):
        values["NLSC_GATEWAY_BASE_URL"] = url
        assert load_runtime_configuration(values).safe_report()["nlsc_gateway"] == "malformed", url

    values["NLSC_GATEWAY_BASE_URL"] = "https://93.184.216.34"
    values["NLSC_GATEWAY_CLIENT_TOKEN"] = "has whitespace secret"
    assert load_runtime_configuration(values).safe_report()["nlsc_gateway"] == "malformed"


def test_health_exposes_gateway_category_without_values(monkeypatch) -> None:
    from backend.api import routes_health

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("NLSC_GATEWAY_BASE_URL", "https://93.184.216.34")
    monkeypatch.setenv("NLSC_GATEWAY_CLIENT_TOKEN", "backend-client-token-123")
    monkeypatch.setattr(routes_health, "health_check", lambda: {"database": "unavailable"})
    payload = routes_health.get_health()
    assert payload["nlsc_gateway"] == "configured"
    assert "backend-client-token-123" not in json.dumps(payload)
    assert "93.184.216.34" not in json.dumps(payload)
