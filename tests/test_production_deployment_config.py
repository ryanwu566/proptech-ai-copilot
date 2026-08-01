"""Production deployment configuration contracts."""

from pathlib import Path

from backend.api_main import DEFAULT_DEV_CORS_ORIGINS, configured_cors_origins, parse_cors_allowed_origins


ROOT = Path(__file__).resolve().parents[1]
RENDER = (ROOT / "render.yaml").read_text(encoding="utf-8")
API_TS = (ROOT / "frontend_next" / "lib" / "api.ts").read_text(encoding="utf-8")
DOCS = (ROOT / "docs" / "production-backend-deployment-v1.md").read_text(encoding="utf-8")


def test_render_blueprint_uses_python_fastapi_runtime() -> None:
    assert "runtime: python" in RENDER
    assert "pip install -r backend/requirements.txt" in RENDER
    assert "uvicorn backend.api_main:app --host 0.0.0.0 --port $PORT" in RENDER
    assert "healthCheckPath: /health" in RENDER
    assert "docker" not in RENDER.lower()


def test_render_blueprint_lists_only_variable_names_not_values() -> None:
    for name in (
        "CORS_ALLOWED_ORIGINS",
        "VALUATION_DATABASE_URL",
        "GOOGLE_MAPS_API_KEY",
        "TGOS_APP_ID",
        "TGOS_API_KEY",
        "TDX_CLIENT_ID",
        "TDX_CLIENT_SECRET",
        "COMMUTE_REFRESH_TOKEN",
    ):
        assert f"key: {name}" in RENDER
    assert "sync: false" in RENDER
    assert "https://" not in RENDER
    assert "token:" not in RENDER.lower()


def test_cors_allowlist_parser_rejects_wildcard_with_credentials() -> None:
    assert parse_cors_allowed_origins("https://frontend.example, * , https://frontend.example/") == ["https://frontend.example"]
    assert "*" not in parse_cors_allowed_origins("*")


def test_cors_defaults_to_localhost_only_when_no_allowlist(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert configured_cors_origins() == list(DEFAULT_DEV_CORS_ORIGINS)


def test_cors_prefers_production_allowlist_variable(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://frontend.example")
    monkeypatch.setenv("CORS_ORIGINS", "https://legacy.example")
    assert configured_cors_origins() == ["https://frontend.example"]


def test_frontend_api_base_fails_closed_in_production() -> None:
    assert "NEXT_PUBLIC_API_BASE_URL" in API_TS
    assert "resolveApiOrigin" in API_TS
    assert "allowRelativeProxy" in API_TS
    origin_source = (ROOT / "frontend_next" / "lib" / "api-origin.ts").read_text(encoding="utf-8")
    assert "localhost" in origin_source
    assert "throw new Error" in API_TS
    assert "localStorage" not in API_TS
    assert "sessionStorage" not in API_TS


def test_deployment_docs_cover_manual_render_and_vercel_steps() -> None:
    for text in (
        "backend.api_main:app",
        "CORS_ALLOWED_ORIGINS",
        "NEXT_PUBLIC_API_BASE_URL",
        "`COMMUTE_REFRESH_TOKEN` belongs only on the Render backend",
        "GET /health",
        "If `NEXT_PUBLIC_API_BASE_URL` is missing in production",
    ):
        assert text in DOCS
    assert ".env" not in DOCS


def test_production_origin_contract_rejects_localhost_and_wildcard() -> None:
    from services.production_config import load_runtime_configuration

    values = {
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql://db.example.invalid/app",
        "PILOT_SESSION_SIGNING_KEY": "s" * 32,
        "PUBLIC_APP_BASE_URL": "https://frontend.example.invalid",
        "CORS_ALLOWED_ORIGINS": "http://localhost:3000",
    }
    assert load_runtime_configuration(values).ready is False
    values["CORS_ALLOWED_ORIGINS"] = "*"
    assert load_runtime_configuration(values).ready is False


def test_hosted_environment_manifest_contains_metadata_only() -> None:
    import json

    manifest = json.loads((ROOT / "config/hosted-environment-manifest.json").read_text(encoding="utf-8"))
    names = {item["name"] for item in manifest["variables"]}
    assert {"DATABASE_URL", "NEXT_PUBLIC_API_BASE_URL", "CORS_ALLOWED_ORIGINS"} <= names
    assert all("value" not in item for item in manifest["variables"])
