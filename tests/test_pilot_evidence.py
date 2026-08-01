from __future__ import annotations

import json

import pytest

from services.pilot_evidence import (
    EVENT_TYPES,
    PILOT_MODES,
    PilotEvidenceStore,
    event_metadata,
    is_publication_eligible,
    sanitize_feedback_text,
)


def store_with_session() -> tuple[PilotEvidenceStore, dict[str, str]]:
    store = PilotEvidenceStore(":memory:")
    store.create_campaign("campaign-a", "code-a")
    session = store.start_session("campaign-a", "code-a", locale="en", device_class="desktop", viewport_class="wide")
    assert session is not None
    assert session["mode"] == "closed_pilot"
    return store, session


def test_pilot_modes_and_task_events_are_explicit() -> None:
    assert PILOT_MODES == ("normal", "competition_demo", "offline_competition_demo", "closed_pilot", "professional_review")
    assert "pilot_started" in EVENT_TYPES
    assert "task_completed" in EVENT_TYPES


def test_invalid_or_expired_campaign_does_not_enumerate_campaign_state() -> None:
    store = PilotEvidenceStore(":memory:")
    store.create_campaign("expired", "code", expires_at="2000-01-01T00:00:00+00:00")
    assert store.start_session("missing", "code", locale="en", device_class="desktop", viewport_class="wide") is None
    assert store.start_session("expired", "code", locale="en", device_class="desktop", viewport_class="wide") is None


def test_consent_is_granular_and_publication_is_independent() -> None:
    store, session = store_with_session()
    assert store.save_consent(session["session_id"], session["session_token"], {"participation": True, "interaction_metrics": True, "written_feedback": True, "follow_up_contact": False, "publication": False})
    assert not is_publication_eligible(written_feedback_consent=True, publication_consent=False, verification_status="externally_verified", publication_status="published")


def test_event_allowlist_excludes_exact_case_values_and_is_idempotent() -> None:
    store, session = store_with_session()
    store.save_consent(session["session_id"], session["session_token"], {"participation": True, "interaction_metrics": True, "written_feedback": True, "follow_up_contact": False, "publication": False})
    metadata = event_metadata({"field_category": "financial", "price": 123456, "address": "private", "active_seconds": 99999})
    assert "price" not in metadata and "address" not in metadata
    assert metadata["active_seconds"] == 900
    assert store.record_event(session["session_id"], session["session_token"], "field_changed", metadata, "event-1") == "accepted"
    assert store.record_event(session["session_id"], session["session_token"], "field_changed", metadata, "event-1") == "duplicate"
    with pytest.raises(ValueError):
        store.record_event(session["session_id"], session["session_token"], "not-an-event", {}, "event-2")


def test_feedback_is_bounded_and_participant_export_excludes_private_identity() -> None:
    store, session = store_with_session()
    store.save_consent(session["session_id"], session["session_token"], {"participation": True, "interaction_metrics": True, "written_feedback": True, "follow_up_contact": False, "publication": False})
    assert store.save_feedback(session["session_id"], session["session_token"], {"task_completion": "completed", "result_clarity": 4, "source_clarity": 4, "limitation_clarity": 4, "entry_ease": 3, "meeting_usefulness": 4, "trust_level": 3, "reuse_likelihood": 4, "free_text": "<script>ignored as markup</script>"})
    exported = store.participant_export(session["session_id"], session["session_token"])
    assert exported is not None
    assert "participant_hash" not in json.dumps(exported)
    assert sanitize_feedback_text("x" * 3000) == "x" * 2000


def test_public_evidence_is_empty_truthful_and_excludes_fixtures() -> None:
    store = PilotEvidenceStore(":memory:")
    store.seed_test_campaign()
    result = store.aggregate_public_evidence()
    assert result["pilot_sessions_started"] == 0
    assert result["paying_customers"] == 0
    assert result["willingness_to_pay"] == "Willingness to pay has not yet been validated."
    assert result["test_fixtures_excluded"] is True
    assert result["small_sample_warning"] is True


def test_deletion_dry_run_is_explicit_and_scoped() -> None:
    store, session = store_with_session()
    store.save_consent(session["session_id"], session["session_token"], {"participation": True, "interaction_metrics": True, "written_feedback": False, "follow_up_contact": False, "publication": False})
    result = store.deletion_dry_run(session["session_id"], session["session_token"])
    assert result and result["dry_run"] is True
    assert result["affected_record_counts"]["pilot_sessions"] == 1
    assert store.delete_session(session["session_id"], session["session_token"])


def test_publication_requires_consent_and_review_then_supports_revocation() -> None:
    store, session = store_with_session()
    session_id, token = session["session_id"], session["session_token"]
    store.save_consent(session_id, token, {"participation": True, "interaction_metrics": True, "written_feedback": True, "follow_up_contact": False, "publication": True})
    payload = {"task_completion": "completed", "result_clarity": 4, "source_clarity": 4, "limitation_clarity": 4, "entry_ease": 4, "meeting_usefulness": 4, "trust_level": 4, "reuse_likelihood": 4}
    store.save_feedback(session_id, token, payload)
    assert not store.approve_publication(session_id)
    assert store.mark_feedback_reviewed(session_id)
    assert store.approve_publication(session_id)
    assert store.aggregate_public_evidence()["publishable_testimonials"] == 1
    assert store.revoke_publication(session_id)
    assert store.aggregate_public_evidence()["publishable_testimonials"] == 0
