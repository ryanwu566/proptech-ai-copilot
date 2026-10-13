"""Process-local provider cost units with fixed, non-sensitive labels."""
from __future__ import annotations

import threading

CAPABILITIES = frozenset({"geocoding", "address_resolution", "places", "places_request", "routes", "satellite", "ardswc", "liquefaction", "nlsc", "tgos", "location", "terrain", "valuation", "trend", "finder", "market", "market_ops", "parcel", "metadata", "identity"})
EVENTS = frozenset({"logical_requests", "physical_calls", "cache_hit", "cache_miss", "coalesced", "operation_success", "operation_failure", "operation_timeout", "avoided_operations", "provider_success", "provider_failure", "provider_timeout", "capacity_bypass", "admitted_requests", "rejected_requests", "rate_limited", "capacity_exhausted", "capability_disabled", "guard_unavailable", "provider_budget_exhausted", "operation_reservations", "capability_request_quota", "principal_request_quota", "principal_operation_quota", "principal_daily_quota", "principal_concurrency", "anonymous_quota", "authenticated_quota"})


class ProviderCostMetrics:
    """Finite counter space; request keys, credentials and payloads never enter it."""

    def __init__(self) -> None:
        self._counts: dict[tuple[str, str], int] = {}
        self._lock = threading.Lock()

    def record(self, capability: str, event: str, count: int = 1, *, provider: str | None = None) -> None:
        if capability not in CAPABILITIES or event not in EVENTS:
            raise ValueError("Unsupported provider cost metric label")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("Provider cost counters require nonnegative integers")
        if provider is not None:
            from services.api_usage import PROVIDER_NAMES
            if provider not in PROVIDER_NAMES or provider == "none" or event not in {"physical_calls", "provider_success", "provider_failure", "provider_timeout"}:
                raise ValueError("Unsupported physical provider dimension")
        with self._lock:
            key = (capability, event)
            self._counts[key] = self._counts.get(key, 0) + count
        from services.api_usage import record_cost_event
        record_cost_event(capability, event, count, provider=provider)

    def snapshot(self) -> dict[tuple[str, str], int]:
        with self._lock:
            return dict(self._counts)

    def render_prometheus(self) -> str:
        lines = ["# HELP proptech_provider_cost_events_total Process-local provider requests, calls and reuse events.", "# TYPE proptech_provider_cost_events_total counter"]
        for (capability, event), count in sorted(self.snapshot().items()):
            lines.append(f'proptech_provider_cost_events_total{{capability="{capability}",event="{event}"}} {count}')
        return "\n".join(lines) + "\n"


PROVIDER_COST_METRICS = ProviderCostMetrics()
