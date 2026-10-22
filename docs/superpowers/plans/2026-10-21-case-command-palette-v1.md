# Case Command Palette v1 Implementation Plan

> Execution: implement inline in the supplied worktree; one final local commit, no push.

**Goal:** Global, deterministic case navigation and action discovery using saved browser state.

**Architecture:** A pure command projection consumes the current route, existing workspace projection, and validated Decision Room read. A standalone root-layout host subscribes to existing repositories. A native modal dialog provides combobox/listbox keyboard interaction and a mobile bottom sheet. All four locale catalogues are complete; no provider client or writer is invoked.

**Spec:** User attachment `29768f6e-a86e-42ad-b1d6-e899ff079145/Pasted text.txt` (Case Command Palette v1).

## Constraints

- Preserve commercial header, authentication, backend, providers, business models and formulas.
- Only navigate existing routes, open the existing tour, or focus existing explicit controls.
- Bundled Chromium only, workers=1, retries=0; do not run the full browser matrix.
- One local feature commit; do not push.

## Tasks

1. Add command-model tests first, verify RED, then implement projection, aliases, and four-locale copy. Use validated workspace identity, existing Risk verification actions, and open Decision Room item count. Location priority precedes Risk, then evidence-rich cases (saved summaries in at least three distinct domains). Current case destination receives a localized marker and follows other ordinary destinations. Global creation remains first on Home because it focuses the existing address field.
2. Add focused browser tests first, verify RED, then implement host, dialog, styles, and root-layout mount. Keep repository subscriptions active while mounted; fail closed for missing/corrupt cases and room state. Native modal supplies background inertness; explicit Tab cycle, initial search focus, Escape, arrows, Enter and restoration cover keyboard behavior. Opening over another modal is suppressed.
3. Verify targeted model/browser tests, four locales and 390/430px, zero provider requests across command destinations, typecheck and lint. Review changes, fix substantive findings, and create the single local feature commit.

## Interfaces

- `buildCaseCommands({ pathname, workspace, room, locale })` returns stable IDs, localized title/context, existing route href or tour action, and current-route marker.
- `filterCaseCommands(commands, query)` matches localized copy plus stable aliases; no remote search.
- Host reads via `createBrowserCaseRepository()` and `createBrowserDecisionRoomRepository()` only, using their subscriptions plus case-cleared events.

## Review focus

Corrupt/removed cases; changes from another tab including storage clear; active option disappearing during live updates; focus restoration after route changes; no automatic provider requests from destination pages.

## Verification

`node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test lib/command-palette.test.ts`

`npm run build:e2e` then `node e2e/run-e2e.cjs e2e/command-palette.spec.ts --project=chromium --workers=1 --retries=0`

`npm run typecheck` and `npm run lint`.

## Implemented files and responsibilities

- `frontend_next/app/layout.tsx`: mount the independent host inside the locale provider.
- `frontend_next/components/command-palette/command-palette-host.tsx`: route context, repository subscriptions, shortcut, trigger, navigation and existing tour entry.
- `frontend_next/components/command-palette/command-palette-dialog.tsx`: native modal, combobox/listbox, filtering, keyboard selection and focus lifecycle.
- `frontend_next/components/command-palette/command-palette.module.css`: design tokens, bounded scrolling, desktop dialog and mobile bottom sheet.
- `frontend_next/lib/command-palette.ts`: deterministic commands, priority and normalized alias search.
- `frontend_next/lib/command-palette-copy.ts`: complete zh-TW/en/ja/ko catalogue.
- `frontend_next/lib/command-palette.test.ts`: projection and search coverage.
- `frontend_next/e2e/command-palette.spec.ts`: targeted bundled Chromium coverage.
- `frontend_next/components/map/explicit-map.tsx`: localized, explicit basemap reveal; mounting the saved view does not request tiles.
- `frontend_next/components/workspace/location/location-view.tsx`: defer the existing basemap until requested.
- `frontend_next/components/workspace/risk/risk-environment-view.tsx`: defer the existing basemap until requested.
- `frontend_next/package.json`: targeted model and browser scripts.
- This plan: implementation and validation record.

## Integration notes

The confirmation action opens `/cases/:id/location`, where the existing location-find control lives. It does not click that control. Case data comes from the validated browser repository; open-item counts come from validated Decision Room records, counting each open item once. Missing, corrupt, removed, and wrong-case records expose only appropriate global navigation or generic room entry, without invented counts.

Both existing basemaps previously requested external tiles on route entry. Their new wrapper requires an explicit button press and resets when case/coordinates change. Resolver logic, Risk interpretation, saved evidence, finance formulas, Report business logic and the commercial header are unchanged.

An independent read-only review identified map loading, the confirmation destination and repeated Home-hash focus. These were addressed; targeted coverage exercises each behavior.

## Build environment notes

The shared Windows host experienced severe memory pressure. The successful normal Turbopack production build used `RAYON_NUM_THREADS=2`, `CIRCLE_NODE_TOTAL=2` and `NODE_OPTIONS=--max-old-space-size=2048`, with the repository E2E test environment. No build configuration changes are committed.

A webpack fallback was also attempted; it rejected existing global-only CSS module selectors in `components/evidence/evidence.module.css:127` and `components/workspace/workspace-shell.module.css:30`. Those unrelated styles were preserved. The normal Turbopack build compiled and passed its TypeScript check.

## Final validation — 2026-10-21

- Model/adjacent tests: **31 passed** (14 palette + 17 existing repository/room/navigation tests). Command: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test lib/command-palette.test.ts lib/decision-room-store.test.ts lib/decision-room-case-adapter.test.ts lib/navigation/model.test.ts`.
- Bundled Chromium: **35 passed**, **workers=1**, **retries=0**, in 3.5 minutes. Command: `node e2e/run-e2e.cjs e2e/command-palette.spec.ts --project=chromium --workers=1 --retries=0`. No full browser matrix was run.
- Twelve command-provider checks observed **0 automatic provider requests**. Case navigation preserved the exact saved-case storage value.
- All four palette locales passed at both **390px and 430px**, with no document/dialog horizontal overflow. Desktop, zh-TW 390px and Korean 430px screenshots were visually inspected; screenshots remain in ignored `frontend_next/test-results/`.
- Normal Turbopack production build: **passed**, including all static routes and its TypeScript check, using the memory limits above.
- `npm run typecheck`: **passed** (exit 0).
- `npm run lint`: **passed** (exit 0), **0 errors, 23 pre-existing warnings in unchanged files**; no palette warnings.
- `git diff --cached --check`: **passed**.
- All implementation tasks are complete. Integration is one local feature commit, without a push.

Automatic approval review rejected recursive deletion of the ignored `.palette-temp` dependency backup as “blocked by policy.” That scratch directory remains local; temporary setup helper files were removed.
