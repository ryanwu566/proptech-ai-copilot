# Commercial UI/UX v1 acceptance

This records the requested E10 scope and local validation. Browser checks used deterministic mocks, without consuming live-provider quota.

| # | Requested field | Result |
| --- | --- | --- |
| 1 | Starting SHA | 23a325e2db732fd63be477ad613973b56e4c97d1; matched origin/main and a clean worktree before changes. |
| 2 | Branch | feat/commercial-uiux-v1; implementation restricted to C:/Projects/proptech-commercial-uiux. |
| 3 | Main product UX | A property-led evidence workspace with calm section hierarchy, compact context, source rows, and subordinate methods. |
| 4 | Homepage | Address entry and one primary start action; optional official-transaction finder; repository-backed latest three cases; compact snapshot/privacy note. Animated demo hero and automatic onboarding removed from the visible home. |
| 5 | Global navigation | Shared compact brand, Home, Saved Cases, locale switcher and Methods disclosure. URL-native method links from cases; existing in-place tool actions from Home. |
| 6 | Case header | Wrapping address, identity state, active price basis, last save time, source details and shared snapshot save. Finance instead links to its existing save workflow. Storage failures replace prior success feedback. |
| 7 | Overview | Blockers/attention first, then known/unknown, readiness, Market, Location, Risk, Finance, freshness disclosure, next verification and secondary planning. Removed repeated identity/summary tiles. |
| 8 | Market | Price context, Market evidence, Valuation evidence, comparables, methodology. Market median and valuation remain separate. |
| 9 | Location | Desktop map and commute approximately 2:1, then POI and demographics. Google route and secondary transit evidence stay independent. Missing POI counts remain unavailable, not zero. |
| 10 | Risk | Agency/source-first evidence table before map, explicit data/result/coverage/limitations/next verification. Source column retains a readable minimum width. Satellite reference is an explicit secondary disclosure. |
| 11 | Finance | Active price, down payment and area, monthly mortgage and known housing subtotal, visible rate/term/down-payment assumptions, holding detail and missing costs. Down payment explicitly excludes acquisition costs. |
| 12 | Compare | Shared typography, alternating field rows, calmer borders and separator-based mobile rows. Preserves 2–4 cases and two-at-a-time mobile comparison, without ranking. |
| 13 | Report | White paper surface, bounded reading width, consistent tables and hierarchy. Frozen nine-section evidence report and native Print/Save as PDF preserved. |
| 14 | Advanced/Methods | Map, Valuation, Market, Terrain, TaxOracle, Aegis, identity methods, demo reference and accessibility utilities remain reachable; case planning remains secondary. |
| 15 | Typography | Existing E2 scale retained: 30px page titles (26px mobile), 20px sections, 14px body, 13px dense rows, 12px metadata and 28px primary metrics. Tabular numerals; values wrap. |
| 16 | Spacing | 32px desktop, 24px tablet and 16px mobile content padding; consistent section gaps; narrower case rail and simpler separators. |
| 17 | Contrast | Ten enabled text/action/status pairs measured against their actual token surfaces: 5.90–16.27:1, all AA for normal text. Does not claim a full assistive-technology certification. |
| 18 | Status language | Google and Satellite state labels, metadata headings and evidence boundaries use the existing four-locale runtime. Recent-case identity reads the current locale. Technical state values remain internal. |
| 19 | Warnings/banners | Removed universal shell warning and auto onboarding. Case/source-specific limitations remain next to their evidence; methodology and freshness use disclosures. |
| 20 | Card density | Removed fixed sidebar and repeated summary cards; plain Finance form sections and summary rows; recent cases use list separators. |
| 21 | Empty states | Compact address/task entry and repository states; Google unavailable/confirmation states use bounded panels; no large dashed preview placeholder. |
| 22 | Mobile navigation | Two-row compact global header; native keyboard-accessible Methods disclosure; one-row internally scrolling case navigation. Existing tools respond to ordinary clicks at 390/430px. |
| 23 | 390px behavior | All eight primary screens have no document overflow. Long address, case title and large amount wrap. 44px commercial touch controls; map height 280px; evidence tables scroll internally. |
| 24 | 1024px behavior | Usable compact case rail, readable tables, balanced map/commute columns, wrapping metric values and no overlapping dropdown or body overflow. |
| 25 | 1440px behavior | Bounded content, compact header, clear section hierarchy, aligned numeric rows and balanced map/evidence layouts. No visible demo hero. |
| 26 | Accessibility | Labelled required address entry, semantic headings/navigation, visible focus and skip link, native disclosure keyboard operation, Escape return to summary, aria-live save feedback, textual statuses and preserved opt-in narration. |
| 27 | Reduced motion | No decorative home animation. Existing reduced-motion overrides retained; commercial loading spinner disables animation under prefers-reduced-motion. |
| 28 | Print behavior | Global header/navigation hidden; complete nine-section report with sources and limitations. Long A4 PDF generated in Chromium and Chrome; print surface inspected locally. |
| 29 | API/provider preservation | No providers, routes, automatic Places/Routes calls or provider-prefetch added. Compare/Report remained at zero analysis calls. One Google iframe at a time; Street View explicit; workspace Satellite loads only after disclosure. |
| 30 | Semantic/trust preservation | E1–E9 models and math unchanged. Missing, unknown, no-match, unavailable, not-started, stale, snapshot and current retain distinct meanings; no overall score, ranking or recommendation. |
| 31 | Files changed | 41 files; exact paths listed below. Screenshots, PDFs and logs remain ignored local artifacts. |
| 32 | Shared components | New CommercialGlobalHeader and CommercialHome; existing AppShell/Topbar, context header/navigation, E2 tokens, evidence styles, Google/Satellite and journey presentation updated. No new UI library. |
| 33 | Tests added/changed | New commercial-uiux acceptance; Finance unsaved-result regression; updated routing, Google view-switch, locale/navigation/speech/Satellite and East/West journey entry; old homepage static contracts now assert the address-led entry. |
| 34 | Chromium results | 103 distinct scenarios passed across final case/UI, methods/locale/speech/Satellite, Google key modes and East/West Location checks. A4 long-print case also rerun successfully. |
| 35 | Chrome results | 100 distinct scenarios passed across final case/UI, methods/locale/speech/Satellite and browser-key Google checks. A4 long-print case also rerun successfully. |
| 36 | Responsive acceptance | Eight screens × three widths × two browsers; additional long address/large amount/four-language home checks at all three widths. Local screenshots inspected. |
| 37 | Print acceptance | Both browser projects passed long A4, hidden shell/controls, expanded sources/limitations, frozen-snapshot, invalid-identity print block and zero-provider contracts. |
| 38 | E3–E9 regression | All ten affected commercial browser suites covered routing, identity/address equivalence, save/reopen/concurrency, valuation prerequisites, Location/terrain context, source-specific unknowns, Finance, Overview, Compare and Report. Node contracts: 150/150; E2 foundations 12/12; monetary reliability 12/12; Google contracts 5/5; runner 1/1. |
| 39 | Lint | Passed with 0 errors. |
| 40 | Lint warning count | 24 unused-declaration warnings remain in existing/legacy code; no warning cleanup expansion. |
| 41 | Typecheck | Passed npm run typecheck; final production build also checks TypeScript. |
| 42 | Build | Passed Next.js 16.3.8 production and deterministic E2E builds; final release-quality gate runs the production build. |
| 43 | Production npm audit | npm audit --omit=dev --audit-level=high: 0 vulnerabilities. Minimal Next.js 16.3.6 → 16.3.8 patch; no new dependencies. Existing approved dev-only exception policy unchanged. |
| 44 | Release-quality gate | Passed all checks, including 2,966 Python tests (31 skipped, one Starlette deprecation warning) and the final production build. |
| 45 | Security/performance gate | Passed all six checks, including unchanged route bundle budgets. |
| 46 | Production operations gate | Passed all six existing checks; no production operation executed. |
| 47 | Independent review | Fresh read-only review followed by one bounded fix review. Final verdict approved: no residual Critical/Important findings. |
| 48 | Critical/Important findings | 0 Critical. Five Important fixed: cross-property assumptions, Finance save entry, storage failure feedback, dropdown stacking, readable source width. Two Minor fixed: mobile nav direction and current-locale identity label. Regression checks passed. |
| 49 | Bundle/performance impact | Baseline total static 2,957,431 bytes; final 2,982,022 bytes (+24,591 bytes, 0.83%). Largest chunk 607,349 → 606,799 bytes. Existing route budgets pass; no framework/icon/animation dependency added. No load-test or live provider performance claim. |
| 50 | Commit SHA | One bounded commit with message `feat: professionalize commercial ui and ux`; exact SHA recorded in the final delivery report. |
| 51 | git status --short | Post-commit result recorded in the final delivery report. |
| 52 | git diff --check | Passed before staging; final delivery also checks the committed tree. |
| 53 | Remaining non-blocking issues | 24 lint warnings; inherited secondary method/source metadata may retain its original language; live providers and exhaustive assistive-technology testing were outside deterministic UI acceptance. Historical legacy browser certifications outside the affected commercial/navigation suites were not rerun. |
| 54 | Safe to push/open PR | Ready for a scoped review/PR after these local gates. No push, merge or deployment performed; hosted/live-provider acceptance is separate. |
| 55 | Provider Closure after merge | May start as a separate task after E10 is reviewed and merged. This commit does not implement or certify Provider Closure. |

## Changed files

- `docs/commercial-uiux-v1-acceptance.md`
- `docs/superpowers/plans/2026-10-08-commercial-uiux.md`
- `frontend_next/app/design-tokens.css`
- `frontend_next/app/globals.css`
- `frontend_next/app/layout.tsx`
- `frontend_next/app/page.tsx`
- `frontend_next/components/app-shell.tsx`
- `frontend_next/components/commercial-global-header.tsx`
- `frontend_next/components/commercial-home.tsx`
- `frontend_next/components/evidence/evidence.module.css`
- `frontend_next/components/google-location-visual-context.tsx`
- `frontend_next/components/guided-journey/guided-property-journey.tsx`
- `frontend_next/components/guided-journey/journey-stage.tsx`
- `frontend_next/components/satellite-evidence.tsx`
- `frontend_next/components/topbar.tsx`
- `frontend_next/components/workspace/finance/finance-workspace.tsx`
- `frontend_next/components/workspace/location/location-view.tsx`
- `frontend_next/components/workspace/market/market-price-view.tsx`
- `frontend_next/components/workspace/overview/overview-view.module.css`
- `frontend_next/components/workspace/overview/overview-view.tsx`
- `frontend_next/components/workspace/property-context-header.tsx`
- `frontend_next/components/workspace/risk/risk-environment-view.tsx`
- `frontend_next/components/workspace/risk/risk-environment.module.css`
- `frontend_next/components/workspace/saved-cases-entry.module.css`
- `frontend_next/components/workspace/saved-cases-entry.tsx`
- `frontend_next/components/workspace/workspace-navigation.tsx`
- `frontend_next/components/workspace/workspace-shell.module.css`
- `frontend_next/e2e/commercial-finance-costs.spec.ts`
- `frontend_next/e2e/commercial-uiux.spec.ts`
- `frontend_next/e2e/commercial-workspace-routing.spec.ts`
- `frontend_next/e2e/google-browser-maps.spec.ts`
- `frontend_next/e2e/i18n.spec.ts`
- `frontend_next/e2e/market-insight-east-west-identity.spec.ts`
- `frontend_next/e2e/mobile-sidebar-navigation.spec.ts`
- `frontend_next/e2e/navigation.spec.ts`
- `frontend_next/e2e/satellite-evidence.spec.ts`
- `frontend_next/e2e/speech.spec.ts`
- `frontend_next/lib/experience-i18n.ts`
- `frontend_next/package-lock.json`
- `frontend_next/package.json`
- `tests/test_frontend_hero_intro.py`

## Verification notes

The first expanded browser run passed 176 scenarios and failed six Satellite cases because the test still selected a Chinese button after switching to English. The corrected Satellite suite passed 8/8. A subsequent overlapping production build temporarily invalidated browser artifacts; builds and browser checks were then serialized and affected checks rerun. Concurrent Python execution encountered worker timing failures; that worker suite passed 25/25 independently, and the final complete release gate was run alone. Gates and timeout policy were not weakened.

Logs, responsive screenshots and A4 PDFs are kept under `.local/e10/`; they are not part of the commit. The final delivery report records the exact commit SHA and post-commit Git checks.
