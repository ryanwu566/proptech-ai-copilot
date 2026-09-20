# Production observability — Metrics Slice A

## Existing observability audit

The backend already had one centralized FastAPI request middleware in
`backend/api_main.py`. It generated correlation IDs, measured request time,
applied response security headers, converted unhandled exceptions into safe
responses, and logged bounded status/error categories for unsuccessful
requests. Slice A uses that middleware as the HTTP metrics insertion point
instead of adding a second request-observation stack.

Other existing signals serve different purposes and are not duplicated:

- `/performance/metrics` accepts allowlisted, sampled browser performance
  events. It is client telemetry ingestion, not a server metrics registry.
- Map and terrain services calculate local timing fields for their response
  contracts and diagnostic logs.
- Public map and pilot endpoints have independent bounded rate limiters.
- Market, map, and terrain code emits application-specific diagnostic logs.
- The repository had no Prometheus/OpenTelemetry registry, scrape endpoint,
  metrics package, or external observability SaaS integration.

Some pre-existing application logs contain business-region or map-query
context. Slice A does not broadly rewrite those logs. The centralized request
log touched by this work now uses the same registered, bounded route template
as HTTP metrics and never falls back to a raw request path.

## Slice A boundary

The in-process registry exposes only HTTP request totals, status class, 429
and 5xx totals, and fixed-bucket request latency. Metric labels are limited to
a fixed HTTP method set, fixed status classes, and canonical templates derived
from the FastAPI routes registered at startup. Every route parameter becomes
`{param}`. Unknown, unmatched, and pre-routing traffic becomes
`/__unmatched__`.

The scrape endpoint is disabled when `METRICS_SCRAPE_TOKEN` is absent and
returns the same generic not-found response for absent, missing, or incorrect
credentials. Operators must supply the value through their secret-management
boundary. This document deliberately provides no credential example.

## Provider metrics decision

Provider metrics are **DEFERRED**. Outbound calls are distributed across
separate Google, TGOS, NLSC, banking, transit, and terrain adapters using
different client lifecycles and error contracts. There is no centralized
provider boundary that can be instrumented without a cross-adapter refactor.
Slice A therefore does not alter provider behavior or semantics.
