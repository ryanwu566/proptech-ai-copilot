# Commercial UX Dependency Matrix v1

**Status:** Final integration dependency and collision record
**Baseline branch:** `docs/commercial-ux-integration-v1`
**Baseline SHA:** `3f369fbccd6391c0af99995513488364367892b9`
**Observed `origin/main`:** `8d41b07eb64ac5e250cece37ac64db4d1fbdef2f`

This matrix is the operational companion to:

- `docs/superpowers/specs/2026-09-27-commercial-ux-master-architecture.md`
- `docs/superpowers/plans/2026-09-27-commercial-ux-master-implementation.md`

## 1. Approved source integrity

All required documents exist at HEAD and their blobs are byte-identical to the named approved source commits.

| Workstream | Approved commit | Integrated commit | Required files | Verification |
|---|---|---|---|---|
| Workspace Architecture | `bb4a160872a2e0bac1dbc28d757dc8f437572074` | `7edae3c` | workspace spec + plan | Exact blob match |
| Commercial Design System | `7cd763f0c894fe4b6e679b3c597dd0db20b7ae47` | `0d40ba3` | design-system spec + migration plan | Exact blob match |
| Commercial Product Language | `4ec8ff33364a60103f58a913a366309f46c7d312` | `c71d562` | language spec + copy migration plan | Exact blob match |
| Broker Commercial Pilot | `919cc3dbc0e92d10e21279a6e8c617b713b6b575` | `3f369fb` | pilot spec + acceptance checklist + observation sheet | Exact blob match |

## 2. Source-spec dependency matrix

| Decision area | Architecture | Design System | Product Language | Pilot / Acceptance | Integrated authority |
|---|---|---|---|---|---|
| Primary navigation | Five property views | Navigation is stable list/tab, not feature cards | Proposed six labels | Tests property workflow, not IA | Master architecture: five views |
| Compare | Cross-case action/route | Up to 3; mobile metric/case view | Factual differences; no winner | Reuse/commercial signal | Separate `/compare`, no ranking |
| Report | Case output route | Editorial/print layout | `物件分析摘要`; known/estimated/unknown | Client-shareability gate | Current-revision report route |
| Decision Summary | Overview synthesis | Findings/unknowns/action rhythm | Neutral decision wording | Client explanation | Top of Overview, no score |
| Property identity | Case/revision anchor | Compact header | Customer vocabulary and conflict wording | Wrong-property is critical failure | Browser-scoped Identity closure + local case fingerprint; not VNext/legal identity |
| State semantics | Independent evidence slices | Fixed semantic colors | Six integrated axes | Unknown-as-safe is NO-GO | E1 contract |
| Units | Explicit units | Tabular figures/alignment | Canonical zh-TW grammar/missing reasons | Unit error is measured | E1 formatter contract |
| Failure boundaries | Local per slice | Local async/message primitives | What/meaning/action copy | Controlled failure tasks | Domain-local recovery |
| Provenance | Progressive disclosure | Quiet metadata/evidence tables | Result/evidence/diagnostics layers | Source/date comprehension | Three-layer model |
| Mobile | Route/shell one scroll owner | Surface-specific responsive rules | Concise labels | 390 px acceptance | E10 gate |
| Commercial maturity | Architecture capabilities | Professional visual criteria | Trust language | Behavioral thresholds | MVP/Beta gates in master spec |

## 3. Engineering closure dependencies

All four observed closure branches currently descend from merge base `1095135b2ff16c2babddc9ab33b94c9f7bd3863c`; none is assumed merged into `origin/main`.

| Closure | Tip observed | Must settle | Blocks | Safe commercial work before merge |
|---|---|---|---|---|
| Geological Sensitivity | `39e6e723f3f14fbf99f2d7fb32d3e7235948b536` | Layer identifier, coverage/no-match/unavailable/freshness, artifact/runtime failure | E6 final risk mapping and acceptance | Generic state types, risk fixtures without response-shape assumptions |
| Valuation/Holding reliability | `dbc196a34a038e9493a17ee8ffc2181119ac9c66` | Null/malformed handling, monetary units, missing-cost semantics, validated values | E1 financial adapters, E4, E7, E8 financial findings, E9 financial comparison/report | Non-financial state/provenance types; isolated tokens |
| Commute closure | `f360e37dcae0bc29777daec8f2ab0236d082f25a` | Google/TDX independence, route evidence/provenance, stale clearing, failure states | E5, commute portions of E8/E9/E10 | Generic map frame and destination-agnostic UI primitive |
| Property Identity closure | `8da030f089dd806225989c66a795a98781bf05f6` | Browser journey anchor, provenance, saved context, switch invalidation, revalidation; explicitly not a durable VNext entity | E3 browser-case repository/header, safe report correlation, global cutover | E1 pure types; E2 isolated primitives |

Required integration order: Geological → Reliability → Commute → Identity. Rebase/merge and recertify each successor against the current main; do not treat branch tips above as permanent base SHAs.

## 4. Epic dependencies and merge gates

| Epic | Priority | Requires | Produces | May run with | Must wait for |
|---|---|---|---|---|---|
| E1 State/language/numeric contracts | P0 | Closure contracts inspected | Six axes, units, provenance, readiness adapters | Isolated E2 token work | Reliability for final financial mapping |
| E2 Design foundations | P0 | E1 semantic roles | Tokens and accessible primitives | E1 new-file work | None for tokens; closures before domain adoption |
| E3 Browser repository/routes/header | P0 | Identity + E1; E2 for final UI | Local case repository, revision/fingerprint, five `/cases/[caseId]` routes, header | Nothing touching `case-storage`/`closed-loop` | Identity merge |
| E4 Market & Price | P0 | Reliability + E1–E3 | Price basis and normalized market/valuation evidence | E5/E6 with strict file ownership | Root extraction owner committed first |
| E5 Location & Commute | P0 | Commute + E1–E3 | Shared location and route evidence | E4/E6 | Commute merge |
| E6 Risk & Environment | P0 | Geological + E1–E3 | Independent risk rows/map/checks | E4/E5 | Geological merge |
| E7 Finance & Costs | P0 | Reliability + E4 | Cash/monthly model, affordability separation, contextual tax | No `app/page.tsx` peer | Active price contract |
| E8 Overview/Save | P0 | E3–E7 | Findings/unknowns/blockers/actions and reusable case | None touching decision/readiness models | Normalized domain evidence |
| E9 Compare/Report | P0 | E3, E8, domain snapshots | Factual comparison and current-revision report | Isolated print CSS may start late in E8 | Case snapshot schema |
| E10 Entry/Mobile/Acceptance | P0 | E1–E9 | Three entries, global cutover, release gate | None touching shell/root | All P0 domain work |
| E11 Advanced evidence/diagnostics | P1 | E10 + pilot need | Expert/support detail | E12 if files do not overlap | MVP acceptance |
| E12 Pilot refinements | P1 | Six valid sessions | Evidence-backed refinements | E11 by ownership | Pilot review |
| E13 Legacy removal/expansion | P2 | Stable release, zero consumers, repeated-use proof | Cleanup or separately specified expansion | None on shared shell | Post-pilot decision |

## 5. Real file and component conflict map

Conflict levels reflect current files plus observed closure branch diffs.

| File / component | Likely branches/epics | Level | Collision reason | Recommended sequencing / owner |
|---|---|---:|---|---|
| `frontend_next/app/page.tsx` | Reliability, Commute, Identity, E4, E7, E10 | HIGH | 1,042-line router, state store, event bus, Tax/Market/Map/Valuation composition | Merge closures sequentially; E4 owns domain extraction; E7 owns Tax extraction; E10 alone owns root cutover |
| `frontend_next/lib/closed-loop-journey.ts` | Reliability, Commute, Identity, E1, E3 | HIGH | Address/valuation/price invalidation and shared journey state | Merge closures in order; E3 ports final rules into repository; no parallel edits |
| `frontend_next/lib/case-storage.ts` | Commute, Identity, E3, E8, E9 | HIGH | Browser-local compacted case, events, new identity/route persistence | Identity merges after Commute; E3 adapter first; E8 save UX next; E9 reads normalized snapshots only |
| `frontend_next/lib/property-case.ts` | Reliability, Commute, E1, E8, E9 | HIGH | Mixed readiness, finance, evidence summaries, current missing/zero semantics | Closures first; E1 adapter; E8 synthesis; deprecate rather than broad rewrite |
| `frontend_next/lib/api.ts` | Reliability, Commute, geological frontend integration, E4–E7 | HIGH | Shared response types/client functions | Engineering closures own schemas; commercial epics consume, not redesign |
| `components/guided-journey/location-market-stage.tsx` | Commute, Identity, E5, E10 | HIGH | Identity propagation, location/market/commute composition | Closures first; E5 avoids guided composition; E10 deprecates after route parity |
| `components/guided-journey/price-decision-stage.tsx` | Reliability, E4, E7, E10 | HIGH | Price basis and finance handoff | Reliability first; E4 establishes basis; E7 consumes; E10 deprecates |
| `components/guided-journey/decision-case-stage.tsx` | Identity, E8, E10 | HIGH | Case identity, summaries, save/reopen | Identity first; E8 provides Overview; E10 removes duplicate shell after parity |
| `components/holding-cost-calculator.tsx` | Reliability, E2, E7 | HIGH | Null/missing cost and unit behavior plus visual migration | Reliability → controlled adapter in E7 → visual adoption |
| Valuation result/visual files | Reliability, E1, E2, E4 | HIGH | Trust status, confidence, units, visual hierarchy | Reliability → E1 mapping → E4 view; E2 supplies primitives only |
| `frontend_next/lib/risk-summary.ts` | Reliability, E8 | HIGH | Weighted overall score and finance/risk inputs | Merge Reliability; E8 reuses facts only and removes primary overall score dependency |
| `frontend_next/lib/case-comparison.ts` | Reliability, E9 | HIGH | Ranking/score and financial inputs | Reliability first; E9 introduces new model before deprecating ranking |
| `components/case-comparison-panel.tsx` | E2, E9 | MEDIUM | Rank cards, wide tables, export | E9 owns semantic replacement; E2 only provides table/section primitives |
| `frontend_next/lib/property-comparison.ts` | E9 | MEDIUM | `topCandidateTitle` and score-led report | Replace with factual report model; compatibility for one release |
| `components/decision-report.tsx` | E2, E8, E9 | HIGH | Recommendation colors, duplicated synthesis, valuation gate | E8 establishes Overview semantics; E9 owns report route; old component retained until parity |
| `components/professional-workspace-shell.tsx` + CSS | Identity, E2, E3, E10 | HIGH | Separate technical IA, raw enums/IDs, feature gate/auth boundary | Preserve auth/read logic; E3 creates commercial shell; E10 cuts over only after contract tests |
| `components/app-shell.tsx`, `sidebar.tsx`, `topbar.tsx` | E2, E10 | HIGH | Global navigation, warning strip, focus behavior | E2 compatibility only; E10 exclusive global migration owner |
| `components/ui.tsx`, `product-ui.tsx` | E2 and all domains | HIGH | Shared Card/Badge/Button/state primitives | E2 lands adapters first; domains adopt without modifying primitive APIs in parallel |
| `frontend_next/app/globals.css`, `tailwind.config.ts` | E2, E10 | HIGH | Global cascade/tokens/responsive behavior | E2 owns tokens; E10 owns final responsive cleanup; no domain edits |
| Copy registries: `runtime-copy*`, `experience-i18n*`, `surface-copy.ts` | E1, E5, E6, E7, E10 | HIGH | Multiple authorities and four-locale parity | E1 defines keys/adapters; domains contribute isolated keys; E10 performs consolidation/parity |
| `location-insight.tsx`, `map/geo-map.tsx` | E2, E5 | MEDIUM/HIGH | Local geocode, map state, raw units | E5 owns controlled integration; E2 primitives are imported, not edited here |
| `commute-route-card.tsx`, `commute-livability-card.tsx` | Commute, E5 | HIGH | Closure replaces provider/failure/provenance behavior | Commute must merge first; E5 wraps final components |
| `terrain-risk-analysis.tsx` | E2, E6 | HIGH | Monolithic UI and independent provider states | Geological backend contract first; E6 owns presentation split |
| `terrain-cadastral-evidence.tsx`, terrain map | E2, E6, E11 | MEDIUM | Map/detail/provenance | E6 primary view first; E11 advanced detail only after MVP |
| `loan-calculator.tsx`, loan visuals | E2, E7 | MEDIUM | Controlled state, explicit units, hierarchy | E7 owns domain behavior adapter; E2 provides primitives |
| `taxoracle-presentation.ts` and Tax page-local code | E1, E7 | HIGH | Rule IDs/API language, contextual placement, root extraction | E1 contract first; E7 extraction/migration; no separate page edit |
| `property-case-readiness.ts`, `workflow-status.ts` | E1, E8 | HIGH | Universal readiness/object-presence completion | E1 defines named readiness; E8 migrates consumers |
| `valuation-share.ts` and print/report components | Reliability, E1, E9 | HIGH | Units, static copy, duplicate report outputs | Reliability/E1 formatters first; E9 owns canonical report/print |
| `frontend_next/app/workspace/[caseId]/page.tsx` | VNext regression only | HIGH boundary | Existing UUID validation, feature gate, auth, and `workspaceId`/`propertyId` contract | Commercial epics do not modify, nest, or redirect it; future migration needs a separate approved contract |
| `frontend_next/app/cases/[caseId]/layout.tsx` + section routes | E3–E10 | HIGH | New commercial shell and five route-owned views share case context | E3 creates shell/routes; one route owner per domain; E10 alone performs entry cutover |
| `frontend_next/app/cases/[caseId]/page.tsx`, `property-case-command-center.tsx` | E3, E8, E10, E11 | MEDIUM | Existing local command center and professional planning boards | E3 adapts route; E8 selects reusable parts; E10 entry links; advanced boards remain secondary |

## 6. Shared-hotspot ownership rules

| Hotspot | Sole owner phase | Parallel branches must do |
|---|---|---|
| Root `app/page.tsx` extraction | E4 then E7; final cutover E10 | Create domain views and request an integration commit; do not patch root independently |
| Global shell/navigation | E10 | Consume route contracts; do not change sidebar/topbar in domain PRs |
| Design primitives/tokens | E2 | Import stable primitives; propose API changes back to E2 owner |
| State/unit/provenance types | E1 | Map domain outputs through adapters; do not fork equivalent enums |
| Case repository/invalidation | E3 | Use repository interface; no direct local/session storage or window events in new views |
| Locale key consolidation | E10 after domain keys land | Add scoped keys with parity; do not delete overrides in parallel |

## 7. Merge-sequencing matrix

| Sequence | Branch | Base requirement | Merge proof |
|---:|---|---|---|
| 1 | `docs/commercial-ux-integration-v1` | Review approval; no merge during this task | Exactly three reviewed integration documents; docs checks pass |
| 2 | `feat/geological-sensitivity-etl-v1` | Main containing approved #1 | Geological artifact/provider/runtime tests |
| 3 | `fix/valuation-holding-reliability-v2` | Main containing #1–2 | Financial service/frontend reliability tests; units/null semantics |
| 4 | `fix/commute-production-closure-v1` | Main containing #1–3 | Route/provider independence and workflow state tests |
| 5 | `feat/property-identity-production-closure-v1` | Main containing #1–4 | Browser-anchor contract/UI, full property-switch invalidation, saved-context tests |
| 6 | `feat/commercial-state-contract-v1` | Main containing all closures | State/unit/provenance/readiness contract tests |
| 7 | `feat/commercial-design-foundations-v1` | Main containing #6 | Token/primitive accessibility tests; no broad page diff |
| 8 | `feat/commercial-workspace-foundation-v1` | Main containing #6–7 | Browser repository, `/cases` routes, header, VNext-boundary, Back/Forward tests |
| 9 | `feat/commercial-market-price-v1` | Main containing #8 | Market/valuation parity and independent failure |
| 10 | `feat/commercial-location-commute-v1` | Main containing #8–9 or isolated ownership agreement | Location/route/map/mobile tests |
| 11 | `feat/commercial-risk-environment-v1` | Main containing #8–10 or isolated ownership agreement | Layer truth table, partial failure, map/table tests |
| 12 | `feat/commercial-finance-costs-v1` | Main containing #9–11 | Finance unit/null/invalidation/tax isolation tests |
| 13 | `feat/commercial-overview-save-v1` | Main containing all domain views | Overview model and save/reopen acceptance |
| 14 | `feat/commercial-compare-report-v1` | Main containing #13 | No-rank compare and print report tests |
| 15 | `feat/commercial-entry-acceptance-v1` | Main containing all P0 epics | Full build/E2E/mobile/a11y/language/visual gates |

## 8. Acceptance prerequisites by release label

| Prerequisite | Internal demo | Limited pilot | Commercial MVP Pilot Ready | Commercial Beta candidate |
|---|---:|---:|---:|---:|
| Four engineering closures merged and recertified | Required for claimed domains | Required | Required | Required |
| Same-property identity and invalidation | Required | Required | PASS | Sustained, zero critical incidents |
| Explicit units and missing != zero | Required | Required | PASS | Sustained |
| Local provider failure | Demonstrated in fixtures | Supported cases documented | PASS across core domains | Operationally reliable |
| Save/reopen | May be browser-local and disclosed | PASS for supported browser | PASS and observed pilot reuse | Repeated multi-week reuse |
| Compare | Optional demo if honest | Supported 2 cases | PASS for 2–3, no rank | Repeated correct use |
| Report | Print preview | Supported format disclosed | Client-readable PASS | Used/shared in repeated workflow |
| 390 px and accessibility basics | Primary path usable | PASS for supported flow | PASS all primary workflows | Regression monitored |
| Hosted acceptance | Smoke | No core FAIL; partials documented | All core sections PASS | Repeated release evidence |
| Broker behavioral evidence | Not required | Early directional evidence | Pilot thresholds pass | Multi-week repeat-use proof |
| Provider/support burden | Known limitations | Named contingency | Acceptable controlled-pilot burden | Operationally acceptable |

## 9. Release-blocking invariants

Any of the following blocks MVP regardless of schedule or visual quality:

- Wrong-property evidence is presented as current or used in a client explanation.
- No-match, no-coverage, unavailable, stale, or not-assessed evidence appears safe/low-risk.
- Missing financial inputs or costs appear as zero.
- A malformed/unvalidated valuation is used as a trusted price basis.
- Compare ranks or recommends a property through an opaque score.
- A report mixes case revisions or omits the known/estimated/unknown distinction.
- A local provider failure destroys unrelated valid evidence or the entire workspace.
- Primary UI exposes confidential data, credentials, raw payloads, or unsafe diagnostic detail.
- 390 px layout blocks entry, save/reopen, comparison, report, or the primary action.

## 10. Integration readiness summary

| Question | Answer |
|---|---|
| Are the four documentation workstreams compatible? | Yes, after the master conflict resolutions; Compare/Report placement was the only material IA contradiction |
| Which closures must merge before commercial page work? | All four for full P0; specific gates are listed in §3 |
| What may safely start first? | E1 pure contracts and E2 isolated token/primitives; merge them only after closure-contract review |
| What must not start yet? | E3 browser-case shell before Identity; E4/E7 before Reliability; E5 before Commute; E6 before Geological; E10 before all P0 domains |
| Highest-risk files? | `app/page.tsx`, `closed-loop-journey.ts`, `case-storage.ts`, `property-case.ts`, `api.ts`, guided stages, shared UI/copy/global CSS |
| Can commercial domains run in parallel? | E4/E5/E6 only after E2/E3 and only with exclusive shared-hotspot ownership |
| What remains intentionally unresolved? | No browser-local commercial v1 architecture blocker. Closure merge SHAs and pilot findings remain future evidence; VNext migration is P2 and requires explicit ID mapping, auth, redirect, and durable-data contracts |
