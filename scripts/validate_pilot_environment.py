"""Safe environment readiness report; never prints configuration values."""

from __future__ import annotations

import os
import json

from services.pilot_evidence import build_readiness


def _configuration_status(value: str | None, *, minimum_length: int = 16) -> str:
    value = (value or "").strip()
    if not value:
        return "not_configured"
    if len(value) < minimum_length or any(ord(char) < 32 for char in value):
        return "malformed"
    return "configured"


def report() -> dict[str, object]:
    database_status = _configuration_status(os.getenv("PILOT_EVIDENCE_DB_PATH"), minimum_length=1)
    admin_status = _configuration_status(os.getenv("PILOT_ADMIN_TOKEN"))
    review_status = _configuration_status(os.getenv("PILOT_REVIEW_TOKEN"))
    return {
        "database_path_configured": database_status == "configured",
        "admin_configured": admin_status == "configured",
        "review_configured": review_status == "configured",
        "configuration_status": {"database": database_status, "admin": admin_status, "review": review_status},
        "readiness": build_readiness(database_available=database_status != "malformed", admin_configured=admin_status == "configured"),
        "secrets_output": False,
    }


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True))
