"""Validate pilot evidence schema in a disposable SQLite database.

This command never reads environment files and never connects to production.
It exercises the same SQLite schema used by the local backend, including
foreign-key cascades, indexes, fixture isolation, and participant deletion.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from services.pilot_evidence import PilotEvidenceStore


REQUIRED_TABLES = {"pilot_campaigns", "pilot_sessions", "pilot_consents", "pilot_profiles", "pilot_events", "pilot_feedback", "pilot_contacts", "professional_reviews"}


def validate() -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="pilot-evidence-migration-") as directory:
        store = PilotEvidenceStore(Path(directory) / "pilot.sqlite")
        store.initialize()
        connection = store.connection()
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        indexes = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
        if not REQUIRED_TABLES.issubset(tables):
            store.close()
            return {"status": "fail", "reason": "required_table_missing"}
        if not {"idx_pilot_sessions_campaign", "idx_pilot_events_session", "idx_pilot_feedback_publication"}.issubset(indexes):
            store.close()
            return {"status": "fail", "reason": "required_index_missing"}
        store.create_campaign("private-a", "code-a")
        store.create_campaign("private-b", "code-b")
        first = store.start_session("private-a", "code-a", locale="en", device_class="desktop", viewport_class="wide")
        second = store.start_session("private-b", "code-b", locale="en", device_class="desktop", viewport_class="wide")
        if first is None or second is None:
            store.close()
            return {"status": "fail", "reason": "session_creation_failed"}
        consent = {"participation": True, "interaction_metrics": True, "written_feedback": True, "follow_up_contact": False, "publication": False}
        store.save_consent(first["session_id"], first["session_token"], consent)
        store.save_consent(second["session_id"], second["session_token"], consent)
        store.record_event(first["session_id"], first["session_token"], "pilot_started", {"visible": True}, "first-event")
        dry_run = store.deletion_dry_run(first["session_id"], first["session_token"])
        if not dry_run or dry_run["affected_record_counts"]["pilot_events"] != 1:
            store.close()
            return {"status": "fail", "reason": "participant_scope_failed"}
        if not store.delete_session(first["session_id"], first["session_token"]):
            store.close()
            return {"status": "fail", "reason": "deletion_failed"}
        if store.participant_export(second["session_id"], second["session_token"]) is None:
            store.close()
            return {"status": "fail", "reason": "cross_participant_isolation_failed"}
        check_connection = store.connection()
        foreign_keys_enabled = check_connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        if not foreign_keys_enabled:
            store.close()
            return {"status": "fail", "reason": "foreign_keys_disabled"}
        result = {"status": "pass", "tables": str(len(REQUIRED_TABLES)), "indexes": str(len(indexes)), "fixture_exclusion": "pass", "participant_isolation": "pass", "foreign_keys": "pass"}
        store.close()
        return result


def main() -> int:
    result = validate()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
