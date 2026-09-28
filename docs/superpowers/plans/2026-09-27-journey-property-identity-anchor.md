# Journey Property Identity Anchor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a conservative browser-scoped identity anchor to the current property journey, preserve it through saved cases, flag conflicting reopened evidence, and prevent stale cross-property evidence.

**Architecture:** A pure TypeScript projection/reconciliation module derives a bounded `JourneyPropertyIdentityAnchorV1` from existing journey and Location Insight contracts. The closed-loop journey owns the anchor and clears it with dependent evidence on property changes; saved cases persist only its normalized projection; one reusable card exposes it in Location and Decision without invoking VNext APIs.

**Tech Stack:** TypeScript 5, React 19, Next.js 16, Playwright, Python/pytest regression suite

**Spec:** `docs/superpowers/specs/2026-09-27-journey-property-identity-anchor-design.md`

## Global Constraints

- The anchor is always named and presented as a journey/browser identity anchor, never a cadastral, government, legal, or durable VNext identity.
- Confidence describes address-level spatial consistency only and never confirms parcel, building, ownership, title, or legal boundary.
- Parcel and building default to `unavailable`, `restricted`, or `unresolved` without real evidence and never block address-level analysis.
- Reopened conflicting evidence preserves the stored anchor and marks it `needs_revalidation`; it is never silently overwritten.
- Persist only bounded normalized fields and provenance; no raw provider payloads, secrets, internals, or unsupported claims.
- Manual confirmation remains explicitly manual and never government-verified.
- Do not enable VNext flags/providers, mutate durable identity tables, change authentication, deploy, or alter production configuration.
- Use one final commit only: `feat: close property identity production workflow`.

## Review Focus

- Formatting-only address differences must not falsely mark a reopened anchor stale.
- Small coordinate precision changes within 100 metres must reconcile, while a material move must require revalidation.
- Missing/unavailable village evidence must not erase a previously stored village or falsely claim a conflict.
- Malformed saved anchors must fail closed without breaking saved-case loading.
- Changing only non-location valuation attributes must preserve identity while clearing only evidence whose existing rules require clearing.

---

### Task 1: Browser-scoped identity contract and reconciliation

**Files:**
- Create: `frontend_next/lib/journey-property-identity.ts`
- Create: `frontend_next/e2e/journey-property-identity-contract.spec.ts`

**Interfaces:**
- Consumes: `JourneyPropertyContext`, `LocationInsightResult`, and `VillageResolution` from existing frontend contracts.
- Produces: `JourneyPropertyIdentityAnchorV1`, `buildJourneyPropertyIdentityAnchor(input, options?)`, `normalizeJourneyPropertyIdentityAnchor(value)`, and `reconcileJourneyPropertyIdentityAnchor(stored, context, location, options?)`.

- [ ] **Step 1: Write failing contract tests**

Add tests asserting address-only projection uses `scope: "journey_browser_anchor"`, a `journey-browser-` ID, `low` confidence, conservative unavailable parcel/building states, and the non-authoritative limitation. Add resolved-location tests asserting normalized address, coordinates, city/district, NLSC village/code, bounded source records, and `high` or `medium` address-level confidence without promoting parcel/building.

- [ ] **Step 2: Run the contract tests and verify RED**

Run: `npm run build:e2e && node e2e/run-e2e.cjs e2e/journey-property-identity-contract.spec.ts`

Expected: FAIL because the module and contract do not exist.

- [ ] **Step 3: Implement the contract and projection**

Define exact bounded unions from the design. Implement `buildJourneyPropertyIdentityAnchor` with an injectable `now` and `idFactory`, normalization of accepted address evidence, bounded provenance, independent parcel/building defaults, and domain-specific confidence.

- [ ] **Step 4: Run the contract tests and verify GREEN**

Run the command from Step 2. Expected: all contract projection tests PASS.

- [ ] **Step 5: Write failing normalization and reconciliation tests**

Test saved-contract validation, formatting-only address equivalence, coordinate agreement within 100 metres, coordinate disagreement beyond 100 metres, normalized-address disagreement, village-code disagreement, unavailable fresh village evidence, and malformed saved anchors. Assert conflicts preserve stored values/provenance, set address status `stale`, confidence `unknown`, and revalidation `needs_revalidation`.

- [ ] **Step 6: Run the reconciliation tests and verify RED**

Run the command from Step 2. Expected: FAIL on missing normalization/reconciliation behavior.

- [ ] **Step 7: Implement normalization and reconciliation**

Use NFKC plus whitespace removal for address comparison and a Haversine distance calculation with an exact 100-metre threshold. Missing fresh evidence is not a conflict; material comparable differences are. Preserve `journey_anchor_id` on agreement and conflict.

- [ ] **Step 8: Run the contract suite and verify GREEN**

Run the command from Step 2. Expected: all tests PASS.

### Task 2: Journey ownership and property-switch clearing

**Files:**
- Modify: `frontend_next/lib/closed-loop-journey.ts`
- Modify: `frontend_next/e2e/journey-property-identity-contract.spec.ts`

**Interfaces:**
- Consumes: Task 1 projection and reconciliation functions.
- Produces: `ClosedLoopJourneyState.identityAnchor?: JourneyPropertyIdentityAnchorV1`; updated `updateJourneyProperty` and `setJourneyLocationResult` transitions.

- [ ] **Step 1: Write failing state-transition tests**

Test that selecting Address A creates an address-level anchor; Location A enriches the same anchor; changing to Address B replaces the anchor ID and clears Location, Market, Terrain/reference, Valuation, Loan, Holding, and Tax evidence; non-address valuation-context changes retain the anchor; conflicting fresh evidence on a reopened anchor marks it stale without overwriting it.

- [ ] **Step 2: Run the tests and verify RED**

Run: `npm run build:e2e && node e2e/run-e2e.cjs e2e/journey-property-identity-contract.spec.ts`

Expected: FAIL because journey state has no identity anchor.

- [ ] **Step 3: Implement journey ownership**

Add the optional anchor to state. Make `updateJourneyProperty` create a fresh address-level anchor only for a material address change and retain it for non-address edits. Make `setJourneyLocationResult` enrich or reconcile the active anchor. Clear `propertySearchResult` on material address changes so an Address A search row cannot remain attached to Address B.

- [ ] **Step 4: Run the tests and verify GREEN**

Run the command from Step 2. Expected: all transition tests PASS.

### Task 3: Bounded saved-case persistence and reopen provenance

**Files:**
- Modify: `frontend_next/lib/case-storage.ts`
- Modify: `frontend_next/app/page.tsx`
- Modify: `frontend_next/e2e/journey-property-identity-contract.spec.ts`

**Interfaces:**
- Consumes: `JourneyPropertyIdentityAnchorV1` and `normalizeJourneyPropertyIdentityAnchor` from Task 1; `ClosedLoopJourneyState.identityAnchor` from Task 2.
- Produces: `SavedCaseData.propertyIdentityAnchor?: JourneyPropertyIdentityAnchorV1`; save/reopen wiring that preserves the stored anchor.

- [ ] **Step 1: Write failing persistence tests**

Test that compact/save retains only the normalized anchor and bounded sources, malformed stored anchors are dropped without breaking case load, reopening restores the same anchor ID/provenance, and later conflicting Location evidence produces `needs_revalidation` rather than overwriting stored identity.

- [ ] **Step 2: Run the tests and verify RED**

Run: `npm run build:e2e && node e2e/run-e2e.cjs e2e/journey-property-identity-contract.spec.ts`

Expected: FAIL because saved cases omit the anchor.

- [ ] **Step 3: Implement bounded persistence**

Add the optional saved field, normalize it in `compactCaseData`/`normalizeSavedCase`, include it in `buildJourneySaveCase`, and restore it in the saved-case event handler before any later Location result is reconciled. Do not persist full Location payloads through the anchor.

- [ ] **Step 4: Run the tests and verify GREEN**

Run the command from Step 2. Expected: all persistence tests PASS.

### Task 4: Minimal main-journey identity UI

**Files:**
- Create: `frontend_next/components/guided-journey/journey-property-identity-card.tsx`
- Modify: `frontend_next/components/guided-journey/location-market-stage.tsx`
- Modify: `frontend_next/components/guided-journey/decision-case-stage.tsx`
- Modify: `frontend_next/app/page.tsx`
- Create: `frontend_next/e2e/journey-property-identity-ui.spec.ts`

**Interfaces:**
- Consumes: `JourneyPropertyIdentityAnchorV1` from Task 1 and the state field from Task 2.
- Produces: `JourneyPropertyIdentityCard({ anchor })` and optional `identityAnchor` props on Location/Decision stages.

- [ ] **Step 1: Write failing Playwright UI tests**

Test that the Location and Decision stages show “Journey property identity”, address/location/village, independent parcel/building unavailable states, sources, confidence limitation, and non-authoritative scope copy. Test a stale fixture shows a revalidation warning. Assert parcel/building unavailability does not disable progression through Location, Price, Finance, or Decision.

- [ ] **Step 2: Run the UI tests and verify RED**

Run: `npm run build:e2e && node e2e/run-e2e.cjs e2e/journey-property-identity-ui.spec.ts`

Expected: FAIL because the identity card is absent.

- [ ] **Step 3: Implement the reusable card and wiring**

Render only bounded fields. Use explicit status labels and fixed copy distinguishing address-level confidence from parcel/building authority. Pass the anchor from `app/page.tsx` to Location and Decision without adding workflow gates.

- [ ] **Step 4: Run the UI tests and verify GREEN**

Run the command from Step 2. Expected: all UI tests PASS.

### Task 5: Regression validation, final review, and one clean commit

**Files:**
- Review every changed file from Tasks 1–4 plus this spec and plan.

**Interfaces:**
- Consumes: completed implementation.
- Produces: verified branch and one bounded commit.

- [ ] **Step 1: Run focused frontend identity and stale-switch tests**

Run the two new specs plus `frontend_next/e2e/journey-identity-propagation.spec.ts`, `frontend_next/e2e/vnext-property-identity.spec.ts`, and `frontend_next/e2e/property-identity-review.spec.ts` through the existing E2E runner. Expected: PASS, excluding explicitly tagged real-provider tests when the runner's normal filtering applies.

- [ ] **Step 2: Run backend identity, parcel/building, and Property Case regression tests**

Run: `python -m pytest tests/test_vnext_property_api.py tests/test_vnext_identity_command_service.py tests/test_vnext_parcel_evidence.py tests/test_vnext_case_parcel_set_service.py tests/test_vnext_legacy_case_import_parser.py tests/test_vnext_legacy_case_import_service.py tests/test_vnext_persistence.py -q`

Expected: PASS or exact environment-dependent skips reported.

- [ ] **Step 3: Run affected frontend regression and static validation**

Run from `frontend_next`: `npm run typecheck`, `npm run lint`, and `npm run build`. Run the complete project test command required by TDD (`python -m pytest -q`) and report every pre-existing or environment-dependent failure by name. Expected for success claim: affected suites, typecheck, and build PASS.

- [ ] **Step 4: Inspect safety boundaries and diff**

Run `git diff --check`, `git diff --stat`, `git diff`, secret-pattern scans over changed files, and `git status --short`. Confirm no unrelated provider/configuration files, legal cadastral claims, raw payload persistence, or production mutations entered the diff.

- [ ] **Step 5: Commit once**

Run `git add` only for the reviewed bounded files, then `git commit -m "feat: close property identity production workflow"`.

- [ ] **Step 6: Record final Git state**

Run `git status --short`, `git log -1 --oneline`, `git diff origin/main...HEAD --stat`, and `git rev-list --left-right --count origin/main...HEAD`. Do not merge or deploy.
