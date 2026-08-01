"""Static production-operations contract gate.

The gate reads repository source and configuration only. It never loads dotenv
files, contacts a database, or calls a hosting/provider API.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "services/production_config.py",
    "services/postgres_runtime.py",
    "backend/repositories/postgres_repo.py",
    "database/migrations/006_add_tax_analysis_history.sql",
    "scripts/validate_postgres_migration.py",
    "scripts/backup_pilot_evidence.py",
    "scripts/restore_pilot_evidence.py",
    "scripts/production_smoke.py",
    ".github/workflows/production-release-ops.yml",
    "docs/deployment-production.md",
    "docs/environment-matrix.md",
    "docs/release-checklist.md",
    "docs/backup-restore.md",
    "docs/disaster-recovery.md",
    "docs/security-operations.md",
    "docs/production-validation.md",
)


def evaluate() -> dict[str, object]:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")
    config = (ROOT / "services/production_config.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/production-release-ops.yml").read_text(encoding="utf-8")
    checks = {
        "required_files": not missing,
        "postgres_required": 'key: DATABASE_URL' in render and "production_like" in config,
        "fail_closed": "raise RuntimeError" in config and "production_like" in config,
        "migration": "006_add_tax_analysis_history.sql" in (ROOT / "scripts/validate_postgres_migration.py").read_text(encoding="utf-8"),
        "workflow": "workflow_dispatch:" in workflow and "pull_request:" in workflow and "push:" not in workflow and "secrets." not in workflow,
        "privacy": "does not contact Render" in (ROOT / "scripts/production_smoke.py").read_text(encoding="utf-8"),
    }
    status = "pass" if all(checks.values()) and not missing else "fail"
    return {"status": status, "checks": checks, "missing": missing}


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass" else 1)
