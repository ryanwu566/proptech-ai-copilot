"""Local contract gate for security, privacy, persistence, and performance.

It reads tracked source and an existing build only. It never reads environment
files, starts a server, calls an external service, or emits source contents.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_route_budgets import measure as measure_route_budgets
from scripts.validate_pilot_environment import report
from scripts.validate_pilot_evidence_migration import validate


REQUIRED_DOC_SECTIONS = ("Threat model", "Trust boundaries", "Authorization model", "CSRF", "Security headers", "SSRF", "Export safety", "Production persistence", "Performance baseline", "Route bundle budgets", "Load-test envelope", "Residual risks")
REQUIRED_FILES = ("docs/security-performance-release.md", "services/security.py", "services/pilot_persistence.py", "database/migrations/005_add_pilot_security_indexes.sql", "scripts/check_route_budgets.py")


def evaluate(root: Path = ROOT) -> dict[str, object]:
    missing = [path for path in REQUIRED_FILES if not (root / path).is_file()]
    doc = (root / "docs/security-performance-release.md").read_text(encoding="utf-8") if not missing else ""
    checks = {
        "required_files": "pass" if not missing else "failed",
        "threat_model": "pass" if not missing and all(section in doc for section in REQUIRED_DOC_SECTIONS) else "failed",
        "environment": "pass" if report()["secrets_output"] is False else "failed",
        "migration": "pass" if validate()["status"] == "pass" else "failed",
        "route_budgets": measure_route_budgets(root / "frontend_next/.next/static")["status"],
        "persistence": "pass" if report()["persistence"]["status"] in {"configured", "unavailable"} else "failed",
    }
    return {"status": "pass" if all(value == "pass" for value in checks.values()) else "failed", "checks": checks, "missing": missing}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    print(json.dumps(result, sort_keys=True) if args.json else "\n".join([f"SECURITY_PERFORMANCE_GATE={result['status']}", *[f"{key.upper()}={value}" for key, value in result["checks"].items()]]))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
