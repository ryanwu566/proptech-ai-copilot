"""Closed-pilot, evidence, and professional-review API boundaries."""

from __future__ import annotations

import os
import secrets
import time
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.pilot_evidence import (
    CONSENT_VERSION,
    EVENT_TYPES,
    PILOT_MODES,
    REVIEW_OUTCOMES,
    PilotEvidenceStore,
    build_readiness,
    event_metadata,
    safe_text,
)
from services.observability import build_observation, normalize_correlation_id, sanitize_client_error


router = APIRouter(tags=["pilot-evidence"])
PILOT_DB_PATH_ENV = "PILOT_EVIDENCE_DB_PATH"
PILOT_ADMIN_TOKEN_ENV = "PILOT_ADMIN_TOKEN"
PILOT_REVIEW_TOKEN_ENV = "PILOT_REVIEW_TOKEN"
_store: PilotEvidenceStore | None = None
_rate_buckets: dict[str, list[float]] = {}


def get_pilot_store() -> PilotEvidenceStore:
    global _store
    if _store is None:
        from backend.db import DB_PATH

        _store = PilotEvidenceStore(os.getenv(PILOT_DB_PATH_ENV, str(DB_PATH)))
    return _store


def reset_pilot_store_for_tests(store: PilotEvidenceStore | None = None) -> None:
    global _store
    _store = store


def _rate_limit(request: Request, bucket: str) -> None:
    key = f"{bucket}:{request.client.host if request.client else 'unknown'}"
    now = time.monotonic()
    recent = [item for item in _rate_buckets.get(key, []) if item > now - 60]
    if len(recent) >= 30:
        raise HTTPException(status_code=429, detail="Too many requests. Please retry later.")
    recent.append(now)
    _rate_buckets[key] = recent


def _session_token(value: str | None) -> str:
    if not value or len(value) > 200:
        raise HTTPException(status_code=401, detail="Pilot session is unavailable.")
    return value


def _admin_authorized(token: str | None) -> bool:
    configured = os.getenv(PILOT_ADMIN_TOKEN_ENV, "").strip()
    return bool(configured and token and secrets.compare_digest(token, configured))


def _review_authorized(token: str | None) -> bool:
    configured = os.getenv(PILOT_REVIEW_TOKEN_ENV, "").strip() or os.getenv(PILOT_ADMIN_TOKEN_ENV, "").strip()
    return bool(configured and token and secrets.compare_digest(token, configured))


class PilotAccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str = Field(min_length=1, max_length=80)
    pilot_code: str = Field(min_length=1, max_length=200)
    locale: str = Field(default="zh-TW", max_length=12)
    device_class: str = Field(default="unknown", max_length=30)
    viewport_class: str = Field(default="unknown", max_length=20)
    workflow_id: str = Field(default="tax-holding-preparation", max_length=80)


class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    participation: bool
    interaction_metrics: bool = False
    written_feedback: bool = False
    follow_up_contact: bool = False
    publication: bool = False


class ProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    participant_role: str = Field(default="other", max_length=80)
    experience_band: str = Field(default="", max_length=60)
    organization_type: str = Field(default="", max_length=80)
    case_volume_band: str = Field(default="", max_length=60)
    current_tools: str = Field(default="", max_length=240)
    device_type: str = Field(default="", max_length=40)
    accessibility_needs: str = Field(default="", max_length=240)


class PilotEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str
    idempotency_key: str = Field(min_length=1, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_type")
    @classmethod
    def allowed_event(cls, value: str) -> str:
        if value not in EVENT_TYPES:
            raise ValueError("unsupported event")
        return value


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_completion: str = Field(min_length=1, max_length=40)
    result_clarity: int = Field(ge=1, le=5)
    source_clarity: int = Field(ge=1, le=5)
    limitation_clarity: int = Field(ge=1, le=5)
    entry_ease: int = Field(ge=1, le=5)
    meeting_usefulness: int = Field(ge=1, le=5)
    trust_level: int = Field(ge=1, le=5)
    reuse_likelihood: int = Field(ge=1, le=5)
    most_confusing_step: str = Field(default="", max_length=160)
    missing_capability: str = Field(default="", max_length=500)
    current_alternative: str = Field(default="", max_length=160)
    decision_maker_role: str = Field(default="", max_length=100)
    privacy_concern: str = Field(default="", max_length=500)
    required_integration: str = Field(default="", max_length=500)
    free_text: str = Field(default="", max_length=2000)
    willingness_to_pay: dict[str, Any] = Field(default_factory=dict)


class ProfessionalReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer_role: str = Field(min_length=1, max_length=80)
    reviewer_display_name: str = Field(default="", max_length=120)
    qualification: str = Field(default="", max_length=200)
    consent_to_display_name: bool = False
    reviewed_capability: str = Field(min_length=1, max_length=120)
    reviewed_rule_version: str = Field(min_length=1, max_length=80)
    review_scope: str = Field(min_length=1, max_length=500)
    outcome: str
    notes: str = Field(default="", max_length=1000)
    required_changes: str = Field(default="", max_length=1000)

    @field_validator("outcome")
    @classmethod
    def allowed_outcome(cls, value: str) -> str:
        if value not in REVIEW_OUTCOMES:
            raise ValueError("unsupported review outcome")
        return value


class ClientErrorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: str = Field(default="client_error", max_length=80)
    route: str = Field(default="unknown", max_length=120)
    boundary: str = Field(default="unknown", max_length=40)
    pilot_mode: str = Field(default="normal", max_length=40)


@router.get("/pilot/modes")
def pilot_modes() -> dict[str, Any]:
    return {"modes": list(PILOT_MODES), "default": "normal", "pilot_modes_require_explicit_entry": True}


@router.post("/pilot/access", status_code=201)
def start_pilot_session(request: Request, payload: PilotAccessRequest) -> dict[str, Any]:
    _rate_limit(request, "access")
    try:
        result = get_pilot_store().start_session(payload.campaign_id, payload.pilot_code, locale=payload.locale, device_class=payload.device_class, viewport_class=payload.viewport_class, workflow_id=payload.workflow_id)
    except Exception:
        result = None
    if result is None:
        # Deliberately do not distinguish missing, disabled, expired, or invalid campaigns.
        raise HTTPException(status_code=404, detail="Pilot access is unavailable.")
    return result


@router.post("/pilot/sessions/{session_id}/consent")
def submit_consent(request: Request, session_id: str, payload: ConsentRequest, x_pilot_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    _rate_limit(request, "consent")
    if not get_pilot_store().save_consent(session_id, _session_token(x_pilot_session_token), payload.model_dump()):
        raise HTTPException(status_code=404, detail="Pilot session is unavailable.")
    return {"status": "accepted", "mode": "closed_pilot", "consent_version": CONSENT_VERSION}


@router.post("/pilot/sessions/{session_id}/profile")
def submit_profile(session_id: str, payload: ProfileRequest, x_pilot_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    # The profile is intentionally bounded and not joined to public aggregate output.
    if not get_pilot_store().save_profile(session_id, _session_token(x_pilot_session_token), payload.model_dump()):
        raise HTTPException(status_code=404, detail="Pilot session is unavailable.")
    return {"status": "accepted", "profile_fields_recorded": ["participant_role", "experience_band", "organization_type", "case_volume_band", "current_tools", "device_type", "accessibility_needs"]}


@router.post("/pilot/sessions/{session_id}/events")
def submit_event(request: Request, session_id: str, payload: PilotEventRequest, x_pilot_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    _rate_limit(request, "events")
    try:
        result = get_pilot_store().record_event(session_id, _session_token(x_pilot_session_token), payload.event_type, event_metadata(payload.metadata), payload.idempotency_key)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Pilot evidence consent is unavailable.")
    except ValueError:
        raise HTTPException(status_code=422, detail="Pilot event is invalid.")
    return {"status": result, "evidence_state": "complete" if result in {"accepted", "duplicate"} else "degraded"}


@router.post("/pilot/sessions/{session_id}/feedback")
def submit_feedback(request: Request, session_id: str, payload: FeedbackRequest, x_pilot_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    _rate_limit(request, "feedback")
    try:
        get_pilot_store().save_feedback(session_id, _session_token(x_pilot_session_token), payload.model_dump())
    except PermissionError:
        raise HTTPException(status_code=403, detail="Written feedback consent is unavailable.")
    except ValueError:
        raise HTTPException(status_code=422, detail="Feedback is invalid.")
    return {"status": "accepted", "publication_status": "private", "verification_status": "unverified"}


@router.post("/pilot/sessions/{session_id}/complete")
def complete_pilot(session_id: str, x_pilot_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    if not get_pilot_store().complete_session(session_id, _session_token(x_pilot_session_token)):
        raise HTTPException(status_code=404, detail="Pilot session is unavailable.")
    return {"status": "completed", "mode": "closed_pilot", "message": "Pilot session completed; evidence remains preliminary until reviewed."}


@router.get("/pilot/sessions/{session_id}/export")
def export_participant_session(session_id: str, x_pilot_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    result = get_pilot_store().participant_export(session_id, _session_token(x_pilot_session_token))
    if result is None:
        raise HTTPException(status_code=404, detail="Pilot session is unavailable.")
    return result


@router.post("/pilot/sessions/{session_id}/deletion-dry-run")
def deletion_dry_run(session_id: str, x_pilot_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    result = get_pilot_store().deletion_dry_run(session_id, _session_token(x_pilot_session_token))
    if result is None:
        raise HTTPException(status_code=404, detail="Pilot session is unavailable.")
    return result


@router.delete("/pilot/sessions/{session_id}")
def delete_participant_session(session_id: str, x_pilot_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    if not get_pilot_store().delete_session(session_id, _session_token(x_pilot_session_token)):
        raise HTTPException(status_code=404, detail="Pilot session is unavailable.")
    return {"status": "deleted", "session_id": session_id, "audit_note": "Participant evidence was removed; no other participant records were targeted."}


@router.get("/pilot/public-evidence")
def public_evidence() -> dict[str, Any]:
    return get_pilot_store().aggregate_public_evidence()


@router.get("/pilot/source-status")
def pilot_source_status() -> dict[str, Any]:
    return {"status": "available", "source": "canonical pilot evidence records", "data_status": "empty_until_real_records", "test_fixtures_excluded": True}


@router.get("/pilot/readiness")
def pilot_readiness() -> dict[str, Any]:
    return build_readiness(database_available=True, admin_configured=bool(os.getenv(PILOT_ADMIN_TOKEN_ENV, "").strip()))


@router.get("/liveness")
def liveness() -> dict[str, str]:
    return {"status": "ok", "service": "proptech-ai-copilot"}


@router.get("/readiness")
def readiness() -> dict[str, Any]:
    return pilot_readiness()


@router.get("/source-status")
def source_status() -> dict[str, Any]:
    return pilot_source_status()


@router.get("/release-version")
def release_version() -> dict[str, str]:
    return {"product_version": "0.1.0", "pilot_evidence_version": "pilot-evidence-v1", "rule_version": "existing-rule-contracts", "frontend_build_version": "runtime-reported"}


@router.post("/professional-review", status_code=201)
def submit_professional_review(payload: ProfessionalReviewRequest, x_pilot_review_token: str | None = Header(default=None)) -> dict[str, Any]:
    if not _review_authorized(x_pilot_review_token):
        raise HTTPException(status_code=503, detail="Professional review mode is not configured.")
    review_id = get_pilot_store().add_professional_review(payload.model_dump())
    return {"status": "received", "review_id": review_id, "publication_status": "private", "public_endorsement": False}


@router.get("/professional-review/status")
def professional_review_status() -> dict[str, Any]:
    return {"status": "pending", "publication_status": "private", "qualification_verification": "not_configured", "public_endorsement": False}


@router.post("/client-errors", status_code=202)
def report_client_error(request: Request, payload: ClientErrorRequest) -> dict[str, Any]:
    _rate_limit(request, "client-errors")
    correlation_id = normalize_correlation_id(request.headers.get("X-Correlation-ID"))
    safe = sanitize_client_error(payload.error_code, payload.route, payload.boundary)
    observation = build_observation(correlation_id=correlation_id, route=safe["route"], method="CLIENT", status_code=500, duration_ms=0, pilot_mode=payload.pilot_mode, error_code=safe["error_code"])
    # Deliberately return only a support reference and categorical acceptance.
    return {"status": "accepted", "support_reference": observation["correlation_id"], "recorded_fields": ["correlation_id", "route", "error_code", "boundary", "pilot_mode"]}


@router.post("/pilot/admin/campaigns", status_code=201)
def create_pilot_campaign(payload: PilotAccessRequest, x_pilot_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
    if not _admin_authorized(x_pilot_admin_token):
        raise HTTPException(status_code=503, detail="Pilot administration is not configured.")
    # The access code is accepted only over the protected admin boundary and
    # is never returned or logged by this endpoint.
    get_pilot_store().create_campaign(payload.campaign_id, payload.pilot_code)
    return {"status": "created", "campaign_id": payload.campaign_id, "access_code_returned": False}


@router.post("/pilot/admin/campaigns/{campaign_id}/disable")
def disable_pilot_campaign(campaign_id: str, x_pilot_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
    if not _admin_authorized(x_pilot_admin_token):
        raise HTTPException(status_code=503, detail="Pilot administration is not configured.")
    get_pilot_store().disable_campaign(campaign_id)
    return {"status": "disabled", "campaign_id": campaign_id}


@router.get("/pilot/admin/evidence/export")
def export_admin_evidence(fmt: str = "json", x_pilot_admin_token: str | None = Header(default=None)) -> Response:
    if not _admin_authorized(x_pilot_admin_token):
        raise HTTPException(status_code=503, detail="Pilot administration is not configured.")
    if fmt not in {"json", "csv", "html"}:
        raise HTTPException(status_code=422, detail="Unsupported export format.")
    media_type = {"json": "application/json", "csv": "text/csv", "html": "text/html"}[fmt]
    return Response(content=get_pilot_store().safe_export(fmt=fmt), media_type=media_type, headers={"X-Evidence-Export": "aggregate-only"})


@router.post("/pilot/admin/evidence/{session_id}/review")
def review_pilot_feedback(session_id: str, verification_status: str = "internally_reviewed", x_pilot_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
    if not _admin_authorized(x_pilot_admin_token):
        raise HTTPException(status_code=503, detail="Pilot administration is not configured.")
    try:
        reviewed = get_pilot_store().mark_feedback_reviewed(session_id, verification_status)
    except ValueError:
        raise HTTPException(status_code=422, detail="Review status is invalid.")
    if not reviewed:
        raise HTTPException(status_code=404, detail="Pilot evidence is unavailable.")
    return {"status": "reviewed", "publication_status": "private", "public_endorsement": False}


@router.post("/pilot/admin/evidence/{session_id}/approve-publication")
def approve_pilot_publication(session_id: str, x_pilot_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
    if not _admin_authorized(x_pilot_admin_token):
        raise HTTPException(status_code=503, detail="Pilot administration is not configured.")
    if not get_pilot_store().approve_publication(session_id):
        raise HTTPException(status_code=409, detail="Publication prerequisites are not met.")
    return {"status": "approved", "publication_status": "anonymized_quote_allowed", "public_endorsement": False}


@router.post("/pilot/admin/evidence/{session_id}/revoke-publication")
def revoke_pilot_publication(session_id: str, x_pilot_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
    if not _admin_authorized(x_pilot_admin_token):
        raise HTTPException(status_code=503, detail="Pilot administration is not configured.")
    if not get_pilot_store().revoke_publication(session_id):
        raise HTTPException(status_code=404, detail="Pilot evidence is unavailable.")
    return {"status": "revoked", "publication_status": "revoked", "public_endorsement": False}
