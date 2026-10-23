# Production Location Reliability v1

Status: repository-side hardening only. Nothing in this document has been
deployed, and no Cloud Run, Vercel, secret or billing setting was changed.
Every infrastructure step below needs explicit owner approval.

## 1. Architecture (hosted)

```
Browser (10 s abort, explicit retry only)
  -> Vercel frontend (calls the backend directly, not through a proxy route)
  -> Cloud Run: uvicorn, 1 process, backend.api_main:app
       IngressMiddleware (Host/Origin) -> AbuseMiddleware (peer + capability admission)
       -> POST /location/resolve (sync route, runs on the AnyIO threadpool)
          -> accepted-resolution cache (60 s, per process)
          -> Google Geocoding (operation permit + durable Postgres usage guard)
          -> strict TGOS fallback only if Google was not accepted (same guards)
  -> Postgres usage guard (fresh connection per durable reservation, no pool)
```

Render is not the production backend authority.

## 2. What the repository controls versus what the console controls

| Setting | Where | Value |
|---|---|---|
| Container command | `Dockerfile.cloudrun` | `uvicorn ... --no-proxy-headers`, one process, no `--workers` |
| Max / min instances | Cloud Run console or gcloud only | Not in the repo. Earlier owner evidence: max 1, min 0 |
| Container concurrency | Cloud Run only | Not in the repo. **UNKNOWN**: needs `gcloud run services describe` |
| CPU allocation, startup CPU boost | Cloud Run only | Earlier evidence: throttling appeared disabled. Current value **UNKNOWN** |
| Startup/liveness probes | Cloud Run only | Not in the repo. Default TCP startup probe assumed |
| Per-process admission | `services/anti_abuse.py` | geocoding: 30 req/60 s per peer, 4 concurrent, 300 operations/h per process; tgos: the same |
| Body buffers | `backend/api/abuse_middleware.py` | 16 per process |
| Provider timeouts | `services/location_resolver.py` | Google cap 5 s, TGOS cap 5 s, both inside an 8 s resolve budget (this change) |
| Browser bound | `frontend_next/lib/workspace/location-confirmation.ts` | 10 s, no automatic retry |
| Durable quota DB | `services/usage_guard.py` | connect timeout 2 s, statement timeout 2 s, lock timeout 500 ms, no pool |

`scripts/verify_cloud_run_guardrails.py` checks an exported service description
for ingress and proxy headers only. It does not check capacity.

## 3. Capacity findings

- **A. Is max = 1 in the repo?** No. It exists only in the deployed service.
- **B. Two or three resolves at once in one process.** They run in parallel.
  The route is synchronous, so it runs on the threadpool (default 40 threads),
  and geocoding allows 4 concurrent operations. Tests check that 2 and 3 held-open
  resolves all succeed under the default policy (`test_simultaneous_resolves_share_one_process_under_default_geocoding_concurrency`).
  A 5th concurrent geocode in the same process fails fast with app 503
  `capacity_exhausted`. It is not queued (`test_simultaneous_resolves_beyond_process_permits_fail_fast_not_queue`).
- **C. Can the process serve more than one request?** Yes. Cloud Run's own
  429 "no available instance" can come from deployed `containerConcurrency`
  set to 1, or from requests waiting on a cold start. The repo cannot tell
  which. The owner must read `spec.template.spec.containerConcurrency`.
- **D. DB and provider caps if max > 1.** Every admission limit is per process:
  rate windows, permits, operation budgets and accepted-result caches. N
  instances give up to N times the provider-operation ceiling (geocoding
  300/h becomes 300·N/h) and N times the concurrent fresh Postgres
  connections. One fallback resolve opens up to 3 guard connections. Each cold
  instance also opens 2 connections at startup (guard check and ledger check).
  Admission keys on the transport peer with `--no-proxy-headers`. Behind Cloud
  Run, many users may share that peer, so the 30/60 s peer window may already
  act close to a per-instance global window. This is inferred, not proven.
- **E. CPU used after the response.** Yes, but none of it affects correctness:
  - `api-usage-flush` daemon thread: flushes usage telemetry to Postgres every
    10 s, plus a final flush at shutdown.
  - Optional Earth Engine worker manager, which only runs when satellite reference is enabled.

  Quota enforcement, provider calls and caching all finish inside the request.
  If CPU is throttled outside requests, telemetry rows arrive late (at the next
  request or at shutdown). Location results are not affected.

## 4. Cold start findings

Uvicorn runs lifespan startup before it binds the port. So a cold request waits for:

1. Importing `backend.api_main`, measured locally at **6.5 s** (2 runs, warm
   disk, 12-core Windows). The cost is spread across routers: `routes_lite`
   1.7 s, `fastapi` 1.4 s, `routes_location_insight` 1.2 s, `routes_admin`
   1.0 s, `routes_terrain_risk` 0.5 s. Cloud Run with 1 vCPU should not be
   faster. The exact hosted value is **UNKNOWN** until the startup latency
   metric is read.
2. Lifespan Postgres checks: the usage guard principal check and the ledger
   check. Each is a fresh TLS connection, with 2 s connect and 2 s statement
   timeouts.
3. The first Google/TGOS TLS handshakes.

Conclusion: with min instances = 0, the first lookup after idle is likely to go
past the 10 s browser bound before any provider is called. A retry is fast
because the instance is warm by then, and Google single-flight lets the retry
join any lookup still running. This matches the earlier evidence. The
server-side deadline cannot fix cold start. Only min instances ≥ 1, startup CPU
boost, or a smaller import graph can.

## 5. Request latency model (warm)

| Segment | Typical | Bound after this change |
|---|---|---|
| Browser -> Vercel -> Cloud Run, TLS, admission | small | outside the server budget, about 2 s reserved |
| Durable usage guard (request + operation) | small | DB timeouts (≤ 2 s connect + 2 s statement each). Pathological only |
| Google Geocoding | sub-second | ≤ 5 s (connect ≤ 1.5 s + read) and ≤ remaining budget |
| TGOS fallback (only if Google not accepted) | provider-dependent | starts only if ≥ 2 s remain, then ≤ min(5 s, remaining) |
| Whole resolve | Google latency | **8 s budget**. Worst-case overrun is one in-flight DB reservation |

Before this change, httpx's 5 s applied **to each phase** (connect, read,
write, pool) of each provider. One provider could take about 10 s, and Google
followed by TGOS could take about 20 s. The browser had already given up by
then, and the orphaned server work kept holding geocoding permits.

## 6. Server deadline (implemented)

`resolve_address` sets one deadline: request start + `RESOLVE_BUDGET_SECONDS` (8 s).

- Google always runs first. Its httpx timeout is computed when the call starts
  (after admission), so connect + read fit both the 5 s cap and the remaining
  budget.
- TGOS runs only when Google was not accepted and at least
  `TGOS_MIN_REMAINING_SECONDS` (2 s) remain. If TGOS is skipped for budget, the
  result is `unavailable` (retryable). It is never reported as a confident
  `unresolved`.
- A call with less than 0.5 s left is not started (no physical call, no spend).
- There is still no automatic retry. Acceptance rules are unchanged: Google
  ROOFTOP + non-partial + structural agreement, strict TGOS full match, and
  rejection of cross-district matches.

The 10 s browser timeout is unchanged on purpose.

## 7. Observability

Each resolve emits one structured stdout JSON line, `"message":"location_resolve"`.
Cloud Logging reads `severity` from it: INFO for normal outcomes, WARNING for
degraded ones. All fields are bounded categories:

| Field | Values |
|---|---|
| `outcome` | `google_resolved`, `tgos_resolved`, `unresolved`, `unavailable`, `reused` (cache/in-flight), `admission_rejected`, `server_error` |
| `google`, `tgos` | `accepted`, `precision_rejected`, `structural_mismatch`, `zero_results`, `fuzzy_rejected`, `timeout`, `http_error`, `provider_status`, `malformed_response`, `invalid_coordinate`, `deadline_exhausted`, `skipped_budget`, `not_configured`, `not_attempted`, `started` (admission rejected mid-flight) |
| `admission` | `admitted` or the app reason code (`capacity_exhausted`, `provider_budget_exhausted`, ...) |
| `fallback` | whether a TGOS call was attempted |
| `google_ms`, `tgos_ms`, `total_ms`, `budget_ms` | integer milliseconds |
| `first_in_process`, `process_age` | cold-start evidence (`lt_30s`, `lt_5m`, `warm`) |

The line never contains addresses, coordinates, credentials or provider payloads (tested).

How to tell each failure apart:

- **Cloud Run capacity unavailable**: Cloud Run's 429 is not produced by the
  app. It has no JSON `reason_code`, no `X-Correlation-ID`, and no
  `location_resolve` line. App rejections always have a `reason_code`.
- **Cold start**: the Cloud Run request log shows a new instance start, and
  the event has `first_in_process: true` with `process_age: lt_30s`.

Remaining gap (not changed here): the existing `proptech.observability`
`request_completed` INFO lines are not emitted under uvicorn's default logging
config, because only WARNING and above reach the last-resort handler.

## 8. Capacity recommendation: **KEEP MAX = 1**

Evidence: one process already serves 2 or 3 simultaneous resolves (tested). The
observed failures fit cold start (6.5 s+ import plus startup DB checks with
min = 0), or a possible low `containerConcurrency`. A higher max does not fix
either one. It adds more cold instances and multiplies process-local budgets.

| Impact | MAX=1 (keep) | MAX=2 / MAX=3 |
|---|---|---|
| Reliability | Cold start remains the main risk. Steady-state 2–3 concurrent resolves are fine | Helps only with real sustained concurrency (not observed). Each extra instance is another cold start |
| Cost | Unchanged | More instance time is possible. Exact amount **UNKNOWN** |
| DB | ≤ 1 process of guard connections | Up to 2–3× concurrent fresh connections and 2–3× startup checks. No pool |
| Provider quota | geocoding/tgos ceiling 300 ops/h each | 600–900 ops/h each. Not a global ceiling |
| Abuse | Process-local limits act as the effective service limit | Per-instance limits multiply. No shared limiter exists |

Owner actions to approve, in priority order (not done):

1. Read the current config:
   `gcloud run services describe SERVICE --region REGION --format=json`.
   Record `containerConcurrency`, `autoscaling.knative.dev/minScale` /
   `maxScale`, `run.googleapis.com/cpu-throttling`, and
   `run.googleapis.com/startup-cpu-boost`.
2. If `containerConcurrency` < 8, set it to about 8–20 rather than raising max.
   Process permits (geocoding 4, bodies 16) already bound the work.
3. Turn on startup CPU boost to shorten the import-bound cold start.
4. Decide on min instances = 1. This is the most direct fix for first-lookup
   timeouts. Cost is **UNKNOWN** and has to come from billing.

## 9. CPU mode recommendation

Request-based billing (CPU throttled outside requests) is **safe for
correctness**. Only the usage-telemetry flush runs after the response, and it
only arrives later. Instance-based billing is needed only if timely ledger rows
matter, or if min instances = 1 is adopted and idle background flushing is
wanted. Startup CPU boost is recommended either way. Exact SKU and billing
impact are **UNKNOWN**.

## 10. Cost certainty

- **Proven from the repo:** single uvicorn process; per-process limits and
  ceilings above; no capacity settings in the repo; work after the response is
  limited to telemetry.
- **From earlier owner evidence, not re-verified here:** max 1, min 0, CPU
  throttling appeared disabled, sporadic Cloud Run 429.
- **Inferred risk:** cold start is longer than the 10 s browser bound; max > 1
  multiplies provider/DB exposure.
- **Unknown:** exact Cloud Run SKU, monthly bill, current `containerConcurrency`,
  and the hosted cold start duration.

## 11. Hosted smoke protocol (run only after an approved deploy)

Rules:

- One request per address per phase.
- Wait at least 65 s between repeats of the same address, so the 60 s
  accepted-result cache does not hide provider behaviour.
- Total budget for the whole protocol: ≤ 8 resolve requests.
- No loops and no load testing.
- Send the Origin header the hosted frontend sends, which must be an approved CORS origin.

Addresses:

| ID | Address | Expected |
|---|---|---|
| A | 新北市新莊區中正路191號 | must **not** resolve to 樹林區. Accepted only with district 新莊區, otherwise `unresolved`/`unavailable` |
| B | 臺北市信義區市府路1號 | known-good control: `resolved`, `google`, district 信義區 |
| C | owner-supplied complete address with 段/巷/弄/號 | must be checked by the owner before the smoke. The repo fixtures (`信義路四段10巷2弄3號`) are synthetic and must not be used |

Phases:

1. **Cold**: after at least 20 min idle, or right after deploy. Send B once.
2. **Warm**: within 2 min, send A, then C, then B.

For each request, record:

```powershell
$body = @{ address = '臺北市信義區市府路1號' } | ConvertTo-Json -Compress
$sw = [Diagnostics.Stopwatch]::StartNew()
$r = Invoke-WebRequest -Method Post -Uri "$env:BACKEND_PRODUCTION_URL/location/resolve" `
  -ContentType 'application/json; charset=utf-8' -Headers @{ Origin = $env:FRONTEND_PRODUCTION_URL } `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) -SkipHttpErrorCheck
$sw.Stop()
[pscustomobject]@{ status = $r.StatusCode; ms = $sw.ElapsedMilliseconds;
  correlation = $r.Headers['X-Correlation-ID']; body = $r.Content }
```

(`-SkipHttpErrorCheck` needs PowerShell 7. The `curl -w '%{http_code} %{time_total}'` equivalent is fine.)

| Column | Source |
|---|---|
| HTTP status | response. 429/503 without `reason_code` means a Cloud Run capacity rejection |
| End-to-end latency | client stopwatch. Must be < 10 000 ms |
| source | body `source` |
| interpreted address | body `formatted_address`, `county`, `district` |
| coordinate presence | `latitude`/`longitude` non-null only when `status=resolved` |
| structural match | `district` equals the supplied district. For A, never 樹林區 |
| fallback occurred | Cloud Logging `location_resolve` line for the correlation window: `fallback`, `google`, `tgos` |
| no unexpected provider calls | event shows `tgos: not_attempted` when Google accepted; `/metrics` (needs the owner's scrape token header) `proptech_provider_cost_events_total{capability="geocoding",event="physical_calls"}` grows by ≤ 1 per non-reused request, and by 0 for `tgos` unless `fallback` is true |
| cold start | Cloud Run request log instance start; event `first_in_process` / `process_age` |

Pass criteria:

- A never resolves to 樹林區.
- B resolves through Google, with no TGOS call.
- C is accepted only if it matches structurally.
- Every warm request finishes in < 8.5 s server-side (`total_ms`) and < 10 s end to end.
- No `server_error`.

A cold B that goes past 10 s is recorded as cold-start evidence for the
min-instances decision. It does not mean the deploy failed.
