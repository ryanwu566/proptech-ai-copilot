# Final production acceptance v1

Acceptance date: 2026-10-09, Asia/Taipei. **Production verdict: NO-GO.**
Local implementation and fixture proof cannot establish hosted provider, global
cost/security or managed PostgreSQL recovery readiness. The categorical gate
record is `final-production-acceptance-evidence-v1.json`; detailed bounded local
observations are `final-production-acceptance-validation-v1.json`. Neither file
contains credentials, raw provider responses or real customer cases.

## Frozen candidate and deployment identity

The clean starting worktree, branch `release/final-production-acceptance-v1`,
HEAD, local origin/main and GitHub's actual `refs/heads/main` all matched
`95018f6fc2a366656cb798414dc54860d009e536`. The candidate remains frozen at that
SHA. The final commit adds acceptance tooling and print improvements; its SHA
is a separate tooling revision, recorded in the delivery response. These changes
have not been deployed and do not become hosted proof by being committed.

One read-only HTTPS GET to the supplied frontend `/release-version` returned
HTTP 200 and exactly that candidate SHA. No other hosted HTTP requests were
sent. No backend target, expected release version or complete hosted environment
contract was supplied. Backend SHA, frontend release version/environment,
frontend/backend compatibility and deployed source/artifact versions remain
**NOT VERIFIED**. The combined identity gate is **BLOCKED**, even though
the frontend commit alone matches.

Frontend release metadata is now build-bound: SHA from RELEASE_COMMIT_SHA or
VERCEL_GIT_COMMIT_SHA, release version from RELEASE_VERSION, and environment
from APP_ENV. Unconfigured metadata stays unconfigured. An owner must supply
the same release contract to both builds and verify both endpoints independently.
The frozen frontend endpoint contains only product and SHA; it cannot satisfy
the newly strengthened version/environment contract through configuration alone.
Genuine acceptance needs a separately authorized successor candidate containing
these changes, its actual newly frozen SHA and fresh evidence. Never label a
successor build with the old candidate SHA. This task did not move the candidate.

## Acceptance tooling

- `production_smoke.py`: pinned matching frontend/backend expectations, required
  production/preview environment and release version, exact HTTPS origins,
  refusal of redirected targets, bounded response reads and timeouts, health
  semantics, supported demo-array shape, CORS and safe categorical output.
  A configured run makes at most 13 requests, once per passive check, without
  retries. An incomplete contract returns CONFIGURATION REQUIRED before traffic.
- `provider_acceptance.py`: the existing config and offline workflows remain;
  live Google Geocoding/Routes require explicit `--allow-live`, confirmed
  environment and `--request-budget 1`. Unsupported live capabilities are refused.
- `certify_real_provider.py`: compatibility entrypoint to that existing runner;
  importing it sends zero requests. The previous automatic 15-address loop and
  raw address/response printing have been removed.
- `generate_release_evidence.py`: `--acceptance-input` accepts a bounded list of
  categorical observations and supplies absent required gates as NOT VERIFIED.
  Duplicate/unknown fields, unsafe reason/action codes, false passing results,
  preview proof for production, mismatched SHAs, missing owner proof and missing
  official metadata are rejected. Required versions, dates, checksums, periods,
  coverage, fixtures and flood scenarios cannot be unknown aliases.

The evidence generator is an aggregator of explicit observations, not an
independent attestation service. Boolean owner assertions must be backed by the
referenced hashed, redacted drill/control evidence. A synthetic checksum or a
manually asserted PASS is not production proof. Local gate passes are scoped to
the local checkout; all production prerequisites remain separately classified.

The bounded change set contains 19 files:

| Area | Files |
| --- | --- |
| Existing scripts | `scripts/production_smoke.py`, `scripts/provider_acceptance.py`, `scripts/certify_real_provider.py`, `scripts/generate_release_evidence.py` |
| Frontend implementation | `frontend_next/next.config.mjs`, `frontend_next/app/release-version/route.ts`, `frontend_next/components/evidence/evidence.module.css` |
| Browser regression | `frontend_next/e2e/final-production-acceptance.spec.ts` |
| Backend/contract regressions | `tests/test_final_production_acceptance.py`, `tests/test_frontend_vnext_property_identity.py`, `tests/test_hosted_production_launch.py`, `tests/test_provider_acceptance.py`, `tests/test_provider_closure_smoke.py` |
| Hosted configuration contracts | `.github/workflows/hosted-production-smoke.yml`, `config/hosted-environment-manifest.json` |
| Documentation/evidence | This report, `docs/operations/final-production-acceptance-evidence-v1.json`, `docs/operations/final-production-acceptance-validation-v1.json`, `docs/superpowers/plans/2026-10-09-final-production-acceptance.md` |

## Provider scorecard

Every requested capability has executable code and passed its existing offline
contract/fixture path. This proves implementation only. The validation JSON
records configuration categories without values, separate accepted-artifact,
deployed-release and bounded-live dimensions, and zero provider requests.

| Capability | Production classification | Required evidence / next step |
| --- | --- | --- |
| PLVR Market, Finder | CONFIGURATION REQUIRED | Configure approved BLUE data connection; identify accepted PLVR release, ledger/checksum, transaction period and per-capability deployed provenance. |
| Valuation, Trend | CONFIGURATION REQUIRED | Disable demo, configure BLUE or supported GREEN valuation correctly; Trend/Finder/Market do not inherit GREEN valuation availability. |
| Google Geocoding | CONFIGURATION REQUIRED | Approved key, restrictions/quota, exact deployed identity and one authorized accepted-address check. Address association is not cadastral confirmation. |
| Google Places | CONFIGURATION REQUIRED | Approved key/quota and bounded category evidence; successful zero remains distinct from unavailable/null. The existing script does not support bounded-live Places. |
| Google Routes | CONFIGURATION REQUIRED | Approved key/quota, confirmed origin/destination and one transit request. TDX failure must not replace a valid Google route. |
| Google Maps / Street View | CONFIGURATION REQUIRED | Browser-key restrictions, enabled APIs, load/no-panorama evidence and owner-approved provider budget. An iframe alone is not health proof. |
| TDX | CONFIGURATION REQUIRED | Approved credentials/refresh contract and snapshot version/SrcUpdateTime. No refresh was transmitted. |
| RIS Demographics | CONFIGURATION REQUIRED | Approved DB, accepted NLSC village boundary and statistical month; demographic absence is not zero. |
| NLSC | CONFIGURATION REQUIRED | Approved numeric gateway/token; separately accept village-boundary artifact. Public WMTS does not prove either. |
| ARDSWC | NOT VERIFIED | Local contracts passed; deployed official vintage 113, source availability, geographic coverage and bounded live fixtures remain unverified. |
| WRA Flood | OWNER ACTION REQUIRED | Supply immutable official manifest/artifact, scenario/vintage/checksums and fixtures, then separately prove deployed runtime loads those exact bytes. |
| GSMMA Geological Sensitivity | OWNER ACTION REQUIRED | Supply accepted immutable exact version, quality/quarantine/CRS/geometry evidence and fixtures; builder existence does not prove rollout. |
| Liquefaction | NOT VERIFIED | Local contracts passed; accepted official coverage/source vintage and deployed/live evidence remain unverified. No-match is not safety. |
| Satellite / GEE | OWNER ACTION REQUIRED | Optional feature stays outside live testing. Separate authorization, project/ADC/IAM, quotas, deadlines and worker isolation required before generation. |
| Active Fault | OWNER ACTION REQUIRED | MANUAL VERIFICATION ONLY; no automated safety claim. |

All provider deployed-release and bounded-live dimensions remain unverified.
No provider is classified as production-ready. Empty requirements for a public
provider mean no credential is required by that code path, not that its official
data or hosted runtime has been accepted.

## Official data and artifact scorecard

| Evidence | Local proof | Deployed official acceptance |
| --- | --- | --- |
| PLVR | Updater/ledger/dry-run, freshness, rollback and invalid-row fixtures passed. | Exact dataset release, source date, import timestamp, manifest/artifact checksum, coverage and newest effective transaction period NOT VERIFIED. Import time is never transaction freshness. |
| WRA | Runtime manifest/index/checksum/scenario and positive/negative/unknown fixtures passed on synthetic bytes. | Official source vintage, scenario coverage and exact deployed artifact NOT VERIFIED. |
| GSMMA | Version/accepted-quality/CRS/topology/checksum and query fixtures passed on synthetic bytes. | Exact accepted official version, quarantine decision, source date and deployed bytes NOT VERIFIED. |
| NLSC village boundary | Boundary validation and resolution fixtures passed. | Approved actual boundary checksum/vintage/coverage NOT VERIFIED. |
| ARDSWC / Liquefaction | MVT/topology/holes, partial/unavailable and no-match semantics passed. | Official byte/version and geographic/live coverage NOT VERIFIED. |
| TDX / RIS | Snapshot/source-time/statistical-month and absence contracts passed. | Actual source version/freshness NOT VERIFIED. |

For WRA/GSMMA offline artifact validation, use the existing runner with
`--manifest`, `--artifact`, immutable `--dataset-version` where applicable and
`--fixtures-json` containing one positive and one negative declared expectation.
The fixtures must test actual accepted bytes, including unknown/no-match behavior.
At most three fixture queries are accepted. An offline artifact pass still does
not verify deployment or authorize R2/provider requests.

## Hosted smoke and bounded real-property acceptance

Missing backend configuration produced CONFIGURATION REQUIRED, with zero smoke
requests. Only the independent frontend identity GET described above was made.
No provider API, production DB, WAF, quota, billing or Satellite call was made.

The prepared property is 台北市大安區敦化南路二段100號; destination 台北車站,
public transit. Fresh Playwright contexts use deterministic synthetic saved
cases. Property → Market/Valuation → Location/Commute → Risk → Finance → Overview
→ Save → Reopen → Report is exercised through existing workspace and guided-flow
tests. Unavailable market/valuation remains unavailable; the manually entered
finance scenario is not converted to asking price. The saved Taipei fixture is
software proof only, not an actual accepted provider result for this property.

For future passive hosted acceptance, after separately authorizing and freezing
the actual successor candidate, the owner must confirm the exact backend origin,
production environment, release version and both deployed SHAs, then run:

```text
python scripts/production_smoke.py --hosted --frontend-url https://proptech-ai-copilot.vercel.app --backend-url <confirmed-HTTPS-origin> --expected-environment production --expected-release <exact-release-version> --expected-frontend-sha <actual-newly-frozen-successor-sha> --expected-backend-sha <actual-newly-frozen-successor-sha>
```

Keep a smoke token in the existing PRODUCTION_SMOKE_TOKEN environment contract;
do not paste it into logs or CLI history. Provider calls are a separate action:

```text
python scripts/provider_acceptance.py --capability geocoding --mode config-only
python scripts/provider_acceptance.py --capability geocoding --mode bounded-live --allow-live --confirmed-environment production --request-budget 1
python scripts/provider_acceptance.py --capability routes --mode bounded-live --allow-live --confirmed-environment production --request-budget 1 --origin <accepted-lat> <accepted-lng> --destination <owner-confirmed-station-lat> <owner-confirmed-station-lng>
```

Those last two commands require explicit owner authorization first. Each sends
at most one provider request, without retry; they do not attest that a deployed
backend used the same credentials, so deployed-path proof remains a separate
gate. Other live capabilities lack a safe one-request automation path and remain
blocked pending an owner-reviewed budget covering physical fanout. Do not use
`/location/insight` as a one-call shortcut: its logical request may fan out into
several billable provider operations. Satellite requires separate authorization.

## Compare, trust, responsive and accessibility

Existing Compare regressions verify 2–4 selection, descriptive results without
ranking/winner, distinct price provenance, missing/stale evidence, A/B isolation
and zero automatic provider refresh. Saved manual finance remains visible in
Overview, Finance, Compare and Report; unknown facility count remains unknown;
missing risk is not score 50; address association is not legal/cadastral identity.

The final browser suite covers Homepage, Overview, Market, Location, Risk,
Finance, Compare and Report at 1440, 1024 and 390px in Chromium and installed
Chrome. It checks body overflow, visible-control labels, Tab focus outline,
reduced-motion animations and sampled heading contrast. Screenshots, PDF
geometry/text checks and request traces are local artifacts. This is bounded
accessibility coverage, not a full WCAG certification or screen-reader audit.

## Real A4 PDF inspection

Browser PDF generation uses A4 portrait/CSS page size, not a Print-button stub.
The initial representative fixture produced 32 pages; actual PDF inspection
identified excessive print spacing. Print spacing and column allocation
were adjusted while retaining sources, timestamps, financial values, missing
evidence and provenance. The regression enforces a maximum 20 pages for this
full synthetic ledger. Final page counts, PDF hashes, geometry, text-boundary
checks and visual-inspection records are in the validation JSON. Navigation and
controls are hidden; printing produces no provider calls.

The final inspection contains eight PDFs, each 17 A4 portrait pages, with zero
out-of-page text spans. All eight were checked for finance, fixture-specific
price provenance, source, timestamp and missing/risk-limit text. All pages of
two representative reports were visually inspected as contact sheets, with
finance and sources sampled at full size; the other six share checked layouts.
The two existing long-address/URL reports have one empty trailing page each;
their sources end on page 16. The six manual-scenario reports have no empty
pages. Compare/PDF is **PASS WITH RESTRICTIONS** for that minor pagination defect;
no source, number or disclosure was removed to improve page count.

PDFs and screenshots contain synthetic fixture data and stay in ignored
`.local/pdf-inspection` and `frontend_next/test-results`. They are inspectable
local artifacts, not committed customer exports. The machine-readable hashes
bind the inspected bytes. Regenerate with the existing owned-server runner after
`npm run build:e2e`:

```text
node e2e/run-e2e.cjs e2e/final-production-acceptance.spec.ts e2e/commercial-compare-report.spec.ts --workers=2 --retries=0
```

## Cost and executable abuse controls

The mocked physical-transport journey still records **17 provider operations,
4 tile decodes**, with identical counts on repeated context. Historical 23/8 is
the documented pre-optimization baseline, not a newly reexecuted historical
checkout. No currency savings are claimed. Satellite generation is mock-only
in that fixture. Save/Reopen/Compare/Report generate zero analysis refresh.

Anti-abuse fixtures cover endpoint-specific admission, Retry-After, concurrency,
physical-operation reservations/budgets, kill switches, oversized body rejection,
sanitized errors, bounded metrics, cancellation/resource recovery and zero
provider calls for rejected work. Process-local controls do not provide a
cross-instance ceiling. See the existing anti-abuse and cost runbooks.

## Global security and cost owner contract

Both global gates are **BLOCKED** until named owners supply redacted evidence:

| Control | Owner acceptance evidence / executable next action |
| --- | --- |
| Trusted ingress/proxy chain | Enumerate deployed ingress, worker/revision count and proxy hops; verify stripping of untrusted forwarding headers and trusted proxy policy. |
| Origin bypass | Confirm every direct backend/default-origin path is prevented or protected by the same policy. Frontend WAF coverage alone is insufficient. |
| Edge/WAF | Record effective endpoint policies, attachment and approved small canary rejection proof; no production abuse/load test. |
| Cross-instance limits | Record centralized limiter or equivalent enforceable provider/edge ceiling across every instance/revision and credential consumer. |
| Google Maps quotas | Provider owner verifies API enablement, browser/server restrictions, effective Geocoding/Places/Routes limits and quota rejection behavior under an approved bounded test. |
| GEE quotas | Verify approved concurrent/EECU-time controls, project access, ADC/IAM and worker deadline/isolation; generation stays disabled without separate authorization. |
| Effective cost ceiling | Combine enforceable quotas, all shared consumers, autoscaling/revision overlap and emergency shutoff; alerts alone do not cap spending. No financial amount is invented. |
| Billing alerts | Supply actual/forecast thresholds, delivery test, named primary/backup recipients and response SLA. |
| Incident escalation | Service/security/billing owners record on-call contacts, triggers, authority and expected response time. |
| Emergency disable | Owner applies ANTI_ABUSE_<CAPABILITY>_DISABLED=true across all active workers/revisions and blocks named routes at ingress during propagation; MAINTENANCE_MODE is the broad control. |
| Rollback | Preserve quotas/edge rules/kill switches while restoring the previous accepted compatible frontend/backend revisions and verifying passive health. |

These cloud changes were not performed. Missing owner identities, effective
values and enforcement/delivery evidence cannot be filled with assumptions.

## Database, backup and operations

Migration registry/checksums and local SQLite backup/restore round trip are
executable local proof. Managed PostgreSQL migration state, PITR/backup, restore,
retention/deletion boundary, PLVR refresh, artifact restore, incident recovery
and deployment rollback remain OWNER ACTION REQUIRED or BLOCKED. The full
suite's 32 disposable PostgreSQL skips are recorded, not promoted to passes.

The database owner must obtain the approved backup/PITR checkpoint and restore
it into a newly confirmed disposable environment, verify schema/checksums,
row/account isolation, deletion/publication boundaries and readiness, then
record elapsed recovery and approved RPO/RTO. Do not run the local SQLite
scripts against production or treat a written procedure as a successful drill.
Use existing `docs/backup-restore.md`, `docs/disaster-recovery.md`,
`docs/hosted-rollback-runbook.md`, PLVR update and risk rollout runbooks.

For PLVR, perform reviewed import dry-run and ledger/freshness inspection first;
no production import or retention deletion occurred here. For artifact restore,
restore previous immutable bytes to a disposable runtime, verify both checksums
and positive/negative fixtures and separately prove deployed version selection.

## Rollback sequence

1. Declare incident and preserve safe correlation/release/ledger references.
2. Keep global provider quotas and edge controls active; disable affected costly
   capabilities across active revisions and stop writes if schema integrity is
   uncertain.
3. Select the previously accepted frontend/backend pair and compatible schema;
   restore application revisions together when the contract requires it. Do not
   infer compatibility from frontend SHA alone.
4. Keep prior accepted PLVR releases and WRA/GSMMA immutable artifacts. Switch
   to the approved prior exact version; never overwrite the WRA v1 prefix or
   modify quality/checksum flags to admit damaged data.
5. Failed import transactions roll back atomically. A successfully imported bad
   release or incompatible migration needs the approved managed PostgreSQL
   restore/corrective-import process; no invented destructive down-migration.
6. Verify both release identities, compatibility, readiness, CORS and artifact
   fixtures before reopening traffic. Log categorical results and owner approval.

Restart resets process-local budgets; it is not a way to bypass exhausted quota.
Do not lift quotas, widen IAM, switch to SQLite or convert missing evidence into
zero/safety during recovery. A real rollback drill has not been demonstrated.

## Verification, independent review and release decision

| Local verification | Result |
| --- | --- |
| Full Python suite | 3,377 passed, 32 guarded PostgreSQL skips, one existing deprecation warning. |
| Frontend unit suite | 239 passed. |
| Comprehensive browser acceptance | 244 passed: 122 Chromium and 122 installed Chrome. |
| Final CSS/Compare/Report/responsive rerun | 78 passed: 39 per browser; actual PDFs regenerated. |
| Provider offline matrix | 18 fixture capabilities passed; Active Fault remains manual-only; zero provider requests. |
| Production/E2E builds, lint and typecheck | Passed; lint retains 23 existing warnings and zero errors. |
| Release, security/performance, operations, bundle, route and hygiene gates | Passed locally; separately executed tests/build are recorded. |
| Dependency audits | Declared runtime requirements and npm production pass; existing dev exception and machine-wide Python findings remain disclosed restrictions. |

The validation JSON records the final command results/counts for full Python,
frontend units, both browsers, production/E2E builds, lint/typecheck, dependency
audits and release/security/operations/bundle/route/hygiene gates. Contract-only
release-gate skip flags do not claim embedded tests/build ran; those are separate
executions. No bundle budget, assertion, retry gate or dependency exception was
relaxed. Browser acceptance uses zero retries and isolated profiles.

The final production static assets total 2,999,975 bytes; largest client chunk
is 608,747 bytes. The 3,000,000-byte homepage budget has only 25 bytes of headroom.
The actual successor build must recompute every unchanged budget using its own
release environment. Equivalent inherited/grouped CSS rules were consolidated
after the initial production build exceeded this budget by 515 bytes; the
affected browser views and PDFs were then regenerated and checked.

Production npm and the declared backend dependency audit pass. The existing
dev-only npm exception expires 2026-11-04 and was not broadened. A separate audit
of the machine-wide Python installation found 26 advisory records across six
packages; that environment is not certified for deployment. Declared dependency
resolution is not the deployed runtime inventory: owner must audit the actual
backend image/SBOM and rebuild from a clean verified environment before acceptance.

Independent review reproduced and corrected false GO from missing/contradictory
owner proof, preview/production ambiguity, unknown metadata aliases, unsupported
demo-array handling and missed refresh endpoint families. It also prompted
allowlisted reason/action codes. Print pagination was found by actual inspection,
not inferred from a passing button test. Initial failed runs and corrections
remain disclosed in validation history.

Final independent software and artifact consistency review passed with zero
remaining Critical or Important findings. Every recorded log/PDF hash and PDF
size/page/geometry record matches the retained local artifact. The empty-tail
pagination defect is Minor and remains explicitly restricted.

The final verdict remains **NO-GO for production**. This change set is suitable
for a software-review PR with the disclosed local restrictions; opening a PR
does not accept the hosted release. Remaining blocking actions are the
complete backend/release contract, actual official artifacts and freshness,
authorized bounded deployed-provider acceptance, verified global ingress/cost
controls, actual runtime dependency audit and PostgreSQL/artifact/recovery/
rollback drills. There was no push, merge, deployment or cloud-setting change.
