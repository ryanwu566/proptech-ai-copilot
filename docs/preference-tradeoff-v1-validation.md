# Preference Profile + Deterministic Trade-off Explanation v1

Validated locally on 2026-10-12 in the isolated `feat/preference-tradeoff-v1` worktree.

## Delivered behavior

- `/preferences` edits a buyer/household profile with must-have, nice-to-have, and veto conditions, price and modeled down-payment comfort, size, building age, floor, transit distance, multiple commute destinations/modes, risk evidence requirements, and free-form rationale.
- Compare shows individual condition outcomes, explicit veto breaches, unknown evidence statements, and deterministic pairwise explanations. No aggregation, ranking, fit score, safety score, or purchase verdict is produced.
- Structured fields are an allowlist of property/evidence criteria. Notes are retained as user-authored rationale and never interpreted as facts or executable preferences.
- `proptech.preferenceProfile.v1` is a separate versioned local store with strict validation, bounds, explicit save/delete, corruption/unsupported-version/read/write diagnostics, and optimistic comparison of the complete saved profile. There are no case-storage schema or persistence changes and no dependency on #181.
- The pure evaluator consumes saved workspace evidence. Age and floor are explicitly labeled saved user inputs; route and down-payment values are saved estimates. No provider or calculator is called by the feature.

## Evidence boundaries

- Inclusive limits; real zero is distinct from missing. Unknown never satisfies or breaches a preference.
- Commute needs an exact whitespace-normalized saved destination and matching travel mode, a valid property origin and usable route evidence. Missing, partial, fallback, invalidated or mismatched routes stay unknown.
- Cash comparisons use saved modeled down payment only, excluding unestimated transaction costs and total cash needs. Cash-preservation statements additionally require known matching price provenance and compatible saved loan assumptions.
- Risk evidence requires a named source, checked date, coverage and usability. Additional options require a recorded dataset version or covered no-match. Placeholder metadata is missing evidence; no-match is never a claim of safety.
- Saved station summaries currently lack property binding. Transit preferences are retained but evaluated as unknown; distances are not invented from station names, counts or route duration.
- Unconfirmed or stale property identity cannot produce preference outcomes from old facts. Saved-case selection and identity guardrails continue to apply.

## Verification

- All frontend `lib` model tests: **247 passed**, including **11 preference regressions**.
- Design-system checks: **12 passed**. Owned E2E runner check: **1 passed** after its production-build prerequisite.
- Production build and TypeScript check: passed. Focused lint on all changed product/model files: zero warnings/errors. Full frontend lint: zero errors, 23 existing warnings outside this feature.
- **32 browser matrix checks passed:** zh-TW/en/ja/ko × 390/430/1024/1440 × Chromium/Chrome. Profile and Compare screenshots were captured; both pages assert no document overflow. English mobile profile and explanation screenshots were visually inspected.
- **24 existing Compare/report regression checks passed** across Chromium/Chrome, covering selection, identity, stale/unknown/zero evidence, frozen reports, print, malformed storage and zero provider calls.
- **16 final profile workflow checks passed** across Chromium/Chrome after the localized-validation fix: keyboard create/edit/save and focus movement, all criterion types, persistence, case-store isolation, corrupt/future-version recovery, read and quota failure, normal cross-tab conflicts, delete/recreate conflicts, and translated incomplete-commute feedback.
- Request interception observed **zero analysis/provider requests** for the locale/layout matrix and profile create/edit/save/Compare flow. Existing Compare/report provider-call regression also passed.
- Fresh independent review found three correctness gaps; all were fixed with red/green model regressions and verified by the reviewer. A browser red/green regression also proved localized incomplete-commute validation.

Browser coverage totals 72 distinct scenarios across the production matrix/regression run and the final targeted workflow rerun. Initial ambiguous selectors were corrected to scope alerts to `main` and identify the evidence-requirement combobox by its exact accessible name. Development-server load timeouts were resolved by using owned production servers on unique ports. No failing check remains unresolved.

## Reproduce

From `frontend_next`:

```powershell
npm run test:preferences
npm run typecheck
npm run lint
npm run build:e2e
node e2e/run-e2e.cjs e2e/preference-tradeoff.spec.ts e2e/commercial-compare-report.spec.ts --workers=2 --retries=0 --timeout=60000
```

The feature-only browser command is `npm run test:e2e:preferences`. Local screenshots remain under `frontend_next/test-results`; they are generated validation artifacts, not product assets.

Delivery is one final local commit. No push or merge is part of this task.
