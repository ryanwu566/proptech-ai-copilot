# Property Scenario Lab v1

Buyers change offer and financing assumptions and immediately compare A/B/C without changing saved property evidence or production valuation.

## Design

Add `/cases/[caseId]/scenarios` to the existing workspace with a navigation entry and finance-page link. Three independent local drafts use TWD throughout. Initialize only offer from asking/active price and compatible saved loan assumptions; all other assumptions start unknown. Support down payment amount or percent, fixed interest rate, integer loan years, acquisition costs, monthly non-mortgage holding costs, renovation, integer holding years, and optional one-way commute minutes. Zero is an explicit assumption; blank is unknown. No taxes, fees, rate, term, or costs are invented.

Local pure TypeScript arithmetic ports the trusted `services/loan_calculator_service.py::_amortized_payment` equation (no grace period) with zero-rate and numerically stable small-rate handling. Money displays round only at presentation. Purchase cash = down payment + entered acquisition costs + renovation; total acquisition = offer + acquisition costs + renovation. Monthly ownership = mortgage + holding costs. First year cash = purchase cash + 12 monthly payments and holding costs. Holding cash = purchase cash + mortgage payments capped at loan duration + holding costs for the chosen period. These are cash outflows, not equity/return forecasts; resale, appreciation, variable rates and sale costs are excluded.

Partial totals are explicitly known subtotals and preserve each missing input. Invalid required fields suppress dependent results and show field errors. Compare signed offer deltas to asking and saved original finance price. A user may freeze one scenario as a separate baseline and compare financial metric deltas. Baseline/drafts save only on explicit action under `proptech.scenarios.v1`, keyed by case, revision, identity and evidence context; storage failure is visible. Saved-case bytes are untouched. No provider calls or LLM numeric calculations.

Accepted commute uses the existing location handoff rules: confirmed identity, matching origin, resolved Google route, no fallback/partial evidence. Manual duration remains labelled manual and does not alter route evidence. Show source, destination and checked date for accepted evidence. Commute does not become a monetary ownership cost.

## Acceptance

Each scenario card includes a sticky primary result strip (mortgage payment, purchase cash, monthly ownership cost), so changes remain visible while editing on mobile. The full comparison retains every requested output.

Full feature copy in zh-TW/en/ja/ko. At 390/430 widths editable cards stack; comparison remains side-by-side in a labelled horizontally scrolling table. At 1024/1440 cards use a three-column layout where space permits. Keyboard labels, field errors and status announcements work. Real Chromium and installed Chrome tests cover all four locales and widths, immediate calculations, A/B/C isolation, missing/invalid/zero inputs, baseline save/reload, provider silence and frozen saved evidence. No new dependencies or bundle ceilings. One final commit; no push/merge.
