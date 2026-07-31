"""Runtime and frontend boundary checks for the official-data package."""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.api_main import app


ROOT = Path(__file__).resolve().parents[1]


def test_source_status_endpoints_do_not_call_external_providers() -> None:
    client = TestClient(app)
    terrain = client.get("/terrain-risk/sources")
    tax = client.get("/taxoracle/sources")
    assert terrain.status_code == 200
    assert tax.status_code == 200
    assert terrain.json()["status"] == "not_checked"
    assert tax.json()["calculation_boundary"] == "preliminary_screening_only"


def test_tax_result_adds_trace_without_changing_existing_rule_output() -> None:
    from models.schemas import TaxCase
    from rules.tax_rules import evaluate_tax_case
    from services.tax_service import analyze_tax_case

    case = TaxCase("FIXTURE", "Private fixture", True, True, True, True, True, True, True, True, False)
    baseline = evaluate_tax_case(case).to_dict()
    result = analyze_tax_case(case, persist=False)
    assert result["eligibility_status"] == baseline["eligibility_status"]
    assert result["risk_score"] == baseline["risk_score"]
    assert result["official_rule_trace"]["rule_version"] == "compatibility-screening-v1"
    assert result["tax_output_boundary"] == "preliminary_screening_only"


def test_new_frontend_status_surface_is_localized_and_has_no_storage() -> None:
    component = (ROOT / "frontend_next" / "components" / "official-data-status-card.tsx").read_text(encoding="utf-8")
    assert all(locale in component for locale in ('"zh-TW"', "en:", "ja:", "ko:"))
    assert "localStorage" not in component
    assert "sessionStorage" not in component
    assert "window.location" not in component
