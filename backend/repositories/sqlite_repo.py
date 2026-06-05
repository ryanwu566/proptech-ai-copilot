"""SQLite repository for TaxOracle analysis history."""

from __future__ import annotations

import json
from typing import Any

from backend.db import get_connection, initialize_database


def save_tax_analysis(case_id: str, client_name: str, result: dict[str, Any]) -> None:
    """Persist one structured TaxOracle result."""

    initialize_database()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO tax_analysis_history
            (case_id, client_name, eligibility_status, risk_score, signal_color, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                client_name,
                result["eligibility_status"],
                result["risk_score"],
                result["signal_color"],
                json.dumps(result, ensure_ascii=False),
            ),
        )


def list_tax_analyses(limit: int = 20) -> list[dict[str, Any]]:
    """Return recent TaxOracle analyses."""

    initialize_database()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, case_id, client_name, eligibility_status, risk_score, signal_color, created_at
            FROM tax_analysis_history ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_tax_analysis(analysis_id: int) -> dict[str, Any] | None:
    """Return one stored structured result for history detail views."""

    initialize_database()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, case_id, client_name, eligibility_status, risk_score,
                   signal_color, payload_json, created_at
            FROM tax_analysis_history WHERE id = ?
            """,
            (analysis_id,),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["payload"] = json.loads(result.pop("payload_json"))
    return result
