# Preference profile and deterministic trade-off v1

**Goal:** Buyers and households save explicit requirements and compare saved properties against them without a score or purchase verdict.

**Design:** A strict versioned profile lives in `proptech.preferenceProfile.v1`, independent of saved cases and #181. A pure evaluator consumes normalized saved workspace evidence. A localized editor is available at `/preferences`; Compare renders individual preference outcomes and pairwise explanations. Free text is user rationale only, never an executable rule.

**Constraints:** Four locales (zh-TW/en/ja/ko); 390/430/1024/1440; keyboard accessible; zero automatic provider calls; unknown remains unknown; no demographic/neighborhood preference fields; one final commit; no push or merge.

**Execution:** Implement inline in the existing isolated worktree. The supplied build requirements authorize implementation; consolidate all artifacts into the single requested final commit.

- [x] Test strict profile validation, separate storage, corruption/version/write failures and revision conflicts; implement local store.
- [x] Test deterministic thresholds, commute destination/mode mismatches, cash assumptions, stale/missing risk and identity evidence; implement pure evaluator and age/floor projection.
- [x] Implement four-locale editor and explanation copy, profile navigation and Compare integration.
- [x] Browser-test persistence, editing/deletion, keyboard access, all locale/viewport combinations, and no provider requests; run typecheck, lint, build and relevant regression suites.
- [x] Review final diff, record validation, create exactly one commit and leave branch unpushed.

**Evaluation rules:** Limits are inclusive. Must-have and nice-to-have share deterministic predicate evaluation; a veto means breaching the entered acceptable range is a deal-breaker. Unknown never means breached or satisfied. Price is saved asking price; cash is saved modeled down payment (not all closing costs or a claimed reserve). Commute uses only saved estimates with an exact whitespace-normalized destination and mode match. Transit uses only saved evidence linked to the property; unbound surrounding-station context is unknown. Risk requirements require usable, covered, dated named-source evidence; stronger options require a dataset version or a recorded no-match. No-match never means safety. Building age and floor are saved user inputs with explicit provenance.

**Review focus:** No stale or identity-invalid facts become evaluable; zero differs from missing; incompatible cash assumptions cannot produce a cash-preservation claim; corrupt or newer-version profile data cannot be silently overwritten; free rationale cannot become an inferred preference.

**Review resolutions:** Require known compatible finance price provenance for cash claims; compare the entire saved profile before a write so a deleted/recreated revision cannot be overwritten; reject placeholder risk source/version metadata. Browser validation uses the selected locale through the strict profile validator. See `docs/preference-tradeoff-v1-validation.md` for results.
