# Performance Budget v2

The route gate measures each route's client assets rather than assigning the
entire static build to every URL. Independent route chunks can grow without
changing homepage bytes. Required runtime, shared application chunks, CSS,
fonts and other requested static assets are counted once within each route.

## Measurement contract

The metric is the sum of file sizes for unique `.next/static` assets required
by a cold route load. It is uncompressed bytes, independent of gzip, browser
cache, response timing or HTTP transfer overhead. HTML and RSC responses are
not static assets and are outside this metric. Assets loaded only after an
explicit user action are outside initial-route measurement; the global limits
continue to protect all build output, including those assets.

Next's app-paths manifest identifies actual built routes. A complete eager
app-build manifest attributes route, inherited layouts and runtime assets;
client-reference manifests supply CSS when needed. Missing or malformed lists,
lazy-import manifests, conditional polyfills and CSS resources with `url()`
require browser measurement. References do not prove a conditional font, image
or lazy component is actually requested. Turbopack's client-reference graph
alone is therefore not treated as a complete loaded-asset graph.

The explicit browser fallback starts its own production server on a free
loopback port, verifies its build identity, and uses fresh Chromium contexts.
Two samples at each of 390 and 1440 pixels must have identical asset sets within
each viewport. The report takes their union. The existing synthetic E9 cases
populate Compare and the case sections, including rendered lazy maps. The
canonical case URL includes assets loaded during its redirect to overview.
Route destinations, fixture hydration and populated view markers must match.

Provider hosts, API requests, other origins, non-GET requests and route prefetch
are blocked before network access. No production records or credentials are
used. A 210-second internal deadline and 240-second hard deadline bound the
measurement; cleanup owns only the spawned server/browser process tree.

Evidence lives in ignored `.next/route-assets-v2.json` and is bound by SHA-256 to
the build ID, static file contents, server rendering artifacts, routing/build
manifests, measurement code and synthetic fixture. Rebuilding or changing any
of them invalidates cached requests. The analyzer and checker never start a
browser without `--measure-browser`; the release gate reads existing evidence.
Missing assets, incomplete/stale evidence and failed browser loads fail closed.

## Baseline and bounded headroom

The baseline was measured on 2026-10-12 from fetched `origin/main` commit
`8b1367a9117e2c8c762f0bad599bba94e9eca771` in an isolated detached worktree,
using its unchanged lockfile and ordinary production build. Main total static
was **2,974,397 bytes**; its largest JS chunk was **597,609 bytes**.
The JSON baseline stores the measured assets and toolchain provenance.

Homepage is strictest by permitted growth: **10%, capped at 200,000 bytes**.
All other route allowances are **20%, capped at 300,000 bytes**. The user selected
growth allowance as the strictness criterion because homepage currently loads
more initial assets than Compare and Preferences. The exact ceiling is:

```text
baseline_client_bytes + min(ceil(baseline_client_bytes * percent / 100), cap)
```

No global limit is raised. The previous fake homepage total ceiling of 3 MB is
replaced by a measured route ceiling of **2,066,966 bytes**.

| Route | Measured baseline bytes | Route ceiling bytes |
| --- | ---: | ---: |
| `/` | 1,879,060 | 2,066,966 |
| `/compare` | 1,084,343 | 1,301,212 |
| `/cases/[caseId]` | 1,084,343 | 1,301,212 |
| `/cases/[caseId]/overview` | 1,084,343 | 1,301,212 |
| `/cases/[caseId]/market` | 1,084,343 | 1,301,212 |
| `/cases/[caseId]/location` | 1,293,212 | 1,551,855 |
| `/cases/[caseId]/risk` | 1,281,707 | 1,538,049 |
| `/cases/[caseId]/finance` | 1,115,916 | 1,339,100 |
| `/cases/[caseId]/report` | 1,084,343 | 1,301,212 |
| `/preferences` | 874,779 (supplemental feature build) | 1,049,735 |
| `/cases/[caseId]/scenarios` | 1,114,869 (supplemental Scenario Lab build) | 1,337,843 |

Preferences is absent on pinned main. Its supplemental measurement comes from
`ec641ea9179458ae3e992c6b698c760bff2f887c`, using the same production protocol.
Scenarios is also absent on pinned main and on this preference worktree. Its
supplemental measurement comes from isolated, unchanged Scenario Lab commit
`a227a18b033c2f6078c2703988761bc1c6707d9f`, using its own lockfile, production
build and the same cold browser protocol. The populated scenario route was
measured directly; its ceiling is not borrowed from finance or the global total.
Absent feature routes report null measured bytes and `route_not_present`;
once present, they must be attributed and fit their own bounded ceiling.
Routes present on pinned main are required by the gate.

The global protections remain mandatory: all static files <= **8,000,000 bytes**,
largest client JS <= **900,000 bytes**. This includes unrequested assets,
unrelated routes and chunks loaded after user actions.

## Reproduce

Use the repository-pinned Node/npm toolchain and installed Python dependencies:

```text
npm ci --prefix frontend_next
npm --prefix frontend_next exec -- playwright install chromium --with-deps
npm --prefix frontend_next run build
node --test scripts/measure_route_assets.test.cjs
python scripts/analyze_next_bundle.py --measure-browser
python scripts/check_route_budgets.py
python scripts/check_frontend_bundle_budget.py
python scripts/security_performance_release_gate.py --json
python scripts/check_repository_hygiene.py
python -m pytest -q
git diff --check
```

`--root <path>/.next` on analyzer/checker supports isolated baseline builds.
The checker also accepts the prior `.next/static` argument for release-gate
compatibility. Both CLIs return nonzero when attribution or budgets fail.
Changes to baselines or allowances require measured, pinned evidence and an
explicit policy explanation; CI does not automatically ratchet ceilings up.

## Validation on this change

- Full Python suite: 3,685 passed, 32 skipped; one existing Starlette/httpx deprecation warning.
- Final focused route/security contract checks: 35 passed (including 25 route regressions).
- Browser network-policy and populated-view regressions: 4 passed.
- Ordinary production frontend builds: current preference branch, pinned main and pinned Scenario Lab passed.
- Final local production browser attribution: all present requested routes passed on all three builds; absent feature routes remained explicit.
- Current branch homepage: 1,898,873 / 2,066,966 bytes; Preferences: 874,779 / 1,049,735 bytes.
- Scenario supplemental route: 1,114,869 / 1,337,843 bytes.
- Current total static: 3,022,697 / 8,000,000 bytes; largest client JS: 597,609 / 900,000 bytes.
- Route budget gate, global bundle gate, security/performance release gate, staged repository hygiene and `git diff --check`: passed.

Review covered layout/CSS omission, stale rendering evidence, blocked API
navigations, populated fixture views and owned process cleanup. No frontend
product code, CSP, dependency audit policy or provider configuration was changed.

## CI measurement failure investigation

The exact Linux install/build/browser command reproduced a deterministic
`build_fingerprint` / `ValueError` / `build_changed_during_measurement` failure:
Next creates 12 response-cache files under `.next/server/route-cache/` during
the first production requests. Those files were incorrectly treated as build
inputs. Exclude only that runtime directory from the evidence fingerprint;
compiled server code, prerendered pages, manifests, static assets, and measurement
code remain fingerprinted. Regressions verify that runtime cache writes preserve
evidence while changes to prerendered output or compiled server code expire it.

Repeated cold runs also exposed a race in case-entry validation. They reproduced
`route_view_validation` / `Error` /
`unexpected_destination`: the observed path was still `/cases/[caseId]` when
the validator required `/cases/[caseId]/overview`. `networkidle` does not prove
that Next's redirect has completed. The measurement now waits at most 10 seconds
for that exact overview destination before applying the existing populated-view
selector and saved-fixture checks. A missing or wrong redirect still fails.

Measurement exceptions remain nonzero with empty route attribution. The analyzer reports
`failure_stage`, the Python and child exception types, `child_exit_code`,
`current_route`, and a sanitized `child_stderr_tail` capped at 1,024 characters.
Only allowlisted structural records from the child survive sanitization;
arbitrary stderr, exception messages, environment values, credentials, provider
payloads, and saved addresses are never forwarded. Stage progress survives hard
timeouts, and cleanup cannot replace an earlier measurement failure.

The route byte metric, two cold samples per viewport, viewport widths, populated
view checks, route budgets, and both global limits are unchanged. The PR build
contains Scenario Lab and explicitly reports `/preferences` as `route_not_present`
with unknown bytes; the Preference supplemental baseline is not a measurement of
this build. The historical validation figures above describe the earlier
isolated preference/Scenario builds.

Final Linux validation used the GitHub PR merge revision `58ba399d4cdb` against
main `e1d7f131c576`, with these fixes applied, Node 24.21.0 and Python 3.12:

- Exact clean npm install, Chromium install, production build, browser analysis,
  route/global budgets, security/performance gate, hygiene, and diff check passed.
- Node regressions: 11 passed; focused route/security/global Python: 43 passed.
- Full merge-revision Python: 3,703 passed, 32 skipped. Full branch Python:
  3,702 passed, 32 skipped. Windows verification after dependency installation
  and UTF-8 setup: 3,698 passed, 32 skipped.
- Case entry: 20 consecutive cold production runs passed after the redirect fix.
- Merge-revision homepage: 1,886,534 bytes; Scenario: 1,108,471 bytes.
- Preference: `route_not_present`, bytes unknown, never a zero-byte measurement.
- Total static: 2,999,166 / 8,000,000 bytes; largest JS: 602,354 / 900,000 bytes.
- Production npm audit and the existing audit gate passed without policy changes.
