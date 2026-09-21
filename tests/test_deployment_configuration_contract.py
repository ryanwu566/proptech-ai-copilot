"""Release-specific deployment contract checks."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_does_not_use_deployment_secrets_or_providers() -> None:
    workflow = (ROOT / ".github/workflows/release-quality.yml").read_text(encoding="utf-8")
    assert "secrets." not in workflow
    assert "production" not in workflow.lower()
    assert "database" not in workflow.lower()
    assert "refresh" not in workflow.lower()


def test_render_and_frontend_contracts_remain_declared() -> None:
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")
    api = (ROOT / "frontend_next/lib/api.ts").read_text(encoding="utf-8")
    assert "uvicorn backend.api_main:app" in render
    assert "healthCheckPath: /health" in render
    assert "VALUATION_DATABASE_URL" in render
    assert "NEXT_PUBLIC_API_BASE_URL" in api
    origin = (ROOT / "frontend_next/lib/api-origin.ts").read_text(encoding="utf-8")
    assert "resolveApiOrigin" in api
    assert "Production API origin must use HTTPS" in origin


def test_render_disables_proxy_header_client_rewriting() -> None:
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")
    start_command = next(line for line in render.splitlines() if "startCommand:" in line)
    assert "--no-proxy-headers" in start_command


def test_cloud_run_dockerfile_runs_fastapi_with_runtime_port_and_signal_contract() -> None:
    dockerfile_path = ROOT / "Dockerfile.cloudrun"
    assert dockerfile_path.is_file()

    dockerfile = dockerfile_path.read_text(encoding="utf-8")
    assert "FROM python:3.12-slim" in dockerfile
    assert "WORKDIR /app" in dockerfile
    assert "COPY backend/requirements.txt backend/requirements.txt" in dockerfile
    assert "pip install --no-cache-dir -r backend/requirements.txt" in dockerfile
    assert "exec uvicorn backend.api_main:app" in dockerfile
    assert "--host 0.0.0.0" in dockerfile
    assert "${PORT:-8080}" in dockerfile
    assert "--no-proxy-headers" in dockerfile
    assert "GOOGLE_APPLICATION_CREDENTIALS" not in dockerfile


def test_cloud_run_dockerfile_does_not_replace_streamlit_image_contract() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "EXPOSE 8501" in dockerfile
    assert 'CMD ["streamlit", "run", "app.py"' in dockerfile
