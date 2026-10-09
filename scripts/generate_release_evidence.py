"""Generate a bounded, non-secret release evidence JSON document.

All inputs are explicit categorical or release metadata arguments. The script
does not read environment files, provider settings, databases, or URLs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from services.guardrail_evidence import evaluate_controls, read_bounded_json

SAFE_VALUE = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")
ALLOWED_STATUS = {"generated", "ci_verified", "preview_verified", "production_verified", "pending", "not_run"}
CLASSIFICATIONS = {"PASS", "PASS WITH RESTRICTIONS", "CONFIGURATION REQUIRED", "OWNER ACTION REQUIRED", "BLOCKED", "NOT VERIFIED"}
LOCAL_GATES = ("local_software", "browser_workflow", "compare_pdf", "responsive_accessibility", "api_cost", "application_abuse", "dependency_audit")
PROVIDER_GATES = ("market", "finder", "valuation", "trend", "geocoding", "places", "routes", "maps", "street-view", "tdx", "ris", "nlsc", "ardswc", "wra", "gsmma", "liquefaction", "satellite")
REQUIRED_GATES = (*LOCAL_GATES, "deployed_identity", "hosted_smoke", *PROVIDER_GATES, "official_data", "global_security", "global_cost", "database_migrations", "backup_restore", "retention", "artifact_restore", "incident_recovery", "deployment_rollback")
OWNER_GATES = ("official_data", "global_security", "global_cost", "database_migrations", "backup_restore", "retention", "artifact_restore", "incident_recovery", "deployment_rollback")
REASON_CODES = {"evidence_missing", "local_regression_passed", "local_regression_failed", "offline_contract_verified", "configuration_required", "backend_target_missing", "deployed_identity_unverified", "official_artifact_unverified", "owner_control_unverified", "owner_drill_unverified", "bounded_live_not_authorized", "acceptance_verified", "optional_disabled", "manual_verification_required", "audit_exception_restricted"}
OWNER_ACTIONS = {"none", "supply_acceptance_evidence", "configure_hosted_contract", "authorize_bounded_live", "supply_official_artifact", "verify_global_controls", "execute_disposable_restore", "verify_migration_ledger", "verify_retention", "verify_artifact_restore", "verify_incident_recovery", "verify_rollback", "separately_authorize_satellite", "manual_verification"}
MISSING_EVIDENCE = {"not_verified", "not_checked", "latest", "current", "unknown", "pending", "unconfigured", "missing", "none", "unavailable", "not_run"}


def build_acceptance_evidence(*, expected_main_sha: str, release_version: str, gates: list[dict[str, object]], guardrail_records: dict | None = None, proof_root: Path | None = None) -> dict[str, object]:
    """Aggregate categorical observations; missing production proof blocks GO.

    This does not certify owner assertions or contact deployments. Unknown keys
    are rejected rather than copied into privacy-safe evidence.
    """
    if not re.fullmatch(r"[a-fA-F0-9]{40}", expected_main_sha) or not SAFE_VALUE.fullmatch(release_version):
        raise ValueError("invalid acceptance identity")
    if len(gates) > len(REQUIRED_GATES):
        raise ValueError("acceptance size limit")
    stamp = datetime.now(UTC).isoformat()
    records = {}
    dimensions = ("code_implemented", "configuration_valid", "accepted_artifact_present", "deployed_release_verified", "bounded_live_verified", "owner_evidence_verified", "positive_fixture_verified", "negative_fixture_verified", "unknown_semantics_verified")
    metadata = ("reason_code", "owner_action", "data_version", "artifact_version", "frontend_sha", "backend_sha", "frontend_release_version", "backend_release_version", "confirmed_environment", "source_release_date", "import_timestamp", "latest_effective_period", "manifest_sha256", "artifact_sha256", "evidence_sha256", "scenario", "geographic_coverage")
    allowed = {"capability", "classification", "mode", "test_result", *metadata, *dimensions}
    for observation in gates:
        if not isinstance(observation, dict) or set(observation) - allowed:
            raise ValueError("unknown acceptance fields")
        capability = observation.get("capability")
        if capability not in REQUIRED_GATES or capability in records:
            raise ValueError("unknown or duplicate capability")
        classification = observation.get("classification", "NOT VERIFIED")
        mode = observation.get("mode", "local")
        test_result = observation.get("test_result", "not_run")
        if classification not in CLASSIFICATIONS or mode not in {"local", "preview", "hosted"} or test_result not in {"pass", "fail", "not_run", "configuration_required"}:
            raise ValueError("invalid acceptance category")
        row = {"capability": capability, "classification": classification, "mode": mode, "test_result": test_result, "expected_sha": expected_main_sha.lower(), "acceptance_timestamp": stamp}
        for key in metadata:
            value = observation.get(key, "evidence_missing" if key == "reason_code" else "supply_acceptance_evidence" if key == "owner_action" else "not_verified")
            if not isinstance(value, str) or not SAFE_VALUE.fullmatch(value):
                raise ValueError("unsafe acceptance metadata")
            if key == "reason_code" and value not in REASON_CODES or key == "owner_action" and value not in OWNER_ACTIONS:
                raise ValueError("unknown acceptance reason or owner action")
            if key == "confirmed_environment" and value not in {"local", "preview", "production", "not_verified"}:
                raise ValueError("unknown acceptance environment")
            if key.endswith("sha256") and value != "not_verified" and not re.fullmatch(r"[a-fA-F0-9]{64}", value):
                raise ValueError("invalid evidence checksum")
            if key.endswith("_sha") and value != "not_verified" and not re.fullmatch(r"[a-fA-F0-9]{40}", value):
                raise ValueError("invalid deployed SHA")
            row[key] = value.lower() if key.endswith("_sha") else value
        for key in dimensions:
            value = observation.get(key)
            if value is not None and type(value) is not bool:
                raise ValueError("invalid evidence dimension")
            row[key] = value
        if classification in {"PASS", "PASS WITH RESTRICTIONS"}:
            if test_result != "pass":
                raise ValueError("passing gate requires a passing observation")
            if capability not in LOCAL_GATES:
                if mode != "hosted" or row["confirmed_environment"] != "production" or row["frontend_sha"] != expected_main_sha.lower() or row["backend_sha"] != expected_main_sha.lower() or row["deployed_release_verified"] is not True:
                    raise ValueError("production gate requires both pinned deployed releases")
                if release_version.lower() in MISSING_EVIDENCE or row["frontend_release_version"] != release_version or row["backend_release_version"] != release_version:
                    raise ValueError("both deployed release versions must match the expected version")
                if capability in PROVIDER_GATES and not all(row[key] is True for key in ("code_implemented", "configuration_valid", "accepted_artifact_present", "deployed_release_verified", "bounded_live_verified")):
                    raise ValueError("provider gate lacks acceptance dimensions")
                if capability in OWNER_GATES and not all(row[key] is True for key in ("configuration_valid", "accepted_artifact_present", "owner_evidence_verified")):
                    raise ValueError("owner gate lacks verified operational evidence")
                if capability in OWNER_GATES and row["evidence_sha256"] == "not_verified":
                    raise ValueError("owner evidence checksum required")
                if capability in {"market", "finder", "valuation", "trend", "tdx", "ris", "ardswc", "wra", "gsmma", "liquefaction", "official_data"} and row["data_version"].lower() in MISSING_EVIDENCE:
                    raise ValueError("exact source version required")
                if capability in {"wra", "gsmma", "official_data"}:
                    if any(row[key].lower() in MISSING_EVIDENCE for key in ("manifest_sha256", "artifact_sha256", "artifact_version", "source_release_date", "import_timestamp", "geographic_coverage")) or not all(row[key] is True for key in ("positive_fixture_verified", "negative_fixture_verified", "unknown_semantics_verified")):
                        raise ValueError("official artifact evidence incomplete")
                    date.fromisoformat(row["source_release_date"])
                    if datetime.fromisoformat(row["import_timestamp"].replace("Z", "+00:00")).tzinfo is None:
                        raise ValueError("timezone-aware import timestamp required")
                if capability == "wra" and not re.fullmatch(r"(?:6h-(?:150|250|350)|12h-(?:200|300|400)|24h-(?:200|350|500|650))mm", row["scenario"]):
                    raise ValueError("exact flood scenario required")
                if capability in {"market", "finder", "valuation", "trend", "official_data"}:
                    period = row["latest_effective_period"]
                    if not re.fullmatch(r"[12][0-9]{3}-(?:Q[1-4]|(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12][0-9]|3[01]))?)", period):
                        raise ValueError("exact effective transaction period required")
                    if len(period) == 10:
                        date.fromisoformat(period)
        records[capability] = row
    for capability in REQUIRED_GATES:
        records.setdefault(capability, {"capability": capability, "classification": "NOT VERIFIED", "mode": "local", "test_result": "not_run", "expected_sha": expected_main_sha.lower(), "reason_code": "evidence_missing", "owner_action": "supply_acceptance_evidence", "acceptance_timestamp": stamp, **{key: "not_verified" for key in metadata if key not in {"reason_code", "owner_action"}}, **{key: None for key in dimensions}})
    statuses = {row["classification"] for row in records.values()}
    verdict = "NO-GO" if statuses - {"PASS", "PASS WITH RESTRICTIONS"} else "CONDITIONAL GO" if "PASS WITH RESTRICTIONS" in statuses else "GO"
    guardrails = evaluate_controls(commit=expected_main_sha.lower(), records=guardrail_records, proof_root=proof_root)
    if guardrails["external_acceptance"] != "PASS":
        verdict = "NO-GO"
    return {"schema_version": "final-production-acceptance-v1", "acceptance_timestamp": stamp, "expected_main_sha": expected_main_sha.lower(), "release_version": release_version, "gates": [records[key] for key in REQUIRED_GATES], "production_guardrails": guardrails, "verdict": verdict, "privacy": {"secrets_included": False, "raw_payloads_included": False, "customer_data_included": False}}


def _safe(value: str, default: str = "pending") -> str:
    value = str(value or "").strip()
    return value if SAFE_VALUE.fullmatch(value) else default


def build_evidence(*, release_id: str, commit: str, schema_version: str, local_status: str = "pending", ci_status: str = "pending", preview_status: str = "pending", production_status: str = "pending", owner_actions: list[str] | None = None, closure: dict | None = None, acceptance_gates: list[dict[str, object]] | None = None, guardrail_records: dict | None = None, proof_root: Path | None = None) -> dict[str, object]:
    statuses = (local_status, ci_status, preview_status, production_status)
    if any(status not in ALLOWED_STATUS for status in statuses):
        raise ValueError("evidence status is not allowlisted")
    result = {
        "schema_version": "production-release-evidence-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "release_id": _safe(release_id),
        "commit": _safe(commit),
        "schema_compatibility": _safe(schema_version),
        "validation": {
            "local": local_status,
            "ci": ci_status,
            "preview": preview_status,
            "production": production_status,
        },
        "owner_actions": [_safe(item) for item in (owner_actions or [])],
        "production_guardrails": evaluate_controls(commit=commit, records=guardrail_records, proof_root=proof_root),
        "privacy": {"secrets_included": False, "raw_payloads_included": False, "customer_data_included": False},
    }
    if acceptance_gates is not None:
        result = build_acceptance_evidence(expected_main_sha=commit, release_version=release_id, gates=acceptance_gates, guardrail_records=guardrail_records, proof_root=proof_root)
    if closure is not None:
        from services.production_closure import SCHEMA, acceptance_projection
        sections = closure.get('sections', {}) if isinstance(closure, dict) and closure.get('schema_version') == SCHEMA else {}
        # Only the fixed acceptance projection is copied; untrusted input fields,
        # raw audits and arbitrary caller-provided PASS/GO claims are not emitted.
        if acceptance_gates is None:
            result['schema_version'] = 'production-release-evidence-v2'
        result['closure_acceptance'] = acceptance_projection(sections, expected_backend_commit=commit)
        if acceptance_gates is not None and result['closure_acceptance']['lane_status'] != 'PASS':
            result['verdict'] = 'NO-GO'
    return result


def write_evidence(output: Path, **kwargs: object) -> dict[str, object]:
    payload = build_evidence(**kwargs)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--schema-version", required=True)
    parser.add_argument("--local-status", choices=sorted(ALLOWED_STATUS), default="pending")
    parser.add_argument("--ci-status", choices=sorted(ALLOWED_STATUS), default="pending")
    parser.add_argument("--preview-status", choices=sorted(ALLOWED_STATUS), default="pending")
    parser.add_argument("--production-status", choices=sorted(ALLOWED_STATUS), default="pending")
    parser.add_argument("--owner-action", action="append", default=[])
    parser.add_argument("--acceptance-input", type=Path, help="Categorical gate observations, never raw provider payloads")
    parser.add_argument("--closure-json", type=Path)
    parser.add_argument("--guardrail-owner-records", type=Path)
    parser.add_argument("--proof-root", type=Path)
    args = parser.parse_args()
    closure = None
    gates = None
    try:
        records = read_bounded_json(args.guardrail_owner_records) if args.guardrail_owner_records else None
        if args.closure_json:
            if args.closure_json.stat().st_size > 2_000_000:
                raise ValueError("closure evidence exceeds bounded limit")
            closure = json.loads(args.closure_json.read_text(encoding="utf-8-sig"))
            if not isinstance(closure, dict):
                raise ValueError("closure evidence must be an object")
        if args.acceptance_input:
            if args.acceptance_input.stat().st_size > 64_000:
                raise ValueError("acceptance input exceeds size limit")
            gates = read_bounded_json(args.acceptance_input)
            if not isinstance(gates, list):
                raise ValueError("acceptance input must be a list")
        write_evidence(args.output, release_id=args.release_id, commit=args.commit,
                       schema_version=args.schema_version, local_status=args.local_status,
                       ci_status=args.ci_status, preview_status=args.preview_status,
                       production_status=args.production_status, owner_actions=args.owner_action,
                       closure=closure, acceptance_gates=gates,
                       guardrail_records=records, proof_root=args.proof_root)
    except (OSError, ValueError, TypeError):
        print("RELEASE_EVIDENCE=invalid_input")
        return 1
    print("RELEASE_EVIDENCE=written")
    print("RELEASE_EVIDENCE_SECRETS_INCLUDED=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
