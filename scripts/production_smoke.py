"""Local, provider-free production smoke contract.

This command uses FastAPI's in-process client and does not contact Render,
Postgres, map providers, or any other external service.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api_main import app


def run() -> dict[str, object]:
    checks: dict[str, str] = {}
    with TestClient(app) as client:
        for name, path in (("liveness", "/liveness"), ("health", "/health"), ("readiness", "/readiness"), ("release_version", "/release-version"), ("source_status", "/source-status")):
            response = client.get(path)
            checks[name] = "pass" if response.status_code == 200 else "fail"
    return {"status": "pass" if all(value == "pass" for value in checks.values()) else "fail", "checks": checks, "external_provider_called": False}


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass" else 1)
