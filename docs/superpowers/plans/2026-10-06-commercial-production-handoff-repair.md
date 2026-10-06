# Commercial Production Handoff Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the existing guided commercial journey so accepted property context saves and reopens safely, Terrain actions are observable, valuation road context stays property-bound, and attempted unavailable valuation state is preserved.

**Architecture:** Keep `ClosedLoopJourneyState`, `JourneyPropertyIdentityAnchorV1`, `SavedCase`, and the existing workspace adapters as the only state contracts. Add narrowly scoped normalization at existing handoff boundaries, persist only bounded journey status metadata, and stabilize guided async callbacks without changing provider contracts.

**Tech Stack:** Next.js 16, React 19, TypeScript 5, Node test runner, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-27-commercial-ux-master-architecture.md`

## Global Constraints

- Do not create a parallel property identity or evidence state model.
- Do not weaken identity validation or promote the browser journey anchor to official parcel, building, ownership, or legal identity.
- Preserve independent commute channels, E6 source semantics, and E7 finance contracts.
- Persist only bounded evidence and status metadata; never raw provider payloads, secrets, or debug traces.
- Property switches and late responses must not attach prior-property evidence.
- Do not implement E8, E9, deploy, push, merge, rebase, or modify production configuration.
- Produce exactly one final commit named `fix: close commercial production handoff gaps`.

## Review Focus

1. Accepted normalized addresses that differ only by safe formatting or administrative enrichment must not create false revalidation, while material address conflicts must remain blocked.
2. A current anchor with normalized address and coordinates may satisfy save identity only when the split address fields are absent; stale or incomplete anchors remain blocked with an actionable reason.
3. Road derivation must accept recognizable Taiwan road/street/avenue components and return no road for ambiguous text.
4. Property A async Terrain or valuation state must not survive a switch to Property B, and late A responses must remain rejected.
5. `unavailable` must survive Decision Summary and save/reopen without fabricating valuation evidence or a numeric result.

---

### Task 1: Close the guided commercial handoff gaps

**Files:**
- Modify: `frontend_next/lib/location-market-journey.ts`
- Modify: `frontend_next/lib/closed-loop-journey.ts`
- Modify: `frontend_next/lib/price-affordability-journey.ts`
- Modify: `frontend_next/lib/case-storage.ts`
- Modify: `frontend_next/app/page.tsx`
- Modify: `frontend_next/components/terrain-risk-analysis.tsx`
- Modify: `frontend_next/components/guided-journey/price-decision-stage.tsx`
- Modify only if reproduced: touched presentation components/copy helpers for raw enum, blank timestamp, or non-interactive affordance defects
- Test: focused Node/Playwright contract and browser regression files under `frontend_next/lib/**` and `frontend_next/e2e/**`

**Interfaces:**
- Consumes: `ClosedLoopJourneyState`, `JourneyPropertyContext`, `JourneyPropertyIdentityAnchorV1`, `SaveCaseInput`, existing Terrain and valuation callbacks.
- Produces: coherent accepted property context, identity-aware save validation, persisted bounded valuation attempt status, stable guided Terrain execution, and deterministic property-switch behavior.

- [ ] **Step 1: Write focused failing contract tests**

Cover identity-backed save success, stale/incomplete identity rejection with exact missing keys, bounded save/reopen, conservative road derivation, coherent location enrichment, valuation `not_started` versus attempted `unavailable`, unavailable round-trip persistence, and A-to-B invalidation.

- [ ] **Step 2: Run the focused contract tests and verify RED**

Run the smallest relevant Playwright/Node commands for the new tests.

Expected: failures identify missing identity-backed save acceptance, road/context derivation, valuation-status propagation/persistence, or property-switch isolation—not syntax or fixture errors.

- [ ] **Step 3: Write deterministic mocked browser tests for guided Terrain and the save/reopen journey**

Cover loading visibility, bounded success, explicit local failure, same identity/address/coordinates, correct road, unavailable valuation at Decision Summary and after reopen, and A-to-B stale-response rejection. Include 390 px overflow/readability and keyboard/status assertions on changed surfaces.

- [ ] **Step 4: Run the browser tests and verify RED**

Expected: the guided Terrain request is cancelled/reset by changing callback identities and/or the handoff loses the bounded state being asserted.

- [ ] **Step 5: Implement the minimal contract fixes**

Stabilize Terrain callback consumption, enrich current context only from accepted Location evidence, conservatively derive the road or leave it empty, pass the stored valuation attempt status into all consumers, persist that status in the existing journey context, and allow save identity to use only a current normalized anchor with coordinates when split address fields are absent.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run all tests named in Steps 1 and 3 plus existing guided journey, identity, case storage, workspace, market, commute, risk, and finance tests touched by these contracts.

Expected: all pass with no provider calls.

- [ ] **Step 7: Run full bounded validation and trust review**

Run lint, typecheck, production build, production dependency audit, the repository bounded audit gate, applicable E1–E7/reliability/monetary suites, `git diff --check`, changed-surface enum/trust-language search, and deterministic Playwright acceptance including 390 px.

Expected: all required gates pass or any pre-existing/environmental limitation is named with exact evidence.

- [ ] **Step 8: Review and create the single bounded commit**

Review the complete branch diff against the spec, fix Critical/Important findings through RED/GREEN, then create exactly one commit:

```bash
git commit -m "fix: close commercial production handoff gaps"
```
