"""Bounded hourly usage aggregates, with no request payload or metric identities."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import re
import threading
import time
from uuid import uuid4

from services.provider_cost_metrics import CAPABILITIES
from services.production_identity import backend_identity
from services.usage_principal import UsagePrincipal, verified_principal

PROVIDERS = {"geocoding": "google_geocoding", "places": "google_places", "routes": "google_routes", "satellite": "earth_engine", "ardswc": "ardswc", "liquefaction": "geologycloud", "nlsc": "nlsc", "tgos": "tgos", "identity": "nlsc_cadastral"}
PROVIDER_NAMES = frozenset({*PROVIDERS.values(), "none", "unknown", "tdx_mrt"})
PROVIDER_COST_CLASSES = {"google_geocoding": "moderate", "google_places": "expensive", "google_routes": "expensive", "earth_engine": "very_expensive", "ardswc": "expensive", "geologycloud": "expensive", "nlsc": "expensive", "tgos": "moderate", "nlsc_cadastral": "expensive", "none": "not_applicable", "unknown": "unknown"}
PROVIDER_COST_CLASSES["tdx_mrt"] = "unknown"
# Only these HTTP pipelines have fully covered physical transport boundaries.
# Composite analyses may include uninstrumented storage/DB/subprovider reads.
COMPLETE_PROVIDER_CAPABILITIES = frozenset({"geocoding", "places", "routes", "satellite"})
COUNTERS = ("observations", "requests", "admitted", "rejected", "responses_429", "responses_5xx", "provider_attempt_count", "provider_accounting_unknown", "provider_failures", "provider_timeouts", "quota_units", "cache_hits", "cache_misses", "cache_unknown", "coalesced", "latency_count", "latency_sum_ms", "latency_le_100ms", "latency_le_1000ms", "latency_le_10000ms")
EVENT_COUNTERS = {"physical_calls": "provider_attempt_count", "provider_failure": "provider_failures", "provider_timeout": "provider_timeouts", "operation_reservations": "quota_units", "cache_hit": "cache_hits", "cache_miss": "cache_misses", "coalesced": "coalesced"}
_CURRENT: ContextVar[UsageContext | None] = ContextVar("api_usage_context", default=None)
_ALLOWED_ROUTES = frozenset({"internal", *(f"{method}:{name}" for method in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "OTHER") for name in CAPABILITIES)})


@dataclass
class UsageContext:
    principal: UsagePrincipal
    capability: str
    route_class: str
    controls: object
    request_permit: object = None
    request_admitted: bool = False
    rejected: bool = False
    cache_observed: bool = False
    cache_state: str = "unknown"
    provider_observed: bool = False
    request_marker: object = field(default_factory=uuid4)
    lock: threading.RLock = field(default_factory=threading.RLock)

    def acquire_request(self, identity=None):
        from services.usage_quota import QuotaExceeded
        with self.lock:
            if self.request_admitted:
                return
            if identity is not None:
                self.principal = identity
            if self.controls is None:
                return
            permit = self.controls.principal_quotas.request(self.principal)
            try:
                permit.__enter__()
                try:
                    self.controls.consume_durable(self.principal, self.capability, "request", self.request_marker)
                except BaseException:
                    permit.__exit__(None, None, None)
                    raise
            except QuotaExceeded as error:
                self.controls.reject(self.capability, error.reason, retry_after=error.retry_after)
            except Exception:
                self.controls.reject(self.capability, "guard_unavailable", status=503)
            self.request_permit = permit
            self.request_admitted = True
            USAGE.observe(capability=self.capability, event="admitted_requests", principal_class=self.principal.principal_class, principal_id=self.principal.principal_id, provider="none", route_class=self.route_class)

    def close(self):
        with self.lock:
            if self.request_permit is not None:
                self.request_permit.__exit__(None, None, None)
                self.request_permit = None


def current_usage_context():
    return _CURRENT.get()


@contextmanager
def usage_context(context):
    token = _CURRENT.set(context)
    try:
        yield context
    finally:
        _CURRENT.reset(token)


def bind_authenticated_usage(identity):
    """Called only after existing verification; sync dependency shares this object."""
    context = current_usage_context()
    normalized = verified_principal(identity)
    if context is not None and normalized is not None:
        context.principal = normalized


def admit_authenticated_usage(identity):
    context = current_usage_context()
    normalized = verified_principal(identity)
    if context is not None and normalized is not None:
        context.acquire_request(normalized)


def cost_estimate(provider, operations, pricing=None):
    if provider not in PROVIDER_NAMES or isinstance(operations, bool) or not isinstance(operations, int) or operations < 0:
        raise ValueError("Invalid provider cost input")
    if operations == 0 or provider == "none":
        return {"status": "not_applicable", "currency": None, "currency_estimate": None}
    contract = (pricing or {}).get(provider)
    if contract is None:
        return {"status": "unknown", "currency": None, "currency_estimate": None}
    try:
        currency = contract["currency"]
        amount = Decimal(str(contract["per_operation"]))
        if not re.fullmatch(r"[A-Z]{3}", currency) or not amount.is_finite() or not 0 <= amount <= 1_000_000:
            raise ValueError()
    except (KeyError, TypeError, InvalidOperation, ValueError):
        raise ValueError("Invalid configured provider pricing") from None
    return {"status": "configured_estimate", "currency": currency, "currency_estimate": str(amount * operations)}


class UsageAggregator:
    def __init__(self, *, max_rows=4096, wall_clock=time.time, release_id=None):
        self.max_rows = max(1, min(int(max_rows), 4096))
        self.wall_clock = wall_clock
        selected = release_id or backend_identity()["commit_sha"]
        self.release_id = selected if re.fullmatch(r"[a-f0-9]{40}", selected) else "unknown"
        self._lock = threading.Lock()
        self._recent = {}
        self._pending = {}
        self._dropped = 0
        self._expired = 0
        self._writer_status = "not_configured"
        self._last_bucket = int(wall_clock() // 3600) * 3600

    def observe(self, *, capability, event, principal_class="system", principal_id="", provider="unknown", route_class="internal", status_class="other", cache_state="unknown", count=1, status=0, duration_ms=0, provider_accounting_known=False):
        if capability not in CAPABILITIES or provider not in PROVIDER_NAMES or principal_class not in {"authenticated", "anonymous", "system"}:
            raise ValueError("Unsupported usage dimension")
        if principal_class == "system":
            principal_id = ""
        elif principal_class == "anonymous" and principal_id and not re.fullmatch(r"[a-f0-9]{64}", principal_id):
            raise ValueError("Invalid opaque principal")
        elif principal_class == "authenticated" and not re.fullmatch(r"[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}", principal_id):
            raise ValueError("Invalid opaque principal")
        if route_class not in _ALLOWED_ROUTES or status_class not in {"1xx", "2xx", "3xx", "4xx", "5xx", "other"} or cache_state not in {"hit", "miss", "unknown", "coalesced"}:
            raise ValueError("Unsupported usage dimension")
        if event not in {*EVENT_COUNTERS, "request", "rejected_requests", "admitted_requests"} or isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("Unsupported usage event")
        bucket = int(self.wall_clock() // 3600) * 3600
        key = (bucket, principal_class, principal_id, capability, provider, route_class, status_class, cache_state, self.release_id)
        delta = dict.fromkeys(COUNTERS, 0)
        delta["observations"] = count
        if event in EVENT_COUNTERS:
            delta[EVENT_COUNTERS[event]] = count
        elif event == "request":
            milliseconds = min(120000, max(0, int(duration_ms)))
            delta.update(requests=1, responses_429=int(status == 429), responses_5xx=int(500 <= status < 600), provider_accounting_unknown=int(not provider_accounting_known), latency_count=1, latency_sum_ms=milliseconds, latency_le_100ms=int(milliseconds <= 100), latency_le_1000ms=int(milliseconds <= 1000), latency_le_10000ms=int(milliseconds <= 10000), cache_unknown=int(cache_state == "unknown"))
        else:
            delta["admitted" if event == "admitted_requests" else "rejected"] = count
        with self._lock:
            if bucket != self._last_bucket:
                for old in [old for old in self._recent if old[0] < bucket - 23 * 3600]:
                    del self._recent[old]
                self._last_bucket = bucket
            if (key not in self._recent and len(self._recent) >= self.max_rows) or (key not in self._pending and len(self._pending) >= self.max_rows):
                self._dropped += count
                return
            for target in (self._recent, self._pending):
                aggregate = target.setdefault(key, dict.fromkeys(COUNTERS, 0))
                for counter, value in delta.items():
                    aggregate[counter] += value

    @staticmethod
    def _rows(values):
        dimensions = ("bucket_start", "principal_class", "principal_id", "capability", "provider", "route_class", "status_class", "cache_state", "release_id")
        return [{**dict(zip(dimensions, key)), **counts} for key, counts in values.items()]

    def snapshot(self):
        with self._lock:
            cutoff = int(self.wall_clock() // 3600) * 3600 - 23 * 3600
            return self._rows({key: dict(value) for key, value in self._recent.items() if key[0] >= cutoff})

    def take_pending(self):
        with self._lock:
            rows = self._rows(self._pending)
            self._pending = {}
            return rows

    def summary(self, hours=24, *, include_principals=False, pricing=None):
        if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= 24:
            raise ValueError("Usage summary window must be 1..24 hours")
        cutoff = int(self.wall_clock() // 3600) * 3600 - (hours - 1) * 3600
        rows = [row for row in self.snapshot() if row["bucket_start"] >= cutoff]
        totals = {name: sum(row[name] for row in rows) for name in COUNTERS}
        by_capability, by_provider = {}, {}
        for row in rows:
            for target, dimension in ((by_capability, "capability"), (by_provider, "provider")):
                values = target.setdefault(row[dimension], dict.fromkeys(COUNTERS, 0))
                for name in COUNTERS:
                    values[name] += row[name]
        if not include_principals:
            # Aggregate consumers get no identities unless explicitly requested.
            rows = []
        with self._lock:
            accounting = {"complete": self._dropped == 0 and self._expired == 0, "dropped_observations": self._dropped, "expired_observations": self._expired, "writer_status": self._writer_status, "pending_rows": len(self._pending)}
        return {"scope": "process_local", "window_hours": hours, "totals": totals, "provider_attempts_complete": accounting["complete"] and totals["provider_accounting_unknown"] == 0, "by_capability": by_capability, "by_provider": by_provider, "estimated_cost_classes": {name: PROVIDER_COST_CLASSES[name] for name in by_provider}, "cost_estimates": {name: cost_estimate(name, values["provider_attempt_count"], pricing) for name, values in by_provider.items()}, "accounting": accounting, "rows": rows}

    def writer_status(self, status):
        if status not in {"not_configured", "configured", "available", "unavailable", "stopped"}:
            raise ValueError("Unsupported writer status")
        with self._lock:
            self._writer_status = status

    def record_expired(self, count):
        with self._lock:
            self._expired += count

    def render_prometheus(self):
        # Finite dimensions only. Principal IDs, release IDs and routes excluded.
        summary = self.summary()
        lines = ["# HELP proptech_api_usage Recent process-local usage (rolling hour buckets, up to 24 hours).", "# TYPE proptech_api_usage gauge"]
        for dimension in ("capability", "provider"):
            for label, values in sorted(summary[f"by_{dimension}"].items()):
                for name, count in values.items():
                    lines.append(f'proptech_api_usage{{dimension="{dimension}",name="{label}",measure="{name}"}} {count}')
        lines.extend([f"proptech_api_usage_dropped_observations {summary['accounting']['dropped_observations']}", f"proptech_api_usage_expired_observations {summary['accounting']['expired_observations']}"])
        return "\n".join(lines) + "\n"


USAGE = UsageAggregator()


def record_cost_event(capability, event, count, *, provider=None):
    context = current_usage_context()
    if event == "rejected_requests" and context is not None:
        context.rejected = True
    # Request admitted count is emitted after identity admission, by middleware.
    if event not in EVENT_COUNTERS and event != "rejected_requests":
        return
    state = "hit" if event == "cache_hit" else "miss" if event == "cache_miss" else "coalesced" if event == "coalesced" else "unknown"
    if context is not None and state != "unknown":
        context.cache_observed = True
        with context.lock:
            if context.cache_state == "unknown" or state == "miss":
                context.cache_state = state
    if context is not None and event == "physical_calls":
        context.provider_observed = True
    # Unadmitted identity churn must not grow the durable telemetry namespace.
    # Durable quota rejections for existing subjects live in quota_hourly.
    identified = context is not None and not (event == "rejected_requests" and not context.request_admitted)
    USAGE.observe(capability=capability, event=event, count=count,
                  principal_class=context.principal.principal_class if identified else "system",
                  principal_id=context.principal.principal_id if identified else "",
                  provider=(provider or PROVIDERS.get(capability, "unknown")) if event in {"physical_calls", "provider_failure", "provider_timeout"} else "none",
                  route_class=context.route_class if context else "internal", cache_state=state)
