# Money / Finance consolidation v1

Starting commit: `895644a171e8e6e423ab3e3bb51ed53154bc0952`  
Branch: `feat/money-consolidation-v1`  
Route: `/cases/[caseId]/finance` (unchanged)

## Buyer workflow

Money summary → cash needed → monthly / holding cost → transaction / tax verification → offer scenarios.

- Cash: active asking / estimate / manual price, down payment, loan principal and a known initial-cash subtotal. The subtotal contains down payment only. Closing costs and the full initial cash requirement stay explicitly unknown.
- Mortgage: existing calculation endpoint, editable starting assumptions, saved non-default values, optional income and separate grace / post-grace payments. No credit scores, approval probabilities or offer ranking.
- Holding: existing endpoint and contract. The subtotal includes mortgage once. Missing area keeps management and repair costs unestimated. Tax amounts retain the existing price-times-rate proxy, explicitly labelled as assumptions rather than assessed tax values. Annual equivalents are monthly assumptions times twelve.
- Transaction: restrained verification list for bank terms, fees, tax bills, management, repairs and insurance. The only supported tax evidence is an existing saved preliminary self-occupied-property repurchase-condition summary. It is not a comprehensive purchase-tax calculation.
- Offers: asking versus one editable manual offer, using the current calculated mortgage assumptions and the existing local amortization equation, with grace-period handling. Previewing makes no API requests. Select a price, update estimates, then save to preserve that scenario on reopening. The case asking price is unchanged. Existing Scenario Lab drafts and Report / Compare contracts are unchanged.
- Truth: original saved assumptions and calculation time remain available in a read-only disclosure. Editing inputs marks results stale and blocks saving until recalculation. Identity and storage guards remain in place. Historical snapshots are not promoted merely by reopening or changing another input.
- Copy: new Money labels, errors, help, boundaries and navigation entries cover zh-TW, en, ja and ko.

## Validation

From `frontend_next`:

```text
node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test lib/workspace/money-workflow.test.ts lib/workspace/money-copy.test.ts lib/workspace/finance-calculation.test.ts lib/workspace/finance-model.test.ts lib/workspace/finance-persistence.test.ts lib/workspace/scenario-model.test.ts lib/workspace/case-evidence.test.ts lib/workspace/compare-report-model.test.ts lib/workspace/compare-diff.test.ts lib/workspace/report-executive.test.ts lib/workspace/report-core.test.ts
npm.cmd run typecheck
node node_modules/eslint/bin/eslint.js components/workspace/finance lib/workspace/money-workflow.ts lib/workspace/money-workflow.test.ts lib/workspace/money-copy.ts lib/workspace/money-copy.test.ts lib/workspace/workspace-navigation-copy.ts lib/navigation/copy.ts --max-warnings 0
node node_modules/eslint/bin/eslint.js --no-ignore e2e/commercial-finance-costs.spec.ts --max-warnings 0
```

The heavy-test slot was initially reserved by another session. After the user freed it, validation ran using bundled Chromium only, headless, one worker and zero retries:

```text
npm.cmd run build:e2e
node e2e/run-e2e.cjs e2e/commercial-finance-costs.spec.ts --project=chromium --workers=1 --retries=0
```

Results: **20 passed, 0 failed, 0 skipped (44.9s)**. All eight locale/width combinations passed (zh-TW, en, ja, ko × 390px, 430px), with no document, Money component or holding-breakdown horizontal overflow. The manual-offer round trip retained 30% down, 2.65% interest, 25 years and the selected 1,700-wan scenario while keeping the 1,850-wan asking price unchanged. Asking versus offer cash, principal and monthly payment all changed. The same saved scenario projected successfully into the existing Report and Compare browser views. Opening, previewing, reopening and projecting made no new provider requests; only the existing mocked loan and holding calculation endpoints ran.

Final focused Money unit run: **41 passed**. Related case-evidence, Report and Compare regression suites: **58 passed**. Navigation regression suite: **8 passed**. Explicit `npm.cmd run typecheck`, E2E production build and focused ESLint (including the browser spec with `--no-ignore`, zero warnings allowed) passed. No full repository browser matrix ran. Personal Chrome was not used.

Final implementation review corrected three state boundaries before browser execution: unknown legacy price provenance cannot be promoted to a manual scenario; invalid automatic mortgage inputs clear when switching price while explicit manual inputs remain; and mortgage recalculation cannot mark unsaved holding work clean, including edits made while a loan request is pending. Repeated mortgage calculations refresh the holding payment even if the resulting amount is unchanged. Browser regression cases cover those asynchronous holding transitions.

No provider, backend, database, schema or dependency changes. No push. Closing fees remain unknown, mortgage rates and holding inputs remain assumptions, and only the selected calculated scenario is saved in the existing Finance snapshot; unsaved previews are not persisted.

Status: `READY_FOR_PUSH` (push remains unrequested and was not performed).
