"""Safe environment readiness report; never prints configuration values."""

from __future__ import annotations

import os
import json

from services.pilot_evidence import build_readiness
from services.pilot_persistence import configured_persistence
from services.production_config import load_runtime_configuration
from services.security import MIN_SESSION_SIGNING_KEY_LENGTH, is_serverless_runtime


def _configuration_status(value: str | None, *, minimum_length: int = 16) -> str:
    value = (value or "").strip()
    if not value:
        return "not_configured"
    if len(value) < minimum_length or any(ord(char) < 32 for char in value):
        return "malformed"
    return "configured"


def report() -> dict[str, object]:
    database_status = _configuration_status(os.getenv("PILOT_EVIDENCE_DB_PATH"), minimum_length=1)
    durable_database_status = _configuration_status(os.getenv("PILOT_EVIDENCE_DATABASE_URL"), minimum_length=1)
    admin_status = _configuration_status(os.getenv("PILOT_ADMIN_TOKEN"))
    review_status = _configuration_status(os.getenv("PILOT_REVIEW_TOKEN"))
    session_status = _configuration_status(os.getenv("PILOT_SESSION_SIGNING_KEY"), minimum_length=MIN_SESSION_SIGNING_KEY_LENGTH)
    persistence = configured_persistence()
    runtime = load_runtime_configuration()
    database_available = persistence["status"] == "configured"
    if runtime.production_like:
        database_available = runtime.database_status == "configured"
    return {
        "database_path_configured": database_status == "configured",
        "durable_database_configured": durable_database_status == "configured",
        "admin_configured": admin_status == "configured",
        "review_configured": review_status == "configured",
        "session_configured": session_status == "configured",
        "configuration_status": {"database": database_status, "durable_database": durable_database_status, "admin": admin_status, "review": review_status, "session": session_status},
        "persistence": {key: persistence[key] for key in ("status", "adapter", "durable", "production", "serverless") if key in persistence},
        "readiness": build_readiness(database_available=database_available and database_status != "malformed" and runtime.ready, admin_configured=admin_status == "configured"),
        "runtime": runtime.safe_report(),
        "secrets_output": False,
        "serverless_without_durable_store": is_serverless_runtime() and durable_database_status != "configured",
    }


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True))
