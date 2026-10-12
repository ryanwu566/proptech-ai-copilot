# Hosted Case and Market Wave 0A: Market evidence

Starting revision: `c9ab5f61a45f7f704326af66cb0bea02740b9927`.

The current authoritative integrated revision is
`8b1367a9117e2c8c762f0bad599bba94e9eca771`.
The preserved live observations and prior local acceptance below were made
against `ef1c49c55a58eb0ab63beefe0cd2ddc1f2f9717b`; they remain
checkout-scoped. Fresh integrated local acquisition is recorded separately
below. No new production request or production repair is claimed for 8b.

## Failure classification and boundary

The UTF-8 attached request names the original Taipei/Daan Dunhua South Road
Section 2 reference. The starting local process has neither
`VALUATION_DATABASE_URL` nor `COMPACT_GREEN_DATABASE_URL`. Both the original
reference and the separately specified Zhongxiao East Road Section 4 reference
return `unavailable / provider_unavailable`, null price, null confidence, and no
comparables. This local failure is **CONFIGURATION**. It is not evidence that
either Taipei road genuinely lacks official transactions.

The deployed Work failure is **UNKNOWN**: no captured deployed request,
response, backend identity, or deployed database/configuration state was
available for this investigation. Cloud settings were not changed. The
dedicated local dry-run connection timed out; the separately available remote
GREEN connection raised `OperationalError`. The latter hostname resolved and
its TCP port was reachable, but PostgreSQL session establishment failed.
These observations do not establish the deployed environment's failure class.

A separate **BACKEND_CONTRACT** defect is proven: `estimate_property` emits
`comparable_decision_trace`, but `/valuation/estimate` discarded it in
`_safe_estimate_response`. A regression exercising the real selection engine
through HTTP failed because the trace was absent. Adding that one existing
field to the response allowlist makes the bounded explanation available to
browser acquisition, persistence, Compare, and Report. Selection, weighting,
confidence, and numeric valuation code are unchanged.

## Request and data path

The workspace explicit refresh constructs a request from the confirmed saved
identity, city/district, accepted road, finite positive area, building type,
age, floor, and coordinates. It calls `POST /valuation/estimate`. The backend
validates the request and selects the PostgreSQL provider only when
`VALUATION_DATABASE_URL` is configured and its legacy table is readable.
Demo data require explicit demo mode; no demo fallback was enabled here.

BLUE selects at most 200 finite-positive official PLVR rows in the requested
district and the current month plus 35 previous months, ranking same-road
rows before other district roads. The service chooses the supported scope,
scores comparables, applies its existing IQR behavior, and selects at most
10. Trace exclusions cover only rows delivered by SQL. SQL exclusions and
rows outside the limit are unknown, not invented counts.

GREEN is explicit (`PLVR_DATA_BACKEND=green`) and uses
`COMPACT_GREEN_DATABASE_URL`, frozen generation key 1, and the geography
dictionary. BLUE still supplies coverage/status and other capabilities.
GREEN query errors must remain unavailable; a silent BLUE fallback is not
valid. No BLUE/GREEN setting or generation pointer was changed.

## Official local acquisition proof

The proof uses an isolated disposable PostgreSQL 17 database bound to loopback
port 55467. Source data are the prior read-only production snapshot and
reconciliation artifacts in the sibling main checkout's ignored
`data/processed/plvr/phase2c5` directory. Only rows already classified
`PROD_AUTHORITATIVE_MATCH` at evidence tier A or B, with matching geography,
no source conflict, and no forensic exclusion are eligible. Every imported
row's production fact hash is checked against its snapshot record. Every
referenced official sale-main ZIP is SHA256 checked against its verified
official acquisition manifest. No transaction is fabricated.

The supported geography is Taichung City, Fengyuan District, Nanyang Road.
The public reference is Nanyang Elementary School's published address,
Nanyang Road 440, as documented by the
[Taichung Education Bureau](https://www.tc.edu.tw/page/d61c396e-63a3-4286-ac38-9874ac4092fe/school-content?id=414).
This is a public geography anchor. The residential query's 30 ping, age 15,
floor 8 inputs are explicit hypothetical test inputs, not school property
attributes or an appraisal of the school. No transaction coordinates exist
in this snapshot, so actual distance is unknown and no distance estimate is
invented. Building area is the imported PLVR area in ping; authoritative
parking separation is unavailable and remains unknown/context only.

The import is bounded to one district and periods 2023-11 through 2026-05.
It establishes an official production-style local acquisition through the
unchanged PostgreSQL provider and HTTP endpoint. It does not establish a
live deployment success, whole-country coverage, current source freshness,
or a GREEN cutover.

Verified outcome: 1,631 authoritative production rows imported; 10 referenced
official artifacts independently checksum-verified. The explicit residential
same-road query delivered 200 candidates, selected 10, and excluded 190:
99 scope exclusions, 84 ranking-limit exclusions, and 7 existing IQR price
outliers. Five excluded examples are retained. Selected sample period:
2024-02 through 2026-02; trace reference: 2026-10; service window: 2023-11
through 2026-10. Deterministic result: 909.0 ten-thousand NTD total,
30.3 ten-thousand NTD/ping, range 877.3–956.0, confidence 85. HTTP and service
results agree, including selected rows and their decision trace.

A valid Taichung/Xitun request outside this demonstration's imported district
returns `no_data / official_comparables_insufficient`, null price and
confidence, and zero selected comparables. That result concerns the bounded
local demonstration dataset; it makes no claim about Xitun's official
transactions or nationwide support.

Ignored local proof command: `python .local/verify_market_official.py`.
Sanitized decision artifact:
`artifacts/hosted-case-market-closure/official-acquisition.json`.
The same sanitized evidence is retained at
`docs/operations/hosted-market-official-acquisition-v1.json`.
Raw transaction addresses stay in ignored local source and database files;
the decision artifact contains no complete transaction addresses.

## Regression evidence

Eight fixed-time valuation fixtures were captured before the response change
and after it. They are byte-identical. Canonical JSON SHA256:
`447f93d2d4ddb3c04cf8ccea18e0387295bb7a335baf2e1a03678c967455acf4`.
The baseline also matches the checked-in
`tests/fixtures/comparable-valuation-baseline.json` fixture.

Focused command:

```powershell
python -m pytest tests/test_valuation_api.py tests/test_comparable_explanation.py tests/test_provider_closure_market_valuation.py tests/test_postgres_valuation_provider.py tests/test_valuation_service.py -q
```

Result: **57 passed**, one existing Starlette/httpx deprecation warning.
The first run of the new HTTP explanation regression failed at the missing
trace assertion; it passed after the response allowlist correction.

Provider acquisition is explicit. Explanation expansion uses the captured
trace and needs no new provider request. The existing ten serialized trace dimensions,
context-vs-selection distinctions, frozen references, unknown parking, and
bounded excluded examples are unchanged.

## Resumed-release current live observation

The user supplied the exact original input, accepted normalized identity and
coordinates, and the manually selected sectionless road with residential
assumptions (30 ping, age 15, floor 8). Raw diagnostic inputs and responses
remain ignored. The tracked synthetic browser fixture separately includes
the public audit/test identity and coordinates authorized by the user. The historical
October 11 Work audit had no captured Market network request or response;
its underlying failure remains **UNKNOWN / NOT VERIFIED**.

Current read-only identity probes returned HTTP 200 for both
`https://proptech-ai-copilot.vercel.app/release-version` and
`https://proptech-ai-copilot-api.onrender.com/release-version`, reporting the
resumed `ef1c49c…` built commit. Backend identity status is `PASS`, but
`runtime_sha_matches_build` is `false`: the separate runtime SHA claim
disagrees with the built artifact. Health reports ready and available durable
persistence; this is not Market availability evidence or complete release
attestation.

One explicit original-equivalent `/valuation/estimate` request returned
HTTP 200, `unavailable / provider_query_failed`, non-actionable, with zero
comparables and null price/confidence. Its active valuation query was
`compact_green`, backend `green`, district-pool query status `failed`.
The separate BLUE status remained readable: 451,672 official rows, mixed
composition, freshness `aging / import_aging`. The observed public state is
GREEN query failure, rather than a successful empty comparable sample. This
is a response classification, not an underlying root cause. Production root
cause remains **ROOT_CAUSE_NOT_PROVEN**: no private exception class, SQLSTATE,
schema error or permission error is available. Connection, configuration,
schema, permission, provider and SQL causes must not be inferred from this
public status. No cloud setting, data pointer or remote database was changed,
and this deployed failure is not repaired.

One explicit Location request and one explicit terrain request also returned
HTTP 200. Location quality was `good`, with village resolution, demographics,
geocoding acceptance, and risk-facility objects present. Terrain quality was
`limited`: landslide/debris-flow limited; flood, geological sensitivity,
liquefaction and active fault unavailable. Their actual private responses
are retained in `.local/live-original-provider-capture` for local browser
replay, preserving timestamps and unknown/limited states. Exact audited
finance inputs were not supplied; finance replay must be labeled synthetic.

Sanitized current evidence:
`docs/operations/hosted-market-current-live-v1.json`. These requests attest
current resumed-release behavior, not the historical unrecorded audit.

An additional explicit current-live normalized-section-2 reference request
also returned HTTP 200 with `unavailable / provider_query_failed`, zero usable
comparables, and GREEN query status `failed`. A first bounded release probe
timed out without making a valuation call; its one retry returned the exact
`ef1c49c…` build and the same runtime/build mismatch before the single POST.
No additional Location or terrain acquisition occurred. This reference
capture is separate from the historical sectionless request and is paired
with the matching local official GREEN response for authentic UI replay.
Original raw captures remain untouched; private responses and sanitized
probe observations are retained in the ignored capture directory.

## Original-geography official GREEN production-style success

The original geography now has a separate successful local GREEN proof,
in addition to the earlier supported BLUE geography. The isolated local
PostgreSQL database applies the actual migration 011 schema and contains
all 5,341 genuine Taipei/Daan rows from the frozen authoritative source,
under a 6,000-row bound. Sixteen referenced official ZIPs are independently
SHA256 verified, and each row's artifact hash agrees with that manifest.
Only local surrogate dictionary/transaction IDs are allocated; transaction
facts are not invented. This bounded slice does not assert completeness of
the entire deployed generation.

The actual lazy pooled GREEN adapter, frozen SQL, unchanged selection engine,
and HTTP route all run against this slice. The exact sectionless road request
with the supplied normalized identity/coordinates succeeds at district scope:
200 candidates, 10 selected, 190 excluded (7 IQR price outliers and 183 ranking
limit exclusions), five bounded excluded examples. Selected sample period is
2024-02 through 2026-03. Result: 3,255.0 ten-thousand NTD total, 108.5
ten-thousand NTD/ping, range 2,526.8–4,192.3, confidence 60.

The normalized section-2 reference independently succeeds at road scope:
200 candidates, 10 selected, 190 excluded (53 scope, 3 price-outlier and
134 ranking-limit exclusions). Selected sample period is 2023-11 through
2025-12. Result: 3,396.0 ten-thousand NTD total, 113.2 ten-thousand NTD/ping,
range 3,112.9–3,550.4, confidence 85. Both traces preserve reference month
2026-10 and window start 2023-11. Source coordinates and authoritative parking
separation are absent: actual distance and parking remain unknown, without
invented distance, parking deductions, or parking filters. Floor is context;
area/type ranking and age/distance weighting follow the unchanged engine.

HTTP and service results agree, including selected rows and decision traces.
Thus the sectionless road, actual SQL/schema contract, and row mapping work
with approved official source data locally. This does not prove the deployed
GREEN connection/schema state or close its current failed query. Eight fixed
valuation fixtures were rechecked against the resumed revision and remain
byte-identical with the same SHA256 stated above. The engine files have no
diff between the initial and resumed base revisions.

Local proof command: `python .local/verify_green_original.py`.
Sanitized selected/excluded traces and all dimensions:
`docs/operations/hosted-market-original-green-acquisition-v1.json`.
The current deployed Market failure remains an unresolved P0 acceptance
limitation; local official success must not be described as cloud repair.

## Accepted-road frontend contract reproduction

Replaying the unchanged current Location response through actual UI with the
supplied manual geography reproduced a separate frontend handoff defect.
Village resolution was unavailable, but accepted-address parsing included the
village text prefix in the valuation road and replaced the manual query scope.
The actual valuation POST failed a strict road-scope comparison; the captured
valuation response was never substituted for that mismatched request.
Browser RED evidence is retained in `browser-baseline-unresolved-village-road`.

The accepted-current identity handoff now preserves the matching explicitly
selected road across bounded village-style address enrichment. Its village
and village code remain null; accepted coordinates and source provenance are
unchanged. Different-road hints and ordinary street prefixes are guarded by
tests. Real journey-transition regression failed before the change and passed
afterward; independent review found no Critical or Important issue.

Four fresh authentic response replays passed in Chromium and installed Chrome
using the exact original sectionless manual-road LIVE/local GREEN bodies.
Request scope and property assumptions are asserted before replay. Save,
reload and reopen diagnostics are ready with one valid case; LIVE unavailable
and local ten-comparable evidence remain truthful, and limited terrain is not
promoted to attachable evidence. The four actual A4 PDFs contain 67 nonblank,
unclipped pages; all eight frozen-operation request windows have zero calls.
Finance remains explicitly synthetic because exact historical finance inputs
were not supplied. This frontend code defect is proven; neither the original
production failure nor the underlying current GREEN exception is proven.

## Integrated 8b local acquisition revalidation

Fresh acquisition on the authoritative 8b baseline used the isolated
requirements-dev environment and the same disposable loopback PostgreSQL.
The existing 5,341 genuine GREEN and 1,631 reconciled authoritative BLUE
transactions were verified before execution. No transaction facts were
changed or added; the complete fact database hash was identical afterwards.
The owned database was stopped after verification.

The original sectionless GREEN request again returned HTTP 200 available:
200 candidates, ten selected, 190 excluded, total 3,255.0 wan and 108.5
wan/ping. The section-2 reference again returned ten comparables and total
3,396.0 wan. Supported BLUE again selected ten comparables and total 909.0
wan. The unsupported geography returned `no_data /
official_comparables_insufficient`, `result_origin: official`, no actionable
valuation, zero comparables, and null price/confidence metrics. Provider
metadata remains truthful. All four complete result entries, traces,
selection, numeric values and official lineage exactly match the preserved
ef1 proof. This is fresh local SQL/service/HTTP evidence, not a cloud repair.

All eight freshly generated valuation fixtures match both their values and
original raw bytes; SHA256 is
`447f93d2d4ddb3c04cf8ccea18e0387295bb7a335baf2e1a03678c967455acf4`.
The engine, GREEN query, comparable-trace and frontend explanation source
contracts are unchanged. The trace has ten serialized dimensions:
location, building_type, area, age, distance, recency, unit_price, floor,
parking and community_distance. A transparent logical 13-criterion mapping
splits location into city/district/road and includes the existing
official-source eligibility rule. This interpretation preserves existing
rules; it does not invent a canonical 13-key schema.

Proofs are retained at
`artifacts/hosted-case-market-closure/integrated-8b/market/summary.json`,
`contract-preservation.json`, `official-acquisition.json` and
`bounded-green-original.json`. Earlier proof files were copied and hash
verified before rerunning. Harness-only RED diagnostics for mistaken trace
count, unavailable-result origin and terminal-newline assumptions remain
preserved; correcting those assumptions changed no engine or valuation data.

Historical production Save and Market roots, and the underlying current
production GREEN exception, remain **ROOT_CAUSE_NOT_PROVEN**. Private logs
and original saved storage remain unavailable. Production Market P0 remains
open; this local success does not authorize ML-B or deployment.
