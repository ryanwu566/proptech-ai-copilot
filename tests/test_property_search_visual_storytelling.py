from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
VISUAL_DIR = FRONTEND / "components" / "data-visualization"


def test_property_search_visual_model_reuses_actionable_state() -> None:
    helper = (FRONTEND / "lib" / "property-search-visualization.ts").read_text(encoding="utf-8")
    state = (FRONTEND / "lib" / "valuation-result-state.ts").read_text(encoding="utf-8")

    assert "getPropertySearchDisplayState" in helper
    assert 'display.kind === "available"' in helper
    assert "display.actionable" in helper
    assert "districtRanges" in helper
    assert "roadRanges" in helper
    assert "sampleCount" in helper
    assert "Number.isFinite" in helper
    assert "?? 0" not in helper
    assert "|| 0" not in helper
    assert "(result.summary.matched_count ?? 0) > 0" in state


def test_property_search_visuals_are_accessible_responsive_and_collapsed() -> None:
    files = [
        VISUAL_DIR / "property-search-price-range-chart.tsx",
        VISUAL_DIR / "property-search-sample-chart.tsx",
    ]
    for path in files:
        source = path.read_text(encoding="utf-8")
        assert 'role="img"' in source
        assert "<title>" in source
        assert "<desc>" in source
        assert "h-auto w-full" in source
        assert "max-w-full" in source
        assert "overflow-x-auto" not in source
        assert "min-w-[560px]" not in source
    evidence = (VISUAL_DIR / "property-search-evidence-summary.tsx").read_text(encoding="utf-8")
    finder = (FRONTEND / "components" / "property-finder.tsx").read_text(encoding="utf-8")
    assert "<details" in evidence
    assert "<summary" in evidence
    assert "PropertySearchEvidenceSummary" in finder
    assert 'title="查看完整成交樣本"' in finder
    assert 'if (visualModel.state !== "available")' in finder


def test_property_search_keeps_manual_api_boundary_and_no_browser_persistence() -> None:
    finder = (FRONTEND / "components" / "property-finder.tsx").read_text(encoding="utf-8")
    visual = (FRONTEND / "lib" / "property-search-visualization.ts").read_text(encoding="utf-8")
    combined = f"{finder}\n{visual}".lower()

    assert finder.count("api.propertySearch") == 1
    assert "async function search" in finder
    assert "onClick={search}" in finder
    assert "localstorage" not in combined
    assert "sessionstorage" not in combined
    assert "document.cookie" not in combined
    assert "urlsearchparams" not in combined
    assert "setcase" not in combined
    assert "token" not in combined
    assert "raw_payload" not in combined


def test_property_search_visuals_do_not_rank_investment_or_invent_missing_values() -> None:
    helper = (FRONTEND / "lib" / "property-search-visualization.ts").read_text(encoding="utf-8")
    finder = (FRONTEND / "components" / "property-finder.tsx").read_text(encoding="utf-8")

    assert "score" not in helper
    assert "investment" not in helper.lower()
    assert "VisualDataUnavailableState" in finder
    assert "數字與操作不會被解讀為低價或完成比較" in finder
    assert "尚無可用資料" not in helper
