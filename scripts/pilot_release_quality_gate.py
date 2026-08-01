"""Machine-readable local release gate for pilot evidence acceptance."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_frontend_bundle_budget import measure
from scripts.validate_pilot_environment import report
from scripts.validate_pilot_evidence_migration import validate


def command_status(command: list[str], *, cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return "pass" if result.returncode == 0 else "failed"


def evaluate(root: Path = Path("."), *, execute: bool = False) -> dict[str, object]:
    checks: dict[str, str] = {}
    checks["diff_check"] = command_status(["git", "diff", "--check"], cwd=root)
    checks["migration"] = "pass" if validate()["status"] == "pass" else "failed"
    checks["environment"] = "pass" if report()["secrets_output"] is False else "failed"
    checks["bundle_budget"] = str(measure(root / "frontend_next/.next/static")["status"])
    if execute:
        checks["python_tests"] = command_status(["python", "-m", "pytest", "-q", "--basetemp", ".pytest-temp-pilot-quality-gate"], cwd=root)
        checks["frontend_build"] = command_status(["npm.cmd", "--prefix", "frontend_next", "run", "build"], cwd=root)
        checks["e2e_build"] = command_status(["npm.cmd", "--prefix", "frontend_next", "run", "build:e2e"], cwd=root)
        checks["chromium"] = command_status(["node", "e2e/run-e2e.cjs", "e2e/pilot-evidence.spec.ts", "--project=chromium"], cwd=root / "frontend_next")
        checks["chrome"] = command_status(["node", "e2e/run-e2e.cjs", "e2e/pilot-evidence.spec.ts", "--project=chrome"], cwd=root / "frontend_next")
    else:
        checks["python_tests"] = "not_run"
        checks["frontend_build"] = "not_run"
        checks["e2e_build"] = "not_run"
        checks["chromium"] = "not_run"
        checks["chrome"] = "not_run"
    status = "pass" if all(value == "pass" for value in checks.values()) else "failed"
    return {"status": status, "checks": checks, "required_not_run": [key for key, value in checks.items() if value == "not_run"]}


def main() -> int:
    result = evaluate(execute="--execute" in sys.argv[1:])
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" and not result["required_not_run"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
