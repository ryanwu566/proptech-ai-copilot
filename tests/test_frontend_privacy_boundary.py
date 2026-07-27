"""Static privacy checks for the release candidate additions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readiness_ui_has_no_storage_or_network_side_effects() -> None:
    source = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "frontend_next/lib/release-readiness.ts",
            "frontend_next/components/release-readiness-notice.tsx",
        )
    )
    for forbidden in ("localStorage", "sessionStorage", "document.cookie", "URLSearchParams", "fetch(", "process.env"):
        assert forbidden not in source


def test_inventory_names_storage_and_sensitive_data_boundaries() -> None:
    inventory = (ROOT / "docs/privacy_and_storage_inventory.md").read_text(encoding="utf-8")
    for marker in ("localStorage", "sessionStorage", "coordinates", "provider payload", "proptech:saved-cases", "share"):
        assert marker in inventory
    assert "secret" in inventory.lower()
