from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_closed_pilot_has_explicit_modes_consent_and_four_locale_copy() -> None:
    source = (ROOT / "frontend_next/components/pilot-evidence-center.tsx").read_text(encoding="utf-8")
    for marker in ("closed_pilot", "participation", "interaction_metrics", "written_feedback", "publication", "zh-TW", "en:", "ja:", "ko:"):
        assert marker in source
    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "document.cookie" not in source


def test_pilot_client_uses_explicit_api_actions_and_no_provider_secrets() -> None:
    api = (ROOT / "frontend_next/lib/api.ts").read_text(encoding="utf-8")
    source = (ROOT / "frontend_next/components/pilot-evidence-center.tsx").read_text(encoding="utf-8")
    for marker in ("/pilot/access", "/pilot/sessions/", "X-Pilot-Session-Token"):
        assert marker in api
    assert "TDX_CLIENT_SECRET" not in source
    assert "COMMUTE_REFRESH_TOKEN" not in source


def test_pilot_operations_docs_define_empty_evidence_and_human_review() -> None:
    runbook = (ROOT / "docs/pilot-release-runbook.md").read_text(encoding="utf-8")
    for marker in ("test fixtures", "deletion", "professional", "Exploratory evidence", "zero paying customers"):
        assert marker in runbook
