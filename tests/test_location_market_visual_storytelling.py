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
    assert "item.count === null" in AMENITY
    assert "item.count" in AMENITY
    assert "Math.max" in AMENITY


def test_visual_order_keeps_summary_chart_map_before_secondary_analysis() -> None:
    order = [
        STAGE.index("<LocationInsight"),
        STAGE.index("<AmenityCategoryChart"),
        STAGE.index("<LocationMarketToolSelector"),
        STAGE.index("<TerrainRiskAnalysis"),
        STAGE.index("{renderMarket"),
        STAGE.index("<LocationMarketSnapshot"),
    ]
    assert order == sorted(order)


def test_terrain_matrix_preserves_independent_reference_states() -> None:
    assert "buildTerrainReferenceEvidence" in TERRAIN
    assert "terrainReferenceStateLabel" in TERRAIN
    assert "不形成總體結論" in TERRAIN or "viz.terrainLayerIndependent" in TERRAIN
    assert "risk_factors.length > 0" in TERRAIN
    for state in ("部分可用", "涵蓋有限", "暫時不可用", "檢查失敗", "未知", "未評估"):
        assert state in TERRAIN


def test_snapshot_is_status_only_and_has_no_completion_score() -> None:
    assert "evidenceAvailable" in SNAPSHOT
    assert "status" in SNAPSHOT
    for forbidden in ("3 / 4", "confidence", "完成度"):
        assert forbidden not in SNAPSHOT
