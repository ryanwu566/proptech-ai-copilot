"""Static contracts for the resilient API-backed guided demo run."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = (ROOT / "frontend_next" / "lib" / "demo-runner.ts").read_text(encoding="utf-8")
COMPONENT = (ROOT / "frontend_next" / "components" / "guided-demo-runner.tsx").read_text(encoding="utf-8")
ENTRIES = (ROOT / "frontend_next" / "components" / "workflow-entry-cards.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")


def test_guided_demo_has_real_api_backed_sequential_steps() -> None:
    for call in (
        "api.propertySearch",
        "api.valuation",
        "api.valuationTrend",
        "api.loanCalculate",
        "api.holdingCostCalculate",
        "api.locationInsight",
    ):
        assert call in RUNNER
    for step in ("搜尋找房", "實價估價", "市場趨勢", "貸款月付", "持有成本", "區位分析", "風險總評"):
        assert step in RUNNER
    assert "for (let index" in RUNNER
    assert "await runStep" in RUNNER
    assert "setTimeout" not in RUNNER


def test_runner_has_api_preflight_and_endpoint_details() -> None:
    assert "runDemoPreflight" in RUNNER
    assert "api.valuationDataStatus" in RUNNER
    assert "API_BASE" in RUNNER
    for status in ('"checking"', '"ready"', '"waking"', '"failed"'):
        assert status in RUNNER
    for endpoint in (
        "/valuation/property-search",
        "/valuation/estimate",
        "/valuation/trend",
        "/loan/calculate",
        "/holding-cost/calculate",
        "/location/insight",
    ):
        assert endpoint in RUNNER
    assert "後端服務可能正在喚醒" in RUNNER


def test_runner_can_stop_retry_continue_restart_and_cancel() -> None:
    for status in ('"queued"', '"running"', '"done"', '"failed"', '"skipped"'):
        assert status in RUNNER
    for action in ("重試 API 預檢", "重試失敗步驟", "從目前進度繼續", "重新開始 Demo", "取消 Demo"):
        assert action in COMPONENT
    assert "throw new DemoRunError" in RUNNER
    assert "isCancelled" in RUNNER
    assert "已成功取得的結果仍可繼續使用" in COMPONENT
    assert "index < startIndex && row.status === \"done\"" in COMPONENT


def test_demo_writes_existing_state_and_does_not_auto_save_or_download() -> None:
    for token in (
        "proptech:viewing-workspace-context",
        "HOLDING_COST_SESSION_KEY",
        "LOCATION_INSIGHT_SESSION_KEY",
        "GUIDED_DEMO_RESULT_EVENT",
        "WORKFLOW_STATUS_EVENT",
    ):
        assert token in COMPONENT
    assert "GUIDED_DEMO_RESULT_EVENT" in PAGE
    assert "saveCase(" not in COMPONENT
    assert "link.click" not in COMPONENT


def test_completion_actions_and_optional_taxoracle_are_integrated() -> None:
    for action in ("保存案件", "匯出看屋報告", "接著跑 TaxOracle 示範案"):
        assert action in COMPONENT
    assert "onSave={saveCurrentCase}" in WORKSPACE
    assert "onExport={exportReport}" in WORKSPACE
    assert "runOptionalTaxOracleDemo" in RUNNER
    assert "optional" in COMPONENT
    assert "快速 Demo" in ENTRIES


def test_runner_updates_the_yellow_assistant_for_each_demo_state() -> None:
    for message in (
        "先確認後端服務是否醒著",
        "Demo 正在跑，請等目前步驟完成",
        "目前卡在這一步，可以重試或改手動操作",
        "Demo 已完成，可以保存案件或匯出報告",
    ):
        assert message in COMPONENT
    assert "onMessage={setCaseMessage}" in WORKSPACE
