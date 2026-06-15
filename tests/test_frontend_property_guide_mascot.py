"""Static contracts for the original yellow viewing assistant."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASCOT = (ROOT / "frontend_next" / "components" / "property-guide-mascot.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
WIZARD_STATUS = (ROOT / "frontend_next" / "lib" / "buying-wizard-status.ts").read_text(encoding="utf-8")


def test_original_yellow_assistant_is_present_and_flow_aware() -> None:
    assert "PropertyGuideMascot" in WORKSPACE
    assert "黃色看房助手" in MASCOT
    for text in ("先用預算和地區找可負擔路段", "推薦路段帶入估價", "試算月付", "管理費、稅費與修繕", "實地確認交通噪音與環境", "匯出報告"):
        assert text in MASCOT
    assert 'role="status"' in MASCOT
    assert "shadow-md" in MASCOT
    assert "ring-yellow-200" in MASCOT
    assert "riskSignal" in MASCOT
    assert "workflowStatus" in MASCOT
    assert "getActiveWizardStep" in MASCOT
    for text in ("確認這個路段的合理價格", "不要只看單一分數", "最後補做稅務快篩"):
        assert text in WIZARD_STATUS
    for text in ("實地確認屋況", "保留議價空間", "先比較其他路段"):
        assert text in MASCOT
    for text in ("保存兩個以上案件", "第 1 名不代表一定要買", "若資料不足"):
        assert text in MASCOT
    assert "caseMessage" in MASCOT


def test_assistant_uses_only_local_css_shapes() -> None:
    lowered = MASCOT.lower()
    forbidden = ["min" + "ion", "小" + "黃人", "http" + "://", "https" + "://", "<im" + "g"]
    assert all(term not in lowered for term in forbidden)
    assert "bg-yellow-300" in MASCOT


def test_assistant_receives_guided_demo_recovery_messages() -> None:
    guided_demo = (ROOT / "frontend_next" / "components" / "guided-demo-runner.tsx").read_text(encoding="utf-8")
    for message in ("先確認後端服務是否醒著", "Demo 正在跑，請等目前步驟完成", "目前卡在這一步，可以重試或改手動操作"):
        assert message in guided_demo
    assert "onMessage?." in guided_demo
    assert "onMessage={setCaseMessage}" in WORKSPACE
