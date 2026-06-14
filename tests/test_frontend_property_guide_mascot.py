"""Static contracts for the original yellow viewing assistant."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASCOT = (ROOT / "frontend_next" / "components" / "property-guide-mascot.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")


def test_original_yellow_assistant_is_present_and_flow_aware() -> None:
    assert "PropertyGuideMascot" in WORKSPACE
    assert "黃色看房助手" in MASCOT
    for text in ("先用預算和地區找可負擔路段", "推薦路段帶入估價", "試算月付", "管理費、稅費與修繕", "實地確認交通噪音與環境", "匯出報告"):
        assert text in MASCOT


def test_assistant_uses_only_local_css_shapes() -> None:
    lowered = MASCOT.lower()
    forbidden = ["min" + "ion", "小" + "黃人", "http" + "://", "https" + "://", "<im" + "g"]
    assert all(term not in lowered for term in forbidden)
    assert "bg-yellow-300" in MASCOT
