"""Static contract checks for the production localization and accessibility layer."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_road_display_pipeline_is_versioned_truthful_and_preserves_canonical_values() -> None:
    roads = read("frontend_next/lib/road-labels.ts")
    phonetics = read("frontend_next/lib/road-phonetics.ts")
    page = read("frontend_next/app/page.tsx")
    assert 'ROAD_LABEL_PIPELINE_VERSION = "road-display-v2"' in roads
    assert "offline deterministic transliteration" in roads
    assert "Official road name (" not in roads
    assert "ROAD_PHONETICS" in phonetics
    assert "ROAD_PHONETICS" in roads
    assert "hash" not in roads.lower()
    assert 'value={item}' in page
    assert "getLocalizedRoadLabel(item, locale)" in page


def test_road_catalog_is_generated_and_reviewable_without_browser_bundle_import() -> None:
    manifest = (ROOT / "data/road-display-catalog-v2/manifest.json").read_text(encoding="utf-8")
    generator = read("scripts/generate_road_display_artifacts.py")
    assert '"schema_version": "road-display-v2"' in manifest
    assert 'source": "data/taiwan_roads.csv"' in manifest
    assert "SCOPED_ROAD_KEYS_TOTAL" in generator
    assert "sourceVersion" in generator
    assert "road-display-catalog-v2" not in read("frontend_next/lib/road-labels.ts")


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
    assert '"build:e2e": "node scripts/build-e2e.mjs"' in package
    build_script = read("frontend_next/scripts/build-e2e.mjs")
    assert "process.env" in build_script
    assert 'NEXT_PUBLIC_APP_ENV: "test"' in build_script
    assert '"http://e2e.test"' in build_script
    assert "spawnSync" in build_script
    assert "stdio: \"inherit\"" in build_script
    assert "node_modules/next/dist/bin/next" in runner
    assert '"start"' in runner
    assert "trace: \"on-first-retry\"" in config
    assert "screenshot: \"only-on-failure\"" in config
    assert 'name: "chromium"' in config
    assert 'name: "chrome"' in config
    assert 'channel: "chrome"' in config
    assert (FRONTEND / "e2e/fixtures.ts").exists()
    assert (FRONTEND / "e2e/i18n.spec.ts").exists()
    assert (FRONTEND / "e2e/navigation.spec.ts").exists()
    assert (FRONTEND / "e2e/speech.spec.ts").exists()
