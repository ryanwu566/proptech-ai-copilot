"""Static contracts for the original yellow viewing assistant."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASCOT = (ROOT / "frontend_next" / "components" / "property-guide-mascot.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
WIZARD_STATUS = (ROOT / "frontend_next" / "lib" / "buying-wizard-status.ts").read_text(encoding="utf-8")
GUIDED_DEMO = (ROOT / "frontend_next" / "components" / "guided-demo-runner.tsx").read_text(encoding="utf-8")


def test_original_yellow_assistant_is_present_and_uses_plain_language() -> None:
    assert "PropertyGuideMascot" in WORKSPACE
    assert "黃色看房助手" in MASCOT
    for text in (
        "第一次用可以先看動畫",
        "看到 ? 可以點開",
        "先不用想太多，填預算和地點就好",
        "這一步是看價格合不合理",
        "買得起不只看總價，還要看月付和持有成本",
        "綠燈不是保證能買，紅燈也不是絕對不能買",
    ):
        assert text in MASCOT or text in WIZARD_STATUS
    assert 'role="status"' in MASCOT
    assert "caseMessage" in MASCOT


def test_assistant_receives_guided_demo_messages() -> None:
    for message in ("先確認後端服務是否醒著", "Demo 正在跑", "目前卡在這一步", "Demo 已完成"):
        assert message in GUIDED_DEMO
    assert "onMessage={setCaseMessage}" in WORKSPACE


def test_assistant_uses_only_local_css_shapes() -> None:
    lowered = MASCOT.lower()
    assert all(term not in lowered for term in ("minion", "小黃人", "http://", "https://", "<img"))
    assert "bg-yellow-300" in MASCOT
