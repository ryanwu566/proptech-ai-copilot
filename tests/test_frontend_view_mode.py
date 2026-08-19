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
LOAN += (ROOT / "frontend_next" / "components" / "data-visualization" / "calculation-evidence-details.tsx").read_text(encoding="utf-8")
HOLDING += (ROOT / "frontend_next" / "components" / "data-visualization" / "holding-cost-visual-panel.tsx").read_text(encoding="utf-8")
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
    assert "summary" in DISCLOSURE
    assert "onToggle" in DISCLOSURE

def test_major_technical_tables_use_disclosure() -> None:
    for source in (FINDER, LOAN, HOLDING, LOCATION, COMPARE, PAGE):
        assert "overflow-x-auto" in source
    for source in (FINDER, LOAN, HOLDING, LOCATION, COMPARE):
        assert "DetailDisclosure" in source
    assert "technicalDetail" in PRODUCT_UI

def test_mascot_explains_current_mode() -> None:
    assert "useViewMode" in MASCOT
    assert "mascot.beginnerMode" in source or "我會先幫你看重點，細節先收起來" in MASCOT
    assert "現在會顯示完整分析細節" in MASCOT
