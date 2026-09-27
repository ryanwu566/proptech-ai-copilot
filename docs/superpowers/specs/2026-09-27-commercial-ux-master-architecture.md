# Commercial UX Master Architecture

**Status:** Final integration review for implementation approval
**Date:** 2026-09-27
**Repository baseline:** `docs/commercial-ux-integration-v1` at `3f369fbccd6391c0af99995513488364367892b9`
**Scope:** Commercial information architecture, state and presentation contracts, product language, pilot gates, and non-regression boundaries. This document does not authorize production-code changes.

## 1. Product decision

PropTech AI Copilot will become a case-first commercial property decision workspace for brokers and property professionals preparing an unfamiliar property for a viewing or client discussion. The product must preserve one explicit property context while the user gathers price, place, risk, and cost evidence; saves and reopens the case; compares it with other cases; and produces a client-readable summary.

The architecture optimizes for truthful evidence, fewer context mistakes, quicker preparation, and recoverable partial failure. It does not claim that the commercial hypothesis is proven. That claim remains gated by the broker pilot.

## 2. Source decision matrix

| Workstream | Primary objective | Major decisions | Terminology / design rules | Phases | Dependencies | Acceptance | Unresolved in source / integrated treatment |
|---|---|---|---|---|---|---|---|
| Workspace Architecture | Replace the root tool collection with a case-first, route-first workspace | Five analytical views; three entry paths; persistent property context; independent evidence slices; Compare and Report as actions | Provider detail is secondary; no safety/property score; local failure; one scroll owner on mobile | Foundation; Overview; four domain views; Compare/Report; cutover | Identity, reliability, commute, geological closures | Deep links, property integrity, save/reopen, 2–3 case compare, report, 390 px | Source assumed a future VNext anchor; the pending Identity closure explicitly supplies only a browser journey anchor, so v1 uses browser case routes and keeps VNext separate |
| Commercial Design System | Make the product quiet, analytical, credible, and consistent | Semantic tokens; fewer containers; one action color; no default card shadow; table/map/chart-led layouts | Green means completed process only; explicit units; tabular numerics; bounded warnings; progressive disclosure | Tokens/formatters; primitives; surface migrations; shell; responsive/accessibility; visual gate | Domain closures before sensitive page migrations; workspace architecture before shell | No nested-card soup; accessible states; maps and tables usable at 390 px | Token values require contrast verification; no architectural blocker |
| Product Language | Establish one customer-facing vocabulary and truth model | Separate query, evidence, completeness, risk, and readiness axes; layered provenance; typed localization | zh-TW primary; no engineering leakage; missing never zero; no-match is not safe; no winner/rank | State/formatters; glossary/nav; domain copy; risk; finance/case/report; locale certification | Same four closures plus architecture/design-system decisions | Axis separation, explicit units, locale parity, actionable errors, conservative reports | Proposed sixth tab `比較與摘要` conflicts with architecture; resolved in §4 |
| Broker Pilot / Acceptance | Falsify or support recurring broker workflow value | Six qualified participants; observed behavior over opinion; public/test data; controlled failures; hosted preflight | Active property, known/estimated/unknown, source/date, local recovery, save/reopen/compare/report | Hosted acceptance; six sessions; gate review; roadmap handoff | Commercial MVP implementation and production acceptance | 5/6 workflow/trust targets, 4/6 efficiency/reuse/value targets, zero critical integrity failures | Beta cannot be awarded by this pilot; retained as a later repeated-use gate |

### Shared assumptions

- Existing analytical providers and calculations remain valuable and must be preserved.
- The durable product object is a property case, not a provider query or chat thread.
- Property identity, evidence usability, and task readiness must be explicit and independently evaluated.
- Commercial v1 uses the browser-local `SavedCase` plus `JourneyPropertyIdentityAnchorV1`. That anchor is a correlation aid, not a durable VNext `PropertyEntity`, parcel identity, or legal identity.
- The current authenticated, feature-gated VNext professional workspace remains a separate surface until a separately approved case-ID/auth migration contract exists.
- Browser print is sufficient for v1 report output.
- Commercial implementation must remain reversible by bounded branch and route cutover.

## 3. Conflict resolution log

| # | Source A | Source B | Conflict | Final resolution | Why this wins |
|---:|---|---|---|---|---|
| 1 | Architecture: five primary property views; Compare/Report are actions | Product Language: sixth label `比較與摘要` | Cross-property and output tasks would be mixed into property analysis | Keep five primary views. Compare is `/compare`; Report is `/cases/[caseId]/report`; Overview owns the decision summary | Preserves object scope, URL integrity, and a coherent mental model |
| 2 | Architecture: `Location & Commute` | Product Language: `區位與周邊` | “周邊” hides the high-value destination-specific commute task | Final label `區位與通勤` / `Location & Commute`; POIs and demographics are subordinate evidence | Matches broker preparation and prevents Commute becoming an orphan card |
| 3 | Architecture: `Finance & Transaction` | Product Language: `資金與持有成本` | “Transaction” implies broader workflow than current capability | Final label `資金與持有成本` / `Finance & Costs`; Tax is contextual transaction detail | Uses concrete supported outcomes without promising transaction management |
| 4 | Architecture/Design: Risk & Environment | Product Language: `風險與待確認` | A navigation label should name the domain, not a transient state | Final label `風險與環境`; the view prominently separates findings, unknowns, and verification actions | Stable navigation plus truthful task semantics |
| 5 | Design System: green for successful completion | Product Language: query success should not imply usable evidence | A completed query could visually appear “good” | Query completion uses success semantics only beside explicit evidence/risk text; no green property or risk conclusion | Keeps process feedback without implying safety |
| 6 | Current UI: rank, score, top candidate | Architecture/Language/Pilot: explainable differences, no winner | Current comparison overclaims decision authority | Remove rank, winner, `bestCaseId`, and composite comparison score from the commercial model | Safer and more useful for professional explanation |
| 7 | Current risk summary: weighted overall score | Architecture/Language: no black-box property/safety score | Unlike domains are collapsed into one evaluative number | Reuse fact extraction only; Overview lists findings, unknowns, blockers, and next actions | Maintains traceability and avoids false certainty |
| 8 | Design source format: `NT$ 2,180 萬`, ISO dates | Language source: `2,180 萬元`, user-facing month/date patterns | Competing financial and date display conventions | zh-TW primary totals use `2,180 萬元`; detailed/report base amounts use `NT$24,800,000`; exact dates use `YYYY-MM-DD`, periods use `YYYY/MM–YYYY/MM` | One convention per context; storage units never dictate presentation |
| 9 | Architecture: route-first cutover | Current repository: root React `page` state and browser events | Immediate replacement would create a high-risk big bang | Add route/repository foundation in parallel, keep legacy entry behind a release flag, then cut over after parity | Protects current production behavior and enables rollback |
| 10 | Architecture: reopened cases restore evidence state | Current `case-storage.ts`: compacted comparables, coordinates, POIs, and terrain payloads | A reopened case cannot reproduce every live surface | Legacy adapter marks summary-only data `limited`; absent detail has `query_status=not_started` and no evidence result; no reconstruction or fabricated freshness | Honest migration while durable persistence is completed |
| 11 | Pilot checklist: current ranking may be bounded | Final language/architecture: no ranking at all | Acceptance wording could preserve a deprecated behavior | Update future acceptance to factual differences only; legacy checklist remains source evidence, not final product policy | Removes ambiguity before implementation |
| 12 | Design migration suggests visual-only early changes | Architecture has shared hotspots and route ownership changes | Page-level styling before shell extraction causes rework | Tokens, formatters, and isolated primitives may start early; page migrations follow domain and shell contracts | Lowest collision and regression risk |
| 13 | Workspace source proposed `/workspace/[caseId]` | Current repository reserves that path for an authenticated, UUID-only, feature-gated VNext shell; Identity closure is browser-only | Reusing the path would conflate local cases with VNext authorization and identifiers | Commercial v1 uses `/cases/[caseId]/[section]`; current `/workspace/[caseId]` remains unchanged. A later migration requires an approved ID mapping, auth, redirect, and data-migration contract | Avoids weakening VNext boundaries and makes the v1 plan executable against current code |

No architectural question remains that blocks foundation work. Durable repository integration, financial adapters, commute presentation, and geological risk mappings remain intentionally gated by their engineering closures.

## 4. Canonical commercial information architecture

### 4.1 Entry

1. **Known address — `分析物件`**: address → identity resolution → explicit confirmation → case Overview. Property Finder is not required.
2. **Area exploration — `找物件`**: `/explore` → candidate → the same identity confirmation → case Overview.
3. **Saved property — `已儲存案件`**: `/cases` or recent cases → one selection → case Overview.

No entry path silently runs the complete provider suite.

### 4.2 Property context

The route and repository scope one active case and one identity revision. Canonical routes are:

```text
/
/properties/new
/explore
/cases
/cases/[caseId]/overview
/cases/[caseId]/market
/cases/[caseId]/location
/cases/[caseId]/risk
/cases/[caseId]/finance
/cases/[caseId]/report
/compare?cases=id1,id2[,id3]
```

`/cases/[caseId]` redirects to Overview after the existing command-center content is migrated or linked from Overview. Browser case IDs remain opaque route segments and are resolved only through the browser case repository. Property identity never travels in a query parameter. Back, Forward, refresh, and deep links are first-class behavior.

The existing `/workspace/[caseId]` route retains its current VNext UUID validation, feature flag, authentication gate, and `workspaceId`/`propertyId` read contract. Commercial v1 does not redirect, weaken, or repurpose that route. Moving commercial cases to VNext is P2 until an explicit mapping between `SavedCase.id`, an authenticated case record, workspace membership, and `PropertyEntity` is approved.

### 4.3 Five primary property views

| Order | zh-TW / English | User question | Dominant content |
|---:|---|---|---|
| 1 | `物件總覽` / Overview | What matters now, what is unknown, and what should I do next? | Findings → unknowns → blockers → next actions |
| 2 | `價格與市場` / Market & Price | Is the price reasonable, and what observed evidence supports it? | Price bases → comparables table → distribution/trend → method |
| 3 | `區位與通勤` / Location & Commute | What is around the property, and how does a real destination journey work? | Confirmed map → relevant POIs → commute → demographics → sources |
| 4 | `風險與環境` / Risk & Environment | What environmental evidence and unknowns require investigation? | Evidence summary → map → ordered layers → unknowns → checks |
| 5 | `資金與持有成本` / Finance & Costs | What cash and monthly cost does this scenario imply, and what is missing? | Inputs → cash/monthly outcomes → breakdown → assumptions → contextual tax |

### 4.4 Compare, Report, and Decision Summary

- **Decision Summary** is the top of Overview and synthesizes only evidence tied to the current case revision. It is not a sixth module and does not provide purchase advice.
- **Compare** is a cross-property workflow launched from Saved Cases or a case action. It accepts two or three cases, aligns bases and units, and reports material differences and non-comparable fields. It never declares a winner.
- **Report** is a case output route for the current saved revision. It is not a workspace tab and does not mutate evidence.
- **Cross-property analysis** occurs only in Compare. A single-property Overview may mention that a case is eligible for comparison but cannot contain comparative conclusions.

### 4.5 Secondary and advanced placement

| Capability | Placement |
|---|---|
| Property Finder | Separate `/explore` entry workflow |
| Demographics | Secondary evidence in Location & Commute |
| Satellite Evidence | Secondary, explicitly non-statutory evidence in Risk & Environment |
| TaxOracle | Contextual detail in Finance & Costs; direct access under Advanced tools |
| Methodology and complete source lists | Per-result disclosure, then report appendix |
| Diagnostics, HTTP/provider IDs, raw codes | Authorized support/diagnostics only |
| VNext identity graph review | Advanced identity correction/review route |
| Aegis-Credit, demos, pilot/evidence tools | Advanced/internal routes, never primary navigation |

## 5. Final module disposition

| Current feature | Final location | Role | Disposition | Reason |
|---|---|---|---|---|
| Property Finder | `/explore` | Secondary entry | Contextualize | Valuable discovery path, harmful mandatory gate |
| Location Insight | Location & Commute | Primary evidence | Merge | Shares one resolved location and map |
| Map Insight | Location & Commute | Primary surface | Merge | Map is an analytical canvas, not a tool destination |
| Market Insight | Market & Price | Primary evidence | Merge | Answers the same price question as Valuation |
| Valuation | Market & Price | Primary evidence | Merge | Preserve model estimate versus observed transactions |
| Terrain Risk | Risk & Environment | Primary evidence | Merge | Independent layers remain explicit |
| Flood | Risk & Environment | Primary layer | Keep | Material official evidence with local failure |
| Landslide / debris flow | Risk & Environment | Primary layers | Keep | Separate matches, coverage, and limitations |
| Liquefaction | Risk & Environment | Primary layer | Keep | Never infer safe from no coverage/no match |
| Geological Sensitivity | Risk & Environment | Primary layer after closure | Keep | Wait for final ETL/runtime contract |
| Satellite Evidence | Risk & Environment | Secondary | De-emphasize | Visual reference, not legal/geological proof |
| Demographics | Location & Commute | Secondary | De-emphasize | Pilot determines whether it deserves further investment |
| Commute | Location & Commute | Primary evidence | Merge | Destination-specific professional value |
| Loan | Finance & Costs | Primary analysis | Merge | Scenario, never approval |
| Holding Cost | Finance & Costs | Primary analysis | Merge | Missing costs remain explicit |
| TaxOracle | Finance & Costs / Advanced | Conditional | Contextualize | Scenario-dependent and preliminary |
| Property Case | Repository, header, `/cases` | Foundation | Keep and migrate | Durable unit of work |
| Decision Summary | Overview | Primary synthesis | Merge | Retires duplicated readiness/risk summaries |
| Compare | `/compare` | Cross-property | Keep, replace ranking | Object scope differs from a property module |
| Report | `/cases/[caseId]/report` | Output | Merge exports | One current-revision client summary |

## 6. Canonical property context header

The header is a compact persistent control, never a hero. In commercial v1, “identity” means the bounded browser journey anchor and its accepted address/location evidence; it never claims VNext, parcel, building, ownership, or legal identity.

**Always visible:** property display address/title; identity state; active price label and value; save state; a revalidation marker when required.
**Desktop supporting line:** case name, last saved time, and a bounded phrase such as `3 個區段今天已更新`.
**Details sheet/disclosure:** normalized address, coordinates, parcel/building distinction, identity revision/provenance, per-source freshness, source IDs, and technical diagnostics.
**Actions:** Save, Change property, More. Report and Compare remain separate case/global actions.

Identity wording:

| State | zh-TW wording | Consequence |
|---|---|---|
| Unconfirmed | `物件尚待確認` | Identity-sensitive synthesis is blocked |
| Confirming | `正在確認物件` | Existing evidence remains visible but no new identity-dependent commitment |
| Confirmed | `物件已確認` | Analyses may run against the recorded revision |
| Conflict | `物件資料不一致，需要確認` | Unsafe synthesis/report is blocked |
| Revalidation required | `物件資料已變更，需重新確認` | Prior affected evidence is retained as stale and cannot appear current |

On mobile the header is at most two rows: property + identity, then price basis/value + save/revalidation. Details and change-property actions live in one overflow sheet.

## 7. Canonical state model

No rendered `status` is valid without an axis. The workspace stores axes independently and may render multiple axes together.

| Axis | Canonical states | zh-TW wording | Visual role | Valid use / invalid use | Transition example |
|---|---|---|---|---|---|
| A. Query execution | `not_started`, `input_required`, `in_progress`, `succeeded`, `failed`, `cancelled` | `尚未查詢`, `需要輸入資料`, `查詢中`, `查詢完成`, `查詢失敗`, `已停止查詢` | Neutral; amber for required input; blue progress; red only for failure | Valid: request lifecycle. Invalid: evidence quality, safety, completeness | `in_progress → succeeded` while evidence becomes `no_match` |
| B. Evidence usability | `usable`, `limited`, `no_match`, `no_coverage`, `unavailable`, `stale`, `unverified`, `unsupported` | `證據可供判讀`, `證據有限`, `查無符合資料`, `不在資料涵蓋範圍`, `目前無法取得證據`, `資料可能已過期`, `來源尚未驗證`, `目前不支援此項資料` | Neutral/information; amber for limited/stale/unverified; red only when task-blocking | Valid: source/scope/period usability. Invalid: risk level | WRA query succeeds but `no_coverage`; risk remains `unknown` |
| C. Analysis completeness | `not_started`, `insufficient`, `partial`, `sufficient_for_task`, `blocked` | `尚未分析`, `資料不足，無法判讀`, `分析僅完成部分`, `已足以進行「{task}」`, `分析無法完成` | Neutral, amber, or red blocker | Always names the task; never a universal completion percent | Market can be sufficient for preliminary discussion but insufficient for report |
| D. Risk interpretation | `elevated_signal`, `caution_signal`, `no_identified_signal`, `unknown`, `not_assessed` | `發現需優先確認的風險訊號`, `發現需進一步確認的訊號`, `目前資料未發現明確風險訊號`, `風險仍無法判定`, `尚未評估風險` | Red for material signal; amber for caution/unknown; neutral for scoped no-signal | Valid only from usable evidence with confirmed coverage and a domain contract where no match means no defined signal in that checked scope. Invalid from query success, an unqualified no-match, no coverage, unavailable, stale, or unverified evidence | Covered layer + defined no-match → scoped `no_identified_signal`, never “safe” |
| E. Property identity | `unconfirmed`, `confirming`, `confirmed`, `conflict`, `revalidation_required` | Header wording in §6 | Neutral/blue/green process/amber/red blocker; never property quality | Governs evidence fingerprints and unsafe synthesis | Address/coordinates change: `confirmed → revalidation_required → confirming → confirmed` |
| F. Task readiness | `not_ready`, `ready_with_limits`, `ready`, `blocked` per named task | `尚不足以…`, `可進行…，但仍有…`, `可進行…`, `需先解決…` | Neutral/amber/green process/red blocker | Valid for `viewing_preparation`, `comparison`, `client_discussion`, `report`, `offer_preparation`; invalid as universal readiness | Loan calculated + no income: cost scenario available, affordability not assessed |

### 7.1 Per-state contract

The tables below are the canonical rendering contract. “Invalid” means the state must not be used for that purpose, even if a legacy model currently does so.

| Query state | Meaning and zh-TW | Visual semantic role | Valid / invalid use | Transition and example |
|---|---|---|---|---|
| `not_started` | No request has been made — `尚未查詢` | Neutral | Valid before user/system initiation; invalid as missing evidence | `not_started → input_required` when an address is absent |
| `input_required` | A required input is missing — `需要輸入資料` | Amber action-needed | Valid for an actionable prerequisite; invalid for provider failure | Add destination, then `in_progress` |
| `in_progress` | Request is active — `查詢中` | Blue progress | Valid only while active; invalid as evidence quality | Route request starts |
| `succeeded` | Request completed normally — `查詢完成` | Green process completion | Valid for execution only; invalid as “data exists” or “safe” | May pair with evidence `usable`, `limited`, `no_match`, or `no_coverage` |
| `failed` | Request ended in error — `查詢失敗` | Red error | Valid for an actual failed attempt; invalid for unsupported scope | Retry may return to `in_progress` while old valid evidence remains |
| `cancelled` | Request was deliberately stopped/superseded — `已停止查詢` | Neutral | Valid for abort or supersession; invalid for timeout unless the client cancelled it | Property switch cancels an in-flight old-property request |

| Evidence state | Meaning and zh-TW | Visual semantic role | Valid / invalid use | Transition and example |
|---|---|---|---|---|
| `usable` | Evidence is fit for the stated scope/task — `證據可供判讀` | Neutral/information | Valid with source, scope, and period; invalid as universal truth | Fresh covered transactions validate successfully |
| `limited` | Some evidence is usable but materially constrained — `證據有限` | Amber limitation | Valid for small samples or compacted summaries; invalid as full coverage | Reopened compact case lacks row-level comparables |
| `no_match` | Covered query returned no matching record — `查無符合資料` | Neutral qualified absence | Valid only with confirmed query scope; invalid as safe or no risk by default | Covered, domain-defined no-match may support a scoped `no_identified_signal` |
| `no_coverage` | Source does not cover this place/time/type — `不在資料涵蓋範圍` | Amber limitation | Valid for proven coverage gaps; invalid as no-match | WRA layer excludes the coordinates |
| `unavailable` | Evidence cannot currently be obtained — `目前無法取得證據` | Amber, red only if task-blocking | Valid for outage/runtime failure; invalid as no coverage | Retry locally without clearing unrelated evidence |
| `stale` | Previously valid evidence no longer satisfies freshness/identity — `資料可能已過期` | Amber stale | Valid after time or relevant assumption change; invalid as current evidence | Price change makes payment evidence stale until recalculation |
| `unverified` | Evidence exists but provenance/integrity is not confirmed — `來源尚未驗證` | Amber trust warning | Valid for uncertain source or artifact; invalid as usable evidence | Validate checksum/source, then `usable` or `unavailable` |
| `unsupported` | Product intentionally does not support this evidence — `目前不支援此項資料` | Neutral limitation | Valid for out-of-scope capability; invalid for temporary errors | A requested specialized layer is outside commercial v1 |

Evidence has no `not_requested` state: before a query, `query_status=not_started` and the evidence result is absent. This prevents request lifecycle from masquerading as evidence quality.

| Completeness state | Meaning and zh-TW | Visual semantic role | Valid / invalid use | Transition and example |
|---|---|---|---|---|
| `not_started` | No analysis for the named task — `尚未分析` | Neutral | Valid before derivation; invalid when evidence was assessed | Report synthesis has not run |
| `insufficient` | Available evidence cannot support the named task — `資料不足，無法判讀` | Amber | Valid with named missing evidence; invalid as generic low confidence | One comparable is insufficient for price discussion |
| `partial` | Some required analysis is complete — `分析僅完成部分` | Amber | Valid when usable results remain; invalid as a completion percentage | Market range exists but trend is unavailable |
| `sufficient_for_task` | Evidence supports a named decision task — `已足以進行「{task}」` | Green process readiness | Valid only with task and limits; invalid as property approval | Enough for viewing preparation, not offer preparation |
| `blocked` | A prerequisite prevents analysis — `分析無法完成` | Red blocker | Valid for a concrete prerequisite/conflict; invalid for optional unopened evidence | Identity conflict blocks report synthesis |

| Risk state | Meaning and zh-TW | Visual semantic role | Valid / invalid use | Transition and example |
|---|---|---|---|---|
| `elevated_signal` | Material defined signal requires priority review — `發現需優先確認的風險訊號` | Red material signal | Valid from usable domain evidence; invalid as a legal conclusion | Covered geological evidence crosses a defined threshold |
| `caution_signal` | Evidence warrants further confirmation — `發現需進一步確認的訊號` | Amber caution | Valid for bounded concern; invalid as “high risk” without contract | Limited flood evidence prompts field verification |
| `no_identified_signal` | No defined signal found in the checked scope — `目前資料未發現明確風險訊號` | Neutral scoped result | Valid only with usable confirmed coverage and domain-defined semantics; invalid as safe/low risk | Covered cadastral check finds no defined overlap |
| `unknown` | Evidence cannot determine risk — `風險仍無法判定` | Amber unknown | Valid for no coverage, unavailable, stale, or unverified evidence; invalid as no signal | Provider outage leaves risk unknown |
| `not_assessed` | Risk interpretation has not run — `尚未評估風險` | Neutral | Valid before assessment; invalid after failed evidence retrieval, which is `unknown` | Newly opened optional layer |

| Identity state | Meaning and zh-TW | Visual semantic role | Valid / invalid use | Transition and example |
|---|---|---|---|---|
| `unconfirmed` | Browser-case property anchor lacks confirmation — `尚未確認物件` | Neutral | Valid before anchor confirmation; invalid as legal/VNext identity | New address entry begins unconfirmed |
| `confirming` | Address/coordinates/fingerprint are being resolved — `正在確認物件` | Blue progress | Valid during correlation; invalid as confirmed ownership | Geocoding and anchor comparison run |
| `confirmed` | Browser-case anchor is internally consistent — `物件已確認` | Green process completion | Valid for same-case evidence correlation; invalid as parcel/legal/VNext identity | Address and coordinates match saved fingerprint |
| `conflict` | Identity inputs disagree — `物件資料不一致，需要確認` | Red blocker | Valid for wrong-property risk; invalid as a dismissible warning | Saved coordinates disagree with resolved address |
| `revalidation_required` | Property/assumptions changed and affected evidence must be checked — `物件資料已變更，需重新確認` | Amber blocker | Valid after relevant mutation; invalid while silently showing old evidence current | Address change invalidates every property-bound slice |

| Readiness state | Meaning and zh-TW | Visual semantic role | Valid / invalid use | Transition and example |
|---|---|---|---|---|
| `not_ready` | Named task lacks required evidence — `尚不足以進行「{task}」` | Neutral/amber | Valid with missing prerequisites; invalid as universal product status | Comparison waits for a second confirmed case |
| `ready_with_limits` | Named task can proceed with explicit caveats — `可進行「{task}」，但仍有…` | Amber qualified readiness | Valid when limits are visible; invalid when a hard blocker exists | Client discussion can proceed with limited market sample |
| `ready` | Named task meets its declared minimum — `可進行「{task}」` | Green process completion | Valid only for one task/revision; invalid as recommendation | Current revision is ready for report generation |
| `blocked` | Named task cannot proceed until a concrete issue is resolved — `需先解決…，才能進行「{task}」` | Red blocker | Valid for identity conflict or unsafe input; invalid for optional evidence | Report blocked by mixed property revisions |

Hard invariants:

- Query success does not mean evidence is usable or analysis is complete.
- Query success, no match, no coverage, and unavailable never mean safe.
- Calculation completion does not mean affordability is assessed.
- Green never means a good property, good investment, low risk, or recommended purchase.
- Optional unopened evidence does not automatically block a named task.

## 8. Final numeric and unit contract

| Value | Canonical primary presentation | Rules |
|---|---|---|
| Asking price | `開價：2,480 萬元` | Preserve seller/listing origin |
| User-entered price | `比較基準價格：2,480 萬元（依輸入條件）` | Never relabel as estimate |
| Estimated price | `成交資料推估區間：1,720–1,980 萬元`; midpoint secondary | Never `官方估價`; state confidence/evidence |
| Market median | `市場成交中位數：52.4 萬元／坪` | Include geography, period, sample |
| Comparable price | Total `1,850 萬元`; unit `51.8 萬元／坪` | Columns declare unit and transaction period |
| Price range | `1,720–1,980 萬元` | En dash; no ambiguous `萬` |
| Loan principal | `貸款本金：1,984 萬元` or detailed `NT$19,840,000` | State scenario basis |
| Monthly payment | `NT$60,752／月` | Never place raw NTD under a 萬元 label |
| Monthly income | `NT$180,000／月` | State gross/net basis where relevant |
| Holding cost | `NT$12,400／月`; `NT$148,800／年` | List included and unestimated categories |
| Tax | `{稅名}估算：NT$…／年` or transaction-specific amount | Name tax, scenario, period |
| Percentage | `18.7%` | State numerator/denominator for burden ratios |
| Area | `26.0 坪`; optional `（86.0 平方公尺）` | One decimal maximum unless source requires more |
| Distance | `450 公尺`; `1.2 公里`; `12 公里` | Method qualifier: straight-line/route |
| Duration | `約 28 分鐘`; `1 小時 15 分鐘` | Name travel mode and traffic basis |
| Exact date | `2026-09-27` | Absolute date for retrieval/check detail |
| Period | `2025/01–2026/07`; quarter `2026 Q2` | Period precedes query time |
| Source vintage | `圖資版本：2025 年版` or `最新統計期：2026/06` | Never replace with relative time only |

Inputs for total price may use a field label `開價（萬元）` with the numeric value `2,480`. Display results add the full unit. `—` is only a compact unavailable marker when an adjacent state explains why. Prefer `未提供`, `尚未估算`, `未納入`, `不適用`, `不在涵蓋範圍`, or `目前無法取得`.

Missing financial values must never silently become `0` or `NT$0`. Zero is valid only when a domain contract explicitly proves a real zero amount.

## 9. Integrated design principles

1. Structure before decoration; page sections and dividers precede containers.
2. Use fewer cards; a card requires independent interaction, state, or lifecycle.
3. Use one primary action color and one dominant action per section.
4. No default card shadow; use restrained 6/8/12 px radii and overlay shadow only where spatially required.
5. Explicit units and tabular figures for comparable numbers.
6. Query, evidence, completeness, risk, identity, and readiness semantics remain visually distinct.
7. Maps are large analytical surfaces; tables are primary for comparable evidence.
8. Errors remain local and preserve unrelated and previous valid evidence.
9. Methodology, full provenance, and diagnostics use progressive disclosure.
10. Mobile layouts are task-specific, not desktop scaled down; the document is the normal scroll owner.
11. Warnings appear once at the affected result boundary and are proportional to consequence.
12. Status never relies on color alone; WCAG 2.2 AA, visible focus, reduced motion, and 44 px mobile targets are minimums.

## 10. Content rhythm by workspace

| View | Required rhythm |
|---|---|
| Overview | Current posture → up to five findings → material unknowns → blockers → three to five next actions → supporting details |
| Market & Price | Labeled price bases → primary comparable table → range/distribution → trend/volume → method/source disclosure |
| Location & Commute | Confirmed address/map → relevant facility evidence → saved commute destinations/routes → demographics → source detail |
| Risk & Environment | Coverage and finding summary → map → ordered evidence table → unknown/unavailable sources → verification actions → source detail |
| Finance & Costs | Price/loan/holding inputs → cash/monthly/annual outcomes → breakdown/sensitivity → assumptions/missing costs → contextual tax |

These views share tokens and state semantics, not identical layouts.

## 11. What leaves primary UI

HTTP methods/status, API routes, provider adapter IDs, raw source/reason/error codes, request IDs, backend field names, raw enums, database/storage language, rule IDs such as `TX001`, duplicate source cards, repeated methodology, debug wording, unqualified demo/fallback output, “Lite” labels, provider health claims without real health data, black-box scores, duplicate warnings, and feature-gallery navigation move to diagnostics, method detail, advanced/internal routes, or are removed.

## 12. Score policy

| Score | Policy |
|---|---|
| Location overall score | Remove from primary UI unless formula/range/inputs can be explained; prefer raw proximity evidence |
| POI/category indices | May remain secondary as qualified 0–100 indices with formula and coverage disclosure |
| Risk score | No overall property or safety score; show layer findings and unknowns |
| Tax score | Replace with eligibility state, failed/missing conditions, and review items |
| Valuation confidence | Retain as categorical `價格推估可信度`; number belongs in methodology |
| Evidence confidence/quality | Categorical reasons based on provenance, coverage, freshness, and completeness |
| Case completeness | May show completed/required counts neutrally; never investment merit or readiness |
| Comparison score/rank | Remove; use normalized factual deltas and non-comparable explanations |

## 13. Three-layer provenance

| Layer | Content | Examples |
|---|---|---|
| Primary result | Result, state, unit, effective period, one material limitation | PLVR median/sample; WRA scoped no-signal; route duration; valuation range |
| Expanded evidence | Agency/dataset, geography/period, method, coverage, vintage, exclusions | PLVR filters; WRA layer/radius; RIS village/statistic month; liquefaction scale; geological artifact version; Google route mode/traffic basis |
| Diagnostics/support | Adapter/provider ID, endpoint, HTTP status, request ID, raw code, import/model version | Available only in authorized support detail |

Provider names never substitute for a result. Official source data does not make a derived valuation an official appraisal. Geological, liquefaction, flood, or satellite evidence never claims parcel certainty when only a point/radius was checked.

## 14. Failure recovery contract

| Failure/change | Remains usable | Stale / clears | User sees | Next action / retry |
|---|---|---|---|---|
| Valuation unavailable/malformed | Asking/manual price, market, location, risk, finance using another basis | Invalid estimate is not stored; estimate-based finance becomes stale | `目前無法取得價格推估`; no invented range | Retry valuation locally or choose asking/manual basis |
| Commute unavailable | Address, map, POIs, demographics, other destinations | Only failed route clears/current prior route may remain dated | Route-specific unavailable state | Retry route or edit destination/mode locally |
| Risk source unavailable | Other layers and prior valid evidence | Failed layer unavailable; no sibling clear | `目前無法取得{layer}` and risk remains unknown for that scope | Retry layer locally; show manual check |
| Geological source unavailable | All non-geological evidence | Geological row unavailable | No-match is never fabricated | Retry after closure/provider recovery; official portal check |
| Market unavailable | Asking/manual price, valuation if valid, location, risk, and finance using an explicit basis | Market slice unavailable; prior observations may remain dated/stale | `目前無法取得區域成交資料`; no zero median/sample | Retry Market locally or proceed with an explicit limitation |
| No coverage | Other evidence | Nothing fabricated or globally cleared | `不在資料涵蓋範圍`; consequence | Use alternate/official verification |
| Malformed evidence | Prior valid evidence and siblings | Reject malformed payload; prior evidence is dated/stale | `取得的資料無法安全判讀` | Local retry/support reference |
| Stale identity | Notes and explicitly identity-independent content | Identity-dependent evidence marked stale, not current | Persistent header warning + Overview blocker | Review identity, then selective refresh |
| Missing area | Non-area market/location/risk and valid finance items | Area-dependent costs unestimated | `尚未估算（缺少坪數）` | Enter area; recompute dependent items only |
| Price changed | Property/location/risk/market | Finance/tax/decision using old basis stale | Changed basis and affected outputs | Recalculate affected slices |
| Save fails | Current in-memory case and all obtained evidence | Save state becomes failed; nothing is discarded | `儲存失敗`; warn before leaving when material edits remain | Retry Save locally; navigation never clears work |
| Browser Back/Forward | Committed route/case state | Ephemeral drawers only | Correct section and header | No recovery needed; invalid route gets bounded state |
| Saved case reopen | Compacted trusted summaries and identity/assumptions | Summary evidence may be `limited`; absent detail has `query_status=not_started` and no evidence result | Honest freshness and persistence scope | Refresh selected evidence; never reconstruct |

Global page failure is reserved for a case shell that cannot load or is unauthorized. A local retry mutates one evidence slice.

## 15. Property-change invalidation

Legend: **P** preserve, **R** recompute, **I** invalidate/clear, **S** retain visibly stale, **V** revalidate.

| Change | Location | Market | Valuation | Commute | Risk | Finance | Tax | Decision | Report |
|---|---|---|---|---|---|---|---|---|---|
| Address or selected property changes | I/R | I/R | I/R | I/R origin | I/R | I/R | I/R | I/R | I/R |
| Coordinates change | I/R | V; R if geography changes | V; R if scope changes | I/R origin | I/R | P unless dependent property fact changes | P/S by scenario | S | S |
| Identity conflict | S/V | S/V | S/V | S/V | S/V | S if identity-dependent | S | blocked | blocked |
| Asking price changes | P | P | P | P | P | I/R when asking basis | I/R when amount-dependent | S/R | S/R |
| Area changes | P | P unless filter scope chosen | I/R | P | P | I/R area-dependent costs | R if area affects scenario | S/R | S/R |
| Loan assumptions change | P | P | P | P | P | R loan/affordability only | P | R | S/R |
| Commute destination changes | P | P | P | I/R selected route only | P | P | P | R if material finding | S/R |

Every response carries case revision plus an input fingerprint. Late responses with an older revision/fingerprint are discarded. Before a property/identity change, the UI previews affected evidence. User-authored notes remain attached to the old revision unless the user explicitly carries them forward.

## 16. Responsive commercial architecture

| Surface | Desktop 1280–1440+ | Tablet 768–1024 | Mobile 390 |
|---|---|---|---|
| Property header | Compact sticky below top bar, ≤88 px | Compact top context | Two rows; details sheet |
| Navigation | Stable five-link rail/tab | Collapsed rail or top control | Current-section control or scrollable tabs; no page overflow |
| Maps | 60/40 or 65/35; minimum height 520 px | Stack unless ≥480/320 split fits | Fill the 358 px content width inside 16 px gutters; minimum height 360 px; full-screen option; in-flow results |
| Evidence tables | Dense semantic table, sticky header as needed | Selective scroll/pinning | Stacked rows or one-axis table scroll; never body scroll |
| Finance inputs | 320–360 px inputs + fluid results | Two columns when labels fit | One column, joined units, one full-width primary action |
| Comparison | Up to three case columns | Two columns or metric groups | Metric-first/case-stacked view with sticky selector |
| Report | 960 px reading width, print preview | Fluid reading layout | Reading order preserved; print/export action explicit |
| Disclosures | Quiet inline/details | Same | Accordion summary includes state; avoid multiple large opens |
| Sticky elements | Header plus at most one context panel | Header only by default | Header; bottom CTA only for a clear incomplete action |

## 17. Commercial MVP Pilot Ready gate

All of the following are required on the exact hosted candidate:

- Known-address, area-exploration, and saved-case entry work without coaching.
- One coherent active property identity persists across all primary views, save/reopen, Compare, and Report.
- Valuation and holding-cost reliability closure is merged; malformed/null financial results fail locally; units are explicit; missing costs are never zero.
- Identity closure is merged; its browser journey anchor persists with `SavedCase`, and property changes invalidate/revalidate deterministically without being described as VNext identity.
- Commute closure is merged; route failure is local and route evidence is case-scoped.
- Geological Sensitivity closure is merged; a runtime provider outage may still render that layer explicitly unavailable without blocking unrelated Risk evidence.
- Market, location, commute, risk, finance, unknowns, save, reopen, two-case comparison, and browser-print report are usable.
- Compare contains no winner/rank/composite score; Report distinguishes known, estimated, unavailable, and unknown.
- Desktop and 390 px primary workflows pass; Back/Forward/refresh preserve coherent context.
- Professional language, provenance layering, unit consistency, accessibility basics, and visual acceptance pass.
- Hosted acceptance has no core `FAIL` or critical integrity incident.
- Broker pilot gates pass: at least 5/6 workflow/trust targets, 4/6 efficiency/reuse/commercial signals, and zero wrong-property or unknown-as-safe client claims.

This label authorizes a larger controlled broker pilot, not general launch.

## 18. Commercial Beta gate

Beta requires all MVP gates plus a later multi-week study showing repeated independent use on real professional workflows, successful save/reopen reuse, useful comparison and client-shareable reports, acceptable support burden, reliable hosted/provider operation, privacy practice, no critical property-context errors, and demonstrated recovery from local failures. At least one real return-use trigger and displaced task must be observed; satisfaction alone is insufficient.

## 19. Product decision ↔ pilot evidence

| Observed pilot pattern | Product decision |
|---|---|
| Demographics ignored | Keep secondary; do not lengthen primary flow |
| Compare used correctly and changes preparation | Prioritize navigation, identity alignment, differences, and compare output |
| Compare merely restates information | Keep secondary; do not market as core differentiator |
| Save/reopen removes repeated work | Strengthen durable repository and recent-case entry |
| Save/reopen unused | Re-test recurring SaaS value and return triggers |
| External valuation checks remain necessary | Prioritize coverage, freshness, comparable evidence, and provenance |
| Report is not client-shareable | Prioritize editable/source-aware output before new modules |
| One provider fails but work completes | Preserve isolation; prioritize provider work only when client value repeatedly blocks |
| Unknown/unavailable read as safe or zero | NO-GO; fix semantics before another session |
| Property switching causes confusion | Stop expansion; identity/invalidation becomes the next release gate |

## 20. Deliberately deferred

- General AI chat or ungrounded generated recommendations.
- A universal investment, safety, location, tax, confidence, or comparison score.
- More random government/provider modules without a validated job.
- CRM, contacts, assignments, document management/vault, title/ownership workflows, and enterprise permissions.
- Self-host migration and portfolio tooling above three properties.
- Decorative visualization gimmicks, elaborate motion, or marketing rebrand.
- Server-generated PDF while browser print meets acceptance.
- Irreversible local-case migration before durable case/identity contracts are approved.

## 21. Do-not-break contracts

Commercial redesign must not silently remove or weaken PLVR market/valuation evidence, RIS demographics, NLSC/cadastral reference boundaries, WRA flood evidence, Earth Engine/satellite evidence, Google Maps/Routes attribution and routing, existing loan/holding/tax calculations, existing case persistence and compatibility loading, current production deployment boundaries, authenticated VNext reads, or tested API contracts. Presentation adapters may normalize semantics; backend provider contracts change only when an engineering closure explicitly owns that change. In particular, commercial routing must not bypass the VNext feature flag, UUID validation, authentication, or workspace/property authorization checks.

## 22. Implementation readiness

**A. Compatibility:** Yes. The four source workstreams are compatible after the twelve resolutions above.
**B. Closures that merge first:** Identity, Valuation/Holding reliability, Commute, and Geological Sensitivity must land before their dependent domain/page work; see the implementation plan for exact order.
**C. Safe first commercial epic:** semantic state/unit contract and isolated design-system foundations, followed by the browser-case repository and `/cases/[caseId]/[section]` shell once Identity is merged.
**D. Do not start yet:** page-level Finance, Location/Commute, Risk, and shell cutover; each depends on a closure or shared hotspot.
**E. Most dangerous files:** `frontend_next/app/page.tsx`, `lib/closed-loop-journey.ts`, `lib/case-storage.ts`, `lib/property-case.ts`, `lib/api.ts`, guided journey stages, and shared UI/copy registries.
**F. Blocking architectural questions:** none for browser-local commercial v1 because the route boundary is resolved above. A future VNext migration remains intentionally blocked until an approved case-ID mapping, authentication, authorization, redirect, and data-migration contract exists.
