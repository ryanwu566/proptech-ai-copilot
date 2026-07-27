"""Static checks for safe Next.js recovery routes."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(name: str) -> str:
    return (ROOT / "frontend_next" / "app" / name).read_text(encoding="utf-8")


def test_recovery_routes_exist_and_offer_safe_navigation() -> None:
    error = _text("error.tsx")
    global_error = _text("global-error.tsx")
    not_found = _text("not-found.tsx")
    assert '"use client"' in error
    assert '"use client"' in global_error
    for source in (error, global_error, not_found):
        assert 'role="alert"' in source
        assert 'href="/"' in source
        assert 'type="button"' in source or "href=\"/\"" in source
        assert "error.message" not in source
        assert "error.stack" not in source
        assert "digest" not in source


def test_recovery_routes_do_not_call_api_or_storage() -> None:
    source = "\n".join(_text(name) for name in ("error.tsx", "global-error.tsx", "not-found.tsx"))
    assert "fetch(" not in source
    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "URLSearchParams" not in source
