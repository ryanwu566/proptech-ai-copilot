"""Bounded, release-bound extension to production release acceptance evidence.

Offline proof checks validate owner assertions, not live infrastructure. An
owner must independently collect and review exports. Hashes prove identity,
not authenticity of cloud configuration. No default or self-attestation PASS.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

MAX_BYTES = 262_144
STATES = frozenset({"PASS", "FAIL", "BLOCKED", "UNKNOWN", "NOT_APPLICABLE"})
SHA = re.compile(r"[a-f0-9]{40}\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
EVIDENCE_KINDS = frozenset({"cloud_export", "staging_drill", "notification_receipt", "owner_review"})
# Numerical tuples are inclusive minimum/maximum; these are proposed beta
# acceptance ceilings, not assertions that cloud quotas exist at these values.
EXPECTATIONS = {
    "trusted_ingress": ("ingress_owner", {"proxy_headers": "disabled", "direct_backend_bypass": "denied", "all_ingress_paths_reviewed": True}),
    "cross_instance": ("reliability_owner", {"atomic_shared_reservations": True, "all_workers_revisions_covered": True, "store_failure": "reject_503", "two_instance_drill": "PASS"}),
    "edge_waf": ("ingress_owner", {"expensive_routes_covered": True, "aggregate_rules": True, "bot_rules": True, "body_limit_bytes": (1, 1_000_000), "upload_limit_bytes": (1, 11_000_000), "backend_bypass": "denied", "emergency_deny_test": "PASS"}),
    "google_quota": ("provider_owner", {"geocoding_per_minute": (1, 30), "places_per_minute": (1, 30), "routes_per_minute": (1, 10), "all_projects_keys_consumers_covered": True, "effective_quota_verified": True}),
    "google_browser_quota": ("provider_owner", {"api_restrictions": True, "referrer_restrictions": True, "effective_quotas_verified": True, "separate_browser_consumers_reviewed": True}),
    "earth_engine_quota": ("provider_owner", {"daily_eecu_seconds": (1, 3600), "concurrent_requests": (1, 2), "effective_quota_verified": True, "approximate_quota_acknowledged": True}),
    "other_metered_providers": ("provider_owner", {"r2_storage_requests_egress_reviewed": True, "tdx_tgos_gateway_entitlements_reviewed": True, "all_active_consumers_inventoried": True}),
    "billing_alerts": ("billing_owner", {"actual_percent_thresholds": [50, 80, 100], "forecast_percent_threshold": 100, "primary_delivery_test": "PASS", "backup_delivery_test": "PASS"}),
    "global_cost_ceiling": ("billing_owner", {"all_metered_services_covered": True, "enforced_currency_ceiling": True, "alert_only": False, "overshoot_delay_reviewed": True, "shutdown_drill": "PASS"}),
    "kill_switch_rollout": ("incident_owner", {"all_active_revisions_covered": True, "safe_disable_drill": "PASS", "recovery_drill": "PASS", "inflight_work_reviewed": True}),
    "monitoring": ("reliability_owner", {"protected_scrape": True, "all_instances_scraped": True, "bounded_labels": True, "health_alert": True, "error_latency_budget_alerts": True, "artifact_release_alerts": True, "notification_delivery_test": "PASS"}),
    "production_backup": ("database_owner", {"encrypted_offsite": True, "retention_days": (7, 90), "backup_age_hours": (0, 24), "checksum_verified": True, "restore_access_verified": True, "all_datastores_covered": True}),
    "production_restore": ("database_owner", {"target": "disposable_or_staging", "row_constraint_ledger_validation": "PASS", "artifact_compatibility": "PASS", "owner_rpo_rto_reviewed": True}),
    "hosted_rollback": ("release_owner", {"immutable_frontend": True, "immutable_backend": True, "schema_artifact_compatibility": "PASS", "staging_drill": "PASS", "health_identity_verification": "PASS"}),
    "incident_escalation": ("incident_owner", {"primary_backup_named_privately": True, "paging_delivery_test": "PASS", "runbook_reviewed": True, "decision_authority_recorded": True}),
}


def read_bounded_json(path: Path):
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("invalid_evidence_size")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_evidence_key")
            result[key] = value
        return result
    def reject_constant(_value):
        raise ValueError("nonstandard_evidence_number")
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique, parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError("invalid_evidence_json") from None


def facts_match(facts, expected):
    if not isinstance(facts, dict) or set(facts) != set(expected):
        return False
    for key, want in expected.items():
        value = facts[key]
        if isinstance(want, tuple):
            if type(value) not in {int, float} or not want[0] <= value <= want[1]:
                return False
        elif type(value) is not type(want) or value != want:
            return False
    return True


def _proof_path(root, relative_name):
    relative = Path(relative_name)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix not in {".json", ".txt", ".pdf"}:
        raise ValueError("invalid_proof_path")
    supplied = root / relative
    path = supplied.resolve()
    if not path.is_relative_to(root.resolve()) or supplied.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("invalid_proof_file")
    return path


def _verify(control, row, commit, root, now):
    owner, facts = EXPECTATIONS[control]
    required = {"state", "owner_role", "verified_at", "release_commit", "proof_file", "proof_sha256"}
    if set(row) != required or row["owner_role"] != owner or row["release_commit"] != commit or not DIGEST.fullmatch(str(row["proof_sha256"])) or root is None:
        return False
    try:
        observed = datetime.fromisoformat(row["verified_at"])
        if observed.tzinfo is None or not now - timedelta(days=7) <= observed <= now:
            return False
        if not isinstance(row["proof_file"], str) or not row["proof_file"].endswith(".json"):
            return False
        path = _proof_path(root, row["proof_file"])
        proof = read_bounded_json(path)
        if not isinstance(proof, dict):
            return False
        sources = proof.get("evidence_files")
        if not isinstance(sources, list) or not 1 <= len(sources) <= 8:
            return False
        for source in sources:
            if not isinstance(source, dict) or set(source) != {"file", "sha256", "kind"} or not isinstance(source["kind"], str) or source["kind"] not in EVIDENCE_KINDS or not DIGEST.fullmatch(str(source["sha256"])):
                return False
            support = _proof_path(root, source["file"])
            if support == path or hashlib.sha256(support.read_bytes()).hexdigest() != source["sha256"]:
                return False
        return (hashlib.sha256(path.read_bytes()).hexdigest() == row["proof_sha256"]
                and set(proof) == {"control", "release_commit", "facts", "evidence_files"}
                and proof["control"] == control and proof["release_commit"] == commit
                and facts_match(proof["facts"], facts))
    except (OSError, ValueError, TypeError, OverflowError):
        return False


def evaluate_controls(*, commit: str, records=None, proof_root: Path | None = None, now: datetime | None = None):
    records = {} if records is None else records
    if not isinstance(records, dict) or set(records) - set(EXPECTATIONS):
        raise ValueError("unsupported_evidence_controls")
    now = now or datetime.now(UTC)
    controls = {}
    for control, (owner, _) in EXPECTATIONS.items():
        row = records.get(control)
        state, reason = "BLOCKED", "owner_evidence_required"
        if row is not None:
            if not isinstance(row, dict) or not isinstance(row.get("state"), str) or row["state"] not in STATES:
                state, reason = "FAIL", "invalid_evidence"
            elif row["state"] == "PASS":
                valid = bool(SHA.fullmatch(commit)) and _verify(control, row, commit, proof_root, now)
                state, reason = ("PASS", "owner_proof_verified") if valid else ("FAIL", "invalid_owner_proof")
            elif row["state"] == "NOT_APPLICABLE":
                state, reason = "FAIL", "required_control_cannot_be_waived"
            else:
                state, reason = row["state"], "owner_control_unverified"
        controls[control] = {"state": state, "reason": reason, "owner_role": owner}
        if state == "PASS":
            controls[control].update({key: row[key] for key in ("proof_sha256", "verified_at", "release_commit")})
    return {"schema_version": "production-guardrails-v1", "release_commit": commit if SHA.fullmatch(commit) else "unconfigured",
            "controls": controls, "external_acceptance": "PASS" if all(row["state"] == "PASS" for row in controls.values()) else "BLOCKED",
            "production_decision": "NO_GO", "unrelated_acceptance": "UNKNOWN", "verification_scope": "offline_owner_proof"}
