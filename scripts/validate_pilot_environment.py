"""Safe environment readiness report; never prints configuration values."""

from __future__ import annotations

import os
import json

from services.pilot_evidence import build_readiness


def report() -> dict[str, object]:
    return {
        "database_path_configured": bool(os.getenv("PILOT_EVIDENCE_DB_PATH", "").strip()),
        "admin_configured": bool(os.getenv("PILOT_ADMIN_TOKEN", "").strip()),
        "review_configured": bool(os.getenv("PILOT_REVIEW_TOKEN", "").strip()),
        "readiness": build_readiness(database_available=True, admin_configured=bool(os.getenv("PILOT_ADMIN_TOKEN", "").strip())),
        "secrets_output": False,
    }


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True))
