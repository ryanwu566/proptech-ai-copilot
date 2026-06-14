"""Static contracts for the interactive TaxOracle API flow."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend_next" / "lib" / "api.ts").read_text(encoding="utf-8")
STEPPER = (ROOT / "frontend_next" / "components" / "workflow-stepper.tsx").read_text(encoding="utf-8")


def test_taxoracle_uses_real_existing_api_endpoints() -> None:
    assert 'runTaxOracleCase: (taxCase: TaxCase)' in API
    assert '"/taxoracle/analyze"' in API
    assert 'api.runTaxOracleCase(taxCase)' in PAGE
    assert 'apiUrl("/taxoracle/report")' in API
    assert "setTimeout" not in PAGE.split("function TaxOracle", 1)[1].split("function MapInsight", 1)[0]
    assert "console.log" not in PAGE.split("function TaxOracle", 1)[1].split("function MapInsight", 1)[0]


def test_taxoracle_has_demo_and_custom_case_inputs() -> None:
    for text in ("範例案件", "自訂案件", "CustomTaxCaseForm", "selectedCase", "customInput"):
        assert text in PAGE
    for field in (
        "sold_self_occupied", "residency_condition_met", "purchase_within_reasonable_period",
        "purchased_self_occupied", "same_owner", "land_value_available",
        "required_docs_complete", "enters_five_year_monitoring", "exceptional_circumstances",
    ):
        assert field in PAGE


def test_taxoracle_loading_error_result_and_report_states_are_clear() -> None:
    for text in (
        "正在檢核 TX001–TX009", "稅務快篩 API 呼叫失敗，請稍後再試",
        "未通過規則", "需複核規則", "通過規則", "命中規則與下一步",
        "請先完成稅務快篩才能輸出報告", "下載 TaxOracle HTML 報告",
    ):
        assert text in PAGE
    assert "disabled={downloading}" in PAGE
    assert "isRunning" in PAGE


def test_taxoracle_rule_trace_and_step_status_are_interactive() -> None:
    assert "<details" in PAGE
    assert "row.detail" in PAGE
    assert "setTab(\"規則追蹤\")" in PAGE
    assert "activeStep" in PAGE
    assert "activeStep?: number" in STEPPER
