from datetime import datetime, timedelta, timezone
from uuid import UUID

from services.vnext.case_monitoring import SourceObservation, source_change, plan_cached_checks, NotificationEvent

NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


def test_ui_rerenders_and_checks_do_not_mean_source_changes():
    a = SourceObservation(source_id="market", content_digest="a" * 64, status="available", source_updated_at=NOW)
    assert source_change(a, a) == "unchanged"
    assert source_change(a, a.model_copy(update={"source_updated_at": NOW + timedelta(hours=1)})) == "unchanged"
    assert source_change(None, a) == "baseline"
    assert source_change(a, a.model_copy(update={"status": "failed", "content_digest": None})) == "unknown"
    assert source_change(a, a.model_copy(update={"content_digest": "b" * 64})) == "changed"
    assert source_change(a, a.model_copy(update={"source_id": "other"})) == "unknown"


def test_no_schedule_without_configuration_and_bounded_quota_plan():
    due = [(UUID(int=i), NOW - timedelta(days=2)) for i in range(1, 51)]
    assert plan_cached_checks(due, now=NOW, worker_configured=False, remaining_quota=100) == []
    assert len(plan_cached_checks(due, now=NOW, worker_configured=True, remaining_quota=100)) == 20
    assert len(plan_cached_checks(due, now=NOW, worker_configured=True, remaining_quota=2)) == 2
    assert plan_cached_checks(due, now=NOW, worker_configured=True, remaining_quota=0) == []
    assert plan_cached_checks([(UUID(int=1), NOW + timedelta(seconds=1))], now=NOW, worker_configured=True, remaining_quota=10) == []
    plan = plan_cached_checks(due + due, now=NOW, worker_configured=True, remaining_quota=100)
    assert len({item.case_id for item in plan}) == 20
    assert all(item.refresh_policy == "cached_sources_only" for item in plan)


def test_notification_is_a_reference_contract_without_destination_or_credentials():
    event = NotificationEvent(case_id=UUID(int=1), recipient_id=UUID(int=2), activity_revision=3, kind="source_changed")
    assert event.deduplication_key == f"{UUID(int=1)}:3:{UUID(int=2)}:source_changed"
    assert set(event.model_dump()) == {"case_id", "recipient_id", "activity_revision", "kind"}
