from __future__ import annotations

import json

from services.pilot_persistence import configured_persistence
from services.production_config import load_runtime_configuration


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
