"""Static contracts for Phase 2 data-first visual hierarchy."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE = (ROOT / "frontend_next/components/guided-journey/location-market-stage.tsx").read_text(encoding="utf-8")
AMENITY = (ROOT / "frontend_next/components/data-visualization/amenity-category-chart.tsx").read_text(encoding="utf-8")
TERRAIN = (ROOT / "frontend_next/components/data-visualization/terrain-status-matrix.tsx").read_text(encoding="utf-8")
SNAPSHOT = (ROOT / "frontend_next/components/guided-journey/location-market-snapshot.tsx").read_text(encoding="utf-8")


def test_amenity_chart_uses_existing_counts_without_quality_scoring() -> None:
    assert "poi_summary" in (ROOT / "frontend_next/lib/location-market-journey.ts").read_text(encoding="utf-8")
    assert 'role="img"' in AMENITY
    assert "aria-label" in AMENITY
    assert "API 可取得的搜尋結果摘要" in AMENITY
    assert "不代表生活品質分數" in AMENITY
    assert "item.count === null" in AMENITY
    assert "item.count" in AMENITY
    assert "Math.max" in AMENITY


def test_visual_order_keeps_summary_chart_map_before_secondary_analysis() -> None:
    order = [
        STAGE.index("<LocationInsight"),
        STAGE.index("<AmenityCategoryChart"),
        STAGE.index("地圖"),
        STAGE.index("<LocationMarketToolSelector"),
        STAGE.index("<TerrainRiskAnalysis"),
        STAGE.index("{renderMarket"),
        STAGE.index("<LocationMarketSnapshot"),
    ]
    assert order == sorted(order)


def test_terrain_matrix_preserves_independent_unknown_and_blocking_states() -> None:
    assert "Object.values(result.hazards)" in TERRAIN
    assert "不合成總分" in TERRAIN
    assert "尚未評估。這不代表沒有風險。" in TERRAIN
    assert "risk_factors.length > 0" in TERRAIN
    assert "安全認證或購買建議" in TERRAIN


def test_snapshot_is_status_only_and_has_no_completion_score() -> None:
    assert "地點與市場資料概況" in SNAPSHOT
    assert "各項資料彼此獨立" in SNAPSHOT
    for forbidden in ("3 / 4", "完成度", "安全程度", "confidence", "推薦"):
        assert forbidden not in SNAPSHOT
