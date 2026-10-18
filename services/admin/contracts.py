"""Closed, bounded projections. Extra metadata is discarded, never serialized."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Section = Literal["overview", "users", "usage", "providers", "limits", "operations", "audit"]
State = Literal["known", "unknown", "unavailable", "not_applicable"]
Source = Literal["wave_1a", "wave_1b", "wave_1c", "provider_observations", "provider_cost_metrics", "anti_abuse", "build_identity", "external"]
Window = Literal["current_snapshot", "process_lifetime", "last_result", "last_24h", "last_7d"]
Code = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$", max_length=64)]
Count = Annotated[int, Field(strict=True, ge=0, le=9_007_199_254_740_991)]


class Projection(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_assignment=True, revalidate_instances="always")


class Metric(Projection):
    key: Literal["accounts", "active_users", "requests", "provider_attempts", "admitted", "rejected", "http_429", "http_5xx", "latency_ms", "quota_consumed", "cache_hit", "warnings", "events", "health"]
    state: State
    value: Annotated[float, Field(strict=True, ge=0, le=9_007_199_254_740_991, allow_inf_nan=False)] | None = None
    source: Source
    window: Window

    @model_validator(mode="after")
    def truth(self):
        if (self.state == "known") != (self.value is not None):
            raise ValueError("metric state/value mismatch")
        return self


class UserRow(Projection):
    user_id: UUID
    status: Literal["active", "suspended", "unknown"]
    platform_role: Literal["consumer", "platform_admin", "unknown"]
    created_at: datetime | None = None
    last_activity: datetime | None = None
    usage_requests: Count | None = None


class Cost(Projection):
    state: Literal["known", "unknown", "not_applicable"] = "unknown"
    amount: Annotated[float, Field(strict=True, ge=0, le=1e12, allow_inf_nan=False)] | None = None
    currency: Literal["USD", "TWD", "JPY", "KRW"] | None = None

    @model_validator(mode="after")
    def truth(self):
        if self.state == "known":
            if self.amount is None or self.currency is None:
                raise ValueError("known cost requires server estimate")
        elif self.amount is not None or self.currency is not None:
            raise ValueError("unknown cost is not zero")
        return self


class UsageRow(Projection):
    capability: Code
    provider: Code | None = None
    requests: Count | None = None
    provider_attempts: Count | None = None
    admitted: Count | None = None
    rejected: Count | None = None
    http_429: Count | None = None
    http_5xx: Count | None = None
    latency_ms: Annotated[float, Field(ge=0, le=120_000, allow_inf_nan=False)] | None = None
    quota_consumed: Count | None = None
    cache_hit: Count | None = None
    cost: Cost = Field(default_factory=Cost)


class ProviderRow(Projection):
    capability: Code
    configuration: Literal["configured", "not_configured", "invalid", "not_applicable"]
    status: Literal["not_checked", "available", "partial", "limited", "no_data", "no_match", "unavailable", "error", "unaccepted", "resolved", "unresolved", "demo"]
    freshness: Literal["current", "fresh", "stale", "unknown", "unavailable"] = "unknown"
    checked_at: datetime | None = None
    last_success: datetime | None = None
    last_failure: datetime | None = None
    disabled: bool
    quota_evidence: Literal["unavailable"] = "unavailable"


class LimitRow(Projection):
    capability: Code
    audience: Literal["all_peers"] = "all_peers"
    requests: Count
    window_seconds: Count
    operations: Count
    operation_window_seconds: Count
    concurrency: Count
    enabled: bool


class EvidenceRow(Projection):
    key: Literal["release", "compatibility", "maintenance", "backup", "restore", "incident", "fleet_enforcement", "principal_quota"]
    state: State
    value: Literal["enabled", "disabled", "declared", "local_only"] | None = None
    commit_sha: Annotated[str, Field(pattern=r"^[a-f0-9]{40}$")] | None = None
    source: Source


class AuditRow(Projection):
    timestamp: datetime
    actor: UUID | None = None
    event_type: Literal["account_suspended", "account_restored", "role_changed", "policy_changed", "admin_read", "access_denied"]
    target_type: Literal["account", "policy", "admin"]
    outcome: Literal["success", "denied", "failure"]
    reason_code: Literal["authorized", "permission_denied", "account_suspended", "policy_updated", "unknown"]
    target: Annotated[str, Field(max_length=64)] | None = None
    reason: Annotated[str, Field(max_length=500)] | None = None
    command_id: UUID | None = None
    before_state: dict[str, str | int] = Field(default_factory=dict, max_length=4)
    after_state: dict[str, str | int] = Field(default_factory=dict, max_length=4)


class AdminSnapshot(Projection):
    schema_version: Literal["admin-v1"] = "admin-v1"
    section: Section
    state: Literal["available", "partial", "empty", "unavailable"]
    source: Source
    window: Window = "current_snapshot"
    as_of: datetime
    reason: Literal["waiting_for_1a", "waiting_for_1b", "process_local", "external_evidence", "source_unavailable", "durable_aggregates"] | None = None
    metrics: list[Metric] = Field(default_factory=list, max_length=20)
    users: list[UserRow] = Field(default_factory=list, max_length=50)
    usage: list[UsageRow] = Field(default_factory=list, max_length=50)
    providers: list[ProviderRow] = Field(default_factory=list, max_length=50)
    limits: list[LimitRow] = Field(default_factory=list, max_length=50)
    operations: list[EvidenceRow] = Field(default_factory=list, max_length=20)
    audit: list[AuditRow] = Field(default_factory=list, max_length=50)
    next_cursor: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")] | None = None
