"""Static accessibility contract for release readiness UI."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTICE = (ROOT / "frontend_next/components/release-readiness-notice.tsx").read_text(encoding="utf-8")
ERROR = (ROOT / "frontend_next/app/error.tsx").read_text(encoding="utf-8")


def test_readiness_notice_has_non_color_status_and_typed_controls() -> None:
    assert "role=\"status\"" in NOTICE
    assert "aria-label" in NOTICE
    assert "summary.label" in NOTICE
    assert "type=\"button\"" in ERROR
    assert "disabled" not in NOTICE


def test_recovery_control_is_keyboard_native_and_not_autofocused() -> None:
    assert "<button type=\"button\"" in ERROR
    assert "autoFocus" not in ERROR
    assert "tabIndex={-1}" not in ERROR
