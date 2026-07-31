"""Static contract checks for the production localization and accessibility layer."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_road_display_pipeline_is_versioned_truthful_and_preserves_canonical_values() -> None:
    roads = read("frontend_next/lib/road-labels.ts")
    page = read("frontend_next/app/page.tsx")
    assert 'ROAD_LABEL_PIPELINE_VERSION = "road-display-v1"' in roads
    assert "Official road name (" in roads
    assert "hash" not in roads.lower()
    assert 'value={item}' in page
    assert "getLocalizedRoadLabel(item, locale)" in page


def test_admin_labels_use_explicit_four_locale_artifact_without_fake_fallbacks() -> None:
    structured = read("frontend_next/lib/structured-options.ts")
    assert "taiwan-admin-labels.json" in structured
    assert "cleanAdminLabel" in structured
    assert 'replace(/邊/gu, "辺")' in structured
    assert "Taiwan administrative area ${" not in structured


def test_navigation_focus_and_assistive_narration_are_runtime_safe() -> None:
    shell = read("frontend_next/components/app-shell.tsx")
    heading = read("frontend_next/components/product-ui.tsx")
    speech = read("frontend_next/components/assistive-narration-controls.tsx")
    topbar = read("frontend_next/components/topbar.tsx")
    assert "data-page-heading" in shell
    assert "requestAnimationFrame" in shell
    assert "data-page-heading" in heading
    assert 'useState(false)' in speech
    assert "SpeechSynthesisUtterance" in speech
    assert "localStorage" not in speech
    assert "sessionStorage" not in speech
    assert "fetch(" not in speech
    assert "AssistiveNarrationControls" in topbar


def test_playwright_matrix_is_maintained_and_uses_a_local_production_server() -> None:
    package = read("frontend_next/package.json")
    config = read("frontend_next/playwright.config.ts")
    runner = read("frontend_next/e2e/run-e2e.cjs")
    for script in ("test:e2e", "test:e2e:i18n", "test:e2e:navigation", "test:e2e:speech"):
        assert f'"{script}"' in package
    assert "@playwright/test" in package
    assert '"build:e2e"' in package
    assert "node_modules/next/dist/bin/next" in runner
    assert '"start"' in runner
    assert "trace: \"on-first-retry\"" in config
    assert "screenshot: \"only-on-failure\"" in config
    assert (FRONTEND / "e2e/fixtures.ts").exists()
    assert (FRONTEND / "e2e/i18n.spec.ts").exists()
    assert (FRONTEND / "e2e/navigation.spec.ts").exists()
    assert (FRONTEND / "e2e/speech.spec.ts").exists()
