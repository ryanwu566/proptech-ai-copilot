"""Static contracts for recent cases and save/load controls."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGER = (ROOT / "frontend_next" / "components" / "case-manager.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")


def test_case_manager_has_save_recent_load_and_clear_controls() -> None:
    for text in ("保存案件", "最近案件", "清除目前案件", "載入", "刪除", "清空全部案件", "比較案件"):
        assert text in MANAGER
    assert "再次點擊確認刪除" in MANAGER
    assert "再次點擊確認清空全部案件" in MANAGER
    assert "alert(" not in MANAGER


def test_case_manager_has_empty_feedback_and_optional_html_export() -> None:
    assert "尚未保存案件，完成任一步後可按保存案件" in MANAGER
    assert "案件已保存，可稍後繼續分析" in MANAGER
    assert "已載入案件，可繼續分析" in MANAGER
    assert "匯出 HTML 報告" in MANAGER
    assert "onExport" in MANAGER


def test_case_manager_is_available_on_home_and_buying_wizard() -> None:
    assert "<CaseManager listOnly" in PAGE
    assert "<CaseManager current={currentCase}" in WORKSPACE
    assert "buildValuationSummaryHtml" in WORKSPACE
    assert "buildValuationShareUrl" in PAGE
