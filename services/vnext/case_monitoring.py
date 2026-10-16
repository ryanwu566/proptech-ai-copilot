"""Pure monitoring contracts. No timer, polling, provider call, queue or delivery.

Future workers must claim jobs transactionally and recheck membership, account
status, cadence, provider quota and job deduplication immediately before work.
"""
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: str = Field(min_length=1, max_length=100)
    content_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    status: Literal["available", "failed", "unknown", "unavailable"]
    source_updated_at: datetime | None = None


def source_change(before: SourceObservation | None, after: SourceObservation) -> Literal["baseline", "changed", "unchanged", "unknown"]:
    # Fingerprint actual source content, excluding fetched/rendered timestamps.
    if after.status != "available" or not after.content_digest:
        return "unknown"
    if before is None:
        return "baseline"
    if before.source_id != after.source_id or before.status != "available" or not before.content_digest:
        return "unknown"
    return "changed" if before.content_digest != after.content_digest else "unchanged"


class CachedCheck(BaseModel):
    case_id: UUID
    refresh_policy: Literal["cached_sources_only"] = "cached_sources_only"


def plan_cached_checks(due: list[tuple[UUID, datetime]], *, now: datetime, worker_configured: bool, remaining_quota: int) -> list[CachedCheck]:
    """At most 20 unique due cached reads per worker batch. Not an executor.

    Future SQL claim uses SKIP LOCKED, per-case/day unique key, 24h/7d cadence,
    bounded jitter, leases and capped retry/backoff. No expensive refresh path.
    """
    if not worker_configured or remaining_quota <= 0:
        return []
    ids = dict.fromkeys(case_id for case_id, due_at in sorted(due, key=lambda item: (item[1], str(item[0]))) if due_at <= now)
    return [CachedCheck(case_id=case_id) for case_id in list(ids)[:min(20, remaining_quota)]]


class NotificationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    case_id: UUID
    recipient_id: UUID
    activity_revision: int = Field(ge=1)
    kind: Literal["source_changed", "collaboration_changed"]

    @property
    def deduplication_key(self) -> str:
        return f"{self.case_id}:{self.activity_revision}:{self.recipient_id}:{self.kind}"


class NotificationDelivery(Protocol):
    """Only implement after a delivery provider is configured and consent exists.

    Resolve recipient server-side; recheck access at delivery; never put a token,
    destination, note body, or historical evidence in the event or delivery logs.
    """
    def deliver(self, event: NotificationEvent) -> Literal["delivered", "failed"]: ...
