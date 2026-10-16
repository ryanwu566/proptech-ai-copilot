# Grounded Property Copilot v1 — acceptance report

Branch: `feat/grounded-property-copilot-v1`. The original verified base was
`59631992e03c05ff01e67fb691710c738fcc6d1b`; the completed Wave 3 commit was
`0d80c42cda92f4b3a9a5db21819b4cba11237122`.
For current-main integration closure, a clean working tree was recorded and that
commit was preserved at
`backup/grounded-property-copilot-v1-pre-current-main-0d80c42` before rebasing.
Fetching confirmed `origin/main` at
`194d17ce721fac5fa878db3c16c1c9233348bae5`. Its two added commits cover the
Wave 1B portable usage-database bootstrap and merge PR #189. Their nine changed
files have zero overlap with the 21 Wave 3 files. Rebase completed without
conflicts; the feature remains one local commit above main. No push, merge or
deployment was performed.

## Delivered behavior

- Entry from Saved Cases, the property workspace, Compare, Report and Decision
  Room. Conversation code loads only after explicit entry.
- Local conversation, suggested questions and follow-ups; active case/property,
  save date, saved evidence and explicitly unrequested live evidence indicators.
- Pure context assembly from the existing Saved Case evidence projection,
  context-bound saved Scenario Lab drafts and validated active-case Decision Room
  records. Scenario calculations reuse the existing calculator.
- Deterministic topic-based answers with `supported`, `partially_supported`,
  `insufficient_evidence` or `conflicting_evidence` contracts. Evidence, missing
  items, original source caveats, timestamps and case-scoped citations accompany
  answers. Asking versus regional median arithmetic does not establish valuation;
  known housing subtotals do not establish affordability or total ownership cost.
- UI copy in zh-TW, en, ja and ko. Original source names, values and caveats retain
  their language. Generated scenario labels and limitations are localized.
- Exact evidence-context and request-sequence binding, conversation reset on
  property/evidence changes, cancellation on unmount and foreign/stale payload
  rejection at the future provider boundary.

## Grounding and privacy boundaries

No active model provider was found: `services/llm_service.py` is a template
fallback. This wave adds no paid provider, network transport, credentials, API
endpoint, Admin access, remote workspace/tenancy path or database migration.
Neither migration 022 nor 023 is consumed.

The active conversation reads one case. Other Saved Cases, session-state results,
Decision Room note bodies, personal task ownership/history and raw configuration
are not included. Compare links open a named case's Copilot; selecting other cases
remains an explicit action in Compare. Report links open the case workspace and
show its saved date; they do not alter the report's frozen snapshot.

Saved observations never become live evidence. Opening, asking, following up,
changing locale and reopening are local operations. Refresh links lead to existing
evidence screens, where the user explicitly requests fresh data through existing
provider safeguards. Copilot itself does not refresh providers.

Future model input is a minimized structured selection: known references,
numeric evidence and states. Property/evidence prose and user instructions cannot
become system authority. Future model output can only echo the complete evidence
selection; extra keys, invented/foreign references or malformed output fail closed.
Model output cannot author claims, numbers, URLs, certainty or conflict resolution.

## Current-main integration verification

Fresh verification after the rebase onto `194d17c`:

| Check | Result |
| --- | --- |
| Workspace + Decision Room deterministic/unit suites | 210 passed, no failures or skips |
| Grounding/security/citation/context-isolation suite | All 19 passed, including an independent reviewer run |
| Focused Chromium E2E, retries=0 | 33 passed |
| Focused installed Chrome E2E, retries=0 | 33 passed |
| Saved Case / Compare / Report regressions | All 25 cases per browser passed within the focused run |
| Typecheck | Passed, exit 0 |
| Lint | Passed, zero errors and 23 existing warnings |
| Production build (`npm run build:e2e`) | Passed, compilation, TypeScript and static generation |
| Route asset budgets | All 17 routes passed after fresh production-browser measurement; coverage passed |
| Global asset budgets | 3,300,603 / 8,000,000 bytes total; 602,295 / 900,000 bytes largest JS |
| Relevant Python usage/quota/database safety/route/security suites | 152 passed, 68 database-gated skips, one existing deprecation warning |
| Disposable local PostgreSQL 17 bootstrap/security rehearsal | 63 passed, no skips |
| Disposable local PostgreSQL 17 usage/quota regression rehearsal | 99 passed, no skips; one existing deprecation warning |

The 66 browser cases passed in one uninterrupted invocation in 5.4 minutes.
The focused files were `grounded-property-copilot.spec.ts`,
`commercial-compare-report.spec.ts` and `commercial-overview-save.spec.ts`, with
both projects, `--workers=1 --retries=0 --timeout=120000 --max-failures=1`.
All four widths and locales, provider-free opening/asking/locale/reopening,
missing/conflicting evidence, citations, follow-up context and case switches are
covered. No retries, timeouts, assertions or performance ceilings were weakened.

The independent read-only integration review found no grounding/security issues
in the rebased application diff. It covered Case A to B leakage, stale evidence,
saved/live confusion, invented citations, model authority, prompt injection,
provider calls, credentials and tenant boundaries. Wave 1B bootstrap, rehearsal,
security, runtime guard and associated test files exactly match `origin/main`.
All application and test files from Wave 3 remain byte-for-byte identical to the
backup commit. Only this acceptance record changed during integration closure.
Browser-local records retain their existing trust model; future provider helpers
remain unused. No migration was added, modified or consumed by this feature.

The fresh context budget used 140 CPU ms for 100 assemblies, below the unchanged
1,000 ms ceiling; fixture serialization remained below 128 KiB. The browser
2-second answer budget passed at all four widths in both browser projects.
Route measurement used the existing network-blocking protocol and unchanged
deadlines/ceilings. Homepage measured 1,909,848 / 2,066,966 bytes; Compare and
Report each measured 1,132,258 / 1,301,212 bytes. The ad hoc console summary needed
an encoding correction for PowerShell's UTF-16 redirection; measurement and the
route gate themselves passed without changes or retries.

## Original Wave 3 verification

| Check | Result |
| --- | --- |
| Workspace + Decision Room native tests | 210 passed, 0 failed |
| Grounding/security cases within that suite | 19 passed |
| Typecheck | Passed, exit 0 |
| ESLint | Passed, 0 errors; 23 existing warnings in untouched files |
| Standard production build (`npm run build:e2e`) | Passed, Turbopack compilation + TypeScript + static generation, exit 0 |
| Chromium + Chrome, retries=0 | 200 unique cases passed, 100 per browser; aggregate runs documented below |
| Widths 390 / 430 / 1024 / 1440 and four locales | Passed |
| Saved Case / Compare / Report / Scenario / Decision Room regressions | Passed |
| Provider-free open / ask / locale / reopen / Compare / Report | Passed; zero attempted provider requests in guarded workflows |
| No migrations / no push / no deployment | Verified; no package, lockfile or build-config changes either |

Unit coverage includes isolation, failed/missing evidence, preserved conflicting
prices, populated POI/TDX invalidation after identity conflicts, saved versus live,
citation resolution, follow-up context, stale response rejection, foreign/stale
future-provider payload rejection, malformed model output and evidence injection.

Latest deterministic context budget: 100 assemblies used **63 CPU ms / 83.0
elapsed ms**; standard fixture serialization stayed below **128 KiB**. Browser
checks enforce a **2-second** response budget, lazy conversation loading and no
horizontal overflow at all four widths.

Browser timing measures the captured user click through the committed answer
inside the browser. The first diagnostic used driver round-trip time (2.431 s)
and was corrected to exclude automation scrolling/polling. A subsequent cold-load
attempt reached the default 30-second test deadline before hydration. Final runs
allow 120 seconds for a complete multi-step workflow and 30 seconds for initial
Copilot visibility, with **retries=0** and the response budget unchanged.

The combined final-build run passed 151 cases before a legacy Chrome Decision
Room workflow hit its file-level 60-second timeout, which overrode the explicit
120-second CLI setting. Targeted diagnosis also exposed inactive-tab notification,
input and native-lock scheduling assumptions. The test harness now honors longer
explicit project timeouts while keeping its default 60 seconds, waits for real
save completion/readiness, and foregrounds the acting tab. No application change,
mock storage/lock notification, removed assertion or automatic retry was used.

Coverage is aggregated honestly across invocations: 151 initial passes, the fixed
Chrome asking-price case, one remaining Chrome read-failure case, two remaining
Chrome lock/task cases, and the final 45 Chrome cases = **200 unique cases**. The
fixed lock/task cases also passed again in Chromium. The 45-case remainder exited
0. The corrected asking-price case then passed again in Chromium in 16.5 seconds,
and standalone typecheck exited 0. All invocations used **retries=0**; this was not
one uninterrupted green run.

Validation environment: an exact matching lockfile and installed versions were
verified before reusing local package files. An external dependency junction was
rejected by Turbopack; replacing it with local hardlinks resolved the filesystem
boundary without changing dependencies, the lockfile or build configuration.

## Independent grounding/security review

A separate fresh-context reviewer inspected authority, projection, state changes,
citations, privacy and network paths. No critical issue was found. Two important
issues were reproduced by failing tests and fixed:

1. Market-only and Decision-Room-only questions now retain both conflicting
   asking-price observations, each with its own citation.
2. Identity conflict/revalidation now invalidates saved POI and secondary transit
   observations rather than allowing them to support the changed property.

The minor generated-label issue was also fixed. The implementer additionally
reproduced and fixed stale/foreign answer leakage at future payload construction,
and whitelisted scenario revision inputs so additional JSON fields cannot survive
inside context metadata. Injection coverage includes literal malicious property
text and a saved commute-destination value; these remain data, never authority.
The final native suite covers all fixes. The reviewer performed static UI review
and direct Node reproductions; browser validation is performed by the implementer.

## V1 limits

This is a deterministic evidence assistant with bounded topic recognition and
safe calculations, not a general language model or purchase recommendation. It
does not infer missing zoning, parcel, ownership, valuation or safety facts. Saved
Scenario drafts that no longer match their property/evidence binding remain
unavailable. Decision Room progress remains user-recorded and cannot certify
official facts. Conversations are in memory and are not persisted.

## Reproduce validation

From `frontend_next` in PowerShell:

```powershell
npm run typecheck
npm run lint
npm run build:e2e
$copilotTests = @(rg --files lib/workspace -g '*.test.ts')
node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test --test-concurrency=1 @copilotTests lib/decision-room-store.test.ts lib/decision-room-case-adapter.test.ts
$copilotSpecs = @(
  'e2e/grounded-property-copilot.spec.ts',
  'e2e/commercial-compare-report.spec.ts',
  'e2e/commercial-overview-save.spec.ts',
  'e2e/evidence-checklist.spec.ts',
  'e2e/property-scenario-lab.spec.ts',
  'e2e/property-scenario-loading.spec.ts',
  'e2e/decision-room.spec.ts'
)
node e2e/run-e2e.cjs @copilotSpecs --workers=1 --retries=0 --timeout=120000 --max-failures=1
```
