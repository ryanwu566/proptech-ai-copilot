"""Pilot evidence persistence selection and adapter contract.

SQLite remains the local/test adapter.  Production serverless runtimes must
provide a durable Postgres URL; they never silently fall back to a writable
local file or an in-memory database.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol

from services.pilot_evidence import PilotEvidenceStore
from services.production_config import database_url
from services.security import PersistenceConfigurationError, is_serverless_runtime


PILOT_DATABASE_URL_ENV = "PILOT_EVIDENCE_DATABASE_URL"
PILOT_DATABASE_PATH_ENV = "PILOT_EVIDENCE_DB_PATH"


class PilotEvidencePersistence(Protocol):
    def close(self) -> None: ...


def configured_persistence(*, environ: dict[str, str] | None = None, default_path: str | Path | None = None) -> dict[str, str | bool]:
    values = environ if environ is not None else os.environ
    configured_url = database_url(values)
    path = values.get(PILOT_DATABASE_PATH_ENV, "").strip()
    runtime = values.get("APP_ENV", "development").strip().lower()
    serverless = is_serverless_runtime(values)
    production = runtime in {"production", "preview"} or serverless
    if production and not configured_url:
        return {"status": "unavailable", "adapter": "none", "durable": False, "production": production, "serverless": serverless}
    if configured_url:
        return {"status": "configured", "adapter": "postgres", "durable": True, "production": production, "serverless": serverless}
    return {"status": "configured", "adapter": "sqlite", "durable": False, "production": production, "serverless": serverless, "path_configured": bool(path or default_path)}


def build_pilot_store(*, default_path: str | Path, environ: dict[str, str] | None = None) -> PilotEvidencePersistence:
    values = environ if environ is not None else os.environ
    choice = configured_persistence(environ=values, default_path=default_path)
    if choice["adapter"] == "postgres":
        from services.pilot_evidence_postgres import PostgresPilotEvidenceStore

        return PostgresPilotEvidenceStore(database_url(values))
    if choice["status"] != "configured":
        raise PersistenceConfigurationError("durable pilot persistence is not configured")
    path = values.get(PILOT_DATABASE_PATH_ENV, "").strip() or str(default_path)
    return PilotEvidenceStore(path)
