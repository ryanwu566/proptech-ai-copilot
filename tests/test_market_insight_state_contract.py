from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_market_visual_model_preserves_safe_states() -> None:
    helper = (ROOT / "frontend_next" / "lib" / "market-insight-visualization.ts").read_text(encoding="utf-8")
    state_helper = (ROOT / "frontend_next" / "lib" / "market-result-state.ts").read_text(encoding="utf-8")
    page = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
    assert '"available"' in helper
    assert '"no_data"' in state_helper
    assert '"unavailable"' in state_helper
    assert "getMarketDisplayState" in helper
    assert "model.state === \"no_data\"" in page
    assert "市場資料暫不可用" in page
    assert "不代表價格較低、風險較低或適合購買" in page


def test_partial_and_stale_states_are_disclosed_without_claiming_freshness() -> None:
    helper = (ROOT / "frontend_next" / "lib" / "market-insight-visualization.ts").read_text(encoding="utf-8")
    badge = (ROOT / "frontend_next" / "components" / "data-visualization" / "data-status-badge.tsx").read_text(encoding="utf-8")
    freshness = (ROOT / "frontend_next" / "components" / "data-visualization" / "freshness-indicator.tsx").read_text(encoding="utf-8")
    for marker in ["partial", "stale", "unknown", "source_updated_at", "coverage_status"]:
        assert marker in helper or marker in badge or marker in freshness
    assert "freshness_status" in helper


def test_evidence_contract_includes_safe_metadata_and_limitations_for_all_states() -> None:
    helper = (ROOT / "frontend_next" / "lib" / "market-insight-visualization.ts").read_text(encoding="utf-8")
    for key in ["source_name", "source_updated_at", "period", "transaction_count", "record_count", "coverage_status", "data_status", "aggregation_method", "caveat", "disclaimer"]:
        assert f'"{key}"' in helper
    assert "EvidenceDetails" in (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")


def test_market_page_does_not_transfer_results_or_add_storage() -> None:
    page = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
    section = page.split("function MarketInsight(", 1)[1].split("function LegacyTextMarketInsight", 1)[0]
    assert "sessionStorage" not in section
    assert "localStorage" not in section
    assert "document.cookie" not in section
    assert "URLSearchParams" not in section
    assert "setCase" not in section
    assert "valuation(" not in section
    assert "loan" not in section.lower()
