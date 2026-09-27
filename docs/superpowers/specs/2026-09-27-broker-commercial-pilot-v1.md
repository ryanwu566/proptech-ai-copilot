# Broker Commercial Pilot v1

Status: draft for review

Date: 2026-09-27

Scope: commercial product validation only

## 1. Decision and falsifiable hypothesis

This pilot tests whether residential real-estate brokers and property professionals can use PropTech AI Copilot to prepare an unfamiliar property for a client discussion more quickly, with less repeated work and fewer context mistakes, while correctly understanding evidence limitations.

The hypothesis fails if the product does not materially shorten a real preparation workflow, causes property or evidence confusion, requires substantial facilitator help, or creates more verification work than it removes.

The recurring workflow under test is:

```text
Create property → Analyze → Save → Reopen → Compare
→ Prepare client discussion/report → Reuse on the next property/client
```

This pilot does not validate market size, pricing, statistical superiority, formal valuation accuracy, legal/tax correctness, or individual-buyer demand. Observed behavior is primary evidence; participant opinion is supporting evidence.

## 2. Current capability audit and pilot boundary

This audit uses current runtime code, service contracts, and checked-in browser tests at starting commit `7f442f8aa9f2217b872fa703065ea522dd8a8457`. Documentation-only capabilities are not treated as available.

Classification meanings:

- **Available now:** in the current consumer runtime and suitable for a controlled pilot.
- **Partially available:** usable with material provider, persistence, coverage, or integration limits.
- **Currently being fixed:** a verified in-scope fix exists but is absent from this commit. Nothing is assigned this label; branch names alone are not evidence.
- **Planned:** architecture or foundation exists without a pilot-ready runtime flow.
- **Not suitable for pilot:** unsafe, misleading, or too incomplete for participant tasks.

| Capability | Classification | Evidence and pilot use |
| --- | --- | --- |
| Property entry / Property Finder | Available now | Primary guided-journey entry backed by property search. Use public/test inputs only. |
| Location | Partially available | Location analysis, map, nearby context, and limited/unavailable states exist; live providers and coverage are conditional. |
| Market | Partially available | Query, source, period, coverage, freshness, and no-data states exist; hosted dataset coverage requires preflight. |
| Valuation | Partially available | Official-comparable results can fail closed and show confidence/freshness; not a formal appraisal and coverage-dependent. |
| Risk | Partially available | Terrain/hazard results preserve partial and unavailable providers; reference evidence only. |
| Commute | Partially available | Address/routing workflow exists; snapshot/provider availability is conditional and failure must remain local. |
| Loan | Available now | Deterministic calculation and sensitivity output; fictional inputs only and not loan approval. |
| Holding Cost | Available now | Deterministic calculator; missing inputs must remain unestimated rather than zero. |
| TaxOracle | Partially available | Deterministic trace/report exists, but official-rule currency is not fully proven; reference prompt only. |
| Property Case | Partially available | Guided case plus separate case workspace exist; main saved-case flow is browser-local rather than a durable team workspace. |
| Save / reopen | Partially available | Same-browser `localStorage`, maximum 10 cases, compacted evidence; no cross-device/team continuity. |
| Compare | Available now with prerequisites | Compares 2–3 saved cases with title, property identifier, and positive price; missing data stays explicit. |
| Decision | Available now | Client-side synthesis and next actions exist but inherit upstream limitations and are not purchase advice. |
| Report / export | Partially available | Valuation HTML, TaxOracle report, current-summary print, and comparison print exist; no guaranteed server PDF/client pack. |
| Property Identity | Partially available | Consumer active-property context invalidates dependent results. Separate VNext confirmation foundations are not integrated as a production broker identity flow. Pilot identity means correct active context, not legal parcel/building identity. |
| Evidence/source display | Partially available | Market/valuation are strongest; other modules vary. Trust must be tested per output. |
| Mobile/narrow | Partially available | Tests cover 390×844 journey/navigation; exact hosted flow still needs manual 390px acceptance. |
| Hosted production acceptance | Partially available | Hosted/provider tests exist, but the repo cannot prove current deployment, credentials, coverage, or every provider path. |
| Durable professional workspace, team collaboration, CRM, listings, title/documents | Planned or not suitable | Do not include in tasks or imply availability. |

Pilot only the consumer guided journey, local cases, comparison, and current report surfaces in one controlled browser profile. Do not promise authoritative identity, active listings, ownership/title, team collaboration, formal appraisal, legal/tax advice, or lender approval.

Run `docs/commercial-acceptance-checklist-v1.md` against the exact hosted build before recruitment. An unavailable module is a controlled failure or `NOT TESTED`; it is never replaced by documentation, mock data, or facilitator narration.

## 3. Participants and sample

### Primary hypothesis

Residential brokers/property professionals who personally prepare properties before viewings or discussions have a repeatable workflow and the clearest opportunity for recurring value.

### Inclusion

- Personally prepares residential properties for clients or client-facing colleagues.
- Conducted at least one viewing or property discussion in the previous 30 days.
- Uses at least two digital tools or sources in normal preparation.
- Has compared, revisited, or followed up on properties as part of the role.
- Can use public/test properties and fictional financial inputs.

### Exclusion

- No property-preparation responsibility or administrative-only role.
- No recent viewing/client workflow.
- Participation requires confidential client, seller, tenant, ownership, income, or transaction data.
- Helped design or implement the product.
- Cannot independently use the supported device/language with ordinary accessibility accommodations.

Record role and experience ranges, not employer, client list, or name.

### Size and design

Recruit **six qualified participants**, with up to two reserves. Six supports close observation and recurring-pattern discovery without implying statistical market validation.

It can reveal repeated usability/trust failures, directional within-person time/effort changes, recurrence value, and workflow-replacement evidence. It cannot establish causality, significance, market size, pricing, retention, regional generalizability, or accuracy certification.

Use two preflighted comparable public/test property pairs. Alternate which member is baseline versus product property across participants to reduce property-specific bias. Because product always follows baseline, report practice/fatigue as a limitation.

## 4. Session and facilitation

Target 85–95 minutes:

| Segment | Guide |
| --- | ---: |
| Introduction, consent, privacy | 5 min |
| Pre-task interview | 8 min |
| Normal-process baseline | 18 min |
| Reset | 2 min |
| PropTech task | 25 min |
| Reuse, switch, failures | 17 min |
| Pretend-client explanation | 8 min |
| Post-task interview | 12 min |

If time expires, record incomplete/time-censored; do not finish the task for the participant.

Read once:

> Please work as you normally would and say what you are looking for or expecting. I will not guide you unless you cannot continue.

Intervene only when the participant explicitly asks after 90 seconds without progress, privacy/safety is at risk, the test environment would be left, a provider failure blocks continuation, or accessibility/time limits require it. First use a neutral prompt such as “What would you try next?” Record time, trigger, exact help, and outcome. Revealing a control counts as an intervention.

## 5. Pre-task interview

1. Describe the last residential property you prepared from start to finish.
2. Which tools, websites, files, or colleagues did you use?
3. What do you always check? What takes longest?
4. What is easiest to forget or mix up?
5. What do you prepare or send for clients?
6. When and how do you compare properties?
7. How often do you reopen an old case?
8. How do you verify data?
9. What makes preparation complete enough for a client discussion?

Do not ask whether an AI PropTech tool would be useful.

## 6. Baseline task

Give one unfamiliar public/test residential property and fictional client brief:

> Prepare this property for a client viewing or discussion as you normally would. Produce whatever notes, message, comparison, or brief you ordinarily use. Stop when it is usable for that conversation.

Do not coach unless permitted. Capture start/end, time to first useful evidence, time to usable brief, tools, searches, repeated address/price entry, copied notes, calculations, external sources, missing information, unresolved questions, context/unit/source mistakes, and output created.

## 7. PropTech task

Give a comparable second public/test property and the same fictional client objective:

> Prepare this second property for the same kind of client discussion using PropTech AI Copilot. Use the product as you think appropriate. Stop when you have a usable brief.

Where preflight permits, cover:

```text
Confirm active property → Market and price → Location → Commute
→ Risk/environment → Loan, holding cost, and TaxOracle references → Decision/next actions
→ Save → Reopen → Compare → Report
```

Do not explain every control. Record baseline measures plus retries, blocks, interventions, recovery, skipped modules, active-property understanding, and readiness judgment.

## 8. Reuse and property-switch tests

### Reuse

1. Save the PropTech case.
2. Leave it without explaining how to return.
3. Reopen it in the same browser profile.
4. Identify findings, unknowns, and next action.
5. Continue without unnecessary re-entry.
6. Compare it with a second saved test case.
7. Identify work the saved context prevented.

Measure save/reopen/compare/report success, orientation time, repeated input, lost/compacted evidence, help, and understanding of same-browser limits.

### Property-switch integrity

1. Analyze Property A through location plus price or risk.
2. Change to Property B using ordinary entry.
3. Ask which property each visible result belongs to.
4. Ask what old evidence remains and what needs refresh.
5. Run one downstream calculation for B.

Record carryover, stale evidence, repeated input, active-property uncertainty, correct invalidation, and any A evidence explained as B evidence. Wrong-property evidence in the client explanation is a critical failure.

## 9. Controlled failure recovery

Use an approved staging/control seam or natural unavailable response. Never break production or fabricate success. If a scenario cannot be safely induced, mark it `NOT TESTED`.

| Scenario | Expected invariant | Measure |
| --- | --- | --- |
| Valuation unavailable | Other analysis usable; no invented estimate; verification action named. | Help, retry, external check, brief impact. |
| Commute unavailable | Location remains usable; commute explicitly unavailable. | Local recovery and semantic confusion. |
| Missing area | Area-dependent outputs missing/unestimated, not zero. | Unit interpretation and explanation. |
| Partial risk provider | Available evidence visible; unavailable is explicit and never “low risk.” | Trust language and next check. |
| Identity revalidation | User knows what may need refresh. | Active-property certainty and refresh choice. |
| Asking price change | Finance/decision updates or invalidates; property evidence remains tied correctly. | Stale outputs and recalculation. |
| Back/forward/reopen | Context stays coherent or loss is explicit/recoverable. | Loss, duplication, help, recovery time. |

## 10. Client explanation and trust

Ask for a five-minute pretend-client explanation covering market/price, location/commute, risk, financial assumptions, unknowns, and next verification actions.

Then ask the participant to identify what they trust immediately, would verify elsewhere, is estimated/calculated, is official/reference data, is unavailable, is unknown, and which source/date matters.

Success is calibrated trust, not blind trust or visual appeal. Record independent explanation of one major finding, limitation, unknown, and next action.

## 11. Behavioral measures and structured notes

| Dimension | Measures |
| --- | --- |
| Efficiency | Time to first useful evidence, usable brief, total completion, reopen orientation. |
| Effort | Tools, external searches, repeated inputs, copied notes, calculations. |
| Integrity | Wrong-property carryover, stale evidence, unit/source misunderstandings, unknown-as-low-risk incidents. |
| Assistance | Interventions, blocks, retries, recovery success. |
| Reuse | Save, reopen, compare, report, repeated work avoided, local-limit understanding. |
| Explanation | Finding, limitation, unknown, source/date, next action, client-shareable output. |
| Commercial | Next-week reuse, task replaced/shortened, tool displaced/retained, blocker, output sent. |

For completed tasks only:

```text
directional time change = (baseline time - PropTech time) / baseline time
```

Tag notes as confusing terminology, missing evidence, redundant information, unnecessary step, trusted feature, ignored feature, misunderstood feature, useful output, duplicated workflow, client-facing value, or workflow blocker. Include task, time, behavior, quote/paraphrase, consequence, intervention, and severity.

Use `docs/templates/broker-pilot-observation-sheet-v1.md`.

## 12. Post-task interview

1. Which part changed your normal workflow?
2. What did you still check elsewhere?
3. Which result did you trust least, and why?
4. What information was unnecessary? What was missing?
5. What would you show a client? What would you never show?
6. What would make you use this on the next property? What would stop you?
7. Which current tool would remain necessary?
8. Did save/reopen remove real work?
9. Did comparison change your preparation or merely restate it?
10. Did the report support a client conversation? What must change before sending it?

Avoid “Did you like it?” and praise-seeking questions.

## 13. Success criteria

These are product-discovery thresholds, not statistical significance. Report every participant and critical incident.

### Workflow

- At least 5 of 6 reach a usable brief with no more than one procedural intervention.
- At least 5 of 6 state the active property correctly at decision/report.
- At least 5 of 6 recover from the assigned non-critical failure without procedural help.
- No participant explains wrong-property evidence after switching properties.

### Efficiency

- At least 4 of 6 complete the PropTech brief at least 20% faster than baseline, or save at least five minutes when both tasks finish inside the time box.
- At least 4 of 6 use fewer external searches and repeated address/price entries.
- The product does not increase total tools used for a majority.

### Trust

- At least 5 of 6 distinguish estimated/calculated from official/reference evidence.
- At least 5 of 6 distinguish unknown/unavailable from low risk.
- At least 5 of 6 recognize an incomplete cost estimate and missing input.
- At least 5 of 6 identify a material source/date limitation without correction.
- Any confident client claim based on unavailable or wrong-property evidence fails this gate.

### Reuse

- At least 5 of 6 save and reopen; at least 4 do so without help.
- At least 4 of 6 compare two eligible cases and explain a meaningful difference.
- At least 4 of 6 identify work avoided and a credible reason to return within a week.

### Commercial usefulness

**Strong:** observed use materially replaces or shortens a real task, reduces re-entry/search, supports client explanation, and produces a concrete next-use case.

**Weak:** the participant says it is interesting or attractive but keeps the old workflow unchanged, cannot name displaced work, or would not use the saved case/report with a client.

Commercial usefulness passes only when at least 4 of 6 show a strong signal. Enthusiasm cannot substitute for behavior.

## 14. Failure signals and roadmap implications

| Failure signal | Roadmap implication |
| --- | --- |
| Participants return to existing tools for core evidence | Identify the missing trusted source; do not add summary UI first. |
| Preparation is not faster or uses more tools | Reduce handoffs/re-entry and simplify the core path before expansion. |
| Active property is unclear or stale evidence survives | Stop rollout; prioritize visible identity and invalidation rules. |
| Source/date limits are misunderstood | Redesign evidence labels and require comprehension acceptance. |
| Unknown/unavailable becomes low risk or zero cost | NO-GO; fix state semantics before another session. |
| Report is not client-usable | Prioritize editable, source-aware client output. |
| Save/reopen adds no value | Question recurring SaaS positioning and study actual revisit triggers. |
| Comparison does not affect work | Keep it secondary or remove it from the commercial story. |
| Verification work increases | Narrow claims, improve provenance/coverage, or stop the affected workflow. |
| Facilitator is repeatedly needed | Fix navigation, terminology, and recovery before broader recruitment. |

## 15. Commercial maturity gate

Apply the highest level whose conditions all hold. A critical integrity/trust failure overrides counts.

### NO-GO

Any critical safety failure, material workflow/efficiency/trust gate failure, core information unavailable for most sessions, or more verification work than baseline. Do not broaden recruitment.

### LIMITED PILOT

Works only for selected properties/providers/browsers or with facilitator help. Continue only with a named cohort, supported cases, explicit limitations, and remediation plan.

### COMMERCIAL MVP PILOT READY

All workflow, efficiency, trust, reuse, and commercial gates pass; hosted acceptance has no unresolved core `FAIL`; participants complete the core flow independently; limitations are explicit/local. This authorizes a larger controlled broker pilot, not general launch.

### COMMERCIAL BETA CANDIDATE

Cannot be awarded from this study. It requires a later multi-week pilot showing repeated professional reuse, acceptable support burden/provider reliability, privacy practice, and client-facing output.

## 16. Standard production acceptance scenario

Use a public building address, never a participant/client private address.

### Public/test property

- Dongming Social Housing (東明社會住宅)
- `臺北市南港區南港路二段60巷16號`
- Taipei City Government public-source basis: <https://udd.gov.taipei/assets/fsBnbPJY11eGqSi3QvTDmC/attachs/%E9%99%84%E4%BB%B61_112%E5%B9%B4%E5%BA%A6%E9%9D%92%E9%8A%80%E6%8F%9B%E5%B1%85%E8%A8%88%E7%95%AB%E5%9F%BA%E5%9C%B0%E4%BB%8B%E7%B4%B9.pdf>

The fixture identifies only a publicly named building location, never a resident, unit, owner, or real listing.

### Fictional assumptions

- Asking price: TWD 24.8 million (`2,480 萬`)
- Area: 26 ping; age: 7 years; floor: 8
- Buyer cash: TWD 6.5 million; down payment: 20%
- Loan: 30 years at 2.40%
- Monthly household income: TWD 180,000
- Other monthly obligations: TWD 20,000
- Monthly ownership reserve: TWD 6,000
- Commute destination: Taipei City Hall, `臺北市信義區市府路1號`

All unit and financial assumptions are fictional. Do not infer a real sale or available terms. Do not hard-code market, valuation, route, risk, tax, or nearby-place outputs because live data changes.

## 17. Standard acceptance flow and invariants

```text
Enter property → confirm identity/location → market → valuation
→ location/map → commute → risk → finance → decision
→ save → reopen → compare → report
```

Then:

1. Change address to the public social-housing location `臺北市南港區向陽路248號`; old evidence must clear or become explicitly stale. Taipei City’s public notice identifies this as Xiaowan Social Housing: <https://health.gov.taipei/News_Content.aspx?n=644DCCC309F8D7F8&s=D271C5E8CC615C6E&sms=C6F19B8D392E863A>.
2. Change asking price from `2,480 萬` to `2,680 萬`; finance/decision must update or invalidate while property-bound location/risk remains.
3. Remove area; area-dependent costs must be missing/unestimated, not zero.
4. Exercise one approved provider-unavailable case; failure must remain local, explicit, safe, and retryable where appropriate.
5. Use back, forward, leave, and reopen; context must remain coherent or loss explicit/recoverable.
6. Repeat the primary flow at 390px using ordinary clicks, without page overflow blocking the task.

Test invariants, not exact dynamic values:

- correct visible active property;
- explicit units and understandable source/date;
- unavailable fails safely;
- no current-looking stale evidence after property change;
- module failure stays local;
- same-browser save/reopen preserves intended compact context;
- two eligible cases compare correctly;
- report distinguishes known, estimated, unavailable, and unknown.

Record evidence in `docs/commercial-acceptance-checklist-v1.md`.

## 18. Privacy and participant handling

Collect participant ID, role/experience range, timestamps/actions, public/test property inputs, fictional finance, structured notes, and only separately consented recordings.

Do not collect names, phone numbers, emails, IDs, private addresses, real income documents, bank statements, ownership documents, private transaction files, employer-confidential material, or credentials.

State that participation is voluntary, may stop/skip at any time, and has no job-performance implications. Describe the product as unfinished decision support that does not replace valuation, legal, tax, engineering, lending, or brokerage compliance advice. Make no pricing promises.

For recording, obtain separate explicit screen/audio/video consent, offer a non-recorded option, restrict access, define retention before recruitment, and delete on schedule. Never record unrelated tabs or notifications.

## 19. Analysis framework

Keep two evidence streams separate.

**Observed behavior:** completion, time, tools/searches/inputs, errors, interventions, recovery, reuse/report outcomes, client explanation, workflow replacement.

**Participant opinion:** stated trust, preference, value, desired output, blockers, and reuse intent.

Report one row per participant/task; ranges and medians for completed times where sensible; censored tasks separately; intervention/error/retry/recovery counts; recurring theme counts; strong/weak signals; and contradictions such as “faster” when observed time increased.

Do not calculate significance, extrapolate to the market, or hide critical incidents in averages.

## 20. Roadmap decision rules

| Pattern | Rule |
| --- | --- |
| Faster workflow, weak report | Preserve core flow; prioritize a broker-editable, source-aware report. |
| Demographics ignored | Keep it secondary; do not lengthen the core path. |
| Comparison heavily/correctly used | Strengthen multi-case navigation, identity, evidence, and export. |
| External price evidence still essential | Prioritize Market/Valuation coverage, freshness, and provenance. |
| Saved cases not reused | Question recurring SaaS positioning and test event-triggered/per-case value. |
| Fast but trust is wrong | Do not advance maturity; fix trust semantics first. |
| Property switching confuses | Stop expansion; make identity/invalidation the next release gate. |
| One provider fails but work finishes | Preserve isolation; prioritize only if client value repeatedly blocks. |
| External tools remain but PropTech indexes them | Test orchestration positioning rather than replacement. |
| Explanation improves but time does not | Test explanation/report as the primary job; do not claim efficiency. |

## 21. Pricing boundary

Do not invent or validate subscription pricing here. This is problem-solution fit. A later study may test per-user, per-team, per-case, report/export, and workflow value only after repeated-use evidence identifies displaced work and budget ownership.

## 22. Broker versus buyer secondary hypothesis

Brokers prepare many properties, compare cases, revisit work, and reuse client explanations, creating a plausible recurring loop. Buyers have fewer cases, a finite purchase episode, greater education needs, and different household/privacy dynamics.

A separate buyer pilot should test non-expert comprehension, episodic reuse, household collaboration, emotional confidence versus calibrated trust, and value across a purchase journey. Do not mix buyers and brokers in this six-person pilot or compare them statistically.

## 23. Stop and review

After six valid sessions, stop recruitment and review the gates. Stop earlier if a reproducible wrong-property, unknown-as-safe, or privacy incident occurs. Do not broaden the pilot, invent pricing, or inflate maturity without an explicit review.
