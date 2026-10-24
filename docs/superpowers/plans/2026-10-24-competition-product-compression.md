# Competition product compression implementation plan

> Execute inline with superpowers:executing-plans. The user's supplied final-implementation brief authorizes implementation, one commit, push and one Draft PR; no merge or deployment.

**Goal:** Address → Confirm Location → Build pre-viewing pack → existing Overview / Brief → Compare → Report.

**Architecture:** Compress presentation and navigation around existing saved evidence. Keep Overview's model, Demo A/B installer and comparison notice, Report core, acquisition contracts and all persistence schemas.

**Tech stack:** Existing Next.js / React / TypeScript, native Node tests and focused Playwright.

## Inspection before editing

Origin/main and initial HEAD: `c0688a767b1ccdfad7d578186675c6e414b080e7`. Clean linked worktree on `feat/competition-product-compression-v1`. Inspected merged #224 presentation / workspace shell and #226 trust closure, current home, Overview, Decision Room, Compare, Report entry/core, Demo installer/notice and footer navigation. #227 browser timeout is still 75 minutes.

| Finding | Classification | Safe action |
| --- | --- | --- |
| Complete demo installs A/B and opens Overview | Already solved | Preserve installer and CTA |
| Demo A exposes one-click comparison with B | Already solved | Preserve DemoCaseNotice; no duplicate CTA |
| Overview known / unknown / attention, four domains and checklist | Already solved | Reframe existing title/intro as Brief, retain evidence |
| Risk coverage, no-match and affordability trust defects | Stale finding after #226 | No domain/model changes |
| Localized overview, mounted frame and reduced-motion handling | Stale finding after #224 | Reuse existing behavior |
| Three-page Report and Compare → Report handoff | Already solved | No report redesign |
| Evidence footer defaults to Scenarios | Still real | Market → Location → Risk → Finance → Overview → Compare |
| Compare under Tools; Decision Room under outputs | Still real | Brief, evidence, outputs, collapsible Tools |
| Resume competes with two main home actions | Still real | Text action; retain all routes |
| Decision Room history/evidence detail dominates default view | Still real | Existing disclosures for saved evidence/history, retain unresolved items and gaps |
| TrustEstate vs repository identity | No bounded naming defect | Keep product and repository naming |

## Constraints and review focus

- No new providers, models, dependencies, schemas, domain arithmetic, infrastructure or deployment.
- Navigation must not imply completed analysis or automatically run evidence queries.
- Location is both confirmation and commute evidence: unconfirmed cases must keep confirmation visible before Market; confirmed cases proceed to Risk after Location evidence.
- Tools disclosure opens on direct tool routes, remains keyboard accessible, fits the existing one-row mobile strip and retains active-link scrolling.
- Demo comparison uses existing A/B action; real cases still require explicit case selection.
- Unknown/unavailable/no-match semantics and saved evidence remain visible in Overview/Report.
- Changed copy covers zh-TW/en/ja/ko; affected navigation/home at 390/430; reduced motion.

## Tasks

- [x] Update native navigation tests first; prove failure for the new evidence progression and initial Location handling.
- [x] Implement pure progression in `lib/navigation/model.ts`, context-aware footer in `components/navigation/case-workflow-handoff.tsx`; no readiness inference or writes. On confirmed Location before any Market query, the existing Market route is also presented as “Build pre-viewing pack”; it never runs analysis automatically.
- [x] Reorganize `components/workspace/workspace-navigation.tsx` and its existing CSS/copy. Keep Overview nav label for route continuity; use the page eyebrow/intro to explain Brief.
- [x] Demote Home resume and replace catalogue-style helper copy with the address → evidence → Brief → Compare → Report framing in four locales.
- [x] Collapse Decision Room saved-evidence/history via existing DetailsDisclosure; preserve all editable workflows and unresolved evidence gaps. Preserve saved-evidence hash links by revealing their enclosing disclosure.
- [x] Update affected browser expectations and add one focused compression spec for locale/mobile, tool disclosure, unknown states, demo comparison and Report entry.
- [x] Run focused native/domain tests, typecheck, lint, production E2E build and affected browser specs with one worker. Never run the full local matrix or loosen assertions.
- [ ] Review full diff, record evidence, create one feature commit, push, open one Draft PR and inspect fresh SHA-matched remote CI. Keep Draft; no merge/deploy.

## Execution evidence

- Native navigation red: 2 expected failures (`scenarios` was still the next step); green: 5/5.
- Focused native navigation, Overview model/presentation, Demo A/B, Compare brief, Report core, risk evidence and finance: **120/120 passed**.
- `npm run typecheck`: exit 0.
- Independent read-only review found a hidden Tools link in an older browser test; updated the test to open Tools first. Also synchronized pulse dots after pathname changes so the remounted Decision Room link retains its state.
- Local validation is serial due observed physical-memory pressure. No full local browser matrix, retry/worker/assertion loosening or workflow changes.
- `npm run lint`: exit 0; 23 existing warnings in unchanged files, no errors. After the mobile fix, focused ESLint on `components/workspace/workspace-shell.tsx` also exited 0.
- `npm run build:e2e`: exit 0, including fresh TypeScript checking. Rebuilt successfully after the mobile correction (compile 8.4s, TypeScript 11.9s).
- New `product-compression.spec.ts`: **11/11 passed**, covering four locales × 390/430, reduced motion, two Home buttons, unknown evidence, Tools keyboard access, demo A/B comparison and Report entry, evidence progression and saved-evidence hash links.
- Existing focused suite: **116/118 passed initially** across navigation, discoverability, case shell, Home start, location confirmation, Decision Room and three-page Report. The two failures reproduced a new nested-disclosure offset bug on direct Decision Room entry at 390/430. Fixed the rail calculation using viewport rectangles rather than nested `offsetLeft`; retained all original assertions. Independent review confirmed the correction.
- Fresh rebuilt rerun of the full case-shell spec plus compression spec: **18/18 passed**, including both formerly failing cases. No unresolved local failures.
- Physical Report checks passed for five zh-TW cases and en/ja/ko: exactly three core A4 pages; appendix starts on page four. All four locales also passed 390/1024/1440 print-overflow and unknown/stale/not-a-valuation checks.
- Browser commands used `--project=chromium --workers=1 --retries=0`. The full local release matrix was not run. Remote CI remains the authoritative heavy regression gate after push.

## Final judge journey

Start with one address → confirm location → “Build pre-viewing pack” opens existing Market → Location / commute → Risk → Money → existing Overview (Pre-viewing Brief) → Compare → Report.

Complete-demo shortcut: Home's existing complete-demo action → Demo A's real Brief → existing single A/B comparison action → case Report. Decision Room and Scenarios remain optional Tools. No ranking/winner semantics are added.

## Exact changed files

Presentation and navigation:

- `frontend_next/app/home.css`
- `frontend_next/components/commercial-home.tsx`
- `frontend_next/components/decision-room/decision-room.tsx`
- `frontend_next/components/navigation/case-workflow-handoff.tsx`
- `frontend_next/components/workspace/location/location-view.tsx`
- `frontend_next/components/workspace/workspace-navigation.tsx`
- `frontend_next/components/workspace/workspace-shell.module.css`
- `frontend_next/components/workspace/workspace-shell.tsx`
- `frontend_next/lib/home-start-copy.ts`
- `frontend_next/lib/navigation/model.ts`
- `frontend_next/lib/workspace/overview-presentation.ts`
- `frontend_next/lib/workspace/workspace-navigation-copy.ts`

Verification and delivery record:

- `frontend_next/lib/navigation/model.test.ts`
- `frontend_next/e2e/product-compression.spec.ts`
- `frontend_next/e2e/case-shell-continuity.spec.ts`
- `frontend_next/e2e/decision-room.spec.ts`
- `frontend_next/e2e/discoverability.spec.ts`
- `frontend_next/e2e/helpers/commercial-navigation.ts`
- `frontend_next/e2e/location-confirmation.spec.ts`
- `frontend_next/e2e/navigation.spec.ts`
- `docs/superpowers/plans/2026-10-24-competition-product-compression.md`
