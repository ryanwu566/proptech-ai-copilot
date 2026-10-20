# Compare Difference Brief v1

Compare now opens with a compact, deterministic summary of saved case evidence. It preserves the buyer's selection order (A/B, or A/B/C/D for existing multi-case comparisons). Each of five categories presents one factual statement per case, followed by a neutral explanation of the contrast.

- Price / market: saved asking price, unit price derived from saved asking price and area, market unit median and available P25–P75 band. Expanded evidence includes sample size, scope and period. Regional transaction distributions are not a valuation.
- Location / commute: confirmed browser location association, saved administrative completeness, available nearby evidence and explicit saved routes. A time delta requires usable saved routes with the same destination, mode and units. Different destinations or modes are identified rather than compared for speed.
- Risk / environment: matched, unknown, unavailable, not queried, no match, unsupported / no coverage and stale counts stay distinct. Unknown is not safe; no match is not zero risk. Equal counts do not imply equal findings.
- Money: saved down payment, loan principal, monthly mortgage and known housing costs including the mortgage. No new calculation runs. Down payment is not labelled total cash needed. Missing and stale calculations stay unavailable for numeric contrasts. Expanded evidence retains the saved price basis, interest, term, down-payment ratio and missing costs.
- Verification: distinct listed evidence gaps and reconciled open manual checklist actions are counted separately. Saved Money tasks are listed separately because they can overlap checklist actions. Reviewing an action does not remove missing evidence; changed evidence reopens the action using the existing checklist reconciliation.

Every category has an expandable saved-evidence section with the original values, state, sources, dates, limitations and relevant action links. The brief never uses session results, refreshes providers, calls Routes, calculates an aggregate score or expresses a purchase preference. Compare's existing identity and repository gates still apply. The saved schema on this branch has no selected offer scenario or complete cash-needed total, so neither is invented.

Validation commands (from `frontend_next`):

```text
npm run test:documents
node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test lib/workspace/evidence-checklist.test.ts
npm run typecheck
npm run build:e2e
node e2e/run-e2e.cjs e2e/compare-difference-brief.spec.ts e2e/commercial-compare-report.spec.ts --project=chromium --workers=1 --retries=0
```

Browser coverage checks the compact summary before the detailed comparison, desktop and narrow layouts, stale and missing values, evidence disclosures, selection, storage changes, identity blocking, and zero provider requests. UI summaries support Traditional Chinese, English, Japanese and Korean; original saved source text keeps its source language.
