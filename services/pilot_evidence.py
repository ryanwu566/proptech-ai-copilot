"""Privacy-safe closed-pilot evidence domain.

This module deliberately stores workflow metadata rather than property facts.  It
is usable with the existing SQLite deployment while keeping the public evidence
surface aggregate-only and excluding test fixtures.
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import secrets
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable


PILOT_MODES = ("normal", "competition_demo", "offline_competition_demo", "closed_pilot", "professional_review")
EVENT_TYPES = (
    "pilot_started", "consent_completed", "workflow_opened", "step_started", "field_changed",
    "recalculation_requested", "recalculation_succeeded", "recalculation_failed", "rule_trace_opened",
    "printable_report_opened", "supporting_module_opened", "assistive_narration_enabled", "task_completed",
    "task_skipped", "feedback_started", "feedback_submitted", "pilot_completed", "pilot_abandoned",
    "recoverable_error", "unrecoverable_error",
)
PROVENANCE_STATES = ("user_submitted", "system_observed", "reviewer_submitted", "imported", "test_fixture")
VERIFICATION_STATES = ("unverified", "internally_reviewed", "externally_verified", "rejected", "superseded")
PUBLICATION_STATES = ("private", "aggregate_only", "anonymized_quote_allowed", "attribution_allowed", "published", "revoked")
REVIEW_OUTCOMES = ("approved_for_pilot", "approved_with_notes", "revision_required", "out_of_scope", "unable_to_review")
CONSENT_VERSION = "pilot-consent-v1"
PRODUCT_VERSION = "pilot-evidence-v1"
SMALL_SAMPLE_THRESHOLD = 5
PUBLIC_NOTICE = "Exploratory evidence — sample size is too small for a general conclusion."
NO_VALIDATED_PRICING = "Willingness to pay has not yet been validated."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def safe_text(value: str, *, limit: int) -> str:
    text = str(value or "")
    if any(ord(char) < 32 and char not in "\t\n\r" for char in text):
        raise ValueError("control characters are not allowed")
    return text.strip()[:limit]


def sanitize_feedback_text(value: str) -> str:
    """Bound and neutralize feedback before storage; output is escaped at render time."""

    return safe_text(value, limit=2000)


def event_metadata(value: dict[str, Any] | None) -> dict[str, Any]:
    """Keep only bounded event metadata, never exact case values."""

    value = value or {}
    allowed = {"field_category", "changed", "validation_succeeded", "required", "step_id", "task_id", "visible"}
    result: dict[str, Any] = {}
    for key in allowed:
        item = value.get(key)
        if key in {"changed", "validation_succeeded", "required", "visible"}:
            if isinstance(item, bool):
                result[key] = item
        elif isinstance(item, str) and item.strip():
            result[key] = safe_text(item, limit=80)
    active_seconds = value.get("active_seconds")
    if isinstance(active_seconds, (int, float)) and not isinstance(active_seconds, bool):
        result["active_seconds"] = max(0, min(int(active_seconds), 900))
    return result


def is_publication_eligible(*, written_feedback_consent: bool, publication_consent: bool, verification_status: str, publication_status: str) -> bool:
    return (
        written_feedback_consent
        and publication_consent
        and verification_status in {"internally_reviewed", "externally_verified"}
        and publication_status in {"anonymized_quote_allowed", "attribution_allowed", "published"}
    )


@dataclass(frozen=True)
class PilotTask:
    task_id: str
    purpose: str
    expected_action: str
    completion_event: str
    skip_reason_allowed: bool = True


PILOT_TASKS: tuple[PilotTask, ...] = (
    PilotTask("tax-holding-preparation", "Prepare a tax and holding-cost review", "Review facts, recalculate, inspect sources and open the report", "printable_report_opened"),
    PilotTask("supporting-evidence-review", "Review one supporting evidence module", "Inspect source and limitation status, then return to the case", "supporting_module_opened"),
    PilotTask("accessibility-navigation", "Try assistive narration", "Enable narration, hear one result and stop narration", "assistive_narration_enabled"),
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS pilot_campaigns (
    campaign_id TEXT PRIMARY KEY,
    access_code_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    starts_at TEXT,
    expires_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_test_fixture INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pilot_sessions (
    session_id TEXT PRIMARY KEY,
    session_token_hash TEXT NOT NULL,
    campaign_id TEXT NOT NULL REFERENCES pilot_campaigns(campaign_id),
    participant_hash TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    locale TEXT NOT NULL,
    device_class TEXT NOT NULL,
    viewport_class TEXT NOT NULL,
    completion_status TEXT NOT NULL DEFAULT 'active',
    current_step TEXT,
    consent_version TEXT,
    publication_permission INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    abandoned_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_test_fixture INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pilot_consents (
    session_id TEXT PRIMARY KEY REFERENCES pilot_sessions(session_id) ON DELETE CASCADE,
    participation INTEGER NOT NULL,
    interaction_metrics INTEGER NOT NULL,
    written_feedback INTEGER NOT NULL,
    follow_up_contact INTEGER NOT NULL,
    publication INTEGER NOT NULL,
    audio_collected INTEGER NOT NULL DEFAULT 0,
    transcript_stored INTEGER NOT NULL DEFAULT 0,
    version TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pilot_profiles (
    session_id TEXT PRIMARY KEY REFERENCES pilot_sessions(session_id) ON DELETE CASCADE,
    profile_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pilot_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES pilot_sessions(session_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    UNIQUE(session_id, idempotency_key)
);
CREATE TABLE IF NOT EXISTS pilot_feedback (
    session_id TEXT PRIMARY KEY REFERENCES pilot_sessions(session_id) ON DELETE CASCADE,
    task_completion TEXT NOT NULL,
    result_clarity INTEGER NOT NULL,
    source_clarity INTEGER NOT NULL,
    limitation_clarity INTEGER NOT NULL,
    entry_ease INTEGER NOT NULL,
    meeting_usefulness INTEGER NOT NULL,
    trust_level INTEGER NOT NULL,
    reuse_likelihood INTEGER NOT NULL,
    most_confusing_step TEXT NOT NULL,
    missing_capability TEXT NOT NULL,
    current_alternative TEXT NOT NULL,
    decision_maker_role TEXT NOT NULL,
    privacy_concern TEXT NOT NULL,
    required_integration TEXT NOT NULL,
    free_text TEXT NOT NULL,
    willingness_to_pay_json TEXT NOT NULL,
    provenance TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'unverified',
    publication_status TEXT NOT NULL DEFAULT 'private',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pilot_contacts (
    session_id TEXT PRIMARY KEY REFERENCES pilot_sessions(session_id) ON DELETE CASCADE,
    contact_ciphertext TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS professional_reviews (
    review_id TEXT PRIMARY KEY,
    reviewer_role TEXT NOT NULL,
    reviewer_display_name TEXT,
    qualification TEXT NOT NULL,
    qualification_verification_status TEXT NOT NULL DEFAULT 'unverified',
    consent_to_display_name INTEGER NOT NULL DEFAULT 0,
    reviewed_capability TEXT NOT NULL,
    reviewed_rule_version TEXT NOT NULL,
    reviewed_product_version TEXT NOT NULL,
    review_scope TEXT NOT NULL,
    outcome TEXT NOT NULL,
    notes TEXT NOT NULL,
    required_changes TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    publication_status TEXT NOT NULL DEFAULT 'private',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pilot_sessions_campaign ON pilot_sessions(campaign_id);
CREATE INDEX IF NOT EXISTS idx_pilot_events_session ON pilot_events(session_id);
CREATE INDEX IF NOT EXISTS idx_pilot_events_type ON pilot_events(event_type);
CREATE INDEX IF NOT EXISTS idx_pilot_feedback_publication ON pilot_feedback(publication_status, verification_status);
"""


class PilotEvidenceStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._connection: sqlite3.Connection | None = None
        self._file_connections: list[sqlite3.Connection] = []
        self.initialize()

    def connection(self) -> sqlite3.Connection:
        if self.path == ":memory:":
            if self._connection is None:
                self._connection = sqlite3.connect(":memory:", check_same_thread=False)
                self._connection.row_factory = sqlite3.Row
                self._connection.execute("PRAGMA foreign_keys=ON")
            return self._connection
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        self._file_connections.append(connection)
        return connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        for connection in self._file_connections:
            connection.close()
        self._file_connections.clear()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(SCHEMA)

    def seed_test_campaign(self, campaign_id: str = "fixture-campaign", access_code: str = "fixture-code") -> None:
        now = utc_now()
        with self.connection() as connection:
            connection.execute("INSERT OR REPLACE INTO pilot_campaigns(campaign_id, access_code_hash, status, created_at, updated_at, is_test_fixture) VALUES (?, ?, 'active', ?, ?, 1)", (campaign_id, hash_secret(access_code), now, now))

    def create_campaign(self, campaign_id: str, access_code: str, *, expires_at: str | None = None, is_test_fixture: bool = False) -> None:
        now = utc_now()
        with self.connection() as connection:
            connection.execute("INSERT INTO pilot_campaigns(campaign_id, access_code_hash, status, expires_at, created_at, updated_at, is_test_fixture) VALUES (?, ?, 'active', ?, ?, ?, ?)", (safe_text(campaign_id, limit=80), hash_secret(access_code), expires_at, now, now, int(is_test_fixture)))

    def disable_campaign(self, campaign_id: str) -> None:
        with self.connection() as connection:
            connection.execute("UPDATE pilot_campaigns SET status='disabled', updated_at=? WHERE campaign_id=?", (utc_now(), campaign_id))

    def start_session(self, campaign_id: str, access_code: str, *, locale: str, device_class: str, viewport_class: str, workflow_id: str = "tax-holding-preparation") -> dict[str, str] | None:
        now = utc_now()
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM pilot_campaigns WHERE campaign_id=? AND is_test_fixture=0", (campaign_id,)).fetchone()
            if row is None or row["status"] != "active" or not secrets.compare_digest(row["access_code_hash"], hash_secret(access_code)):
                return None
            if row["expires_at"] and row["expires_at"] <= now:
                return None
            session_id = secrets.token_urlsafe(18)
            access_token = secrets.token_urlsafe(32)
            participant_hash = hash_secret(secrets.token_urlsafe(18))
            connection.execute("INSERT INTO pilot_sessions(session_id, session_token_hash, campaign_id, participant_hash, workflow_id, locale, device_class, viewport_class, started_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (session_id, hash_secret(access_token), campaign_id, participant_hash, safe_text(workflow_id, limit=80), safe_text(locale, limit=12), safe_text(device_class, limit=30), safe_text(viewport_class, limit=20), now, now, now))
            return {"session_id": session_id, "session_token": access_token, "mode": "closed_pilot", "consent_version": CONSENT_VERSION}

    def _authorized_session(self, connection: sqlite3.Connection, session_id: str, session_token: str) -> sqlite3.Row | None:
        row = connection.execute("SELECT * FROM pilot_sessions WHERE session_id=?", (session_id,)).fetchone()
        if row is None or not secrets.compare_digest(row["session_token_hash"], hash_secret(session_token)):
            return None
        return row

    def save_consent(self, session_id: str, session_token: str, consent: dict[str, bool]) -> bool:
        now = utc_now()
        with self.connection() as connection:
            if self._authorized_session(connection, session_id, session_token) is None or not consent.get("participation"):
                return False
            connection.execute("INSERT OR REPLACE INTO pilot_consents(session_id, participation, interaction_metrics, written_feedback, follow_up_contact, publication, version, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (session_id, 1, int(bool(consent.get("interaction_metrics"))), int(bool(consent.get("written_feedback"))), int(bool(consent.get("follow_up_contact"))), int(bool(consent.get("publication"))), CONSENT_VERSION, now))
            connection.execute("UPDATE pilot_sessions SET consent_version=?, publication_permission=?, updated_at=? WHERE session_id=?", (CONSENT_VERSION, int(bool(consent.get("publication"))), now, session_id))
            return True

    def record_event(self, session_id: str, session_token: str, event_type: str, metadata: dict[str, Any] | None, idempotency_key: str) -> str:
        if event_type not in EVENT_TYPES:
            raise ValueError("unsupported event")
        if not idempotency_key or len(idempotency_key) > 120:
            raise ValueError("invalid idempotency key")
        with self.connection() as connection:
            row = self._authorized_session(connection, session_id, session_token)
            if row is None:
                raise PermissionError("session unavailable")
            consent = connection.execute("SELECT interaction_metrics FROM pilot_consents WHERE session_id=?", (session_id,)).fetchone()
            if consent is None or not consent[0]:
                raise PermissionError("interaction consent unavailable")
            event_id = secrets.token_urlsafe(16)
            metadata_json = json.dumps(event_metadata(metadata), ensure_ascii=False, separators=(",", ":"))
            try:
                connection.execute("INSERT INTO pilot_events(event_id, session_id, event_type, metadata_json, occurred_at, idempotency_key) VALUES (?, ?, ?, ?, ?, ?)", (event_id, session_id, event_type, metadata_json, utc_now(), idempotency_key))
            except sqlite3.IntegrityError:
                return "duplicate"
            return "accepted"

    def save_profile(self, session_id: str, session_token: str, payload: dict[str, Any]) -> bool:
        allowed = ("participant_role", "experience_band", "organization_type", "case_volume_band", "current_tools", "device_type", "accessibility_needs")
        profile = {key: safe_text(payload.get(key, ""), limit=240) for key in allowed}
        with self.connection() as connection:
            if self._authorized_session(connection, session_id, session_token) is None:
                return False
            now = utc_now()
            connection.execute("INSERT OR REPLACE INTO pilot_profiles(session_id, profile_json, created_at, updated_at) VALUES (?, ?, COALESCE((SELECT created_at FROM pilot_profiles WHERE session_id=?), ?), ?)", (session_id, json.dumps(profile, ensure_ascii=False, separators=(",", ":")), session_id, now, now))
            return True

    def save_feedback(self, session_id: str, session_token: str, payload: dict[str, Any]) -> bool:
        now = utc_now()
        required = ("task_completion", "result_clarity", "source_clarity", "limitation_clarity", "entry_ease", "meeting_usefulness", "trust_level", "reuse_likelihood")
        for key in required:
            if key not in payload:
                raise ValueError("feedback field missing")
            if key != "task_completion" and (not isinstance(payload[key], int) or isinstance(payload[key], bool) or not 1 <= payload[key] <= 5):
                raise ValueError("feedback scale out of range")
        with self.connection() as connection:
            row = self._authorized_session(connection, session_id, session_token)
            if row is None:
                raise PermissionError("session unavailable")
            consent = connection.execute("SELECT written_feedback, publication FROM pilot_consents WHERE session_id=?", (session_id,)).fetchone()
            if consent is None or not consent[0]:
                raise PermissionError("written feedback consent unavailable")
            connection.execute("INSERT OR REPLACE INTO pilot_feedback(session_id, task_completion, result_clarity, source_clarity, limitation_clarity, entry_ease, meeting_usefulness, trust_level, reuse_likelihood, most_confusing_step, missing_capability, current_alternative, decision_maker_role, privacy_concern, required_integration, free_text, willingness_to_pay_json, provenance, verification_status, publication_status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (session_id, safe_text(payload["task_completion"], limit=40), payload["result_clarity"], payload["source_clarity"], payload["limitation_clarity"], payload["entry_ease"], payload["meeting_usefulness"], payload["trust_level"], payload["reuse_likelihood"], safe_text(payload.get("most_confusing_step", ""), limit=160), safe_text(payload.get("missing_capability", ""), limit=500), safe_text(payload.get("current_alternative", ""), limit=160), safe_text(payload.get("decision_maker_role", ""), limit=100), safe_text(payload.get("privacy_concern", ""), limit=500), safe_text(payload.get("required_integration", ""), limit=500), sanitize_feedback_text(payload.get("free_text", "")), json.dumps(payload.get("willingness_to_pay", {}), ensure_ascii=False, separators=(",", ":")), "user_submitted", "unverified", "private", now, now))
            return True

    def complete_session(self, session_id: str, session_token: str, *, status: str = "completed") -> bool:
        if status not in {"completed", "abandoned"}:
            raise ValueError("invalid completion status")
        with self.connection() as connection:
            if self._authorized_session(connection, session_id, session_token) is None:
                return False
            column = "completed_at" if status == "completed" else "abandoned_at"
            connection.execute(f"UPDATE pilot_sessions SET completion_status=?, {column}=?, updated_at=? WHERE session_id=?", (status, utc_now(), utc_now(), session_id))
            return True

    def participant_export(self, session_id: str, session_token: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            session = self._authorized_session(connection, session_id, session_token)
            if session is None:
                return None
            consent = connection.execute("SELECT participation, interaction_metrics, written_feedback, follow_up_contact, publication, version FROM pilot_consents WHERE session_id=?", (session_id,)).fetchone()
            profile = connection.execute("SELECT profile_json, created_at, updated_at FROM pilot_profiles WHERE session_id=?", (session_id,)).fetchone()
            feedback = connection.execute("SELECT task_completion, result_clarity, source_clarity, limitation_clarity, entry_ease, meeting_usefulness, trust_level, reuse_likelihood, most_confusing_step, missing_capability, current_alternative, decision_maker_role, privacy_concern, required_integration, free_text, willingness_to_pay_json FROM pilot_feedback WHERE session_id=?", (session_id,)).fetchone()
            return {"session": {"session_id": session["session_id"], "workflow_id": session["workflow_id"], "locale": session["locale"], "device_class": session["device_class"], "completion_status": session["completion_status"], "consent_version": session["consent_version"]}, "consent": dict(consent) if consent else None, "profile": dict(profile) if profile else None, "feedback": dict(feedback) if feedback else None}

    def deletion_dry_run(self, session_id: str, session_token: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            if self._authorized_session(connection, session_id, session_token) is None:
                return None
            counts = {}
            for table in ("pilot_events", "pilot_consents", "pilot_profiles", "pilot_feedback", "pilot_contacts", "pilot_sessions"):
                column = "session_id"
                counts[table] = connection.execute(f"SELECT COUNT(*) FROM {table} WHERE {column}=?", (session_id,)).fetchone()[0]
            return {"dry_run": True, "session_id": session_id, "affected_record_counts": counts}

    def delete_session(self, session_id: str, session_token: str) -> bool:
        with self.connection() as connection:
            if self._authorized_session(connection, session_id, session_token) is None:
                return False
            connection.execute("DELETE FROM pilot_sessions WHERE session_id=?", (session_id,))
            return True

    def aggregate_public_evidence(self) -> dict[str, Any]:
        with self.connection() as connection:
            sessions = connection.execute("SELECT COUNT(*) AS count, SUM(CASE WHEN completion_status='completed' THEN 1 ELSE 0 END) AS completed FROM pilot_sessions WHERE is_test_fixture=0").fetchone()
            feedback_count = connection.execute("SELECT COUNT(*) FROM pilot_feedback f JOIN pilot_sessions s ON s.session_id=f.session_id WHERE s.is_test_fixture=0").fetchone()[0]
            publishable_count = connection.execute("SELECT COUNT(*) FROM pilot_feedback f JOIN pilot_sessions s ON s.session_id=f.session_id JOIN pilot_consents c ON c.session_id=f.session_id WHERE s.is_test_fixture=0 AND c.publication=1 AND f.verification_status IN ('internally_reviewed','externally_verified') AND f.publication_status IN ('anonymized_quote_allowed','attribution_allowed','published')").fetchone()[0]
            durations = connection.execute("SELECT started_at, completed_at FROM pilot_sessions WHERE is_test_fixture=0 AND completion_status='completed' AND completed_at IS NOT NULL").fetchall()
            times: list[float] = []
            for row in durations:
                try:
                    times.append(max(0.0, (datetime.fromisoformat(row["completed_at"]) - datetime.fromisoformat(row["started_at"])).total_seconds()))
                except (TypeError, ValueError):
                    continue
            count = int(sessions["count"] or 0)
            completed = int(sessions["completed"] or 0)
            return {"pilot_sessions_started": count, "pilot_sessions_completed": completed, "feedback_response_count": feedback_count, "median_observed_completion_seconds": median(times) if times else None, "sample_size": completed, "small_sample_warning": count < SMALL_SAMPLE_THRESHOLD, "sample_notice": PUBLIC_NOTICE if count < SMALL_SAMPLE_THRESHOLD else "", "paying_customers": 0, "willingness_to_pay": NO_VALIDATED_PRICING, "professional_review": "pending", "publishable_testimonials": int(publishable_count), "source": "canonical pilot evidence records", "test_fixtures_excluded": True}

    def safe_export(self, *, campaign_id: str | None = None, fmt: str = "json") -> str:
        aggregate = self.aggregate_public_evidence()
        if fmt == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=sorted(aggregate))
            writer.writeheader()
            writer.writerow(aggregate)
            return output.getvalue()
        if fmt == "html":
            rows = "".join(f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>" for key, value in aggregate.items())
            return f"<!doctype html><html><body><h1>Pilot evidence pack</h1><table>{rows}</table><p>Only aggregate, non-identifying evidence is included.</p></body></html>"
        return json.dumps({"exported_at": utc_now(), "campaign_scope": campaign_id or "all approved aggregate scope", "methodology": "canonical evidence records; fixtures excluded", "aggregate": aggregate, "limitations": ["No customer, revenue, accuracy, or time-saving claim is made.", "Small samples are exploratory."], "verification_status": "aggregate_only"}, ensure_ascii=False)

    def add_professional_review(self, payload: dict[str, Any]) -> str:
        review_id = secrets.token_urlsafe(16)
        now = utc_now()
        if payload.get("outcome") not in REVIEW_OUTCOMES:
            raise ValueError("invalid review outcome")
        with self.connection() as connection:
            connection.execute("INSERT INTO professional_reviews(review_id, reviewer_role, reviewer_display_name, qualification, qualification_verification_status, consent_to_display_name, reviewed_capability, reviewed_rule_version, reviewed_product_version, review_scope, outcome, notes, required_changes, reviewed_at, publication_status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'private', ?, ?)", (review_id, safe_text(payload.get("reviewer_role", "other"), limit=80), safe_text(payload.get("reviewer_display_name", ""), limit=120), safe_text(payload.get("qualification", ""), limit=200), "unverified", int(bool(payload.get("consent_to_display_name"))), safe_text(payload.get("reviewed_capability", ""), limit=120), safe_text(payload.get("reviewed_rule_version", ""), limit=80), PRODUCT_VERSION, safe_text(payload.get("review_scope", ""), limit=500), payload["outcome"], safe_text(payload.get("notes", ""), limit=1000), safe_text(payload.get("required_changes", ""), limit=1000), now, now, now))
        return review_id

    def approve_publication(self, session_id: str) -> bool:
        with self.connection() as connection:
            row = connection.execute("SELECT c.publication, f.verification_status FROM pilot_consents c JOIN pilot_feedback f ON f.session_id=c.session_id WHERE c.session_id=?", (session_id,)).fetchone()
            if row is None or not row["publication"] or row["verification_status"] not in {"internally_reviewed", "externally_verified"}:
                return False
            connection.execute("UPDATE pilot_feedback SET publication_status='anonymized_quote_allowed', updated_at=? WHERE session_id=?", (utc_now(), session_id))
            return True

    def revoke_publication(self, session_id: str) -> bool:
        with self.connection() as connection:
            updated = connection.execute("UPDATE pilot_feedback SET publication_status='revoked', updated_at=? WHERE session_id=?", (utc_now(), session_id)).rowcount
            return bool(updated)

    def mark_feedback_reviewed(self, session_id: str, verification_status: str = "internally_reviewed") -> bool:
        if verification_status not in {"internally_reviewed", "externally_verified", "rejected", "superseded"}:
            raise ValueError("invalid verification status")
        with self.connection() as connection:
            updated = connection.execute("UPDATE pilot_feedback SET verification_status=?, updated_at=? WHERE session_id=?", (verification_status, utc_now(), session_id)).rowcount
            return bool(updated)


def build_readiness(*, database_available: bool = True, admin_configured: bool = False) -> dict[str, Any]:
    return {"status": "ready" if database_available else "degraded", "dependencies": {"database": "available" if database_available else "unavailable", "pilot_administration": "available" if admin_configured else "not_configured", "public_evidence": "available"}, "message": "Pilot evidence operations are privacy-safe and empty until real records are collected."}


def stale_review_status(reviewed_rule_version: str, current_rule_version: str) -> str:
    return "current" if reviewed_rule_version == current_rule_version else "potentially_stale"
