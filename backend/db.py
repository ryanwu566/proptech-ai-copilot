"""SQLite connection and health-check helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "proptech.db"


def get_connection() -> sqlite3.Connection:
    """Open the local SQLite database with dictionary-like rows."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Create the analysis history table when needed."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tax_analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                client_name TEXT NOT NULL,
                eligibility_status TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                signal_color TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def health_check() -> dict[str, str]:
    """Verify that SQLite can initialize and answer a basic query."""

    initialize_database()
    with get_connection() as connection:
        connection.execute("SELECT 1").fetchone()
    return {"database": "ok", "path": str(DB_PATH)}

