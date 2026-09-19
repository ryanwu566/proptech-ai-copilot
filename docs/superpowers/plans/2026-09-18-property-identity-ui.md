# Property Identity UI Slice 1 Implementation Plan

**Goal:** Let a user review parcel and cadastral building hypotheses on a PropertyEntity without confusing a manual proposal with an official finding.

**Architecture:** Keep the existing FastAPI identity contract and Next.js session reader. Add strict request/response helpers to the identity client and a reusable review component whose API is injected. Mount the component only in an isolated fixture preview until production sign-in and session creation exist.

**Tech stack:** Next.js 16, React 19, TypeScript, Playwright.

**Spec:** User brief in this session, “PROPERTY IDENTITY — USER WORKFLOW UI SLICE 1”.

## Global constraints

- All three commands send only the request fields in `backend/api/v1/property_identity.py`.
- Graph starts with `confirmed` and `disputed`; `proposed` is requested only after the explicit filter is enabled.
- Manual proposals always read as unverified and nonofficial, including immediately after save.
- Production has a token reader but no production sign-in/session creation UI; no live write mount.
- Fixture preview makes no network requests and is unavailable in a normal production build.

## Tasks

### 1. Strict client contract

- [x] Test exact allowlisted payloads for parcel, cadastral building, and relation commands, plus graph status query.
- [x] Verify invalid UUID request test failed, then fix and re-run.
- [x] Add builders and strict response parsers; extend `vnextIdentityClient` with authenticated command methods and filtered graph reads.
- [x] Re-run tests and typecheck.

### 2. Review workflow

- [x] Test default/proposed graph behavior, labels, forms, relation reference selection, evidence, and loading/error/empty states in a fixture preview.
- [x] Observe browser test failures for missing or incorrect behavior, then fix them.
- [x] Add the injected review component, style it in plain Traditional Chinese, and provide a local-only fixture route.
- [x] Re-run frontend tests.

### 3. Gate and verification

- [x] Verify preview has no credentials or live API traffic and does not appear in a normal production build.
- [x] Run `npm typecheck`, `npm build`, relevant frontend tests, and `git diff --check`.
- [x] Review the diff against the user checklist and prepare one commit candidate.
