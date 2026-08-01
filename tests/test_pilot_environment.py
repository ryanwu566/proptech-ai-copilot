from __future__ import annotations

from scripts.validate_pilot_environment import report


def test_environment_report_never_outputs_values_and_disables_admin_by_default(monkeypatch) -> None:
    for key in ("PILOT_EVIDENCE_DB_PATH", "PILOT_ADMIN_TOKEN", "PILOT_REVIEW_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    result = report()
    assert result["admin_configured"] is False
    assert result["review_configured"] is False
    assert result["readiness"]["dependencies"]["pilot_administration"] == "not_configured"
    assert result["secrets_output"] is False
