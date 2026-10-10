"""Read-only immutable rollback compatibility checks; never switches traffic."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from services.guardrail_evidence import DIGEST, SHA, read_bounded_json
from scripts.migration_registry import parse_registry, MigrationRegistryError


def compatibility(current, candidate):
    checks = {}
    for label in ("frontend", "backend"):
        checks[f"{label}_immutable"] = all(isinstance(row, dict) and SHA.fullmatch(str(row.get(f"{label}_sha", ""))) for row in (current, candidate))
    # No release-bound frontend API contract exists in this repository. Equal
    # consumer trees can be proven locally; a changed frontend needs separate
    # reviewed compatibility evidence and must not inherit the backend label.
    checks["frontend_consumer_tree"] = bool(SHA.fullmatch(str(current.get("frontend_tree", "")))) and current.get("frontend_tree") == candidate.get("frontend_tree")
    checks["api_contract"] = isinstance(current.get("api_contract"), str) and bool(re.fullmatch(r"api-contract-v[0-9]+", current["api_contract"])) and current.get("api_contract") == candidate.get("api_contract")
    checks["schema"] = bool(DIGEST.fullmatch(str(current.get("migration_registry_sha256", "")))) and current.get("migration_registry_sha256") == candidate.get("migration_registry_sha256")
    artifacts = current.get("artifacts")
    checks["artifacts"] = (isinstance(artifacts, dict) and 1 <= len(artifacts) <= 64 and artifacts == candidate.get("artifacts")
                           and all(isinstance(key, str) and re.fullmatch(r"[a-z0-9_.-]{1,80}", key) and DIGEST.fullmatch(str(value)) for key, value in artifacts.items()))
    return {"state": "PASS" if all(checks.values()) else "BLOCKED", "checks": checks,
            "scope": "offline_compatibility_only", "production_rollback": "BLOCKED"}


def _git(*args):
    result = subprocess.run(["git", "-C", str(ROOT), *args], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, check=False)
    if result.returncode:
        raise ValueError("rollback_git_object_unavailable")
    return result.stdout


def inspect_release(frontend_sha, backend_sha, artifacts):
    if not SHA.fullmatch(frontend_sha) or not SHA.fullmatch(backend_sha):
        raise ValueError("immutable_rollback_sha_required")
    for sha in (frontend_sha, backend_sha):
        if _git("cat-file", "-t", sha).strip() != b"commit":
            raise ValueError("rollback_commit_required")
    if _git("cat-file", "-t", f"{frontend_sha}:frontend_next").strip() != b"tree":
        raise ValueError("frontend_rollback_tree_required")
    frontend_tree = _git("rev-parse", f"{frontend_sha}:frontend_next").decode().strip()
    registry = _git("show", f"{backend_sha}:database/migration_registry.json")
    rows = parse_registry(json.loads(registry), verify_files=False)
    inventory = {name for name in _git("ls-tree", "--name-only", f"{backend_sha}:database/migrations").decode().splitlines() if name.endswith(".sql")}
    if inventory != {row.filename for row in rows}:
        raise ValueError("rollback_migration_inventory_mismatch")
    for row in rows:
        filename = row.filename
        if not re.fullmatch(r"[0-9]{3}_[a-z0-9_]+\.sql", filename):
            raise ValueError("invalid_rollback_migration")
        contents = _git("show", f"{backend_sha}:database/migrations/{filename}")
        if hashlib.sha256(contents.replace(b"\r\n", b"\n")).hexdigest() != row.sha256:
            raise ValueError("rollback_migration_checksum_failed")
    render = _git("show", f"{backend_sha}:render.yaml").decode()
    matches = re.findall(r"key: API_CONTRACT_VERSION\s+value: (api-contract-v[0-9]+)", render)
    if len(matches) != 1:
        raise ValueError("rollback_api_contract_unknown")
    backend_source = _git("show", f"{backend_sha}:backend/api/routes_pilot.py").decode()
    runtime_matches = re.findall(r'^API_CONTRACT_VERSION = "(api-contract-v[0-9]+)"$', backend_source, re.MULTILINE)
    if runtime_matches != matches:
        raise ValueError("rollback_api_runtime_metadata_mismatch")
    return {"frontend_sha": frontend_sha, "backend_sha": backend_sha, "api_contract": matches[0],
            "migration_registry_sha256": hashlib.sha256(registry).hexdigest(), "artifacts": artifacts, "frontend_tree": frontend_tree}


def main():
    parser = argparse.ArgumentParser()
    for name in ("current-frontend", "current-backend", "candidate-frontend", "candidate-backend"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--current-artifacts", required=True, type=Path)
    parser.add_argument("--candidate-artifacts", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        current = inspect_release(args.current_frontend, args.current_backend, read_bounded_json(args.current_artifacts))
        candidate = inspect_release(args.candidate_frontend, args.candidate_backend, read_bounded_json(args.candidate_artifacts))
        result = compatibility(current, candidate)
        result.update(schema_version="rollback-drill-v1", current_frontend=current["frontend_sha"], current_backend=current["backend_sha"], candidate_frontend=candidate["frontend_sha"], candidate_backend=candidate["backend_sha"])
    except (OSError, ValueError, KeyError, TypeError, MigrationRegistryError, subprocess.TimeoutExpired):
        result = {"state": "FAIL", "reason": "rollback_evidence_invalid", "production_rollback": "BLOCKED"}
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["state"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
