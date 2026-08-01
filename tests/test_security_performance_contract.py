from __future__ import annotations

import json
from pathlib import Path

from scripts.check_route_budgets import ROUTE_BUDGETS
from scripts.generate_sbom import generate
from scripts.performance_baseline import report


ROOT = Path(__file__).resolve().parents[1]


def test_security_workflow_is_least_privilege_and_has_no_production_secrets() -> None:
    workflow = (ROOT / ".github/workflows/security-performance.yml").read_text(encoding="utf-8")
    assert "permissions:\n  contents: read" in workflow
    assert "pull_request:" in workflow and "workflow_dispatch:" in workflow
    assert "secrets." not in workflow
    assert "PILOT_ADMIN_TOKEN" not in workflow


def test_route_budgets_and_baseline_are_machine_readable() -> None:
    assert {"homepage", "competition_demo", "taxoracle", "map_insight", "pilot", "admin"} <= set(ROUTE_BUDGETS)
    result = report(ROOT)
    assert result["schema_version"] == "performance-baseline-v1"
    assert "route_static_measurement" in result


def test_sbom_is_manifest_only_and_contains_no_environment_values() -> None:
    result = generate()
    assert result["bomFormat"] == "CycloneDX"
    text = json.dumps(result)
    assert ".env" not in text.lower()
    assert "token" not in text.lower()
