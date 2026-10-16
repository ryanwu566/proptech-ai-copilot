# Navigation & Discoverability v1 Implementation Plan

**Goal:** Connect existing product routes through coherent, accessible navigation.
**Architecture:** Static route metadata and localized entry copy; native disclosure;
case chooser and contextual workflow links using existing case storage only.
**Tech stack:** Next.js, React, TypeScript, Node test runner, Playwright.
**Spec:** ../specs/2026-10-16-navigation-discoverability-v1.md

## Constraints and execution
Implement inline in the supplied worktree. The user's implementation request supplies
the scope and authorization. Retain one local commit as requested. No migration,
provider logic changes, expensive auto-refresh, unavailable AI action, dependency
addition or budget increase. Keep full workflow copy and implementations route-local.

## Review focus
- Hostile/unknown next query must never become an external or invented destination.
- Missing/deleted/corrupt cases must never silently select another case.
- Escape, Tab exit and route changes must leave predictable keyboard focus.
- Locale switching must preserve current path, case and comparison query.
- Narrow layouts and long translated labels must not overflow the document.

## Tasks
1. Add failing navigation model tests for inventory, filtering, destination safety,
   encoding and next steps. Run red; implement lib/navigation/{model,copy}. Run green.
2. Update commercial-global-header with grouped/searchable navigation and responsive
   CSS; retain method buttons and accessibility controls. Add browser coverage for
   touch, keyboard, locale and no analysis requests. Preserve tool/workflow deep links
   and browser back/forward in app/page.tsx.
3. Add capability orientation to CommercialHome, preserving existing recent-case
   diagnostics. Update SavedCasesEntry with a localized allowlisted section chooser
   and actionable empty states. Test real local rows and blocked/malformed storage.
4. Group the case rail and add small case workflow handoffs, including standalone
   Decision Room, Commute and Report routes. Add comparison-to-report links without
   changing projections, identity guards or repository writes.
5. Run focused and existing commercial browser suites on Chromium and Chrome with
   retries=0, unit suites, typecheck, lint, ordinary production build and unchanged
   route/global gates. Perform an independent UX/accessibility/code review, address
   findings and record exact acceptance results before the single local commit.

## Execution ledger
- Base verified against fetched origin/main and ls-remote; existing linked worktree
  reused. No AGENTS.md found in workspace or C:/Projects.
- Design choice: a native product disclosure plus persistent primary links avoids
  introducing a command-dialog dependency or focus trap. Search is local filtering.
- Design choice: use actual local recent cases already maintained by Home; do not add
  a second history store or persist user-entered search text.
- Tasks 1–4 implemented: grouped/filterable entry UI, safe case chooser, localized
  empty/recovery states, URL-aware tool/workflow entry, and contextual output links.
- Initial verification: 206 workspace/evidence/design/navigation Node tests and 51
  focused Python route/commercial tests passed. Initial Auth checks hit incomplete
  dependency extraction. After recovery, the expanded suite passed all 242 tests,
  including Auth/account race coverage. Route measurement's 17 Node tests also pass.
- Independent static review identified chooser recovery, internal tool history and
  property workflow focus gaps. Fixed those and the follow-up guided Map/Tax paths;
  added regression coverage. Final acceptance below records browser/layout results.
- Setup ruling: the memory-constrained host stalled npm extraction and checks saw
  incomplete dependencies. Stopped only owned processes. A serial cache extractor
  in ignored .tmp verifies every package archive against the unchanged lockfile
  before extraction. No dependency versions, application configuration or budgets
  are changed by this fallback. Final checks must use the recovered pinned modules.
- First production-mode browser build passed. Typecheck passed; lint exited zero
  with 23 existing unused-symbol warnings. First Chromium run, retries=0: 15 passed,
  one meaningful red regression exposed missing-case skip-link focus. Recovery
  views do not all carry main-content IDs; the shared skip handler now locates and
  focuses the actual main element without changing repository/provider behavior.
- Visual review at 390 and 1024 confirmed contained layout and visible focus.
  Added localized descriptions to retained method names, with aria-describedby,
  to make legacy English tool names understandable without changing their names.
- Focused Chromium + Chrome run, retries=0: missing-case skip link passed in both.
  Keyboard address submission exposed a second real focus gap in both: the stage
  opened while focus remained outside it. Explicit starts now focus the active
  stage heading; the generic property entry still focuses its workflow heading.
  A small ref prevents the general entry effect from overriding that destination.
- Locale audit found preference/My Places naming drift in the new copy. Extracted
  the existing four preference titles into a tiny entry catalogue, preserving the
  editor's exact output, and reused canonical entry catalogues in navigation.
  The locale/viewport browser matrix now searches these actual feature names.
- Production layout audit: a 390px probe with a valid, unbroken local case title
  reproduced document overflow in Saved Cases. Added inherited wrapping to the
  case article. A local-only regression covers chooser and comparison at all four
  widths, suitable for the final ordinary production build as well as E2E builds.
  The combined configured-build regression run keeps using its immutable build;
  the final CSS change will receive a separate production-build layout check.
- The broader regression run exposed a guide focus integration issue: closing the
  product menu while the modal owns focus hides its original opener. On guide close,
  reveal only the opener's disclosure ancestors, restore focus and bring it into
  view. A keyboard completion test reproduced the failure before this fix. The
  guide test must explicitly reopen navigation after using the external locale
  control, since leaving the menu intentionally closes it.
- One existing Commute loading assertion missed its 100ms mock-response window.
  The failure snapshot showed correct completed results. Replace that arbitrary
  timer with a response barrier released in finally after pending-state assertions;
  retain completion, storage, case-isolation and provider-count coverage. These
  focused test adjustments run only after the combined baseline run finishes.
- Combined baseline: 506/512 passed, zero skips, zero automatic retries (253/256 in
  each browser). All 186 commercial-pack tests passed. The other six failures were
  the guide integration (four), Commute mock window (one), and a Decision Room test
  failing to acquire its manual lock before any save (one). Foreground the lock
  owner in that fixture and preserve every concurrency assertion and timeout.
- Post-review focused verification collects 140 checks: navigation, touch at 390/430,
  four-width overflow, guide, synthetic example, complete My Places/Commute, and
  the affected Decision Room concurrency check, in both browsers with retries=0.
- Final verification: all 140 focused checks passed (70 per browser), no skips or
  retries. An ordinary production build then passed; its eight local layout checks
  passed in both browsers. The latest accepted coverage spans 546 distinct cases
  across the broad and focused runs, with no unresolved failures.
- Final standalone typecheck passed. Lint passed with zero errors and 23 existing
  unused-symbol warnings. The expanded 242-test Node suite passed again after the
  guide fix; 17 measurement regressions and 51 focused Python checks also passed.
- Final ordinary-build browser attribution and all 17 route budgets passed with
  existing ceilings. Home: 1,909,583 / 2,066,966 bytes. Total static: 3,290,584 /
  8,000,000; largest JS: 604,425 / 900,000. Security/performance contract gate passed.
- Independent final review found no additional concrete issues. Visual review
  covered mobile/desktop menu and long-title mobile Saved Cases/Compare. Actual
  touch handoffs passed at 390/430 in both browsers; keyboard, locale and recovery
  assertions passed. No manual screen-reader session is claimed.
- Tasks 1–5 are complete. The acceptance report is
  [navigation-discoverability-v1-acceptance.md](../../navigation-discoverability-v1-acceptance.md).
  Staged-source repository hygiene and staged diff checks passed before the
  single requested local commit. Only the intended 29 files are staged; provider,
  database, lockfile and budget registry paths remain unchanged.
