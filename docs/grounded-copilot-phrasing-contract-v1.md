# Grounded Copilot phrasing contract v1 (future, not implemented)

Status: design contract only. This repository has **no** model provider, transport,
credentials or endpoint for the Copilot. Nothing in this document is wired up.

## Pipeline

```text
deterministic authority answer      grounded-copilot.ts  answerQuestion()
→ structured approved answer         copilot-compose.ts   composeAnswer() → AnswerPresentation
→ bounded phrasing model             (future, optional)
→ strict validator                   (future, required before any model text renders)
→ rendered answer                    copilot-conversation.tsx
```

The deterministic layer stays the only authority. `AnswerPresentation` is the
complete set of approved content: status, headline kind and values, key facts with
their references, trust classes (`origin`) and states, missing-evidence preview and
total, one next action and follow-up topics. Today it is rendered by fixed
four-locale templates in `copilot-answer-copy.ts`.

## What a future phrasing model MAY do

- Rephrase the approved headline and qualifier.
- Shorten them or improve readability in the active locale.

## What it MAY NOT do

- Add claims, facts, comparisons or conclusions.
- Add, remove, round differently or recompute numbers.
- Add URLs, links or citations, or move a citation onto a different statement.
- Change `status`, the headline kind, a band position, or a trust class
  (user-entered, saved source, saved calculation, scenario assumption, user record, derived).
- Resolve, soften or omit a conflict.
- Infer or fill missing evidence; turn unavailable, no-match, not-run or stale into safe/current.
- Introduce purchase, safety or valuation verdicts (buy, safe, overpriced, fair value …).
- Trigger provider calls, refreshes, navigation or any state change.

## Input

Only the structured `AnswerPresentation` of the **current** context key plus the
target locale. Never raw evidence prose, user notes, Decision Room text, other
cases, saved-case JSON, secrets or configuration. Saved text values that must
appear verbatim (for example a commute destination) are passed as opaque tokens and
re-inserted by the renderer, never paraphrased.

## Output and validator — fail closed

The model returns a single object `{ "headline": string, "note": string | null }`.
The validator must reject the output (and the fixed template is rendered instead)
when any of the following holds:

1. Any key other than `headline` / `note`, a non-string value, or excessive length.
2. The output was produced for a different context key or request sequence
   (`createResponseGate` binding, as today).
3. The multiset of numerals in the output differs from the numerals in the
   template rendering of the same presentation and locale.
4. It contains a URL, markup, citation marker or reference string.
5. Any opaque token is missing, duplicated or altered.
6. It matches the forbidden-verdict lexicon (all four locales) or an affirmative
   safety/currency claim.
7. The presentation status is `conflicting_evidence` or `insufficient_evidence`
   (these are never rephrased; the fixed templates are authoritative).

Rejection is silent to the user beyond showing the fixed template, and is never
retried automatically against a provider. Citations, key facts, missing evidence,
next action, full evidence and provenance are always rendered from the structured
presentation, never from model text.

## Test obligations when implemented

- Every validator rule above has a failing-input test.
- Foreign/stale context outputs are rejected (extend existing gate tests).
- Model text can never change `data-answer-status`, citations or key facts.
- Zero provider calls in all existing provider-free browser workflows.
