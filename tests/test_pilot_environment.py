from __future__ import annotations

from scripts.validate_pilot_environment import report


def clear_pilot_environment(monkeypatch) -> None:
    for key in ("PILOT_EVIDENCE_DB_PATH", "PILOT_ADMIN_TOKEN", "PILOT_REVIEW_TOKEN"):
        monkeypatch.delenv(key, raising=False)


def test_environment_report_never_outputs_values_and_disables_admin_by_default(monkeypatch) -> None:
    clear_pilot_environment(monkeypatch)
    result = report()
    assert result["admin_configured"] is False
    assert result["review_configured"] is False
    assert result["readiness"]["dependencies"]["pilot_administration"] == "not_configured"
    assert result["secrets_output"] is False


def test_environment_configuration_matrix_is_safe_and_value_free(monkeypatch) -> None:
    cases = [
        ({}, ("not_configured", "not_configured", "not_configured")),
        ({"PILOT_EVIDENCE_DB_PATH": "local.sqlite"}, ("configured", "not_configured", "not_configured")),
        ({"PILOT_EVIDENCE_DB_PATH": "local.sqlite", "PILOT_ADMIN_TOKEN": "a" * 16}, ("configured", "configured", "not_configured")),
        ({"PILOT_EVIDENCE_DB_PATH": "local.sqlite", "PILOT_REVIEW_TOKEN": "b" * 16}, ("configured", "not_configured", "configured")),
        ({"PILOT_EVIDENCE_DB_PATH": "local.sqlite", "PILOT_ADMIN_TOKEN": "a" * 16, "PILOT_REVIEW_TOKEN": "b" * 16}, ("configured", "configured", "configured")),
        ({"PILOT_EVIDENCE_DB_PATH": "local.sqlite", "PILOT_ADMIN_TOKEN": "short"}, ("configured", "malformed", "not_configured")),
    ]
    for values, expected in cases:
        clear_pilot_environment(monkeypatch)
        for key, value in values.items():
            monkeypatch.setenv(key, value)
        result = report()
        assert tuple(result["configuration_status"][key] for key in ("database", "admin", "review")) == expected
        assert result["secrets_output"] is False
