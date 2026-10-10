"""Static production-operations contract gate.

The gate reads repository source and configuration only. It never loads dotenv
files, contacts a database, or calls a hosting/provider API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from services.guardrail_evidence import EXPECTATIONS, STATES, evaluate_controls, read_bounded_json
REQUIRED = (
    "services/production_config.py",
    "services/postgres_runtime.py",
    "backend/repositories/postgres_repo.py",
    "database/migrations/006_add_tax_analysis_history.sql",
    "database/migration_registry.json",
    "scripts/migration_registry.py",
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
    "services/production_guardrails.py",
    "services/guardrail_evidence.py",
    "backend/api/ingress_middleware.py",
    "scripts/backup_integrity.py",
    "scripts/postgres_recovery_drill.py",
    "scripts/verify_rollback.py",
    "scripts/verify_cloud_run_guardrails.py",
    "docs/operations/production-guardrails-recovery-v1.md",
    "docs/operations/production-guardrails-recovery-v1-runbook.md",
    "docs/operations/production-guardrails-recovery-v1-evidence.json",
    "docs/operations/production-guardrails-evidence-v1.schema.json",
)


def evaluate() -> dict[str, object]:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")
    config = (ROOT / "services/production_config.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/production-release-ops.yml").read_text(encoding="utf-8")
    registry = json.loads(
        (ROOT / "database/migration_registry.json").read_text(encoding="utf-8")
    )
    registered_migrations = {
        item.get("filename")
        for item in registry.get("migrations", [])
        if isinstance(item, dict)
    }
    external = evaluate_controls(commit="unconfigured")
    evidence_valid = False
    try:
        evidence = read_bounded_json(ROOT / "docs/operations/production-guardrails-recovery-v1-evidence.json")
        external = evidence["production_guardrails"]
        evidence_valid = (external["schema_version"] == "production-guardrails-v1"
                          and set(external["controls"]) == set(EXPECTATIONS)
                          and all(row["state"] in STATES for row in external["controls"].values())
                          and external["production_decision"] == "NO_GO")
        # The committed repository artifact contains no owner proof archive.
        # External PASS is permitted only in a separate owner-generated release
        # document whose proof files were actually checked by the generator.
        evidence_valid = evidence_valid and all(row["state"] != "PASS" for row in external["controls"].values())
    except (OSError, ValueError, KeyError, TypeError):
        pass
    checks = {
        "required_files": not missing,
        "postgres_required": 'key: DATABASE_URL' in render and "production_like" in config,
        "fail_closed": "raise RuntimeError" in config and "production_like" in config,
        "migration": {
            "006_add_tax_analysis_history.sql",
            "007_add_schema_migration_ledger.sql",
            "012_security_rls_deny_by_default.sql",
        }.issubset(registered_migrations),
        "workflow": "workflow_dispatch:" in workflow and "pull_request:" in workflow and "push:" not in workflow and "secrets." not in workflow,
        "privacy": "provider-free" in (ROOT / "scripts/production_smoke.py").read_text(encoding="utf-8") and "external_provider_called" in (ROOT / "scripts/production_smoke.py").read_text(encoding="utf-8"),
        "guardrail_evidence_contract": evidence_valid,
    }
    status = "pass" if all(checks.values()) and not missing else "fail"
    return {"status": status, "checks": checks, "missing": missing,
            "external_guardrails": "BLOCKED", "production_decision": "NO_GO"}


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass" else 1)
