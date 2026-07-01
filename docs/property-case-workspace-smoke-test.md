# Property Case Workspace Smoke Test

This checklist is for manual demo verification of the property case workspace. It uses only in-memory user input and existing UI flows. Do not enter secrets, provider URLs, database values, real transaction rows, or raw provider responses.

## Scope

- Property case route opens without calling market, refresh, commute, location, terrain, or map providers.
- Basic case data can be typed without losing focus.
- Financial Decision Lab remains user driven.
- Due Diligence Review Board remains user driven.
- Viewing & Offer Planning Board remains user driven.
- Timeline & Executive Decision Pack remains user driven.
- Comparison and HTML report remain conservative and do not create buy/sell advice.

## Smoke Fixture

Use a single fictional case with:

- Case name.
- Property address or identifier.
- Listing price.
- Two financial scenarios.
- At least one due diligence item marked by the user.
- At least one viewing log.
- At least one viewing question.
- Up to three offer plans.
- At least one timeline event.
- At least one completed milestone.
- Executive summary note.
- Final review note.

Do not use real addresses, coordinates, station names, transaction rows, tokens, or provider payloads.

## Route And Initial Render

1. Open `/cases/<case-id>`.
2. Confirm the route renders the case workspace title, basic case form, readiness summary, decision summary, and print summary.
3. Confirm Financial, Value/Tax, Location/Market, Due Diligence, Viewing/Offer, and Executive Pack are available through the workspace section selector.
4. Confirm only the selected heavy workspace section is mounted at a time.
5. Confirm changing sections does not erase typed draft state.

## Interaction Stability

1. Type into the basic case fields and confirm focus stays in the active input.
2. Switch to Financial and edit scenario rows.
3. Switch away and back; confirm scenario rows remain.
4. Switch to Due Diligence and edit an item status, note, reference note, next action, and target date.
5. Switch away and back; confirm values remain.
6. Switch to Viewing & Offer and add/edit/remove a viewing log, question, and offer plan.
7. Switch to Executive Pack and add/edit/remove a timeline event, toggle a milestone, and edit executive/final notes.
8. Confirm item rows use stable IDs, not array index keys.
9. Confirm no auto-save, localStorage, sessionStorage, cookie, URL query, or URL hash is introduced for the workspace editor state.

## Safe Data Semantics

1. Missing or unknown data must not display as `0`.
2. Missing or unknown data must not display as low risk, low price, complete, approved, safe, or recommended.
3. Commute, market, terrain, location, valuation, loan, tax, due diligence, viewing, offer, timeline, or milestone state must not automatically change `decision_status`.
4. Timeline and Executive Pack must not create recommendations, risk scores, financial advice, legal advice, loan approval probability, or investment conclusions.
5. Partial report notice must remain visible for printable current summaries.

## Report And Comparison

1. Print summary includes the Executive Decision Pack summary.
2. Comparison report remains derived from existing saved case comparison state.
3. HTML export contains conservative limitations and must not include raw errors, SQL, DB details, tokens, secrets, provider payloads, or real transaction rows.
4. Print uses browser print behavior only; no server-side PDF generation is added.

## Browser Test Stack

The frontend package currently exposes a Next.js build command and no checked-in Playwright or Cypress script in `frontend_next/package.json`. Until a browser test stack is formally added, keep this checklist as manual smoke coverage and continue protecting behavior with static and helper tests.
