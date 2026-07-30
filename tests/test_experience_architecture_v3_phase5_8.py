from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_supported_locales_and_resource_fallback_are_internal():
    source = read("frontend_next/lib/experience-i18n.ts")
    assert '"zh-TW", "en", "ja", "ko"' in source
    assert "normalizeExperienceLocale" in source
    assert "DEFAULT_LOCALE" in source
    assert "Intl.NumberFormat" in source
    assert "Intl.DateTimeFormat" in source
    assert "fetch(" not in source
    assert "localStorage" not in source
    assert "sessionStorage" not in source


def test_locale_switcher_is_runtime_only_and_changes_document_language():
    provider = read("frontend_next/components/experience-locale-provider.tsx")
    switcher = read("frontend_next/components/locale-switcher.tsx")
    assert "document.documentElement.lang" in provider
    assert "setLocale" in switcher
    assert "localStorage" not in provider + switcher
    assert "sessionStorage" not in provider + switcher
    assert "fetch(" not in provider + switcher


def test_read_aloud_uses_explicit_safe_summary_and_no_autoplay():
    model = read("frontend_next/lib/safe-speech.ts")
    controls = read("frontend_next/components/read-aloud-controls.tsx")
    assert "SafeSpeechSummary" in model
    assert "visibleText" in model
    assert "speechSynthesis" in controls
    assert "summary.visibleText" in controls
    assert "querySelector" not in controls
    assert "textContent" not in controls
    assert "useEffect(() => {" in controls
    assert "synthesis.speak" in controls
    assert "onClick={start}" in controls
    assert "synthesis.cancel()" in controls
    assert "autoplay" not in controls.lower()


def test_voice_input_is_browser_native_deterministic_and_confirmation_gated():
    parser = read("frontend_next/lib/voice-input.ts")
    controls = read("frontend_next/components/voice-input-controls.tsx")
    assert "SpeechRecognition" in controls
    assert "parseVoiceCommand" in controls
    assert "isSafeVoiceAction" in controls
    assert "confirmation_required" in parser
    assert "eval(" not in parser
    assert "fetch(" not in parser + controls
    assert "localStorage" not in parser + controls
    assert "sessionStorage" not in parser + controls
    for forbidden in ("save", "delete", "export", "print", "purchase"):
        assert forbidden in parser.lower()
    assert "onAction?.(command.action)" in controls


def test_voice_actions_are_runtime_only_and_existing_business_surfaces_remain_untouched():
    page = read("frontend_next/app/page.tsx")
    shell = read("frontend_next/components/app-shell.tsx")
    assert "proptech:select-journey-step" in page
    assert "onVoiceAction" in shell
    assert "proptech:stop-read-aloud" in page
    assert "proptech:repeat-read-aloud" in page
    assert "api." not in read("frontend_next/components/voice-input-controls.tsx")
    assert "ViewingDecisionPanel" in page
    assert "sessionStorage" not in shell


def test_active_phase_document_records_release_boundaries():
    doc = read("docs/experience-architecture-v3-phases5-8.md")
    for marker in ("Phase 5", "Phase 6", "Phase 7", "Phase 8", "no autoplay", "not persisted", "SpeechRecognition", "domain API contracts"):
        assert marker in doc


def test_pytest_temp_pattern_is_ignored_without_touching_generated_directories():
    gitignore = read(".gitignore")
    assert ".pytest-temp*/" in gitignore
