# Wave 1B: API usage, quota and abuse controls v1

## Scope and starting state

Authoritative main: `319d7ef397e63493edebf4c91e6365bf929a04bf` (PR #187).
Worktree: `C:\Projects\proptech-api-usage-abuse-v1`, branch `infra/api-usage-abuse-v1`.
At inspection it was clean, seven commits behind main and one local feature commit ahead. The existing feature commit predated Wave 1A and provided local quotas plus optional aggregate telemetry. It was rebased, then extended to the requested shared quota contract. Migration 020 and every historical migration remain unchanged; this wave owns 021 and the next available sequence is 022.

No Admin UI/control plane, billing, subscriptions, cross-device Saved Cases, ML, deployment or hosted migration is included. No provider load testing is permitted.

## Threat model and identity boundaries

An attacker can rotate headers, query parameters, bodies, retry keys and editable JWT metadata, race multiple instances, exploit restarts, saturate caches/identity maps and trigger provider failures. The application server and its deployment credentials are trusted; an attacker controlling a backend guard credential can assert subjects and consume their allowance. That credential is never a consumer credential.

Authenticated subjects are `user:<AuthenticatedPrincipal.user_id>` using the canonical verified UUID, never email or metadata. Existing Supabase JWT verification is the only verifier. VNext admission binds the identity after `require_active_account` succeeds. Public expensive routes optionally use the same verifier plus `AccountAuthorizer.require_active`; absent Authorization remains anonymous. Invalid, suspended, missing or unavailable account authority cannot fall back to anonymous. Account status reads (`/v1/account`) remain available to suspended users as Wave 1A requires.

Headers `X-User-ID`, `X-Role`, `X-Workspace-Role`, `X-Forwarded-For`, `Forwarded`, `X-Real-IP`, `X-Client-IP`, query `user_id`, browser storage and `user_metadata` cannot select a quota subject. VNext's existing identity-override rejection is preserved.

Anonymous subjects are `anon:<HMAC-SHA256>` over a domain-separated, bounded direct transport peer, without its port. `API_USAGE_PEER_HMAC_KEY` must be exactly 64 hexadecimal characters (32 random bytes, generated outside this repository). It stays backend-only and must be identical across instances. The UUID is pseudonymous and directly correlatable to account authority by authorized backend operators/readers. The HMAC is opaque coarse peer accounting, **not** a unique person/device or a claim of anonymity. Shared NAT/proxy peers share allowance. Forwarding headers remain untrusted; proxy topology must be assessed before hosted acceptance.

Missing peers share the bounded `unknown` peer bucket. Production, preview and the existing serverless deployment contract require a valid key. Any durable usage URL also requires it. Only development without durable configuration may use an ephemeral process key. Rotate the key with a coordinated fleet restart: anonymous identities and allowance change, retained old aggregates cannot be joined without retaining the old key and original peer externally, and mixed keys temporarily partition anonymous budgets. Authenticated subjects do not change. Rotation cannot be advertised as preserving anonymous quota continuity.

## Admission and endpoint inventory

The independent layers remain:

1. Existing ingress, byte/query/body deadline and bounded resource safety envelopes.
2. Existing coarse-peer and aggregate process capability request admission.
3. Existing per-capability process provider-operation budget.
4. Authenticated subject request/hour and operation/hour/day durable quota.
5. Anonymous coarse-peer request/hour and operation/hour/day durable quota.
6. Existing physical capability semaphore and bounded local principal concurrency.
7. Environment emergency `ANTI_ABUSE_<CAPABILITY>_DISABLED`; malformed values reject.

Local short-window principal quotas remain an additional envelope. No local ceiling was raised. Shared subject budgets do not make existing global/provider safety envelopes fleet-global; provider account/ingress ceilings remain required.

| Endpoint family | Admission choice |
| --- | --- |
| Map search/nearby/insight, location resolve/insight | Existing geocoding/places/metadata/location capability; optional verified active account, otherwise coarse anonymous |
| Commute lookup/nearest/route | Geocoding/metadata/routes, preserving anonymous exploration and cached results |
| Commute refresh | Existing operator token first at route; `market_ops` request envelope and provider reservation/kill switch; token never becomes a consumer identity |
| Satellite, terrain, valuation, trend, finder, parcel analysis | Corresponding existing capability, shared subject budget before work; individual internal fan-out reservations remain separate |
| Market reads and comparisons | Existing market or metadata request class and market operation reservation; no authentication added |
| Market refresh/coverage operator mutations | Existing operator authorization plus strict `market_ops` limits; same coarse peer budget unless an active verified consumer bearer is supplied; no privileged tier derived from an operator token |
| VNext resolutions/planning/observations | Existing protected router JWT, active account, workspace/feature gates; identity capability admission; provider operations remain at adapters |
| VNext stored cases/properties/read-only account, health, source/config status, fixed UI options, calculators and bundled-only lite/tax workflows | No new identity quota middleware classification; existing authorization, ingress/body and product controls remain. Login/signup/logout acquire no usage quota and call no provider |
| Roads/demographics/market metadata | Existing bounded metadata admission; intentionally conservative shared hourly request budget, no physical-provider claim for local reads |
| Internal provider fan-out | No synthetic logical HTTP requests; per-operation reservation with propagated context and physical dispatch counters at existing transport boundaries |

The authoritative provider metric vocabulary has 20 finite capabilities, including helper dimensions `address_resolution` and `places_request`. The abuse policy vocabulary has 18 capabilities. Helpers do not become separate billable provider calls.

## Durable schema and atomicity

Migration `021_api_usage_quota_ledger.sql` creates private `api_usage`, never an exposed browser schema:

- `quota_policy`: exactly the supported principal classes and checked integer request/hour, operation/hour and operation/day limits. Initial anonymous values: 1200/240/1000; authenticated: 6000/600/2000. The backend request role cannot update them. Existing local short-window limits can reject earlier. There is no billing/entitlement adapter.
- `quota_subjects`: one checked subject, class, UTC hour/day buckets, successful request count, reserved operation count, daily operation count and update timestamp. Maximum 100,000 retained subjects. Expired inactive subjects are pruned only after two days, longer than every enforced quota window.
- `quota_hourly`: UTC bucket, subject, finite capability, admitted logical requests, quota rejections and operation reservations. Admission and rejection are distinct additive counters, never reconstructed from provider success.
- `reservation_markers`: subject, server-generated UUID, finite capability, request/operation kind and creation time. No payload or client key.
- `hourly`: telemetry dimensions bucket, principal class/ID, capability, finite provider/route/status/cache classes and backend release SHA; nonnegative aggregate counters listed below.
- `flush_batches`: random backend UUID and creation timestamp for atomic telemetry batch retries.

`api_usage.consume` validates every dimension, reads database-owned policy and takes a transaction-scoped advisory lock on the subject across capabilities and kinds. New subject creation also uses one bounded registry lock to enforce the subject cap. It then locks the subject row and selects the database clock **after** lock waits, preventing an older waiting request from resetting a newer hour. Counter comparison, mutation, hourly admission/rejection and the marker commit in one transaction. Rejection commits only its separate rejected observation. Multiple connections/instances and restarted adapters observe the same committed allowance. Hash-lock collisions serialize extra work; they do not grant extra allowance.

A successful admission means acceptance by the quota boundary, not a successful product response: later body/field validation, workspace authorization or provider failure can still return an error while consuming that admitted logical request. Quota rejection itself never increments admitted/reservation consumption.

The function is the atomic boundary; there is no Python read/compare/later-write race. No dispatch occurs before its committed success. An ambiguous commit fails the request closed; an internal retry with the same still-live marker can recover the decision. Conservatively consumed allowance after a lost acknowledgement or cancellation is not refunded automatically. Policy is database-owned so one stale Python process cannot supply a larger shared limit.

## Retry and duplicate semantics

A logical admission creates one random server UUID in its request context. Each real owner operation creates a separate random server UUID. Neither HTTP `Idempotency-Key` nor `X-Correlation-ID` participates. Within ten minutes, the same subject/marker/capability/kind returns duplicate without incrementing successful counters. A mismatched use fails closed. Each subject has at most 2048 live markers; saturation returns safe 503. Collision is conservative duplicate/mismatch behavior, not an unbounded namespace. Expired markers are removed in bounded batches; reuse after pruning is a new admission, while an expired marker still awaiting cleanup denies conservatively. Do not retry a decision beyond its documented lifetime.

This deduplicates internal database reservation retries, not arbitrary HTTP re-execution or provider transport attempts. A new HTTP request is a new admission, including a replay of a business command; existing business idempotency/cache may avoid provider work independently. A quota marker is not a response cache or permission to suppress physical-attempt counters.

Telemetry uses a separate immutable batch UUID and transaction marker. Lost commit responses replay the same UUID and payload. A retained retry batch is abandoned after one hour from capture, with every abandoned observation reported as loss; hourly bucket age cannot immediately expire a fresh batch near an hour boundary. Batch markers retain two hours. Fresh aggregate batches can contain older bounded pending telemetry after an outage; metrics still expose incomplete/lost state. Process death can lose unflushed telemetry. These counters are not an invoice or an exact crash-proof event log.

## Provider and cost definitions

Logical request, conservative operation reservation and actual physical transport attempt are different counters. A cache hit or coalesced follower consumes a logical request allowance but creates no additional owner reservation/physical call. Rejection before dispatch creates no physical attempt. A dispatch that fails or times out still counts a physical attempt and the appropriate failure/timeout. Reservation is conservative and may precede work that cannot dispatch; it is never called a physical attempt.

TDX operator refresh counts each actual HTTP dispatch, including token authentication: a complete refresh is three attempts (one token POST, two data GETs), not three invented billable units. Failure/timeout counts survive token or later-data failure, and a per-boundary kill check prevents further dispatch after disable. Its finite `tdx_mrt` provider dimension has unknown monetary cost.

Existing physical counters at Google, Earth Engine and instrumented terrain/gateway boundaries remain authoritative for those measured transports. Context is propagated into executor/worker fan-out and detached producers. Composite pipelines and uninstrumented storage/subprovider work retain an explicit unknown accounting state; observing one child cache hit does not mark the whole pipeline complete. Do not sum nested helper observations as billable calls.

No currency amounts are persisted or inferred. Without an authoritative configured unit, cost is unknown with a null estimate, never zero. Zero observed physical attempts only means no measured dispatch (and does not establish complete coverage). Existing optional configured estimates are labeled estimates and never determine quota.

## Failure and error contract

Production/preview/serverless require PostgreSQL guard mode; explicit local mode fails startup. Missing/malformed database/key/configuration fails closed. Local admission/kill checks run before public bearer verification or account database work. A configured guard's startup probe rejects owner, superuser, BYPASSRLS, role-creation and executor-member credentials (including a privileged session hidden behind SET ROLE), then checks function access without consuming quota. Database connect, statement and lock waits are bounded (2 seconds, 2 seconds and 500 ms respectively).

Request/provider reservation database errors produce generic `guard_unavailable` 503 before that work, with no SQL/DSN/provider detail. Quota exhaustion produces 429, finite `anonymous_quota`/`authenticated_quota` reason and deterministic `Retry-After` in 1..3600 seconds. Daily exhaustion may require multiple bounded retries. VNext retains its structured error envelope. Emergency disable and physical capacity rejections preserve existing safe contracts.

Request and asynchronous provider admission wait in worker threads, keeping the event loop responsive. Cancellation drains an in-flight admission before releasing local permits; a committed reservation can remain consumed while no provider call occurs. Existing cache-owner physical permits survive cancellation until their producer stops.

Telemetry is deliberately fail-open after startup when its writer is unavailable: buffers stay bounded, drops/expiry/unavailability are observable, and **shared quotas do not fall back to telemetry or process counters**. Operators should require `API_USAGE_LEDGER_REQUIRED=true` where complete startup writer readiness is required. An outage affecting the quota guard cannot become unlimited expensive access.

## Grants, RLS and future control seams

All six tables have ENABLE and FORCE RLS. PUBLIC schema/table/function access is revoked; browser `anon`, `authenticated`, `service_role` and VNext request roles have no guard or ledger authority. Workspace owner and account `platform_admin` claims do not change SQL roles or grants.

`proptech_usage_guard` gets schema USAGE and EXECUTE on bounded consume only, with no SELECT/DML/policy grants. `proptech_usage_executor` is a NOLOGIN, NOBYPASSRLS definer separate from table ownership, with explicit RLS and only the table privileges needed for consume/prune; its functions have empty fixed search paths and no dynamic client SQL. Never grant this role to request logins. `proptech_usage_writer` writes aggregate telemetry, manages batch markers and invokes bounded pruning; it cannot mutate quota policy or successful quota counters. `proptech_usage_reader` reads aggregates only and is not a browser grant. A deployment login requires the guard and writer grant roles; VNext uses its existing separate credentials.

Ordinary table owners obey FORCE RLS without a matching policy. Superuser/BYPASSRLS can bypass RLS and are therefore forbidden runtime credentials; local tests explicitly demonstrate both facts. FORCE RLS does not make a database owner safe for application use. Restrict provisioning and schema exposure independently of RLS.

Future Wave 1C may wrap authorized aggregate reads and policy mutations with explicit server authorization and an audit trail. No such mutation API/UI is implemented. Environment emergency disable stays the final escape hatch. Future policy tools must validate caps, invalidate operational expectations safely and audit actors; a platform role alone is not database-owner authority.

## Privacy, retention and observability

Telemetry counters persisted: observations, requests, admitted, rejected, responses_429, responses_5xx, provider_attempt_count, provider_accounting_unknown, provider_failures, provider_timeouts, quota_units (reservations), cache_hits, cache_misses, cache_unknown, coalesced, latency_count, latency_sum_ms, latency_le_100ms, latency_le_1000ms and latency_le_10000ms. No event-level timestamp/path/body is stored. Latency is capped at 120 seconds per observation; routes are method/capability classes only.

Unadmitted peer churn is collapsed to system telemetry rows. Existing admitted subjects' quota rejections are still attributed in `quota_hourly`. This avoids persisting a new subject for every pre-admission rejection. Local buffers retain at most 4096 aggregate keys each; helper/provider/status/cache labels are finite. The subject registry and marker cap prevent an unlimited client-generated retry namespace. Thirty-day hourly retention supports short incident/quota investigations, not indefinite analytics. Subject state lives two inactive days; request/operation markers ten minutes; batch markers two hours. No request-body deduplication, profile enrichment or cross-device tracking is performed.

Explicitly not collected: raw transport IP, forwarding header values, email, addresses, coordinates, search terms, payload/response bodies, tokens/passwords/JWTs, provider credentials, cache keys, provider request IDs, browser storage or arbitrary resource paths. Authorized readers can correlate authenticated UUIDs to accounts; access must be restricted and included in future deletion/access governance. There is no self-service ledger deletion or Admin UI in this wave; retention bounds the current operational copy.

The background writer runs pruning every 5..60 seconds (default 10), including quiet/empty flushes. Per pass, delete at most 5000 expired rows per table; admission also removes at most 256 expired markers for its subject. Subject deletion waits until markers have drained, avoiding cascade amplification. Pruning captures one timestamp per pass so age predicates use retention indexes; disposable auto_explain nested plans verify age Index Conds. Pruning uses row locks with SKIP LOCKED so it cannot reset a subject currently being admitted. Indexes support subject locks, bucket aggregation and age scans. On prolonged downtime no new process traffic is recorded; after recovery the writer catches up at the bounded rate. Monitor backlog and provision maintenance capacity if ingest exceeds pruning throughput. Revoked writer privileges or persistent failures require operational repair; exhausted registry/marker capacity denies work safely.

`/metrics` and `/provider-status` retain the existing scrape-token boundary and generic 404 for unauthorized scrapes. Prometheus uses only finite capability/provider/event/reason/measure labels. No UUID, HMAC, IP, release, arbitrary route, query or payload is a metric label. Existing admission, local concurrency, operation-budget, kill-switch, guard unavailable, attempt/failure and cache/coalesced metrics remain; finite authenticated/anonymous quota rejection events are added. Process-local usage summary is labeled as such; durable aggregates exclude buffered telemetry and must not be presented as exact fleet invoices.

## Production configuration and operational limitations

Before any later deployment, provision/review private migration 021 with the existing registry runner, backend-only nonowner login grants, TLS/connection capacity and one shared HMAC key; configure `API_USAGE_DATABASE_URL`, default/explicit `API_USAGE_GUARD_MODE=postgres`, and preferably `API_USAGE_LEDGER_REQUIRED=true`. Environment manifest contains metadata only, no secret values. Preserve provider/ingress ceilings and scrape tokens. Do not expose `api_usage` in the Data API or reuse VNext/browser/service-role/owner credentials.

The guard opens bounded-deadline connections per operation rather than introducing a new pool. Subject creation uses a globally serialized bounded count (maximum 100,000); production capacity/connection benchmarks remain necessary. Existing process-local physical/capability/provider envelopes do not coordinate fleet concurrency or global provider account spend. No load claim is made beyond local deterministic tests. HMAC rotation/proxy peers, accepted-but-undispatched reservations, ten-minute dedup horizon, telemetry loss on crash/outage and retention catch-up are explicit limits.

PostgreSQL locking and FORCE RLS behavior were checked against official documentation and disposable PostgreSQL 17.11. Local tests do not prove hosted schema/grants, proxy peer selection, fleet secret consistency, production concurrency/latency, provider invoices, failover/backup behavior or actual deployment identity. Hosted acceptance remains NO_GO without later owner evidence. No production system was contacted or changed.

## Validation and adversarial review

Current-session exact commands, outcomes, independent findings and final file inventory are recorded in the acceptance appendix below. Earlier pre-Wave-1A test claims were superseded; they are not evidence for this continuation.

### Independent review (fresh read-only agent)

No Critical findings. Three Important findings were independently identified and each reproduced RED, fixed and verified GREEN:

1. Optional public authentication preceded local capability/peer admission. Local controls now execute once before JWT/JWKS/account work; durable authenticated quota still waits for active-account authority. Invalid bearer retries and disabled capability tests verify the ordering.
2. Newly inventoried TDX transport dispatched without physical accounting. Success/token/later-data failure and disabled tests now cover finite provider observations, attempts/failures/timeouts and unknown cost. Provider overrides are allowlisted and cannot identify a no-provider physical call.
3. Volatile clock comparisons prevented retention index conditions. Pruning now captures its clock once; a real PostgreSQL auto_explain test observes Index Conds for marker creation age, subject update age and hourly bucket age, while concurrent pruning/retention tests remain green.

Deferred Minor: the server-only `PostgresUsageStore.summary` retains legacy `fleet_quota_enforced=false`, which describes that telemetry store rather than authoritative guard configuration. It is not exposed by an API or used for enforcement. Future Wave 1C must remove/replace that field before presenting the summary as shared quota state; `/provider-status.controls` already derives guard mode. No human Admin workflow was added.

Reviewer declined hosted credentials/schema exposure, proxy topology, throughput/failover, invoices and independently rerunning this session's validations: these remain owner/production acceptance work. They are not inferred from local tests.

### Acceptance commands and evidence (2026-10-15)

These counts overlap; they are not additive unique-test totals. No provider traffic was used. Temporary evidence is retained under ignored `.local/` for local review.

| Check | Result |
| --- | --- |
| Focused durable usage/HTTP/SQL/privacy suites | 76 passed, including real PostgreSQL races, quota restart/shared-instance behavior, role probes, index plans and retention |
| Last physical-provider dimension/cache/guard subset | 43 passed, including two final provider-override validation cases |
| Existing anti-abuse, bounded load, provider observability/cache/Google/satellite/terrain/API-cost/metrics | 183 passed |
| Wave 1A auth, account suspension/workspace authority, migration registry/stage gate | 96 passed |
| Existing disposable PostgreSQL account/RLS and migration clean/upgrade/repeat rehearsal | 25 passed |
| All 17 production-runner migrations on disposable PostgreSQL 17.11 | PASS, transaction rolled back; 22 registry entries, next 022 |
| Full final Python run with disposable usage PostgreSQL enabled | **3828 passed, 33 skipped, 0 failures**, one existing Starlette/httpx deprecation warning, 283.90 seconds |
| Frontend consumer authentication/race tests | 25 passed |
| Frontend typecheck / production build | PASS / PASS |
| ESLint | PASS: 0 errors, 23 pre-existing warnings; frontend source unchanged |
| Production route asset measurement | PASS; two samples at 390px and 1440px, all API/provider traffic blocked |
| Unchanged per-route/global bundle budgets | PASS; total static 3,250,629 bytes; largest JS chunk 602,354 bytes |
| Security/performance gate | PASS after refreshing the new build's route attribution evidence |
| Release quality contract gate | PASS with --skip-tests --skip-frontend-build, paired with the standalone full tests/build above |
| Production operations gate | PASS; external guardrails BLOCKED, production decision NO_GO |
| Bounded local ASGI load smoke | PASS, 720 requests at concurrency 1/5/10/20, no unexpected failures; streamed body saturation/recovery passes |
| Repository hygiene, compile checks, staged diff whitespace | PASS |

Commands: `python -m pytest -q --disable-warnings`; `python -m pytest tests/test_usage_guard_postgres.py tests/test_api_usage_ledger.py tests/test_api_usage_quota.py tests/test_usage_durable_guard.py -q`; `python scripts/validate_postgres_migration.py --database-url <explicit-loopback-disposable-url>`; `npm --prefix frontend_next run test:consumer-auth`; `npm --prefix frontend_next run typecheck`; `npm --prefix frontend_next run lint`; `npm --prefix frontend_next run build`; `python scripts/analyze_next_bundle.py --measure-browser`; `python scripts/check_route_budgets.py`; `python scripts/security_performance_release_gate.py --json`; `python scripts/production_ops_gate.py`; `python scripts/release_quality_gate.py --skip-tests --skip-frontend-build`; `python scripts/check_repository_hygiene.py`; `python scripts/run_bounded_load.py --loops 5`.

Real usage SQL tests require both `API_USAGE_TEST_POSTGRES_URL` (loopback, database name beginning `api_usage_test`) and `API_USAGE_TEST_DISPOSABLE=1`; VNext tests require their existing `VNEXT_RLS_POSTGRES_URL`/`VNEXT_RLS_POSTGRES_DISPOSABLE=1` contract. Normal pytest removes application database URLs before collection. No production credentials or database were used.

Earlier failures were classified and fixed: initial migration checksum/terminal-sequence assertions after rebasing; three production fixture tests now isolate their existing provider/readiness contract from the separately tested new guard; migration rehearsal resets its new private schema; a ledger reader assertion selects its own fixture subject when other HTTP tests have persisted rows. No timeout, rate limit, performance ceiling or historical checksum was weakened. The initial security gate lacked fresh route evidence after rebuilding; explicit provider-blocked measurement resolved it without changing budgets. The initial superseded full run had four failures; both original regression assertions and new boundary tests now pass.

### Changed files

- `backend/api/abuse_middleware.py`
- `backend/api/routes_commute.py`
- `backend/api/routes_metrics.py`
- `backend/api_main.py`
- `config/hosted-environment-manifest.json`
- `conftest.py`
- `database/migration_registry.json`
- `database/migrations/021_api_usage_quota_ledger.sql`
- `docs/operations/anti-abuse-hardening-v1.md`
- `docs/operations/api-cost-optimization-v1.md`
- `docs/operations/api-usage-quota-abuse-v1.md`
- `docs/superpowers/plans/2026-10-13-api-usage-abuse-v1.md`
- `scripts/run_bounded_load.py`
- `services/anti_abuse.py`
- `services/api_usage.py`
- `services/earth_engine_worker_pool.py`
- `services/map_service.py`
- `services/provider_cost_metrics.py`
- `services/tdx_mrt_client.py`
- `services/terrain_risk_providers/ardswc_slope_hazard_provider.py`
- `services/terrain_risk_service.py`
- `services/usage_guard.py`
- `services/usage_ledger.py`
- `services/usage_principal.py`
- `services/usage_quota.py`
- `services/vnext/accounts.py`
- `services/vnext/auth.py`
- `tests/test_api_usage_ledger.py`
- `tests/test_api_usage_quota.py`
- `tests/test_apply_production_migrations.py`
- `tests/test_bounded_load.py`
- `tests/test_commute_route_api.py`
- `tests/test_consumer_account_migration.py`
- `tests/test_production_readiness.py`
- `tests/test_usage_durable_guard.py`
- `tests/test_usage_guard_postgres.py`
- `tests/test_vnext_case_parcel_set_migration.py`
- `tests/test_vnext_identity_confirmation_migration.py`
- `tests/test_vnext_identity_resolution_migration.py`
- `tests/test_vnext_legacy_case_import_migration.py`
- `tests/test_vnext_migration_rehearsal_postgres.py`
- `tests/test_vnext_parcel_evidence.py`
- `tests/test_vnext_parcel_hypothesis.py`
- `tests/test_vnext_property_graph_migration.py`
- `tests/test_vnext_stage1_exit_gate.py`
- `tests/test_vnext_workspace_case_migration.py`

Final full-suite command enabled the explicit loopback disposable usage database and backend test HMAC key in that child shell only. All new usage PostgreSQL tests executed rather than skipping. The 33 remaining skips belong to optional external/environment-gated suites; existing VNext account/RLS tests also ran separately against their confirmed disposable database (25 passed). A final repeat of all four Wave 1B modules passed 76 tests. No source, timeout, quota or budget changed after this full acceptance run.

Completion contract: exactly one local feature commit based on the authoritative starting main; worktree retained on the requested branch. No push, PR, merge, deployment or production migration was performed. The final chat acceptance report provides the resulting immutable commit SHA and verified clean/ahead topology.
