from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/production-release-ops.yml").read_text(encoding="utf-8")


def test_production_release_workflow_has_review_and_manual_triggers_only() -> None:
    assert "pull_request:" in WORKFLOW
    assert "workflow_dispatch:" in WORKFLOW
    assert "push:" not in WORKFLOW
    assert "schedule:" not in WORKFLOW
    assert "workflow_run:" not in WORKFLOW
    assert "permissions:" in WORKFLOW
    assert "contents: read" in WORKFLOW


def test_workflow_has_postgres_migration_and_release_gates_without_secrets() -> None:
    assert "postgres:16" in WORKFLOW
    assert "validate_postgres_migration.py" in WORKFLOW
    assert "production_smoke.py" in WORKFLOW
    assert "release_quality_gate.py" in WORKFLOW
    assert "secrets." not in WORKFLOW
    assert "PILOT_ADMIN_TOKEN" not in WORKFLOW
    assert "DATABASE_URL" not in WORKFLOW
