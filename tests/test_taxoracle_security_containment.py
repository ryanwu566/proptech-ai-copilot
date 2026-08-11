"""Security regressions for anonymous TaxOracle persistence and history access."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from backend.api_main import app
from models.schemas import TaxCase
from services import tax_service


ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def _case() -> TaxCase:
    return TaxCase(
        case_id="SEC-001-TEST",
        client_name="Security Test",
        sold_self_occupied=True,
        residency_condition_met=True,
        purchase_within_reasonable_period=True,
        purchased_self_occupied=True,
        same_owner=True,
        land_value_available=True,
        required_docs_complete=True,
        enters_five_year_monitoring=True,
        exceptional_circumstances=False,
    )


def _payload() -> dict[str, Any]:
    return {
        "case_id": "SEC-001-API",
        "client_name": "Security API Test",
        "sold_self_occupied": True,
        "residency_condition_met": True,
        "purchase_within_reasonable_period": True,
        "purchased_self_occupied": True,
        "same_owner": True,
        "land_value_available": True,
        "required_docs_complete": True,
        "enters_five_year_monitoring": True,
        "exceptional_circumstances": False,
    }


def _stub_explanation(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        tax_service,
        "generate_ai_explanation",
        lambda _result: {
            "source": "test",
            "headline": "test",
            "customer_script": "test",
        },
    )


def test_tax_analysis_safe_default_does_not_persist(monkeypatch) -> None:
    saved: list[tuple[Any, ...]] = []
    _stub_explanation(monkeypatch)
    monkeypatch.setattr(tax_service, "save_tax_analysis", lambda *args: saved.append(args))

    result = tax_service.analyze_tax_case(_case())

    assert result["eligibility_status"] == "eligible"
    assert result["signal_color"] == "green"
    assert saved == []


def test_explicit_non_persistent_analysis_does_not_save(monkeypatch) -> None:
    saved: list[tuple[Any, ...]] = []
    _stub_explanation(monkeypatch)
    monkeypatch.setattr(tax_service, "save_tax_analysis", lambda *args: saved.append(args))

    tax_service.analyze_tax_case(_case(), persist=False)

    assert saved == []


def test_persistence_requires_explicit_opt_in(monkeypatch) -> None:
    saved: list[tuple[Any, ...]] = []
    _stub_explanation(monkeypatch)
    monkeypatch.setattr(tax_service, "save_tax_analysis", lambda *args: saved.append(args))

    tax_service.analyze_tax_case(_case(), persist=True)

    assert len(saved) == 1
    assert saved[0][0] == "SEC-001-TEST"


def test_public_analyze_explicitly_disables_persistence(monkeypatch) -> None:
    observed: list[bool] = []
    original = tax_service.analyze_tax_case
    _stub_explanation(monkeypatch)
    monkeypatch.setattr(tax_service, "save_tax_analysis", lambda *_args: None)

    def wrapped(case: TaxCase, persist: bool = False) -> dict[str, Any]:
        observed.append(persist)
        return original(case, persist=persist)

    monkeypatch.setattr(tax_service, "analyze_tax_case", wrapped)
    response = client.post("/taxoracle/analyze", json=_payload())

    assert response.status_code == 200
    assert response.json()["eligibility_status"] == "eligible"
    assert observed == [False]


def test_anonymous_history_list_and_detail_are_generic_not_found(monkeypatch) -> None:
    from backend.repositories import sqlite_repo

    def unexpected_repository_access(*_args, **_kwargs):
        raise AssertionError("history repository must not be queried")

    monkeypatch.setattr(sqlite_repo, "list_tax_analyses", unexpected_repository_access)
    monkeypatch.setattr(sqlite_repo, "get_tax_analysis", unexpected_repository_access)

    responses = [
        client.get("/history"),
        client.get("/history/1"),
        client.get("/history/999999"),
    ]

    assert all(response.status_code == 404 for response in responses)
    assert all(response.json() == {"detail": "Not Found"} for response in responses)
    public_bodies = " ".join(response.text.lower() for response in responses)
    for forbidden in ("client_name", "case_id", "payload", "risk_score", "created_at"):
        assert forbidden not in public_bodies


def test_public_report_remains_non_persistent(monkeypatch) -> None:
    saved: list[tuple[Any, ...]] = []
    _stub_explanation(monkeypatch)
    monkeypatch.setattr(tax_service, "save_tax_analysis", lambda *args: saved.append(args))

    response = client.post("/taxoracle/report", json=_payload())

    assert response.status_code == 200
    assert "TaxOracle" in response.text
    assert saved == []


def test_public_frontends_have_no_global_tax_history_entry_or_fetch() -> None:
    page = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
    sidebar = (ROOT / "frontend_next/components/sidebar.tsx").read_text(encoding="utf-8")
    api_client = (ROOT / "frontend_next/lib/api.ts").read_text(encoding="utf-8")
    streamlit = (ROOT / "app.py").read_text(encoding="utf-8")

    assert "function History()" not in page
    assert "api.history" not in page
    assert '"歷史案件"' not in sidebar
    assert '"/history"' not in api_client
    assert "list_tax_analyses" not in streamlit
    assert "get_tax_analysis" not in streamlit
    assert "analyze_tax_case(case, persist=False)" in streamlit
