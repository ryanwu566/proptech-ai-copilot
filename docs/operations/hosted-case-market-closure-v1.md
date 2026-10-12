# Wave 0A Hosted Case and Market closure evidence

## Scope and release boundary

Authoritative integrated starting SHA: `8b1367a9117e2c8c762f0bad599bba94e9eca771`.
Branch: `fix/hosted-case-market-closure-v1`.
The original `c9ab5f6…` evidence and all uncommitted work were preserved after
the user authorized the already-rebased worktree. No further rebase, reset,
push, merge, deployment, or cloud configuration change is authorized.

**Integrated local/release-equivalent acceptance: PASS. Production P0 closure: NOT VERIFIED.**
The completed ef1 release-equivalent evidence below is preserved as a prior
checkpoint; it is not final evidence for the new baseline. Before its single
commit, remote main moved to PR #180 and execution stopped without staging or
committing. The user authorized the safely rebased 8b worktree and requires
fresh integrated verification, including ML-0 tests and the dev dependency
contract. No ML-B work is authorized. No further rebase/reset/push/merge/deploy.
The last observed production Market query was unavailable; original production
roots are unproven. No fresh 8b production request or deployment is claimed.

## Saved-case investigation and repair

The historical Work audit preserved a generic invalid/duplicate diagnostic,
but no original browser storage. An actual duplicate ID, schema failure, or
serializer failure cannot be inferred from that message. Original production
Save rejection remains **NOT PROVEN**.

Proven repository failures were separately reproduced through the real
serializer/read contract: writes could delete quarantined records, silently
evict an older valid case when the ten-case list was full, return success
after an invalid serialized candidate, and propagate quota failures without
truthful UI feedback. Writes now validate their exact serialized candidate,
retain quarantined original records, refuse a full list, and publish success
only after a verified write. Existing schemas, stable IDs, unknown evidence,
and manual review provenance remain intact. Unsupported or partially written
storage is not replaced with an empty successful list.

Independent review reproduced a cross-tab read/write race after the optimistic
raw-value check. All repository mutations now acquire the same origin-wide
exclusive Web Lock before reading and writing. Unsupported or denied locks
fail closed. This coordinates updated cooperating tabs; already-open older
application code cannot honor the new lock and should be reloaded.

Journey metadata retains absent age/floor facts. Explicit valuation refresh
now reads their knownness from that metadata instead of treating legacy
numeric compatibility defaults as known zero. Explicit user-entered zero is
still valid; legacy records without journey metadata retain their existing
numeric contract. This changes request eligibility, not valuation arithmetic.

Two UI failures were reproduced during independent async-boundary review:
failed Market persistence retained a permanent loading state, and edits made
while a checklist save waited could be cleared by the older save result.
Market now leaves loading on write failure. Checklist disables edits while
the write is pending and retains the draft on failure. Actual Chromium
regressions passed individually and in the final complete browser run.

The resumed actual-UI journey also reproduced a separate evidence-loss bug:
the embedded valuation form submitted age/floor assumptions to valuation but
did not publish those facts to journey state. Save therefore retained absent
metadata and numeric compatibility zero instead of the submitted 15/8 facts.
This is a proven current-code defect, not proof of the historical production
storage-repair diagnostic. The embedded form now publishes only explicitly
edited fields or the complete submitted payload to journey state. Parent
echoes preserve the current result, actual edits cancel stale responses and
invalidate dependent evidence, and unchanged geographic selections retain
accepted coordinates. Blank/invalid numeric drafts remain unknown and block
submission; deliberate zero remains known. Mounting the form never promotes
display defaults into saved facts. The repair leaves schemas and valuation
arithmetic unchanged. At the preserved ef1 checkpoint, independent review
and actual-UI acceptance passed. Fresh 8b review and acceptance are recorded
separately below.

Authentic current-response replay separately reproduced an accepted-address
handoff defect: with village resolution unavailable, the normalized address's
village prefix became part of the valuation road, overriding the explicitly
selected manual road. An actual browser request and a real journey transition
both failed before the repair. The handoff now retains a matching explicit
manual road scope across bounded village-style address enrichment. It does
not resolve the village, invent administrative identity, or alter valuation
arithmetic. Different-road hints and genuine street-name prefixes remain
protected. This frontend defect does not prove the deployed GREEN exception.

Final review also corrected immersive Save feedback: genuinely missing fields
are identified separately from storage failures in all four locales. Its
existing blank-title behavior remains unchanged. Real writer fault tests cover
the failure helper; no immersive browser storage-failure reproduction is
claimed where that blank title already blocks saving.

## Market investigation

See [Market evidence](hosted-case-market-closure-market-v1.md),
[current live observation](hosted-market-current-live-v1.json), and
[official GREEN acquisition](hosted-market-original-green-acquisition-v1.json).

Production Market root cause remains **ROOT_CAUSE_NOT_PROVEN**. The historical
Market failure remains **UNKNOWN** because the original audit
did not preserve its HTTP status or reason code. Preserved ef1 production
testing observed HTTP 200 with `unavailable / provider_query_failed` on
GREEN. The deployed connection/schema/permission cause is not exposed by the
bounded public response. Backend built SHA matches the resumed base, but its
runtime SHA claim does not match the build. No cloud repair is claimed.

The exact original logical request succeeds through actual local GREEN SQL,
the migration-011 schema, pooled PostgreSQL adapter, unchanged service, and
HTTP endpoint using 5,341 genuine district transactions with verified official
artifact lineage. Two hundred candidates produce ten selected comparables
and bounded excluded reasons. The additional approved BLUE geography also
succeeds. These are production-style acquisitions, not browser mock evidence.

The HTTP allowlist now retains the existing bounded comparable decision trace.
Its ten serialized dimensions, context/selection distinctions, unknown parking/distance,
and frozen time semantics are unchanged. The requested 13-criterion view can
be mapped to existing rules by splitting location into city/district/road and
including official-source eligibility; that is a documented interpretation,
not a claim that the existing schema has 13 dimension keys. All eight deterministic valuation
fixtures remain byte-identical, SHA256
`447f93d2d4ddb3c04cf8ccea18e0387295bb7a335baf2e1a03678c967455acf4`.

## Preserved ef1 acceptance evidence

This entire section records prior ef1 results, including prior review claims.
The fresh integrated review found and repaired an additional same-case stale
write described in the integrated section below. Counts here are not final
8b evidence.

- Fresh focused persistence/contract tests: 36 passed after Web Lock repair
  and queued-write cancellation guards.
- Knownness and Market-refresh deterministic tests: 11 passed.
- Before the last road/feedback repairs, the frontend deterministic suite:
  309 passed, zero
  failures, zero skips. The complete suite was rerun after the final print
  CSS repair: 309 passed in 31.04 seconds. Final output:
  `artifacts/hosted-case-market-closure/frontend-final-all-fixes-full.log`.
- After the final road handoff and Save-feedback repairs, the complete
  frontend deterministic suite passed again: 331 passed, zero failed,
  zero skipped, 40.67 seconds. Output: `frontend-final-complete.log`.
- Final-source typecheck passed without diagnostics. Focused persistence,
  knownness and valuation-input tests: 48 passed. Production E2E rebuild and
  actual browser acceptance subsequently passed on the final source. Final
  standalone `npm run typecheck -- --incremental false` and full `npm run lint`
  both exited zero; outputs are `typecheck-final-complete.log` and
  `lint-final-complete.log`.
- First resumed full Python run: 3,608 passed, eight failed, 32 existing
  conditional skips. All eight failed cases passed unchanged in fresh quiet
  processes (three worker lifecycle tests and five satellite adapter tests).
  A second unchanged complete suite passed: 3,616 passed, zero failed, 32
  existing conditional skips, one existing Starlette warning, 344.39 seconds.
  Command: `PYTHONUTF8=1 python -m pytest -q --basetemp
  artifacts/hosted-case-market-closure/pytest-final-full`; output is preserved
  in `artifacts/hosted-case-market-closure/python-final-full.log`.
- Actual final-source two-case smoke passed Create/Save/Reload/Reopen,
  isolation, checklist, comparable expansion and Compare, including the
  exact submitted age/floor facts. Actual PDF A has 16 nonblank, unclipped
  pages. PDF B exposed a real blank seventeenth trailing page, confirmed by
  zero extracted characters and visual inspection. RED PDFs and screenshots
  are preserved in `browser-baseline-blank-report-page`; print layout repair
  removed only trailing report/last-section margin and padding. A same-data
  browser causal diagnostic produced 16 pages for each case with no blank or
  clipped pages and unchanged content/provider assertions. The diagnostic
  injection was removed; native production CSS was independently reviewed.
  Native production CSS then passed a fresh build and the complete matrix.
- Final complete browser run: **48 passed**, zero failed, zero skipped, zero
  flaky tests, CLI retries zero, 17.6 minutes. Chromium and installed Chrome
  each passed 16 two-case locale/width journeys, six numeric/write-failure
  regressions and two authentic captured-response replays. Widths:
  390/430/1024/1440; locales: zh-TW/en/ja/ko. Existing report prose is Chinese;
  functional locale validation does not imply fully translated reports.
  Output and report: `browser-final48-clean/run.log` and its HTML report.
- Final actual PDF audit: **68 PDFs, 1,123 pages**, all A4 within the observed
  sub-point Chromium rounding, zero blank pages, zero clipped text blocks,
  required finance/manual/risk/checklist content present and print actions
  absent. First/last page images are retained; parent and browser reviewer
  inspected actual PDF raster output. Final audit:
  `browser-final48-clean/evidence-audit.json`.
- All **232 frozen-operation request windows recorded zero calls**, including
  Save/reload/reopen/Compare/Report/checklist/comparable expansion. Explicit
  acquisitions and form metadata reads are counted separately. Counters cover
  both GET/POST provider routes and external map/transport provider domains.
- Four authentic captured-response lanes passed in Chromium and installed
  Chrome: the original sectionless manual-road LIVE unavailable response and
  the matching genuine local GREEN successful response. The actual UI enters
  the supplied manual geography before Location analysis; this is a logical
  replay, not an assertion about the undocumented historical UI sequence.
  Both preserve the exact response, coordinates/provenance, unknown risk,
  manual price and synthetic finance assumptions through Save/reload/reopen
  and actual A4 PDF. All read diagnostics remain ready with one valid case.
  The original generic storage-repair condition is not reproduced after the
  current fix in this bounded release-equivalent flow. Original browser
  storage and exact historical finance inputs remain unavailable, so its
  historical root cause remains NOT PROVEN. Focused output:
  `browser-final-capture-green/run.log`, four passed, zero skipped/retried.
- Production npm audit: zero vulnerabilities.
  The full audit policy gate also passed using its existing dev-only
  `GHSA-vfj7-8cjw-p6xm` exception, expiring 2026-11-04. No new exception or
  dependency change was introduced; production dependencies are clean.
- Full frontend lint: exit zero, zero errors, 23 existing warnings.
- Standard final production build passed. Its bundle has 2,983,438 static
  bytes, 2,831,670 JavaScript bytes, largest JavaScript chunk 602,354 bytes.
  Bundle and all six route budgets passed; homepage limit is 3,000,000 bytes.
- The complete unmodified release quality gate subsequently reported
  `python_tests_failed`, while the standard production build and every source
  contract passed. Its discarded child output cannot establish the cause.
  The failure is retained in `release-quality-final.json` and its log. A fresh
  diagnostic run executes the same unchanged gate/commands/900s limits and
  retains subprocess stdout/stderr through an ignored external observer;
  no assertions, skips, environment, exit values or gate source are changed.
  That diagnostic run established one failure: the valuation-share static
  test still located the old typed `const shareInputs:` declaration after
  production moved to a validated helper and inferred declaration. Updating
  only the locator to `const shareInputs=` retained every original no-auto
  and explicit-estimate assertion, including injected-call rejection.
  Independent review cleared the adaptation; all seven focused tests passed.
  The diagnostic RED contains 3,615 passed, one failed, 32 existing skips,
  267.02 seconds; stdout/stderr/execution and gate outputs are retained with
  `.red` suffixes. The complete corrected gate rerun then exited zero:
  **3,616 Python tests passed, 32 existing conditional skips, one existing
  warning, 246.03 seconds**. Standard `npm --prefix frontend_next run build`
  exited zero, and every release source contract passed. No tests or build
  were skipped. Final gate: `release-quality-observed-final.json`; exact
  child commands, unchanged 900s limits and actual exit codes are preserved
  in `release-observed-{python,build}.execution.json`, with stdout/stderr.
- Security/performance contract and operations repository checks passed.
  Operations external guardrails remain `BLOCKED`, production decision `NO_GO`.
- Final standard-build bundle/route/security/operations outputs are
  `bundle-final-standard.json`, `routes-final-standard.json`,
  `security-performance-final-standard.json` and `operations-final-standard.json`.
- Repository hygiene passed across 1,425 tracked/nonignored files with zero
  high-confidence findings. `git diff --check` passed; a final staged hygiene
  and whitespace check is required immediately before the single commit.

Raw provider responses, browser storage diagnostics, network counters,
screenshots, PDFs, transaction source data, and local database files are kept
in ignored local artifacts. The tracked browser fixture includes the public
audit/test address and coordinates supplied by the user; its synthetic
responses are explicitly labeled and are not official acquisition evidence.
Tracked operational evidence is bounded and sanitized. No original user
storage was deleted or inspected remotely.

## Preserved ef1 28-item checkpoint (no commit was created)

| # | Item | Evidence or remaining requirement |
|---|---|---|
| 1 | Starting SHA | `ef1c49c55a58eb0ab63beefe0cd2ddc1f2f9717b`; original baseline evidence preserved. |
| 2 | Final SHA | No ef1 Wave commit was created: remote main moved before staging/commit. The single final integrated 8b commit is reported separately in the final delivery. |
| 3 | Save/Reopen root cause | Historical generic repair diagnostic is NOT PROVEN. Separately reproduced serializer/write, quarantine retention, capacity eviction, cross-tab race and embedded input-handoff defects are documented above. |
| 4 | Persistence fix | Validate the exact serialized read contract; preserve quarantined originals; fail truthfully on unavailable/quota/capacity; coordinate every mutation with an origin-wide lock; reject stale queued evidence. |
| 5 | Corrupted/legacy recovery | Valid unrelated cases remain usable; malformed/unsupported/duplicate records are retained for explicit repair. Parse corruption blocks writes. Legacy identity-free cases stay unverified, without replacement IDs or schema downgrade. |
| 6 | Case A | Audited public Taipei/Daan test identity, synthetic manual price 2,480 wan, 30 ping/15 years/floor 8, loan 20% down/2.2%/30 years, payment 75,412 NTD; risk count unknown, manual checklist reviewed. Passed all 32 locale/width/browser journeys. |
| 7 | Case B | Distinct synthetic Xinyi identity, manual price 3,650 wan, 42 ping/9 years/floor 12, loan 35% down/2.6%/25 years, payment 107,624 NTD; risk no-match known zero, pending manual review, unsupported Market. Passed all 32 journeys. |
| 8 | Reload/Reopen | Both cases reopen with stable IDs and exact saved facts after reload and after Report. Four authentic replays also remain ready with one valid case and no repair diagnostic. |
| 9 | Isolation | Distinct IDs, addresses, prices, payments, Market/risk/checklist states remain isolated in all 32 journeys. |
| 10 | Compare | Both saved prices/payments render with manual provenance; mobile domain selection and desktop comparison both pass. |
| 11 | Report | Frozen saved evidence, source timestamps, unknown/manual limits, finance, review states and comparable explanation render without refetching. |
| 12 | PDF | Native print fix passed 68 actual A4 PDFs/1,123 pages: zero blank/clipped pages and no print action buttons. Raw PDFs and inspected images are retained locally. |
| 13 | Market root cause | `ROOT_CAUSE_NOT_PROVEN` for historical and current production underlying cause. Current public response is HTTP 200 unavailable/provider_query_failed; it is not an exception or SQLSTATE. |
| 14 | Supported Market | Approved genuine local BLUE and exact-original GREEN SQL/HTTP acquisitions each selected ten comparables; official artifact hashes and bounded traces preserved. Local success does not attest deployed repair. |
| 15 | Unsupported Market | Local approved unsupported geography returns truthful no_data with null prices/confidence; browser synthetic public-contract no_data fixture is explicitly labeled and separate. |
| 16 | Comparable explanation | HTTP retains the existing ten-dimension bounded trace; scope/weight/context and unknown parking/distance semantics unchanged. The integrated investigation corrects the earlier 13-dimension wording above. All browser expansion checks passed without provider calls; genuine ten-row trace survives captured Save/reopen/report. |
| 17 | Valuation before/after | Eight fixtures byte-identical; SHA256 `447f93d2d4ddb3c04cf8ccea18e0387295bb7a335baf2e1a03678c967455acf4`; engine files unchanged. |
| 18 | Provider calls | All 232 frozen-operation windows recorded zero calls. Explicit acquisition and form metadata calls are counted separately. |
| 19 | Locales | zh-TW/en/ja/ko functional acceptance passed in both browsers/all widths. Existing Chinese report prose remains a localization limit. |
| 20 | Responsive | 390/430/1024/1440 all passed in both browsers/all locales, including mobile comparison and horizontal-overflow checks. |
| 21 | Full Python | Final complete release-gate subprocess: 3,616 passed, zero failed, 32 existing conditional skips, one existing warning, 246.03 seconds, exit zero. Earlier failures and their diagnostics remain preserved. |
| 22 | Frontend tests | Complete final-source suite after road/feedback repairs: 331 passed, zero failed, zero skipped. Focused persistence/knownness/input tests: 48 passed; feedback/storage faults: 47 passed. |
| 23 | Browser tests | Final complete run: 48 passed in 17.6 minutes, zero failures/skips/flaky/retries. Prior failures are retained. Assertions remain intact; bounded 90s orchestration budgets have recorded default-timeout proof, with launch/assertion budgets unchanged. |
| 24 | Bundle size | Standard production build passed; total 2,983,438 bytes/largest JS 602,354 bytes. Bundle and all route budgets passed. |
| 25 | Independent review | Final independent source/evidence review and one-line share-test adaptation cleared the requested data-loss/ID/schema/unknown/provider/drift/stale/isolation/provenance risks: no remaining Critical/Important issues. Full browser and release gates passed. |
| 26 | Limitations | No original storage or private production exception; current deployed GREEN remains unavailable and runtime/build SHA claims disagree. External operations guardrails BLOCKED/NO_GO; no cloud changes. |
| 27 | Safe for PR? | Yes, for the verified local contract repairs and documented evidence. All required local test/build/audit/budget/release/security/operations repository checks passed; final staged hygiene/whitespace and unchanged-base checks precede the single commit. Production decision remains NO_GO. |
| 28 | Both P0 closed? | Hosted Case: closed for the current branch's tested scope; the original diagnostic is not reproduced after the fix in bounded authentic replays, but its historical cause is NOT PROVEN. Market: local official acquisition/trace acceptance passed, production P0 remains open. Original production roots were not proven; this does not claim both deployed P0s are closed. |


## Integrated 8b acceptance and independent review

PR #180 adds ML-0 research and changes the development dependency contract;
it changes no frontend product tree or valuation engine. Existing Wave 0A
implementation and every prior artifact were preserved. A dedicated local
venv satisfies requirements-dev (Python 3.13.14, pytest 9.1.1, jsonschema
4.26.0, pyarrow 24.0.0, Starlette 1.3.1); no shared interpreter changes are
required. The fresh pre-review gate checkpoint passed 3,667 Python tests,
including the new ML-0 inventory, with 32 existing conditional skips. It is
preserved separately; final evidence must follow the review repair below.

A fresh independent integrated review found one Important issue: identity
and input-fingerprint guards allowed an older response to overwrite newer
evidence for the same case when identity and inputs had not changed. The
review reproduced this through the real adapter and writer. Thirteen new
storage/context regressions failed before repair; three actual-card hook
regressions also failed because pending commute responses adopted a newer
callback, and route loading cleared persisted evidence before acquisition.

Writers now capture the normalized case content version before acquisition
or waiting for the lock, and compare it with the actual row being mutated
inside the exclusive origin-wide lock. Market, valuation, risk, location and
finance writers reject stale content, including same-timestamp updates.
Snapshot/checklist writes use the same guard. Unrelated case changes remain
allowed. Market input fingerprints remain separate, so successful writes do
not invalidate their own result. Commute callbacks retain the acquisition
context across rerenders, and loading retains the previous persisted route.
The content version is transient: no persisted schema/version, ID, provider
payload, valuation calculation or report field is changed.

The complete focused regression run passed 49/49. The first GREEN run exposed
an incorrect test assumption about the existing two notification events and
a race injection that had moved before the mutation read; the corrected
harness counts the unchanged generic/detail event contract and injects the
race at the actual raw-write guard using the captured version. Failure and
raw-preservation assertions remain intact. The complete frontend suite then
exposed one expected-object contract assertion missing the new transient
version. Adding the exact expected version retained all identity and payload
assertions. RED outputs are preserved; the full suite passed 353/353, no
failures or skips, 29.72 seconds.

The independent reviewer followed up read-only on the repair and found no
remaining Critical or Important issue: all five writers, snapshot/checklist,
unrelated-case handling, acquisition callbacks and transient projection
boundaries were checked. The review explicitly declined to judge still-running
acceptance and historical production roots; those are determined only by
actual final gate outputs and the retained evidence limitations.

Final integrated acceptance outputs are collected under
`artifacts/hosted-case-market-closure/integrated-8b/post-review`.
The new browser matrix adds one actual same-case pending-response regression
per engine, without changing the existing 48 assertions or cases. Complete
integrated browser, print and gate results were pending at that checkpoint;
all final local results below now pass.


Final post-review release quality gate exited zero on the unmodified complete
commands: **3,667 Python tests passed**, 32 existing conditional skips, one
existing Starlette warning, 311.00 seconds. The new ML-0 inventory is included;
the prior 3,616 count is not reused. The standard production build also exited
zero and all eleven release checks passed. The ignored observer retains the
actual child stdout/stderr, unchanged 900-second limits, command and exit
values; it changes no source gate, assertion, skip or result.

Full frontend deterministic acceptance: **353 passed**, zero failures or
skips, 29.72 seconds. Standalone typecheck exited zero; full lint exited zero
with zero errors and 23 existing warnings. Fresh 8b production npm audit:
zero vulnerabilities. Dependency/lockfile changes are absent. Standard-build
budgets passed: 2,984,027 total static bytes, 2,832,259 JavaScript bytes and
602,354 bytes for the largest client chunk. All six route budgets passed,
including the 3,000,000-byte homepage limit. Security/performance checks all
passed. Operations repository checks all passed; external guardrails remain
**BLOCKED**, production decision **NO_GO**. These are repository checks,
not production owner evidence or deployment approval. Repository hygiene
covered 1,442 tracked/nonignored text files with zero high-confidence findings;
final staged hygiene and whitespace checks precede the one local commit.


The first integrated full 50-test browser run preserved 48 passes and two
failures in the newly added test, before any acquisition was clicked. Its
RecordedRequests array has an enumerable zeroWindows bookkeeping property;
comparing that augmented object to [] failed despite zero request entries.
Comparing calls.slice() to [] preserves the exact zero-request assertion.
Only that harness line changed. Complete RED report, errors and all 68 PDFs
(1,123 nonblank/unclipped A4 pages) remain in browser-final50.red. Both
engines then passed the focused actual pending-response regression, 2/2,
with four monitoring windows and zero automatic calls. The final complete
50-test run is required separately, without retries or new skips.

The application, backend, Python and deterministic-test source hashes match
the final full gates exactly; only that new browser assertion changed.
Typecheck and lint were rerun for the corrected harness. The existing E2E
build contract enables PROFESSIONAL_WORKSPACE and uses the controlled
http://e2e.test API origin. Synthetic browser contracts and preserved actual
response replays verify frontend persistence and request boundaries; genuine
Market facts are verified separately through fresh local SQL/service/HTTP.
No browser synthetic fixture is presented as official acquisition or fresh
production behavior.


Final clean integrated browser acceptance: **50 passed in 16.7 minutes**, no
unexpected failures, flaky tests, skips or retries; Chromium and installed
Chrome each pass 25. All 32 two-case locale/width journeys, 14 numeric/write/
concurrency regressions and four authentic response replays pass. Actual
same-case older responses are rejected in both engines while identity,
inputs, revision and timestamps remain identical, newer evidence survives
reload/Report, and the other case remains unchanged. Both browser-owned
runner and Next server stopped after execution.

Final audit confirms **68 newly generated actual A4 PDFs / 1,123 pages**,
zero blank/clipped pages, and **236 monitored frozen-operation windows /
zero automatic provider calls**. All 19 raster SHA256 groups match the prior
visually inspected output; root additionally viewed fresh final Case A/B and
captured-report raster output. Root independently validates all 32 matrix
entries, four replay diagnostics, two stale-write records, final counters,
unchanged application source hashes and the actual PDF binaries. Preserved
capture hashes also match. Final report/results and evidence/visual audits
are under `integrated-8b/browser-final50`; root verification manifests are
under `integrated-8b/post-review`.

Hosted Case is closed for the current branch's tested local/release-equivalent
scope: both cases save/reload/reopen/compare/report with isolated frozen
facts, and the historical generic repair diagnostic is not reproduced in
four bounded authentic post-fix replays. Original storage and exact finance
inputs are unavailable; its historical root and deployed closure remain
NOT VERIFIED. Market local official acquisition and explanation acceptance
pass; production Market P0 remains OPEN. The original and underlying current
production roots remain ROOT_CAUSE_NOT_PROVEN. All required local checks
pass; this is safe for a PR with those limitations, not deployment.

## Final integrated 25-item report

| # | Required item | Final integrated result |
|---|---|---|
| 1 | Starting SHA | `8b1367a9117e2c8c762f0bad599bba94e9eca771`. |
| 2 | Final SHA | Exactly one enclosing local Wave 0A commit; its exact SHA is reported in delivery using `git rev-parse HEAD`. No push, merge or deployment. |
| 3 | Changed-file count | 42 files; 35 implementation/test files and seven bounded evidence/plan documents. |
| 4 | Local Save/Reopen root causes | Proven unsafe serialized-candidate success, quarantine deletion/capacity eviction, cross-tab and same-case stale overwrites, lost embedded age/floor handoff, and accepted-road enrichment. Exact serialized validation, preservation/refusal, exclusive origin lock, captured content versions and explicit input handoff repair those defects. This is not proof of the historical diagnostic. |
| 5 | Original production root-cause status | **ROOT_CAUSE_NOT_PROVEN** for Save and Market; original storage/request trace and private backend exceptions are absent. No original duplicate-ID inference or deployed repair claim. |
| 6 | Case A | PASS in all 32 two-case journeys. Public audit identity with synthetic manual 2,480 wan, 30 ping/15 years/floor 8; loan 20% down/2.2%/30 years, 75,412 NTD/month. Risk unknown, manual checklist reviewed. |
| 7 | Case B | PASS in all 32 two-case journeys. Distinct identity with synthetic manual 3,650 wan, 42 ping/9 years/floor 12; loan 35% down/2.6%/25 years, 107,624 NTD/month. Known no-match risk zero, pending review, unsupported Market. |
| 8 | Compare | PASS. Both cases' prices/payments and manual provenance remain distinct; desktop/mobile domain selection and no overflow. |
| 9 | Report | PASS. Frozen saved evidence/source times/manual limits/unknown risk/income/checklists/comparable explanation; no refetch or cross-case leakage. |
| 10 | A4 PDF | PASS: 68 regenerated actual A4 PDFs / 1,123 pages, zero blank/clipped pages; binary geometry/content audit and fresh raster inspection recorded. |
| 11 | Market acquisition | Fresh genuine local GREEN original request: HTTP 200 available, 200 candidates/ten selected/190 excluded, 3,255 wan/108.5 wan per ping. Section-2 GREEN and supported BLUE also select ten; official lineage and facts verified unchanged. |
| 12 | Unsupported Market | Actual SQL/HTTP returns no_data/official_comparables_insufficient, official origin, no actionable valuation, zero comparables and null price/confidence. Browser synthetic coverage and captured LIVE unavailable stay truthfully bounded. |
| 13 | Comparable Explanation | PASS. Existing ten serialized dimensions, included/excluded counts/examples, context vs selection, unknown distance/parking and frozen references preserved. Logical 13-criterion grouping is explicitly an interpretation, not a new schema. |
| 14 | Valuation regression | All eight fixtures value- and byte-identical: SHA256 `447f93d2d4ddb3c04cf8ccea18e0387295bb7a335baf2e1a03678c967455acf4`; engine/query/trace source unchanged. |
| 15 | Provider-call count | **Zero automatic calls in all 236 windows**. Monitored Save/reload/reopen/Compare/Report/Checklist/Comparable Explanation; explicit acquisitions separate. Covers GET/POST and provider/map/transport domains. |
| 16 | Locale matrix | PASS: zh-TW/en/ja/ko × both browsers × every width. Existing Chinese report prose is a localization limitation; functional locale acceptance does not imply complete translation. |
| 17 | Width matrix | PASS: 390/430/1024/1440 × both browsers × every locale; 32 two-case journeys. |
| 18 | Full Python final count | **3,667 passed**, 32 existing conditional skips, one existing Starlette warning, 311.00s. Complete unmodified release-gate subprocess includes ML-0; no reused 3,616 count. |
| 19 | Frontend count | **353 passed**, zero failures/skips, 29.72s. All application/deterministic-test source hashes unchanged subsequently. |
| 20 | Browser count | **50 passed**, 16.7 minutes, both engines 25/25, workers=1, retries=0, no failures/skips/flaky results; earlier 48-pass/two pre-click harness failures preserved separately. |
| 21 | Build/audit/budget/gates | Typecheck/lint/standard production build pass; lint 23 existing warnings, zero errors. Production npm audit zero vulnerabilities. Bundle 2,984,027 bytes; JS 2,832,259; largest 602,354; all six route budgets pass. Full release/security/performance/operations repository gates pass. External operations **BLOCKED / NO_GO**. Final staged hygiene/whitespace required before commit. |
| 22 | Independent review | Fresh integrated review identified one Important same-case stale-write issue. RED/GREEN repair, cleared independent follow-up and real two-engine UI regression resolve it; no remaining Critical/Important. Reviewed loss/duplicate IDs/schema/isolation/unknown/provider/drift/stale report/provenance/root-cause claims. Historical production roots explicitly declined because evidence is absent. |
| 23 | Hosted Case P0 | Closed for the current branch's bounded tested scope. Original generic diagnostic is not reproduced in four authentic post-fix replays; historical production cause and deployed closure are **NOT VERIFIED**. Quarantined originals remain retained, usable unrelated/legacy cases are not replaced or assigned new IDs, corruption blocks writes. |
| 24 | Market P0 | Local genuine supported acquisition/trace contract passes; **production P0 remains OPEN**. Original and underlying deployed roots remain unproven. No cloud repair or fallback is claimed. |
| 25 | Safe for PR? | Yes, for the verified local repairs and documented limits. All integrated local checks pass; staged hygiene/whitespace and unchanged-base checks precede the enclosing commit; production decision remains NO_GO. No ML-B, push, merge, deployment, reset or further rebase. |

## PR #181 browser regression investigation — 2026-10-12

The original Wave 0A commit `5bdf9438bcbb251ff639aa6ca6b0b81d37ea04ef`
was not merge-ready. Its fresh Production Release Operations browser job
`114492623415` (run `38144472774`) exhausted the existing 35-minute limit
after the three valuation refresh tests repeatedly exhausted their existing
30-second limits in both engines. The earlier 50-test acceptance above did
not cover these legacy saved-case refresh fixtures.

Fresh local production E2E builds reproduced all six failures on that commit
and passed all six on the clean requested base
`8b1367a9117e2c8c762f0bad599bba94e9eca771`. Traces and error snapshots prove
the same stall: Playwright waited to click the disabled
`valuation-refresh-button`. The valuation/trend APIs, storage lock,
saved-case mutation, snapshot-version check, response commit guard, success
feedback and Compare/Report reopen were not reached. The A-to-B test had
started only its deliberately held Market request before its valuation
click stalled. This proves a branch input-contract regression, rather than
a persistence deadlock or workflow-timeout root cause.

`buildValuationRefreshContext` had begun requiring age and floor exclusively
from optional journey metadata whenever a journey existed. Older saved
cases carry valid positive age/floor in `data.inputs` while omitting those
journey fields. The smallest repair accepts a positive existing input only
when its corresponding journey field is undefined. Explicit journey values
retain precedence, including explicit zero and invalid values. A missing
journey field with a legacy zero default remains unknown and blocks refresh;
all existing input validation remains. No migration or saved schema changes
are needed. Web Locks, snapshotVersion semantics, identity/fingerprint guards,
request IDs and evidence persistence are unchanged. No workflow or test
timeouts, valuation arithmetic or fixtures changed. The three originally
reported browser tests remain unchanged; other completion/transition harness
repairs are documented below.

Initial exact local timings with traces enabled (milliseconds; failure
durations include artifact/teardown time after the unchanged 30-second limit):

| Exact test | Original HEAD Chromium / Chrome | Clean base Chromium / Chrome |
|---|---|---|
| `commercial-market-price.spec.ts:284` valuation refresh | TIMEOUT 34,378 / 33,694 | PASS 4,145 / 3,742 |
| `commercial-market-price.spec.ts:354` A-to-B late responses | TIMEOUT 32,164 / 31,982 | PASS 2,536 / 2,766 |
| `comparable-explanation.spec.ts:72` Save/Reopen/Compare/Report | TIMEOUT 35,203 / 34,968 | PASS 11,847 / 12,112 |

Three repetitions without retries passed in each engine on both the base and
the repair. Exact measured durations in milliseconds, in repetition order:

| Exact test | Base Chromium | Repair Chromium | Base Chrome | Repair Chrome |
|---|---|---|---|---|
| Valuation refresh | 2,990 / 1,466 / 4,220 | 2,740 / 2,471 / 2,655 | 3,903 / 3,803 / 2,724 | 4,635 / 4,859 / 5,050 |
| A-to-B late responses | 2,051 / 2,905 / 2,886 | 1,969 / 1,831 / 2,272 | 3,358 / 2,246 / 2,108 | 2,452 / 3,400 / 3,232 |
| Save/Reopen/Compare/Report | 12,109 / 12,629 / 14,873 | 10,616 / 10,165 / 10,872 | 13,774 / 9,808 / 9,753 | 13,330 / 16,013 / 11,953 |

The base and repaired repetition runs overlapped on the local Windows
machine; these measurements establish completion and comparison with the
same local baseline, not equivalence to GitHub's faster PDF/screenshot
runtime. No 30-second pass or timeout increase is used as evidence.

Focused deterministic coverage first failed for the legacy positive-input
case, then passed all five knownness tests after the repair. Coverage also
preserves missing/zero knownness and explicit journey precedence. Independent
read-only review found no Critical, Important or Minor issues and passed
15 knownness/input tests plus nine refresh tests. All eight regenerated
valuation fixtures remain byte-identical with SHA256
`447f93d2d4ddb3c04cf8ccea18e0387295bb7a335baf2e1a03678c967455acf4`.

Investigation traces, exact timing JSON, RED/GREEN tests and fresh verification
logs are retained under `artifacts/ci-regression-181/`. The first full Python
attempt collected duplicate modules from the clean-base comparison copy and
stopped during collection. Moving that copy to `.base` removed it from pytest
discovery; the unchanged complete command subsequently passed **3,667 tests**,
with 32 existing conditional skips and one existing Starlette warning, in
365.15 seconds. Fresh full frontend deterministic validation passed **356
tests**, with zero failures or skips. Fresh complete browser and repository
gate results are recorded below when finished.

The original GitHub log also contained failures beyond the three reported
timeouts. Each additional repair follows captured failure evidence:

- The new storage result reports quota/write failures as
  `storage_unavailable`, rather than throwing. Snapshot-save feedback now
  prefixes that result's detailed message with `儲存失敗：`, restoring the
  accessible failure transition. Other blocked reasons retain their messages.
- Older Save tests read storage, change inputs, or reload immediately after
  clicking Save. A controlled 200 ms delay inside the real exclusive Web Lock
  reproduced all ten failures across both engines. Case reads occurred 10–17
  ms after the click; finance reload began 68 ms after it, before persistence.
  Three completion waits now observe persisted case counts or finance-save
  success before the original assertions and subsequent actions. The identical
  delayed-lock experiment then passed all ten cases, without changing any
  assertion, timeout, lock, storage mutation, revision guard, or production
  persistence behavior.
- Two older valuation transition tests relied on reselecting an equivalent
  city spelling or the already-selected district. The new intentional no-op
  guards suppress those actions: one test could not load its canonical fixture
  directory, and the other observed only the initialization A request, never
  holding its intended later A response. Both failures reproduced in both
  engines. One test first selects another available city; the other clears
  its district before selecting A. These explicit transitions preserve all result and request-count
  assertions, the actual held late-A response, and both no-op guards.
- The actual A4 audit imports PyMuPDF in the browser job, which previously
  installed neither Python nor that dependency. The exact auditor command
  failed with `ModuleNotFoundError` against an actual generated browser PDF in
  a clean Python environment and passed after installing PyMuPDF 1.28.2.
  Browser CI now sets up Python 3.12 and installs the pinned test-only
  `frontend_next/e2e/requirements.txt` before browser execution. The existing
  35-minute workflow limit and every browser test timeout are unchanged.

Final full Python rerun passed **3,667 tests**, with the same 32 conditional
skips and one Starlette warning, in **297.99 seconds**. The clean-base
comparison remains archived under `.base`; no tests are omitted by the full
Python command. Final browser/gate verification follows.

After the final E2E rebuild, the three unchanged reported tests passed three
more repetitions in each engine: **18/18**, zero failures, retries or skips,
131.50 seconds for the entire run. Exact durations in milliseconds:

| Exact test | Final Chromium | Final installed Chrome |
|---|---|---|
| Valuation refresh | 4,230 / 2,727 / 3,115 | 3,429 / 4,404 / 2,996 |
| A-to-B late responses | 2,351 / 2,301 / 1,923 | 2,347 / 2,950 / 2,445 |
| Save/Reopen/Compare/Report | 11,471 / 11,756 / 12,608 | 10,962 / 11,916 / 15,659 |

Accessible storage-failure feedback passed both engines. The separate final
transition/satellite run passed **6/6**, with no retries or skips. Traces prove
exactly two A requests and the held second A completing **606.821 ms after B
in Chromium** and **625.160 ms after B in Chrome**; all original stale-road
and request-count assertions passed. Independent review of the complete
repair found no remaining Critical, Important or Minor issues.

A subsequent optional local run selected the entire 1,140-test browser suite,
then was stopped after two checklist width tests timed out on this shared
Windows machine. This is retained as a failed, incomplete attempt under
`browser-final/`, not counted as a passing full suite. All 18 isolated
checklist repetitions then passed without changes, retries or skips.
The slow first passing trace spent 4.42 seconds on its initial navigation
and 10.46 seconds opening the checklist; the earlier failure video remained
on the initial overview and did not reach the second Save. Several unrelated
browser jobs were active on the same machine, but the exact cause of those
two timeouts is not established. No speculative application or checklist
change was made. The complete requested three-file pack and the fresh full
GitHub browser suite are the remaining verification boundaries.

The first requested-pack attempt also exhausted its unchanged 90-second
two-case budget on the final `/cases` navigation after both actual PDF audits
had completed. Concurrent machine CPU use was 98%. That failed attempt is
retained under `browser-requested-contention.red/`. Giving only the verified
owned runner, server and browser descendants `AboveNormal` Windows process
priority brought subsequent closure cases to 30–35 seconds, and a complete
clean pack rerun was started with that bounded local resource adjustment.
No other workspace's process was changed. Neither committed test configuration
nor CI process priority nor any timeout changed. The original branch/base
comparison and both 18-case regression repetitions preceded this adjustment.

Final local verification completed successfully:

| Check | Final result |
|---|---|
| Three unchanged reported tests | 18/18 repetitions after the final E2E rebuild; nine Chromium and nine installed Chrome; zero retries/skips |
| Complete requested browser pack | **72/72**, 20m58.913s; Chromium **36/36**, Chrome **36/36**; zero failures, retries, skips or flaky results |
| Hosted-case closure | **50/50**, including four authentic captured-response replays; all four locales and four widths; stale/competing writes and zero-automatic-provider contracts retained |
| Entire commercial Market-price file | **12/12** across both engines |
| Entire comparable-explanation file | **10/10** across both engines |
| Actual A4 audit | **68 PDFs / 1,123 pages** audited; another two comparable Save/Reopen PDFs generated; no blank/clipped-page assertion failures |
| Full Python | **3,667 passed**, 32 existing conditional skips, one existing Starlette warning; 297.99s |
| Full frontend deterministic tests | **356 passed**, zero failures/skips; 9.62s |
| Typecheck / lint | PASS; lint retains 23 existing warnings, zero errors |
| Standard production build | PASS; separate from the E2E production build |
| Bundle | PASS: **2,984,243 bytes** total, 2,832,475 JavaScript bytes; largest client chunk **602,354 bytes** |
| Route budgets | All six PASS, including the 3,000,000-byte homepage budget |
| Release / security-performance / operations gates | PASS; external production guardrails remain **BLOCKED / NO_GO** |
| Production-safe smoke / repository hygiene / whitespace | PASS |
| npm production audit / audit policy gate | PASS; zero production vulnerabilities; existing dev-only exception expires 2026-11-04 |
| Preservation checks | Original three tests, Web Locks/storage implementation, snapshot-save revision checks, Market response guards, shared fixtures and timeout configuration unchanged from original #181 |

Machine-contention failures and every RED attempt remain archived; none is
represented as a passing complete suite. The original broader local run was
incomplete. Fresh GitHub CI must independently pass the entire normal browser
suite on the amended SHA. The branch keeps exactly one Wave 0A commit above
the requested `8b1367a` base. PR #181 remains open without auto-merge; no merge,
deployment, production repair, or ML-B work is authorized by this validation.
