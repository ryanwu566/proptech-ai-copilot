"""Durable pilot evidence adapter boundary for Postgres-compatible storage.

The SQL is explicit and parameterized.  The adapter intentionally exposes the
same public contract as the local store while keeping connection details out
of responses and logs.  The additive schema is applied by the reviewed
operator migration, never implicitly at request time.
"""

from __future__ import annotations

import json
import csv
import html
import io
import secrets
from datetime import datetime, timezone
from typing import Any, Callable

from services.pilot_evidence import CONSENT_VERSION, EVENT_TYPES, NO_VALIDATED_PRICING, PUBLIC_NOTICE, REVIEW_OUTCOMES, SMALL_SAMPLE_THRESHOLD, event_metadata, hash_secret, safe_text
from services.postgres_runtime import connect as connect_postgres


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class PostgresPilotEvidenceStore:
    def __init__(self, database_url: str, *, connection_factory: Callable[..., Any] | None = None) -> None:
        if not database_url or len(database_url) > 4096:
            raise ValueError("pilot durable persistence is not configured")
        self.database_url = database_url
        self._connection_factory = connection_factory

    def _connect(self):
        if self._connection_factory:
            return self._connection_factory(self.database_url)
        from psycopg.rows import dict_row

        return connect_postgres(self.database_url, row_factory=dict_row)

    def close(self) -> None:
        return None

    def _connection(self):
        return self._connect()

    def create_campaign(self, campaign_id: str, access_code: str, *, expires_at: str | None = None, is_test_fixture: bool = False) -> None:
        now = utc_now()
        with self._connection() as connection:
            connection.execute("INSERT INTO pilot_campaigns(campaign_id, access_code_hash, status, expires_at, created_at, updated_at, is_test_fixture) VALUES (%s, %s, 'active', %s, %s, %s, %s)", (safe_text(campaign_id, limit=80), hash_secret(access_code), expires_at, now, now, is_test_fixture))

    def disable_campaign(self, campaign_id: str) -> None:
        with self._connection() as connection:
            connection.execute("UPDATE pilot_campaigns SET status='disabled', updated_at=%s WHERE campaign_id=%s", (utc_now(), campaign_id))

    def start_session(self, campaign_id: str, access_code: str, *, locale: str, device_class: str, viewport_class: str, workflow_id: str = "tax-holding-preparation") -> dict[str, str] | None:
        now = utc_now()
        with self._connection() as connection:
            row = connection.execute("SELECT campaign_id, access_code_hash, status, expires_at FROM pilot_campaigns WHERE campaign_id=%s AND is_test_fixture=false", (campaign_id,)).fetchone()
            if row is None or row["status"] != "active" or not secrets.compare_digest(row["access_code_hash"], hash_secret(access_code)) or (row["expires_at"] and str(row["expires_at"]) <= now):
                return None
            session_id, token = secrets.token_urlsafe(18), secrets.token_urlsafe(32)
            participant_hash = hash_secret(secrets.token_urlsafe(18))
            connection.execute("INSERT INTO pilot_sessions(session_id, session_token_hash, campaign_id, participant_hash, workflow_id, locale, device_class, viewport_class, started_at, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (session_id, hash_secret(token), campaign_id, participant_hash, safe_text(workflow_id, limit=80), safe_text(locale, limit=12), safe_text(device_class, limit=30), safe_text(viewport_class, limit=20), now, now, now))
            return {"session_id": session_id, "session_token": token, "mode": "closed_pilot", "consent_version": CONSENT_VERSION}

    def _authorized_session(self, connection: Any, session_id: str, token: str) -> Any | None:
        row = connection.execute("SELECT session_id, workflow_id, locale, device_class, completion_status, consent_version, session_token_hash FROM pilot_sessions WHERE session_id=%s", (session_id,)).fetchone()
        if row is None or not secrets.compare_digest(row["session_token_hash"], hash_secret(token)):
            return None
        return row

    def save_consent(self, session_id: str, token: str, consent: dict[str, bool]) -> bool:
        now = utc_now()
        with self._connection() as connection:
            if self._authorized_session(connection, session_id, token) is None or not consent.get("participation"):
                return False
            connection.execute("INSERT INTO pilot_consents(session_id, participation, interaction_metrics, written_feedback, follow_up_contact, publication, version, created_at) VALUES (%s, true, %s, %s, %s, %s, %s, %s) ON CONFLICT (session_id) DO UPDATE SET interaction_metrics=excluded.interaction_metrics, written_feedback=excluded.written_feedback, follow_up_contact=excluded.follow_up_contact, publication=excluded.publication, version=excluded.version", (session_id, bool(consent.get("interaction_metrics")), bool(consent.get("written_feedback")), bool(consent.get("follow_up_contact")), bool(consent.get("publication")), CONSENT_VERSION, now))
            connection.execute("UPDATE pilot_sessions SET consent_version=%s, publication_permission=%s, updated_at=%s WHERE session_id=%s", (CONSENT_VERSION, bool(consent.get("publication")), now, session_id))
            return True

    def record_event(self, session_id: str, token: str, event_type: str, metadata: dict[str, Any] | None, idempotency_key: str) -> str:
        if event_type not in EVENT_TYPES or not idempotency_key or len(idempotency_key) > 120:
            raise ValueError("invalid pilot event")
        with self._connection() as connection:
            if self._authorized_session(connection, session_id, token) is None:
                raise PermissionError("session unavailable")
            consent = connection.execute("SELECT interaction_metrics FROM pilot_consents WHERE session_id=%s", (session_id,)).fetchone()
            if not consent or not consent["interaction_metrics"]:
                raise PermissionError("interaction consent unavailable")
            event_id = secrets.token_urlsafe(16)
            result = connection.execute("INSERT INTO pilot_events(event_id, session_id, event_type, metadata_json, occurred_at, idempotency_key) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (session_id, idempotency_key) DO NOTHING", (event_id, session_id, event_type, json.dumps(event_metadata(metadata), ensure_ascii=False, separators=(",", ":")), utc_now(), idempotency_key))
            return "accepted" if result.rowcount else "duplicate"

    def save_profile(self, session_id: str, token: str, payload: dict[str, Any]) -> bool:
        allowed = ("participant_role", "experience_band", "organization_type", "case_volume_band", "current_tools", "device_type", "accessibility_needs")
        profile = {key: safe_text(payload.get(key, ""), limit=240) for key in allowed}
        with self._connection() as connection:
            if self._authorized_session(connection, session_id, token) is None:
                return False
            now = utc_now()
            connection.execute("INSERT INTO pilot_profiles(session_id, profile_json, created_at, updated_at) VALUES (%s, %s::jsonb, %s, %s) ON CONFLICT (session_id) DO UPDATE SET profile_json=excluded.profile_json, updated_at=excluded.updated_at", (session_id, json.dumps(profile, ensure_ascii=False, separators=(",", ":")), now, now))
            return True

    def save_feedback(self, session_id: str, token: str, payload: dict[str, Any]) -> bool:
        required = ("task_completion", "result_clarity", "source_clarity", "limitation_clarity", "entry_ease", "meeting_usefulness", "trust_level", "reuse_likelihood")
        for key in required:
            if key not in payload:
                raise ValueError("feedback field missing")
            if key != "task_completion" and (not isinstance(payload[key], int) or isinstance(payload[key], bool) or not 1 <= payload[key] <= 5):
                raise ValueError("feedback scale out of range")
        with self._connection() as connection:
            if self._authorized_session(connection, session_id, token) is None:
                raise PermissionError("session unavailable")
            consent = connection.execute("SELECT written_feedback, publication FROM pilot_consents WHERE session_id=%s", (session_id,)).fetchone()
            if not consent or not consent["written_feedback"]:
                raise PermissionError("written feedback consent unavailable")
            now = utc_now()
            fields = [safe_text(payload.get(key, ""), limit=limit) for key, limit in (("most_confusing_step", 160), ("missing_capability", 500), ("current_alternative", 160), ("decision_maker_role", 100), ("privacy_concern", 500), ("required_integration", 500), ("free_text", 2000))]
            values = [session_id, safe_text(payload["task_completion"], limit=40), payload["result_clarity"], payload["source_clarity"], payload["limitation_clarity"], payload["entry_ease"], payload["meeting_usefulness"], payload["trust_level"], payload["reuse_likelihood"], *fields, json.dumps(payload.get("willingness_to_pay", {}), ensure_ascii=False, separators=(",", ":")), "user_submitted", "unverified", "private", now, now]
            connection.execute("INSERT INTO pilot_feedback(session_id, task_completion, result_clarity, source_clarity, limitation_clarity, entry_ease, meeting_usefulness, trust_level, reuse_likelihood, most_confusing_step, missing_capability, current_alternative, decision_maker_role, privacy_concern, required_integration, free_text, willingness_to_pay_json, provenance, verification_status, publication_status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s) ON CONFLICT (session_id) DO UPDATE SET free_text=excluded.free_text, updated_at=excluded.updated_at", values)
            return True

    def complete_session(self, session_id: str, token: str, *, status: str = "completed") -> bool:
        if status not in {"completed", "abandoned"}:
            raise ValueError("invalid completion status")
        column = "completed_at" if status == "completed" else "abandoned_at"
        with self._connection() as connection:
            if self._authorized_session(connection, session_id, token) is None:
                return False
            connection.execute(f"UPDATE pilot_sessions SET completion_status=%s, {column}=%s, updated_at=%s WHERE session_id=%s", (status, utc_now(), utc_now(), session_id))
            return True

    def participant_export(self, session_id: str, token: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            session = self._authorized_session(connection, session_id, token)
            if session is None:
                return None
            consent = connection.execute("SELECT participation, interaction_metrics, written_feedback, follow_up_contact, publication, version FROM pilot_consents WHERE session_id=%s", (session_id,)).fetchone()
            profile = connection.execute("SELECT profile_json, created_at, updated_at FROM pilot_profiles WHERE session_id=%s", (session_id,)).fetchone()
            feedback = connection.execute("SELECT task_completion, result_clarity, source_clarity, limitation_clarity, entry_ease, meeting_usefulness, trust_level, reuse_likelihood, most_confusing_step, missing_capability, current_alternative, decision_maker_role, privacy_concern, required_integration, free_text, willingness_to_pay_json FROM pilot_feedback WHERE session_id=%s", (session_id,)).fetchone()
            return {"session": {key: session[key] for key in ("session_id", "workflow_id", "locale", "device_class", "completion_status", "consent_version")}, "consent": dict(consent) if consent else None, "profile": dict(profile) if profile else None, "feedback": dict(feedback) if feedback else None}

    def deletion_dry_run(self, session_id: str, token: str) -> dict[str, Any] | None:
        tables = ("pilot_events", "pilot_consents", "pilot_profiles", "pilot_feedback", "pilot_contacts", "pilot_sessions")
        with self._connection() as connection:
            if self._authorized_session(connection, session_id, token) is None:
                return None
            return {"dry_run": True, "session_id": session_id, "affected_record_counts": {table: connection.execute(f"SELECT COUNT(*) AS count FROM {table} WHERE session_id=%s", (session_id,)).fetchone()["count"] for table in tables}}

    def delete_session(self, session_id: str, token: str) -> bool:
        with self._connection() as connection:
            if self._authorized_session(connection, session_id, token) is None:
                return False
            connection.execute("DELETE FROM pilot_sessions WHERE session_id=%s", (session_id,))
            return True

    def aggregate_public_evidence(self) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS count, COUNT(*) FILTER (WHERE completion_status='completed') AS completed FROM pilot_sessions WHERE is_test_fixture=false").fetchone()
            feedback_count = connection.execute("SELECT COUNT(*) AS count FROM pilot_feedback f JOIN pilot_sessions s ON s.session_id=f.session_id WHERE s.is_test_fixture=false").fetchone()["count"]
            publishable = connection.execute("SELECT COUNT(*) AS count FROM pilot_feedback f JOIN pilot_sessions s ON s.session_id=f.session_id JOIN pilot_consents c ON c.session_id=f.session_id WHERE s.is_test_fixture=false AND c.publication=true AND f.verification_status IN ('internally_reviewed','externally_verified') AND f.publication_status IN ('anonymized_quote_allowed','attribution_allowed','published')").fetchone()["count"]
            count, completed = int(row["count"] or 0), int(row["completed"] or 0)
            return {"pilot_sessions_started": count, "pilot_sessions_completed": completed, "feedback_response_count": int(feedback_count or 0), "median_observed_completion_seconds": None, "sample_size": completed, "small_sample_warning": count < SMALL_SAMPLE_THRESHOLD, "sample_notice": PUBLIC_NOTICE if count < SMALL_SAMPLE_THRESHOLD else "", "paying_customers": 0, "willingness_to_pay": NO_VALIDATED_PRICING, "professional_review": "pending", "publishable_testimonials": int(publishable or 0), "source": "canonical pilot evidence records", "test_fixtures_excluded": True}

    def safe_export(self, *, campaign_id: str | None = None, fmt: str = "json") -> str:
        aggregate = self.aggregate_public_evidence()
        if fmt == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=sorted(aggregate))
            writer.writeheader()
            writer.writerow({key: str(value).replace("=", "'=") if str(value).startswith(("=", "+", "-", "@")) else value for key, value in aggregate.items()})
            return output.getvalue()
        if fmt == "html":
            rows = "".join(f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>" for key, value in aggregate.items())
            return f"<!doctype html><html><body><h1>Pilot evidence pack</h1><table>{rows}</table></body></html>"
        return json.dumps({"methodology": "canonical evidence records; fixtures excluded", "aggregate": aggregate, "verification_status": "aggregate_only"}, ensure_ascii=False)

    def add_professional_review(self, payload: dict[str, Any]) -> str:
        if payload.get("outcome") not in REVIEW_OUTCOMES:
            raise ValueError("invalid review outcome")
        review_id, now = secrets.token_urlsafe(16), utc_now()
        with self._connection() as connection:
            connection.execute("INSERT INTO professional_reviews(review_id, reviewer_role, reviewer_display_name, qualification, consent_to_display_name, reviewed_capability, reviewed_rule_version, reviewed_product_version, review_scope, outcome, notes, required_changes, reviewed_at, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (review_id, safe_text(payload.get("reviewer_role", "other"), limit=80), safe_text(payload.get("reviewer_display_name", ""), limit=120), safe_text(payload.get("qualification", ""), limit=200), bool(payload.get("consent_to_display_name")), safe_text(payload.get("reviewed_capability", ""), limit=120), safe_text(payload.get("reviewed_rule_version", ""), limit=80), "pilot-evidence-v1", safe_text(payload.get("review_scope", ""), limit=500), payload["outcome"], safe_text(payload.get("notes", ""), limit=1000), safe_text(payload.get("required_changes", ""), limit=1000), now, now, now))
        return review_id

    def mark_feedback_reviewed(self, session_id: str, verification_status: str = "internally_reviewed") -> bool:
        if verification_status not in {"internally_reviewed", "externally_verified", "rejected", "superseded"}:
            raise ValueError("invalid verification status")
        with self._connection() as connection:
            return bool(connection.execute("UPDATE pilot_feedback SET verification_status=%s, updated_at=%s WHERE session_id=%s", (verification_status, utc_now(), session_id)).rowcount)

    def approve_publication(self, session_id: str) -> bool:
        with self._connection() as connection:
            row = connection.execute("SELECT c.publication, f.verification_status FROM pilot_consents c JOIN pilot_feedback f ON f.session_id=c.session_id WHERE c.session_id=%s", (session_id,)).fetchone()
            if not row or not row["publication"] or row["verification_status"] not in {"internally_reviewed", "externally_verified"}:
                return False
            return bool(connection.execute("UPDATE pilot_feedback SET publication_status='anonymized_quote_allowed', updated_at=%s WHERE session_id=%s", (utc_now(), session_id)).rowcount)

    def revoke_publication(self, session_id: str) -> bool:
        with self._connection() as connection:
            return bool(connection.execute("UPDATE pilot_feedback SET publication_status='revoked', updated_at=%s WHERE session_id=%s", (utc_now(), session_id)).rowcount)
