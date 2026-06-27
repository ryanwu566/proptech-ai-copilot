"""Static contracts for beginner and professional display modes."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODE = (ROOT / "frontend_next" / "lib" / "view-mode.ts").read_text(encoding="utf-8")
TOGGLE = (ROOT / "frontend_next" / "components" / "view-mode-toggle.tsx").read_text(encoding="utf-8")
DISCLOSURE = (ROOT / "frontend_next" / "components" / "detail-disclosure.tsx").read_text(encoding="utf-8")
TOPBAR = (ROOT / "frontend_next" / "components" / "topbar.tsx").read_text(encoding="utf-8")
WIZARD = (ROOT / "frontend_next" / "components" / "buying-wizard.tsx").read_text(encoding="utf-8")
FINDER = (ROOT / "frontend_next" / "components" / "property-finder.tsx").read_text(encoding="utf-8")
LOAN = (ROOT / "frontend_next" / "components" / "loan-calculator.tsx").read_text(encoding="utf-8")
HOLDING = (ROOT / "frontend_next" / "components" / "holding-cost-calculator.tsx").read_text(encoding="utf-8")
LOCATION = (ROOT / "frontend_next" / "components" / "location-insight.tsx").read_text(encoding="utf-8")
COMPARE = (ROOT / "frontend_next" / "components" / "case-comparison-panel.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
MASCOT = (ROOT / "frontend_next" / "components" / "property-guide-mascot.tsx").read_text(encoding="utf-8")
PRODUCT_UI = (ROOT / "frontend_next" / "components" / "product-ui.tsx").read_text(encoding="utf-8")


def test_view_mode_defaults_to_beginner_and_persists_locally() -> None:
    assert 'type ViewMode = "beginner" | "pro"' in MODE
    assert 'VIEW_MODE_STORAGE_KEY = "proptech.viewMode.v1"' in MODE
    assert 'DEFAULT_VIEW_MODE: ViewMode = "beginner"' in MODE
    assert "window.localStorage.setItem" in MODE


def test_toggle_is_available_sitewide_and_in_wizard() -> None:
    for text in ("新手模式：我只想知道值不值得看", "專業模式：我要看完整分析細節"):
        assert text in TOGGLE
    assert "ViewModeToggle compact" in TOPBAR
    assert "ViewModeToggle" in WIZARD
    assert "aria-pressed" in TOGGLE


def test_detail_disclosure_collapses_beginner_and_expands_pro() -> None:
    assert "export function DetailDisclosure" in DISCLOSURE
    assert 'viewMode === "pro"' in DISCLOSURE
    assert "useEffect(() => setOpen" in DISCLOSURE
    assert "新手模式預設收合" in DISCLOSURE
    assert "專業模式預設展開" in DISCLOSURE


def test_major_technical_tables_use_disclosure() -> None:
    for source, text in (
        (FINDER, "查看完整成交樣本"),
        (LOAN, "查看利率敏感度詳細表"),
        (HOLDING, "查看每月成本明細"),
        (LOCATION, "查看最近 POI 詳細表"),
        (LOCATION, "查看資料品質與限制"),
        (COMPARE, "查看案件比較完整表"),
        (PAGE, "查看 TX001–TX009 完整規則追蹤"),
    ):
        assert text in source
    for source in (FINDER, LOAN, HOLDING, LOCATION, COMPARE, PAGE):
        assert "overflow-x-auto" in source
    for detail in ("可比成交", "本次估算依據", "市場趨勢", "估價資料狀態"):
        assert detail in PRODUCT_UI
    assert "technicalDetail" in PRODUCT_UI


def test_mascot_explains_current_mode() -> None:
    assert "useViewMode" in MASCOT
    assert "我會先幫你看重點，細節先收起來" in MASCOT
    assert "現在會顯示完整分析細節" in MASCOT
