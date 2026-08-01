"""Postgres repository for durable TaxOracle history.

The repository mirrors the existing SQLite contract. SQL is parameterized and
the application payload remains on the server side.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from services.postgres_runtime import connect


class PostgresTaxHistoryRepository:
    def __init__(self, database_url: str, *, connection_factory: Callable[..., Any] | None = None) -> None:
        self.database_url = database_url
        self._connection_factory = connection_factory

    def _connection(self) -> Any:
        return connect(self.database_url, connection_factory=self._connection_factory)

    def save(self, case_id: str, client_name: str, result: dict[str, Any]) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO tax_analysis_history
                (case_id, client_name, eligibility_status, risk_score, signal_color, payload_json)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (case_id, client_name, result["eligibility_status"], result["risk_score"], result["signal_color"], json.dumps(result, ensure_ascii=False)),
            )

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, case_id, client_name, eligibility_status, risk_score, signal_color, created_at FROM tax_analysis_history ORDER BY id DESC LIMIT %s",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, analysis_id: int) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, case_id, client_name, eligibility_status, risk_score, signal_color, payload_json, created_at FROM tax_analysis_history WHERE id = %s",
                (analysis_id,),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        payload = result.pop("payload_json")
        result["payload"] = payload if isinstance(payload, dict) else json.loads(payload)
        return result
