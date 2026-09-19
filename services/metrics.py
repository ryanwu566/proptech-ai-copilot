"""Dependency-free, bounded production metrics primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
import threading
from collections.abc import Awaitable, Callable, Iterable, MutableMapping
from typing import Any


UNMATCHED_ROUTE = "/__unmatched__"
ALLOWED_METHODS = frozenset({"DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"})
LATENCY_BUCKETS_SECONDS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
MAX_LATENCY_SECONDS = 120.0
_ROUTE_PARAMETER = re.compile(r"\{[^{}]+\}")
_SAFE_ROUTE_TEMPLATE = re.compile(r"/[A-Za-z0-9._~!$&'()*+,;=:@%/{}-]*\Z")
_SCRAPE_TOKEN = re.compile(r"[A-Za-z0-9._~+/-]+={0,2}\Z")
_ROUTE_LABEL_STATE_KEY = "proptech.observability.route_label"

_Receive = Callable[[], Awaitable[dict[str, Any]]]
_Send = Callable[[dict[str, Any]], Awaitable[None]]
_AsgiApp = Callable[[dict[str, Any], _Receive, _Send], Awaitable[None]]


def valid_scrape_token(value: object) -> bool:
    """Accept only bounded, header-safe scrape credentials."""

    return (
        isinstance(value, str)
        and 32 <= len(value) <= 512
        and _SCRAPE_TOKEN.fullmatch(value) is not None
    )


def canonical_route_template(value: object) -> str:
    """Return a safe template shape, never a raw request path fallback."""

    if not isinstance(value, str) or not value.startswith("/") or len(value) > 160:
        return UNMATCHED_ROUTE
    template = _ROUTE_PARAMETER.sub("{param}", value)
    if (
        "?" in template
        or "#" in template
        or "\\" in template
        or any(ord(character) < 32 for character in template)
        or not _SAFE_ROUTE_TEMPLATE.fullmatch(template)
        or template.count("{") != template.count("}")
    ):
        return UNMATCHED_ROUTE
    return template


def route_template_from_scope(scope: dict[str, object]) -> str:
    """Read only the registered Starlette route template from an ASGI scope."""

    route = scope.get("route")
    return canonical_route_template(getattr(route, "path", None))


def _request_state(scope: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    state = scope.get("state")
    if isinstance(state, MutableMapping):
        return state
    state = {}
    scope["state"] = state
    return state


def captured_route_label(scope: MutableMapping[str, Any]) -> str:
    """Return the one post-routing label captured for this request, if any."""

    value = _request_state(scope).get(_ROUTE_LABEL_STATE_KEY)
    return value if isinstance(value, str) else UNMATCHED_ROUTE


class _RouteLabelCapture:
    """Capture a route's registered template after the router selects it."""

    def __init__(self, app: _AsgiApp, route_template: object) -> None:
        self.app = app
        self.route_label = canonical_route_template(route_template)

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: _Receive,
        send: _Send,
    ) -> None:
        state = _request_state(scope)
        state.setdefault(_ROUTE_LABEL_STATE_KEY, self.route_label)
        await self.app(scope, receive, send)


def install_route_label_capture(routes: Iterable[object]) -> None:
    """Wrap registered route handlers at their post-match ASGI boundary."""

    for route in routes:
        route_app = getattr(route, "app", None)
        route_template = getattr(route, "path", None)
        if not callable(route_app) or not isinstance(route_template, str):
            continue
        if isinstance(route_app, _RouteLabelCapture):
            continue
        route.app = _RouteLabelCapture(route_app, route_template)


def _method_label(value: object) -> str:
    method = str(value or "").upper()
    return method if method in ALLOWED_METHODS else "OTHER"


def _status_class(value: object) -> str:
    if isinstance(value, bool):
        return "other"
    try:
        status_code = int(value)
    except (TypeError, ValueError, OverflowError):
        return "other"
    return f"{status_code // 100}xx" if 100 <= status_code <= 599 else "other"


def _duration(value: object) -> float:
    try:
        duration = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if not math.isfinite(duration):
        return MAX_LATENCY_SECONDS if duration > 0 else 0.0
    return max(0.0, min(duration, MAX_LATENCY_SECONDS))


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _number(value: float) -> str:
    return format(value, ".12g")


@dataclass
class _Histogram:
    bucket_counts: list[int] = field(
        default_factory=lambda: [0 for _ in LATENCY_BUCKETS_SECONDS]
    )
    count: int = 0
    total: float = 0.0

    def observe(self, duration: float) -> None:
        for index, boundary in enumerate(LATENCY_BUCKETS_SECONDS):
            if duration <= boundary:
                self.bucket_counts[index] += 1
        self.count += 1
        self.total += duration


class BoundedMetricsRegistry:
    """Thread-safe HTTP metrics whose labels come from fixed finite domains."""

    def __init__(self, route_templates: Iterable[str]) -> None:
        allowed_routes = {
            canonical
            for route in route_templates
            if (canonical := canonical_route_template(route)) != UNMATCHED_ROUTE
        }
        self._allowed_routes = frozenset({*allowed_routes, UNMATCHED_ROUTE})
        self._request_totals: dict[tuple[str, str, str], int] = {}
        self._latencies: dict[tuple[str, str], _Histogram] = {}
        self._responses_429 = 0
        self._responses_5xx = 0
        self._lock = threading.Lock()

    @property
    def allowed_routes(self) -> frozenset[str]:
        return self._allowed_routes

    def observe_http_request(
        self,
        *,
        method: object,
        route_template: object,
        status_code: object,
        duration_seconds: object,
    ) -> None:
        method_label = _method_label(method)
        canonical_route = canonical_route_template(route_template)
        route_label = (
            canonical_route
            if canonical_route in self._allowed_routes
            else UNMATCHED_ROUTE
        )
        status_label = _status_class(status_code)
        latency = _duration(duration_seconds)
        request_key = (method_label, route_label, status_label)
        latency_key = (method_label, route_label)

        with self._lock:
            self._request_totals[request_key] = self._request_totals.get(request_key, 0) + 1
            histogram = self._latencies.setdefault(latency_key, _Histogram())
            histogram.observe(latency)
            if status_label == "5xx":
                self._responses_5xx += 1
            if status_code == 429:
                self._responses_429 += 1

    def render_prometheus(self) -> str:
        """Render a deterministic Prometheus text exposition snapshot."""

        with self._lock:
            request_totals = dict(self._request_totals)
            latencies = {
                key: (tuple(value.bucket_counts), value.count, value.total)
                for key, value in self._latencies.items()
            }
            responses_429 = self._responses_429
            responses_5xx = self._responses_5xx

        lines = [
            "# HELP proptech_http_requests_total Total HTTP requests.",
            "# TYPE proptech_http_requests_total counter",
        ]
        for (method, route, status_class), count in sorted(request_totals.items()):
            lines.append(
                "proptech_http_requests_total"
                f'{{method="{_escape_label(method)}",route="{_escape_label(route)}",'
                f'status_class="{_escape_label(status_class)}"}} {count}'
            )
        lines.extend(
            (
                "# HELP proptech_http_responses_429_total Total HTTP 429 responses.",
                "# TYPE proptech_http_responses_429_total counter",
                f"proptech_http_responses_429_total {responses_429}",
                "# HELP proptech_http_responses_5xx_total Total HTTP 5xx responses.",
                "# TYPE proptech_http_responses_5xx_total counter",
                f"proptech_http_responses_5xx_total {responses_5xx}",
                "# HELP proptech_http_request_duration_seconds HTTP request latency.",
                "# TYPE proptech_http_request_duration_seconds histogram",
            )
        )
        for (method, route), (buckets, count, total) in sorted(latencies.items()):
            labels = f'method="{_escape_label(method)}",route="{_escape_label(route)}"'
            for boundary, bucket_count in zip(LATENCY_BUCKETS_SECONDS, buckets):
                lines.append(
                    "proptech_http_request_duration_seconds_bucket"
                    f'{{{labels},le="{_number(boundary)}"}} {bucket_count}'
                )
            lines.append(
                "proptech_http_request_duration_seconds_bucket"
                f'{{{labels},le="+Inf"}} {count}'
            )
            lines.append(
                f"proptech_http_request_duration_seconds_count{{{labels}}} {count}"
            )
            lines.append(
                f"proptech_http_request_duration_seconds_sum{{{labels}}} {_number(total)}"
            )
        return "\n".join(lines) + "\n"
