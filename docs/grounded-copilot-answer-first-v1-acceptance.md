# Grounded Copilot answer-first v1 — acceptance record

Branch `feat/copilot-answer-first-v1`, based on `origin/main`
`2d15b1dc2fe46eb3eb6eea8a32cc03218dfece53`. Extends
[grounded-property-copilot-v1-acceptance.md](grounded-property-copilot-v1-acceptance.md);
every authority, isolation and provider-free guarantee recorded there is unchanged.
No model provider, transport, credentials, migration, dependency or budget change.

## Answer hierarchy

Question → status + direct headline (with cited markers) → bounded qualifier →
2–4 key facts → up to 3 missing items with an honest remaining count → one next
action (navigation only) → follow-up chips → collapsed "view all missing evidence"
→ collapsed full evidence ledger → collapsed provenance. The missing-evidence
disclosure opens by default only for insufficient answers. Citations in the
headline and facts open the provenance disclosure and move focus to the row.

## Layers

- `grounded-copilot.ts` (authority): adds the `asking_unit_vs_band` insight. It
  requires usable asking price, area > 0, P25 ≤ P75, P25/P75 unit equal to
  `asking unit／area unit`, no conflict, and cites all four inputs. Position uses
  the unrounded quotient. The saved area is a supporting row for market questions.
- `copilot-compose.ts` (pure): `composeAnswer(answer, context)` → `AnswerPresentation`.
  No fetch, storage, clock, React or provider access. A foreign/stale answer or
  rows that are not this context's own objects compose to a closed presentation.
  It never changes status, resolves conflicts, or cites refs outside `answer.used`.
- `copilot-answer-copy.ts`: four-locale headline/action/trust-class wording and
  human-readable units (`82.7 萬／坪`, `NT$55,111／月`, `24 分鐘`, `NT$826.7K / ping`).
  Rounding happens after comparison; a rounding tie with the exceeded bound shows
  two extra digits. Saved free text (commute destination) is quoted.

## Rules

- Headlines: market band position (with "not a valuation" note), known monthly
  housing (affordability unknown when income is missing), saved commute route
  ("not current traffic"), risk counts (no-match labelled "not proof of safety"),
  scenario payment, Decision Room record counts, or generic supported/partial,
  insufficient, legal-unsupported, live-not-requested, invalid-output and conflict
  sentences. Without a complete band there is no market headline; total price vs
  regional median is not promoted.
- Key facts: ≤ 4, each with refs, per-ref state and a trust class: user-entered,
  saved source, saved assumption, saved calculation, scenario assumption, user record
  or derived. The active price and price basis are never key facts because their
  trust class depends on the basis.
- Next action: at most one, always a `/cases/{id}/…` link; never runs analysis,
  calls providers or mutates evidence. Multi-topic questions route to Evidence.
- Re-reading unchanged evidence keeps the same context object so earlier turns stay
  cited; a changed key still discards the conversation.

## Validation (local, Windows)

| Check | Result |
| --- | --- |
| Workspace + Decision Room unit suites | 266 passed, 0 failed |
| Copilot compose / copy / grounding units | 39 passed (compose 17, copy 3, grounding 19) |
| Bundled Chromium, headless, workers=1, retries=0 | 148 passed in one run: Copilot 10 + regressions 138 |
| Regression specs | commercial-compare-report, document-evidence, final-production-acceptance, decision-room, property-scenario-lab, property-scenario-loading, evidence-checklist, commercial-overview-save, navigation |
| Widths 390 / 430 / 1024 / 1440, four locales, no horizontal overflow | Passed |
| Browser response budget (click → committed answer) | < 2 s at all widths |
| Provider requests in Copilot workflows | 0 |
| Typecheck / lint | Pass / 0 errors, 23 existing warnings |
| `build:e2e` / `build` | Pass / Pass |
| Route budgets (browser-measured) | All 17 routes pass; case routes 1,218,669 / 1,301,212 bytes |
| Global budgets | 3,462,973 / 8,000,000 bytes total; 604,482 / 900,000 largest JS |

Installed Google Chrome (`chrome` project) was not run locally; GitHub CI must
provide installed-Chrome validation.

## Independent review

A fresh read-only reviewer found no Critical issues and three Important ones, all fixed
with tests: (1) same-key evidence re-reads invalidated earlier turns, (2) the active
price and finance inputs had wrong trust classes, (3) total vs regional median was
promoted to a headline without a band. Minor fixes: rounding tie display, inline
finance caveat in multi-topic answers, quoted saved destination text, area gaps
routed to Overview, and citation anchor lookup without double decoding.

Future bounded phrasing: [grounded-copilot-phrasing-contract-v1.md](grounded-copilot-phrasing-contract-v1.md).
