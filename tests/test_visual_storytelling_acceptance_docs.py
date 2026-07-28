"""Static operator and privacy acceptance contracts for Phase 5A."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_acceptance_docs_cover_deployment_responsive_accessibility_and_recovery() -> None:
    docs = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in (
            "docs/production_acceptance_checklist.md",
            "docs/visual_data_storytelling_production_acceptance.md",
            "docs/release_candidate_operations.md",
        )
    )
    for marker in ("PENDING", "NO_GO", "320px", "375px", "768px", "keyboard", "failure", "Property Finder", "Valuation"):
        assert marker in docs
    assert "localhost" not in docs.lower()


def test_signoff_template_defaults_to_pending_and_no_go() -> None:
    template = (ROOT / "docs/release_signoff_template.md").read_text(encoding="utf-8")
    for marker in (
        "RELEASE_CANDIDATE_COMMIT=PENDING",
        "LOCAL_AUTOMATED_TESTS=PENDING",
        "PR_CI=PENDING",
        "MERGED_TO_MAIN=no",
        "VERCEL_PRODUCTION_READY=pending",
        "BACKEND_DASHBOARD_HEALTHY=pending",
        "RELEASE_DECISION=NO_GO",
    ):
        assert marker in template
    for forbidden in ("http://", "https://", "secret=", "token="):
        assert forbidden not in template.lower()


def test_privacy_inventory_records_phase_5a_boundaries() -> None:
    inventory = (ROOT / "docs/privacy_and_storage_inventory.md").read_text(encoding="utf-8")
    for marker in ("Phase 5A", "no new storage key", "URL", "Raw JSON", "unavailable", "demo"):
        assert marker.lower() in inventory.lower()
    assert "production response" not in inventory.lower()
