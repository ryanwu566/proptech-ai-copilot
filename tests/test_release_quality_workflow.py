"""Static safety checks for the release quality workflow."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/release-quality.yml").read_text(encoding="utf-8")


def test_workflow_has_review_and_manual_triggers_only() -> None:
    assert "pull_request:" in WORKFLOW
    assert "branches:" in WORKFLOW and "- main" in WORKFLOW
    assert "workflow_dispatch:" in WORKFLOW
    assert "schedule:" not in WORKFLOW
    assert "push:" not in WORKFLOW
    assert "workflow_run:" not in WORKFLOW
    assert "repository_dispatch:" not in WORKFLOW


def test_workflow_is_read_only_and_bounded() -> None:
    assert "permissions:" in WORKFLOW
    assert "contents: read" in WORKFLOW
    assert "timeout-minutes: 30" in WORKFLOW
    assert "actions/checkout@v4" in WORKFLOW
    assert "actions/setup-python@v5" in WORKFLOW
    assert "actions/setup-node@v4" in WORKFLOW
    assert "python scripts/release_quality_gate.py" in WORKFLOW
    assert "deploy" not in WORKFLOW.lower()
    assert "refresh" not in WORKFLOW.lower()
    assert "import" not in WORKFLOW.lower()
    assert "continue-on-error" not in WORKFLOW
    assert "set -x" not in WORKFLOW
    assert "printenv" not in WORKFLOW
    assert "secrets." not in WORKFLOW


def test_workflow_contains_only_one_quality_gate_invocation() -> None:
    assert len(re.findall(r"python scripts/release_quality_gate\.py", WORKFLOW)) == 1
