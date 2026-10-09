# Production identity and provider closure V1

Date: 2026-10-09 (Asia/Taipei). Original implementation baseline:
`b4eb441a8ccf90965102f0646006dc4b0e145491`. Exact branch:
`fix/production-identity-provider-closure-v1`.

Integration baseline (PR #170 merged main):
`602830c8d4d405bb401afa902d5bf69f2c61066f`. The original implementation
started on `b4eb441`; the cherry-pick integration happened afterward on `602830c`.

This is a repository implementation and local evidence snapshot, not production
acceptance. Production remains **NO-GO**. There was no push, merge, deployment,
production infrastructure/database write, live provider probe, dataset download,
satellite generation or ML training. The final commit SHA belongs in the handoff:
embedding it in a document in that same commit would create a self-reference.

## Architecture and evidence boundaries

The existing `/release-version`, `provider_acceptance.py`, configuration contracts,
real offline risk-artifact validators, npm exception gate and release-evidence
generator remain the integration points. New modules provide narrowly scoped build
identity, configuration/provider projections, a single artifact inventory and
sanitized dependency audit results. The collector reads explicit saved audit/smoke
files and local manifests. It never loads dotenv, reads a database, accesses R2,
or calls Google, TGOS, TDX, GEE or government APIs.

The committed JSON records `source_checkout_sha` and `source_checkout_dirty`.
It was generated before the final commit, so the checkout SHA is the starting SHA
and the worktree is dirty. It is explicitly `local_checkout_not_production`.
The separate v2 release-evidence JSON also identifies that starting-checkout
snapshot; CI, preview and production validation remain `pending`. Regenerate
candidate and hosted evidence using the final commit after review/deployment.

## Backend deployment identity contract

`backend/build-identity.json` is generated during a build and ignored by Git.
The build writer uses Render's checkout `RENDER_GIT_COMMIT`, an explicit CI Docker
checkout argument, or Git HEAD for a local build. It never derives identity from
runtime `RELEASE_COMMIT_SHA`, and it never dumps environment variables.

The backend build document contains `backend-build-v1`, service `proptech-api`,
40-character commit SHA, UTC build timestamp, a SHA-256 build identifier and one
of `render-checkout`, `ci-build-argument`, `git-checkout`. The build identifier
hashes ordered backend/service/config/database code and manifests, excluding
generated identity, credentials, data files and Python caches. It is a content
identifier, not a signed image attestation or a complete infrastructure identity.

The existing endpoint adds `service`, `commit_sha`, `build_timestamp`, `build_id`,
`identity_source`, `identity_status`, `runtime_sha_matches_build` and bounded
`configuration_evidence`. Missing, oversized or malformed build files return
`identity_status=UNKNOWN` with unconfigured metadata. A runtime SHA cannot override
the file. An optional runtime SHA disagreement is exposed as `false` and causes
hosted build verification to fail. Schema compatibility remains **declared**;
this endpoint does not verify migration application. Local build identity is not
deployed identity, and a Git checkout build may contain uncommitted code: its build
digest remains separate from its checkout SHA. Use clean reviewed CI checkouts.

Render now generates the file in its existing build command. Cloud Run Docker
builds require a trusted checkout argument, for example in CI:

```sh
docker build -f Dockerfile.cloudrun --build-arg BACKEND_BUILD_COMMIT="$GITHUB_SHA" -t proptech-api .
```

An omitted/invalid argument in a container without Git fails the build. The Docker
context excludes stale build metadata, environment/secret files, local audit/test
output and frontend caches/dependencies. Actual image deployment and checkout
argument provenance still require operator verification; no deployment was run.

The frontend's existing `/release-version` reports its independent build-bound
`NEXT_PUBLIC_RELEASE_COMMIT_SHA`. The backend never reports that frontend SHA as
its own. Hosted smoke verifies separate expected frontend/backend SHAs, immutable
backend build fields, runtime disagreement, release/environment and safe response
headers. Import requires a bounded hosted observation with UTC capture time and
the required checks; PASS labels alone cannot establish identity. The v2 generator
also binds observed backend SHA to its explicit release commit.

## Release configuration projection

The endpoint reports backend runtime categories only: database, signing key, CORS,
public app origin, backend public origin, release/API/schema identifiers,
production environment and actual runtime readiness. Missing/invalid/default
values, reserved example/local origins, and malformed optional metrics credentials
block acceptance. Only categories and a hash of those categories are emitted;
the hash is not a hash of secret values or the complete production configuration.

Frontend build configuration stays `UNKNOWN`: backend process variables cannot
prove the separately deployed frontend API/Supabase configuration. Runtime schema
and release defaults are not migration/deployment proof. The Final Acceptance v2
importer does not clear the complete deployed configuration blocker from this
partial backend report.

## Artifact registry and current results

`services/production_artifact_registry.py::REGISTRY` is the authoritative inventory.
All records include provider, logical name, expected schema/version/storage,
publication/retrieval/build dates, checksum, presence, freshness, limitation,
production requirement and production activation. Requirement means required to
accept the capability, not required for API liveness. GREEN is conditional on the
selected valuation backend; BLUE remains required by other market capabilities.

| Artifact | Production storage / contract | Local result |
| --- | --- | --- |
| WRA flood | R2 `processed/wra/flood/v1/{scenario}`; `wra_flood_processed_v1` | Remote presence/activation/date unknown; processing v1 is not publication date |
| GSMMA sensitivity | R2 immutable dataset version; `gsmma_geological_sensitivity_features:1` | Configured production version and activation unknown |
| ARDSWC landslide/debris flow | Public MVT layers; `113-public-mvt` | Known code-selected vintage; publication/freshness/reachability unknown |
| GSMMA liquefaction | GeologyCloud API; `official-liquefaction-v1` | Dataset version, source date and activation unknown |
| NLSC village boundary | Explicit local or R2 boundary artifact | Deployed checksum/vintage/activation unknown |
| NLSC numeric terrain | Approved gateway | No numeric terrain proof from visible map tiles |
| RIS population | Monthly database observations; `raw/ris/population/{month}/manifest.json` | Active month/archive checksum unknown |
| PLVR BLUE/GREEN | Independent production database contracts | Active release/version/import checksum unknown |
| TDX MRT | Process-memory snapshot; `tdx-mrt-v1` | Production snapshot/version/source age unknown |
| Road display/source | Bundled JSON manifest and CSV | JSON manifest present/schema checked/hash derived; CSV absent in this checkout; deployment/publication unknown |

There are **13 logical records**. WRA's ten supported scenarios remain selected
by the existing runtime, not ten invented provider integrations. Remote absence
is not inferred from missing local files. No local presence establishes deployed
activation. Every publication date/freshness is currently unknown. Processing
versions, ROC vintage labels, file modification dates and retrieval times are
never substituted for publication dates. Freshness calculation requires an exact
known date, explicit age policy and as-of date; future dates remain unknown.

Optional local WRA/GSMMA verification uses the actual runtime checksum/schema/index
validators, with 1MB manifest, 16MB compressed artifact and 64MB decompressed ceilings.
Checksum, geometry and schema failures are BLOCKED. Its receipt is
`local_offline_artifact`; successful local validation does not prove source dates,
coverage, production activation or freshness. Large artifacts remain outside Git.

## Provider acceptance matrix

The collector projects **23 existing capabilities**, including TGOS, Google
Geocoding/Routes/Places/browser Maps/Street View, BLUE/GREEN valuation and other
market operations, PLVR updates, WRA/GSMMA/ARDSWC/liquefaction, NLSC gateway, RIS,
TDX, satellite and the existing manual active-fault/tax-legal capabilities.
TGOS is included because the production location resolver actually uses it.

Each row distinguishes configuration, authorization, reachability, contract
compatibility, freshness, degraded/unavailable state and production acceptance.
Local configuration is not authorization. Public APIs with no credential contract
have configuration NOT_APPLICABLE and reachability NOT_TESTED, not PASS. A fixture
PASS can establish only `local_fixture` contract compatibility. A bounded live
result can establish `operator_probe` reachability/contract compatibility, while
authorization and deployed configuration remain unproven. Unknown degradation and
unavailability are null, never invented success states.

The committed collection uses no runtime environment or provider receipts:
credential-backed integrations are BLOCKED/not tested; public integrations are
UNKNOWN/not tested. Satellite is disabled by its default code policy and remains
NOT_APPLICABLE/unavailable. Active-fault and tax-legal are manual verification only.
Existing runtime anti-abuse switches project intentional unavailability honestly,
including malformed fail-closed switches. Kill switches do not turn a required
provider into an accepted optional provider.

Existing live acceptance permits only one explicit Geocoding or Routes request,
with no retry, bounded input and existing adapter deadlines. `--allow-live` remains
required, together with `--confirmed-environment preview|production` and an
explicit integer `--request-budget 1`. `--max-requests` is restricted to 0 or 1;
0 disables live work. These safeguards are cumulative; the request ceiling does
not substitute for operator authorization, environment confirmation or budget.
`PROVIDER_ACCEPTANCE_DISABLED=true` stops live work before dispatch. No credentials
means configuration-required/not tested. Places fan-out, TDX refresh, satellite
generation, imports and writes are not added as live probes. These are per-process
ceilings; repeated operator invocations still require provider billing controls.
No Save/Reopen/Compare/Report code was changed or given new provider calls.

## Runtime dependency audit results

Audits used the actual manifests. `pip-audit` resolved requirements in the local
Windows/Python 3.13 environment; deployed manifests declare Linux/Python 3.12.
The backend has open version ranges rather than a deployed-image lock/inventory.
Consequently a clean resolution is not a clean deployed-image assertion.

| Scope | Result |
| --- | --- |
| Backend Render/Cloud Run `backend/requirements.txt` | 68 resolved packages; zero known findings |
| Alternate Docker/Compose `requirements.txt`, after fix | 82 resolved packages; zero known findings |
| Alternate runtime, before fix | pytest 8.4.2 had two reported entries for the same `PYSEC-2026-1845` advisory; moved test tooling out of the production manifest |
| Frontend production lock | Zero npm vulnerabilities |
| Frontend full audit | Eight raw findings (six high, two moderate) preserved; exact existing dev-only exception gate passes |
| Existing governed exception | `GHSA-vfj7-8cjw-p6xm`, expires 2026-11-04; no new exception or extended expiry |
| Machine-global Python | 135 audited packages; 26 reported findings in six packages, retained separately; not the deployable runtime |
| Deployed Linux/Python image | UNKNOWN; requires actual image inventory/audit and identity binding |

Machine-global affected packages are cryptography, pip, PyJWT, pypdf, pytest and
urllib3. pip-audit reports some duplicate advisory entries; the JSON preserves all
26 reported entries, safe fix-version fields and UNKNOWN severity. Unknown severity
is never interpreted as low severity or silently accepted. Machine packages were
not upgraded. npm parsing reuses the existing strict schema policy, escalates
nested severe findings, and preserves safe findings across partial malformed data.

Test tooling belongs in `requirements-dev.txt`; a new local developer installation
uses `python -m pip install -r requirements-dev.txt`. It requests patched pytest
9.0.3 or newer within major 9. Verification here used the existing pytest 8.4.2
installation; the new pytest 9 environment was not installed/tested. Existing CI
separately installs its own test requirements. Those development installations
must not be confused with the production manifests or represented as patched.

## Acceptance integration and operator commands

The collector exits nonzero for a blocked lane and still writes evidence. Default
collection uses an empty environment; `--use-runtime-environment` is explicit and
reads only process variables into categorical projections, never dotenv.

```sh
python scripts/collect_production_closure.py --as-of 2026-10-09 --output closure.json \
  --python-audit-json python-runtime-audit.json \
  --alternate-python-audit-json python-alternate-audit.json \
  --npm-production-audit-json npm-production-audit.json \
  --npm-full-audit-json npm-full-audit.json --npm-explanation-json npm-braces-explanation.json \
  --machine-audit-json python-machine-audit.json
python scripts/generate_release_evidence.py --output release-evidence.json \
  --release-id reviewed-release --commit <reviewed-backend-sha> --schema-version declared \
  --closure-json closure.json
```

Generate input audits through the existing CI commands:
`python -m pip_audit -r backend/requirements.txt --strict -f json --desc off`,
the corresponding alternate manifest command, `npm audit --omit=dev --json`,
`npm audit --json`, and `npm explain braces --json` from `frontend_next`.
Use `PYTHONUTF8=1` on Windows if needed. Bounded JSON inputs support UTF-8 and
PowerShell's UTF-16 BOM output. The collector does not launch audit networking.

Optional saved artifact arguments are `--offline-artifact wra-flood` (or
`gsmma-sensitivity`), `--artifact-manifest`, `--artifact-file`, `--scenario` and
`--dataset-version`. Optional existing provider receipt files use repeated
`--provider-evidence-json`, maximum 24. These receipts retain local/operator scope.

For release metadata without categorical acceptance input, the generator retains
v1 compatibility when no closure is supplied and emits
`production-release-evidence-v2` when supplied. It copies only the bounded,
revalidated acceptance summary, not arbitrary raw caller data, PASS/GO claims,
environment values or provider payloads. All five categories remain blocked here.

The integrated CLI also preserves #170's `--acceptance-input`, categorical gates,
owner-action semantics and exact production evidence checks. Both input options
can be supplied together and use one atomic output writer. With acceptance input,
the existing `final-production-acceptance-v1` scorecard schema is retained and the
same `closure_acceptance` projection is added. A blocked closure forces the combined
verdict to `NO-GO`; closure evidence never promotes incomplete categorical gates.

**Current boundary:** no authenticated deployed artifact/provider/image reader or
complete frontend-build configuration receipt exists in this repository workflow.
The v2 importer therefore refuses to clear those four categories from speculative
JSON scopes/status labels. It consumes their evidence deterministically as blockers.
A real deployed collector/receipt contract plus owner authorization is still needed
before those categories can close; editing JSON to say PASS cannot bypass this.
This lane does not claim to have completed live production acceptance.

## Original implementation verification and independent review

Focused new tests were run RED before implementation for missing identity modules,
forged PASS labels, audit severity/partial findings, artifact bounds/checksums,
runtime dependency separation, encoding, reserved origins and kill switches.
Final focused regression and deployment suites passed; final gate results are
recorded in the verification table below.

An early full run encountered absent Node dependencies and an invalid nested
temporary directory. Those environment/setup errors were corrected, not labeled
pre-existing product defects. An intermediate concurrent run had two worker
lifecycle failures and two old mutable-SHA tests. The identity tests were upgraded
to assert immutable build metadata rather than weakened. An archive of the exact
starting SHA ran all 26 Earth Engine worker tests successfully. The worker failures
were therefore not classified as proven pre-existing failures. A later full run
passed **3,422 tests, 32 skipped, one existing Starlette/httpx deprecation warning**.
No assertions, timeouts, skips, retry counts or security gates were relaxed.

The frontend production build passed, including its integrated TypeScript check.
No frontend application source or browser-visible workflow was changed; additional
browser acceptance/typecheck/lint changes were not required for this backend lane.
Production static assets remain 2,997,356 bytes; largest chunk 608,747 bytes. The
existing strict 3,000,000-byte homepage ceiling and all route budgets pass.

Independent review was read-only and checked every requested safety area. Important
findings were fixed with regression evidence: mandatory artifact override and empty
runtime PASS bypasses; npm count/nested-severity and partial-findings handling;
imported deployment/configuration PASS labels; backend readiness/default origins;
TGOS omission; and inaccurate GSMMA/RIS registry contracts. Minor encoding, malformed
JSON and runtime kill-switch findings were also fixed. No unreviewed live probes or
provider calls from saved workflows were introduced. No unresolved Critical or
Important finding is accepted. The reviewer explicitly accepted the documented
unimplemented deployed-reader boundary, rather than treating it as closed evidence.

## Exact remaining blockers and owner actions

1. Build/deploy the reviewed clean commit through the approved release process;
   independently observe expected frontend/backend identities, release and environment.
2. Verify production backend categories, frontend build API/Supabase configuration,
   actual schema migration state, secret/IAM provenance and release bindings.
3. Supply accepted production WRA scenarios, GSMMA version, NLSC boundary hash/vintage,
   RIS month, PLVR releases and TDX snapshot/source age. Verify deployed activation,
   source publication/freshness policy, integrity and relevant geographic coverage.
   Basemap/WMTS/LANDSECT display does not establish numeric terrain acceptance.
4. Obtain provider legal/billing/restriction approval and bounded production-context
   probes. Retain required-but-unavailable providers as blockers; keep intentionally
   disabled/manual capabilities visible. No credentials/live authorization were supplied.
5. Audit the actual resolved Linux/Python 3.12 deployment image and frontend build
   dependency inventory; bind those receipts to deployed identities. Maintain the
   existing dev exception expiry and address machine-global findings separately.
6. Define authenticated deployed receipt readers before clearing the four currently
   unsupported deployed-evidence categories. Run Final Production Acceptance v2
   separately, including every unrelated prior NO-GO blocker.

The software changes can be reviewed in a PR after local verification/review; this
does not authorize deployment, production acceptance or merge. This lane alone
does **not** make production GO.

## Original implementation verification table and changed-file inventory

The exact final results and inventory follow below; raw local verification output
is under ignored `.tmp/closure`, not embedded in Git as large artifacts.

| Verification | Result |
| --- | --- |
| Full Python suite | 3,422 passed; 32 skipped; one existing deprecation warning; 524.79 seconds |
| Final focused closure/provider/deployment regression | 127 passed; one existing deprecation warning |
| Frozen starting-SHA worker suite | 26 passed; 39.84 seconds |
| Frontend production build | PASS, including integrated TypeScript check |
| Production operations gate | PASS |
| Security/performance gate | PASS, including route budgets after production build |
| Release static contracts | PASS; initial contract-only invocation explicitly skipped tests/build |
| Final release gate `--skip-frontend-build` | PASS; fresh Python tests and all nine contracts PASS; frontend build already executed separately |
| Local provider-free smoke | PASS |
| Production frontend and route bundle budgets | PASS; 2,997,356 bytes total, 608,747 largest chunk |
| Production npm audit and full exception policy | PASS; expiry 2026-11-04 unchanged |
| Python backend and alternate runtime resolution audits | PASS; zero known findings after production/test split |
| Machine-global audit | BLOCKED; 26 findings preserved separately |
| Evidence collection and v2 consumption | Expected BLOCKED/nonzero collector exit; all five blockers retained; product_go=false |
| Repository hygiene and diff check | PASS |

Exactly **26 files** are changed in the single final commit:

```text
.dockerignore
.gitignore
Dockerfile.cloudrun
backend/api/routes_pilot.py
docs/operations/production-identity-provider-closure-v1-evidence.json
docs/operations/production-identity-provider-closure-v1-plan.md
docs/operations/production-identity-provider-closure-v1-release-evidence.json
docs/operations/production-identity-provider-closure-v1.md
docs/production-release-evidence.md
render.yaml
requirements-dev.txt
requirements.txt
scripts/collect_production_closure.py
scripts/generate_release_evidence.py
scripts/production_smoke.py
scripts/provider_acceptance.py
scripts/write_backend_build_identity.py
services/production_artifact_registry.py
services/production_closure.py
services/production_identity.py
services/provider_config_contract.py
tests/test_hosted_production_launch.py
services/runtime_dependency_evidence.py
tests/test_production_identity_closure.py
tests/test_production_provider_evidence.py
tests/test_runtime_dependency_evidence.py
```

Final independent reviewer verdict: no unresolved Critical/Important findings;
ready for PR after the required release gate. That gate subsequently passed.
The reviewer ran 43 tests without checkout writes and deselected three temporary
artifact/encoding writes; the complete 127-test implementer run covered them.
The final commit preserves this worktree and branch; no publication is authorized.

## Post-integration validation on PR #170

The cherry-pick of `95cbc7f74f26b344aff90ae46cf7ecf5a0b5c7a9` was completed on
`602830c8d4d405bb401afa902d5bf69f2c61066f`, preserving its intended commit message.
All three conflicts were resolved semantically. Only those three files were
staged for conflict resolution; no abort, reset, skip, push, merge or deployment
was performed. The branch remains one integration commit ahead of `origin/main`.
The final SHA is reported in the handoff, not embedded in its own commit.

| Post-integration verification | Actual result |
| --- | --- |
| Focused suites before cherry-pick continuation | 166 passed; one existing deprecation warning |
| Focused suites immediately after continuation | 166 passed; one existing deprecation warning |
| Final focused acceptance/identity/provider/closure/release suites, including review fix | 168 passed; one existing deprecation warning; 23.13 seconds |
| Runtime evidence and npm policy regression | 43 passed; 2.63 seconds |
| Final serial full Python suite | 3,492 passed; 32 skipped; one existing Starlette/httpx deprecation warning; 362.71 seconds |
| Fresh frontend production build | PASS, including TypeScript check; no frontend source files changed |
| Release gate `--skip-tests --skip-frontend-build` | PASS; all nine contracts passed; full Python and fresh production build executed separately above |
| Security/performance gate against fresh build | PASS; all six checks passed |
| Production operations gate | PASS; all six checks passed |
| Repository hygiene and diff checks | PASS |
| Provider-free closure collection and release consumption | Expected BLOCKED/nonzero collection; all five blockers retained; `product_go=false` |
| Independent final review | No unresolved Critical or Important findings |

The first post-integration full run overlapped the production build and focused
tests and preceded the npm review fix. It reported 3,487 passed, 32 skipped and
three failures: `test_failed_replacement_cleans_other_worker_and_all_pipes`,
`test_repeated_queued_cancellation_does_not_accumulate_executor_work_items`, and
`test_cancellation_before_executor_entry_returns_assigned_worker_slots`, all in
`tests/test_earth_engine_worker_pool.py`. The failures involved worker startup or
replacement under bounded deadlines. The unchanged isolated worker suite passed
all 26 tests in 39.95 seconds. The final full run then passed without competing
validation jobs. No worker implementation, assertions, timeouts or skips were
changed, and the initial failures are not asserted to be proven pre-existing.

Integration regression tests first exposed dropped closure input and a combined
scorecard GO despite blocked closure; both were fixed and verified. Static
comparison also confirmed that #170's categorical acceptance validator is
unchanged, every original hosted-test assertion survives, CLI options are unique,
and provider acceptance has one authoritative `run()` implementation.

Independent review found one Important npm evidence issue: an unsanitizable
package name could discard a critical advisory while the projection reported
PASS. The fix retains severity under a sanitized identity, requires zero invalid
entries for PASS, and leaves incomplete nonblocking reports UNKNOWN. Both
schema-valid regressions were observed failing before the fix and passing after
it. The reviewer independently verified the fix and accepted the final tree.
Its minor documentation suggestion was incorporated by labeling the earlier
verification narrative and table as original implementation results.

The existing committed JSON files remain original implementation snapshots; they
were not relabeled as current deployment evidence. Local integration logs and
JUnit results are under ignored `.tmp/closure/integration-*`. The existing
untracked `conflict-review.txt` is preserved and excluded from the commit.
All deployment/configuration/artifact/provider/runtime and #170 owner-control
blockers remain open. This integration does not make production GO.
