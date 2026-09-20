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


def test_ci_frontend_toolchain_is_pinned_from_one_version_file() -> None:
    node_version = (ROOT / ".node-version").read_text(encoding="utf-8").strip()
    package = json.loads((ROOT / "frontend_next/package.json").read_text(encoding="utf-8"))
    workflows = [
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            ".github/workflows/release-quality.yml",
            ".github/workflows/production-release-ops.yml",
            ".github/workflows/security-performance.yml",
        )
    ]

    assert node_version == "24.21.0"
    assert package["packageManager"] == "npm@11.19.0"
    assert sum(source.count("node-version-file: .node-version") for source in workflows) == 5
    assert all("node-version:" not in source for source in workflows)


def test_security_workflow_validates_the_clean_tree_before_full_audit() -> None:
    workflow = (ROOT / ".github/workflows/security-performance.yml").read_text(encoding="utf-8")
    install = workflow.index("npm ci --prefix frontend_next")
    validate = workflow.index("npm ls --all")
    audit = workflow.index("npm audit --audit-level=high")

    assert install < validate < audit
    assert "working-directory: frontend_next" in workflow[install:audit]
    assert "--package-lock-only" not in workflow


def test_e2e_script_builds_before_exercising_the_owned_server_runner() -> None:
    package = json.loads((ROOT / "frontend_next/package.json").read_text(encoding="utf-8"))
    command = package["scripts"]["test:e2e"]

    assert command.index("npm run build:e2e") < command.index("npm run test:e2e:runner")
    assert command.index("npm run test:e2e:runner") < command.index("node e2e/run-e2e.cjs")


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
