from pathlib import Path


ROOT = Path(__file__).parents[1]
FRONTEND = ROOT / "frontend_next"


def read(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def test_terrain_surface_uses_locale_copy_for_rendered_controls_and_states() -> None:
    source = read("components/terrain-risk-analysis.tsx")
    copy = read("lib/surface-copy.ts")
    assert "getSurfaceCopy(locale).terrain" in source
    assert "copy.layers[layer]" in source
    assert "copy.sourceTransparency" in source
    assert 'title: "Terrain Risk"' in copy
    assert 'title: "地勢／災害風險"' in copy
    assert 'title: "地形・災害リスク"' in copy
    assert 'title: "지형·재해 위험"' in copy
    assert "地勢與災害資料僅供看房風險參考" in copy
    assert "Terrain and hazard data is for viewing risk reference only" in copy
    assert "result.disclaimer" not in source


def test_holding_cost_rendered_surfaces_use_locale_copy_without_formula_changes() -> None:
    calculator = read("components/holding-cost-calculator.tsx")
    panel = read("components/data-visualization/holding-cost-visual-panel.tsx")
    chart = read("components/data-visualization/holding-cost-breakdown-chart.tsx")
    copy = read("lib/surface-copy.ts")
    assert "getSurfaceCopy(locale).holding" in calculator
    assert "getSurfaceCopy(locale).holding" in panel
    assert "getSurfaceCopy(locale).holding" in chart
    assert 'include_tax_estimate: true' in calculator
    assert "sessionStorage.setItem(HOLDING_COST_SESSION_KEY" in calculator
    assert 'title: "Holding Cost"' in copy
    assert 'title: "持有成本"' in copy
    assert 'title: "保有コスト"' in copy
    assert 'title: "보유 비용"' in copy


def test_shared_mode_surface_is_locale_aware_and_does_not_add_storage_or_api_calls() -> None:
    source = read("components/view-mode-toggle.tsx")
    assert "useExperienceLocale" in source
    assert "getSurfaceCopy(locale).shell" in source
    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "api." not in source


def test_localization_copy_covers_all_four_runtime_locales() -> None:
    copy = read("lib/surface-copy.ts")
    for locale in ('"zh-TW"', "en", "ja", "ko"):
        assert f"{locale}:" in copy


def test_terrain_surface_keeps_trust_boundary_language() -> None:
    copy = read("lib/surface-copy.ts")
    for phrase in ("does not mean no risk", "リスクがないことを意味しません", "위험이 없다는 뜻이 아닙니다", "不代表沒有風險"):
        assert phrase in copy
