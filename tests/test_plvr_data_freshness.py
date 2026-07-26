from datetime import UTC, datetime, timedelta

from services.plvr_data_freshness import evaluate_plvr_freshness


NOW = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)


def evaluate(**overrides):
    values = {
        "official_records_count": 10,
        "latest_import_status": "completed",
        "last_updated": NOW - timedelta(days=30),
        "newest_effective_period": "2026-06",
        "provider_available": True,
        "now": NOW,
    }
    values.update(overrides)
    return evaluate_plvr_freshness(**values)


def test_fresh_boundary_is_inclusive() -> None:
    result = evaluate(last_updated=NOW - timedelta(days=120), newest_effective_period="2026-03")
    assert result["freshness_status"] == "fresh"
    assert result["operator_attention_required"] is False


def test_aging_import_and_period() -> None:
    result = evaluate(last_updated=NOW - timedelta(days=121), newest_effective_period="2026-02")
    assert result["freshness_status"] == "aging"
    assert result["freshness_reason_code"] == "import_and_period_aging"


def test_stale_import_and_period() -> None:
    result = evaluate(last_updated=NOW - timedelta(days=211), newest_effective_period="2025-10")
    assert result["freshness_status"] == "stale"
    assert result["freshness_reason_code"] == "import_and_period_stale"


def test_each_single_dimension_reason_is_preserved() -> None:
    assert evaluate(last_updated=NOW - timedelta(days=121), newest_effective_period="2026-06")["freshness_reason_code"] == "import_aging"
    assert evaluate(last_updated=NOW - timedelta(days=30), newest_effective_period="2026-02")["freshness_reason_code"] == "period_aging"
    assert evaluate(last_updated=NOW - timedelta(days=211), newest_effective_period="2026-06")["freshness_reason_code"] == "import_stale"
    assert evaluate(last_updated=NOW - timedelta(days=30), newest_effective_period="2025-10")["freshness_reason_code"] == "period_stale"


def test_unknown_inputs_never_become_zero_age() -> None:
    for overrides, reason in (
        ({"last_updated": None}, "latest_import_missing"),
        ({"newest_effective_period": None}, "effective_period_missing"),
        ({"newest_effective_period": "not-a-period"}, "freshness_input_invalid"),
        ({"latest_import_status": "failed"}, "latest_import_not_completed"),
        ({"newest_effective_period": "2027-01"}, "freshness_input_invalid"),
    ):
        result = evaluate(**overrides)
        assert result["freshness_status"] == "unknown"
        assert result["freshness_reason_code"] == reason
        assert result["latest_import_age_days"] is None
        assert result["newest_effective_period_lag_months"] is None


def test_no_official_data_and_provider_unavailable_are_distinct() -> None:
    no_data = evaluate(official_records_count=0)
    assert no_data["freshness_reason_code"] == "official_data_missing"
    assert no_data["latest_import_at"] is None
    unavailable = evaluate(provider_available=False)
    assert unavailable["freshness_status"] == "unavailable"
    assert unavailable["freshness_reason_code"] == "provider_unavailable"
    assert unavailable["operator_attention_required"] is True
