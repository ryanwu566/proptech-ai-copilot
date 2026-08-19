"""Trust and safe-failure contracts for the Phase 4 case journey."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE = (ROOT / "frontend_next/components/guided-journey/decision-case-stage.tsx").read_text(encoding="utf-8")
COMMAND_CENTER = (ROOT / "frontend_next/components/property-case-command-center.tsx").read_text(encoding="utf-8")
MISSING_PANEL = (ROOT / "frontend_next/components/data-visualization/property-case-missing-data-panel.tsx").read_text(encoding="utf-8")
READINESS = (ROOT / "frontend_next/lib/property-case-readiness.ts").read_text(encoding="utf-8")
PROPERTY_CASE = (ROOT / "frontend_next/lib/property-case.ts").read_text(encoding="utf-8")


def test_embedded_command_center_reuses_existing_readiness_and_print_guards() -> None:
    assert "buildPropertyCaseReadiness" in COMMAND_CENTER
    assert "buildPropertyCaseVisualModel" in COMMAND_CENTER
    assert "PARTIAL_CASE_PRINT_NOTICE" in COMMAND_CENTER
    assert "disabled={!draft.readiness.print_ready}" in COMMAND_CENTER
    assert "embedded = false" in COMMAND_CENTER
    assert "showComparison = true" in COMMAND_CENTER


def test_case_completeness_is_not_a_purchase_or_risk_score() -> None:
    source = "\n".join((STAGE, COMMAND_CENTER, READINESS, PROPERTY_CASE, MISSING_PANEL))
    # Trust boundary: check that the completion-is-not-score semantic exists
    # either directly in copy or via the runtime-copy key
    runtime_copy = (ROOT / "frontend_next/lib/runtime-copy.ts").read_text(encoding="utf-8")
    combined = source + "\n" + runtime_copy
    assert "案件完整度不是投資評分" in combined or "viz.completenessNote" in source
    for forbidden in ("winner", "第一名", "最佳案件", "推薦購買", "自動出價", "安全物件"):
        assert forbidden not in source.lower()
    assert "資料不足不會被填成 0" in combined or "viz.missingNote" in source


def test_evidence_and_partial_print_copy_remain_visible() -> None:
    assert "查看案件證據與欄位狀態" in COMMAND_CENTER
    assert "PARTIAL_CASE_PRINT_NOTICE" in COMMAND_CENTER
    assert "isTrustedValuation" in PROPERTY_CASE
