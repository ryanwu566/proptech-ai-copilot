"""Passive local summaries. No provider probes, scrape tokens, or new ledger."""
import os
from datetime import datetime, timezone
from typing import Protocol
from fastapi import Depends
from services.admin.authorization import require_platform_admin
from services.admin.store import AdminStore, get_admin_store
from services.vnext.auth import AuthenticatedPrincipal

from services.admin.contracts import AdminSnapshot, Section
from services import anti_abuse
from services.anti_abuse import capability_enabled
from services.production_identity import backend_identity
from services.provider_cost_metrics import PROVIDER_COST_METRICS
from services.provider_observability import provider_status


class AdminSummarySource(Protocol):
    def read(self, section: Section, cursor: str | None) -> AdminSnapshot: ...


class LocalAdminSummarySource:
    def read(self, section: Section, cursor: str | None = None) -> AdminSnapshot:
        now = datetime.now(timezone.utc)
        base = {"section": section, "as_of": now, "state": "partial", "reason": "process_local"}
        if section in {"users", "audit"}:
            return AdminSnapshot(**{**base, "state": "unavailable", "source": "wave_1a", "reason": "waiting_for_1a"})
        if section == "overview":
            metrics = [{"key": key, "state": "unavailable", "source": source, "window": "current_snapshot"}
                       for key, source in [("accounts", "wave_1a"), ("active_users", "wave_1a"),
                                           ("requests", "wave_1b"), ("provider_attempts", "wave_1b"),
                                           ("http_429", "wave_1b"), ("http_5xx", "wave_1b"),
                                           ("health", "external"), ("warnings", "wave_1b"), ("events", "wave_1a")]]
            return AdminSnapshot(**{**base, "state": "unavailable", "source": "wave_1b", "reason": "waiting_for_1b", "metrics": metrics})
        if section == "usage":
            counts = PROVIDER_COST_METRICS.snapshot()
            rows = []
            for capability in sorted({key[0] for key in counts}):
                rows.append({"capability": capability, **{field: counts.get((capability, event)) for field, event in {
                    "requests": "logical_requests", "provider_attempts": "physical_calls", "admitted": "admitted_requests",
                    "rejected": "rejected_requests", "cache_hit": "cache_hit"}.items()}})
            return AdminSnapshot(**{**base, "state": "partial" if rows else "unavailable", "source": "provider_cost_metrics",
                                    "window": "process_lifetime", "usage": rows, "reason": "waiting_for_1b"})
        if section == "providers":
            rows = []
            for row in provider_status(os.environ)["capabilities"]:
                config = set(row["configuration"].values())
                recent = row["recent_result"] or {}
                rows.append({"capability": row["capability"], "status": row["provider_status"],
                             "configuration": "invalid" if "invalid-contract" in config else "not_configured" if "missing" in config else "configured" if config else "not_applicable",
                             "freshness": recent.get("freshness", "unknown"),
                             **{key: recent.get(key) for key in ("checked_at", "last_success", "last_failure")},
                             "disabled": not capability_enabled(row["capability"])})
            return AdminSnapshot(**base, source="provider_observations", window="last_result", providers=rows)
        if section == "limits":
            rows = [{"capability": name, "requests": policy.requests, "window_seconds": policy.window,
                     "operations": policy.operations, "operation_window_seconds": policy.operation_window,
                     "concurrency": policy.concurrency,
                     "enabled": capability_enabled(name)}
                    for name, policy in sorted(anti_abuse.CONTROLS.policies.items())]
            return AdminSnapshot(**base, source="anti_abuse", limits=rows)
        identity = backend_identity()
        from services.usage_guard import guard_configuration
        shared_principal_declared = guard_configuration().mode == 'postgres'
        known = identity["identity_status"] == "PASS"
        rows = [{"key": "release", "state": "known" if known else "unknown", "source": "build_identity",
                 "commit_sha": identity["commit_sha"] if known else None},
                {"key": "compatibility", "state": "unknown", "value": "declared", "source": "external"},
                {"key": "maintenance", "state": "known", "source": "anti_abuse", "value": "enabled" if os.getenv("MAINTENANCE_MODE", "").strip().lower() in {"true", "1", "yes", "on"} else "disabled"},
                {"key": "fleet_enforcement", "state": "known", "value": "local_only", "source": "anti_abuse"},
                {"key": "principal_quota", "state": "unknown" if shared_principal_declared else "known", "value": "declared" if shared_principal_declared else "local_only", "source": "anti_abuse"},
                *[{"key": key, "state": "unavailable", "source": "external"} for key in ("backup", "restore", "incident")]]
        return AdminSnapshot(**base, source="build_identity", operations=rows)


def get_admin_summary_source(principal: AuthenticatedPrincipal = Depends(require_platform_admin),
                             store: AdminStore = Depends(get_admin_store)) -> AdminSummarySource:
    from services.admin.durable import DurableAdminSummarySource
    return DurableAdminSummarySource(principal, store, LocalAdminSummarySource())
