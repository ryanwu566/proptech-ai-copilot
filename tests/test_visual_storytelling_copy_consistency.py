"""Static contracts for shared visual state and evidence copy."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_state_labels_are_centralized_and_exact() -> None:
    source = (ROOT / "frontend_next/lib/visual-storytelling-copy.ts").read_text(encoding="utf-8")
    labels = {
        "資料可用",
        "官方資料可用",
        "目前資料不足",
        "資料暫時無法取得",
        "部分資料可用",
        "資料更新時間較早",
        "尚未評估",
        "未提供",
        "有阻擋項目",
        "展示資料，不可作為正式決策依據",
    }
    for label in labels:
        assert label in source
    for phrase in (
        "unavailable.*no_data",
        "unknown.*low risk",
        "partial.*complete",
        "missing.*0",
        "demo.*official",
    ):
        assert phrase not in source.lower()


def test_evidence_disclosure_labels_are_allowlisted() -> None:
    source = (ROOT / "frontend_next/lib/visual-storytelling-copy.ts").read_text(encoding="utf-8")
    for label in ("查看資料依據", "查看完整計算依據", "查看完整規則追蹤", "查看完整成交明細", "查看已知欄位與證據狀態"):
        assert label in source
    details = (ROOT / "frontend_next/components/data-visualization/evidence-details.tsx").read_text(encoding="utf-8")
    summary = (ROOT / "frontend_next/components/data-visualization/evidence-summary.tsx").read_text(encoding="utf-8")
    assert "<details" in details
    assert "open" not in details
    assert "EVIDENCE_DISCLOSURE_LABELS" in details
    assert "EVIDENCE_DISCLOSURE_LABELS" in summary


def test_unavailable_copy_is_conservative_and_accessible() -> None:
    source = (ROOT / "frontend_next/components/data-visualization/visual-data-unavailable-state.tsx").read_text(encoding="utf-8")
    assert "資料暫時無法取得" in source
    assert 'role="status"' in source
    assert 'aria-live="polite"' in source
    assert "值得買" not in source
