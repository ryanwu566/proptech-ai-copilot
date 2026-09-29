# Commercial Property Workspace Design

**Status:** Proposed architecture for implementation review

**Date:** 2026-09-27

**Repository baseline:** `docs/commercial-workspace-architecture-v1` at `7f442f8aa9f2217b872fa703065ea522dd8a8457`

**Scope:** Information architecture, routing, state ownership, failure boundaries, responsive behavior, and component reuse. No production UI or application-logic changes are included.

## 1. Product intent and success definition

The next commercial experience must help a buyer or real-estate professional answer one practical question:

> Should I spend more time investigating or viewing this property?

The durable unit is a **property case**. A user can create or reopen a case, confirm what property it represents, inspect evidence by decision question, save it, compare it with two other cases, and produce a client-readable report. The primary interface does not require knowledge of providers, APIs, agencies, backend modules, or internal readiness enums.

Success means:

- a known-address user reaches useful evidence without using Property Finder;
- all evidence is visibly scoped to one active case and one property identity;
- Market and Valuation answer one price question;
- Location, Map, Commute, and demographics answer one place question;
- environmental layers remain independent evidence, not a synthetic safety score;
- Loan, Holding Cost, affordability, and contextual transaction tax answer one cost question;
- optional evidence does not create false incompleteness;
- navigation survives Back, Forward, refresh, deep links, and reopening a saved case;
- a provider failure is local and never clears unrelated case evidence;
- the 390 px experience has one scroll owner and no page-level horizontal overflow.

## 2. Architecture decision summary

1. **Case-first, route-first workspace.** The canonical context is `/workspace/[caseId]/[section]`; section state is a URL segment, not root-page React state.
2. **Five primary views.** `Overview`, `Market & Price`, `Location & Commute`, `Risk & Environment`, and `Finance & Transaction` are the only primary workspace destinations.
3. **Separate entry workflows.** Known address, area exploration, and saved-case reopening converge on a case before analysis. Property Finder remains `/explore`, not the mandatory first workspace step.
4. **Persistent property context.** One compact header owns address/identity, active price basis, save state, and bounded freshness. It is not a provider badge strip.
5. **Independent evidence slices.** Each capability has its own status, payload, error, freshness, and invalidation key. An aggregate view reads slices but never owns or erases them.
6. **Progressive disclosure.** Decision-relevant evidence is primary; methodology, source/provider detail, diagnostics, and advanced filters are disclosures or advanced tools.
7. **Compare and report are actions.** Compare is a cross-case route. Report is a case output route. Neither appears as a normal analytical tab.
8. **No black-box decision score.** Overview synthesizes findings, unknowns, blockers, and actions. Risk does not create a property safety score; comparison does not name an arbitrary winner.
9. **VNext identity is the future anchor.** The approved PropertyEntity/workspace/case contracts should become the durable identity layer after the active closure merges. Legacy browser cases require an adapter during migration, not a second permanent domain model.
10. **Current calculators and evidence views are reused behind wrappers.** The root page, guided-step shells, repeated readiness strips, and tool-first navigation are presentation debt; proven analytical components and pure view-model functions remain valuable.

## 3. Actual current frontend architecture

### 3.1 Route and composition map

| Route/surface | Current composition | State and navigation consequence |
|---|---|---|
| `/` | `app/page.tsx` (1,042 lines) owns the guided journey, standalone tools, dashboard variants, TaxOracle, Market, Map, and Valuation | `page: AppPage` plus `setPage()` replaces views without changing the URL. Back/Forward, deep links, refresh, and focus history are ambiguous. |
| `/cases/[caseId]` | `PropertyCaseCommandCenter` | Route exists, but the command center initializes its own client state and is separate from the root guided journey. |
| `/workspace/[caseId]` | Feature-gated `ProfessionalWorkspaceShell` with `workspaceId` and `propertyId` query parameters | Strong authenticated PropertyEntity/evidence read boundary, but the current shell is an incomplete technical investigation surface, not the commercial IA. |
| `/vnext/property-identity` | Auth-gated identity resolution, confirmation, case creation, and attachment workflow | The future durable identity/case foundation is present but isolated from commercial analysis. |
| `/vnext/property-identity/[workspaceId]/[propertyId]` | Identity graph review | Useful advanced identity correction surface; not suitable as primary commercial navigation. |

The root page owns `ClosedLoopJourneyState`, listens to browser events, hydrates local saved cases, and embeds domain tools conditionally. `closed-loop-journey.ts` contains valuable selective invalidation rules, but state lifetime is the root component rather than a route-scoped case repository. `case-storage.ts` stores at most ten compacted cases in `localStorage`; raw comparables, resolved coordinates, POIs, and full terrain payloads are deliberately removed, so reopened cases cannot reproduce every live surface.

### 3.2 Complete current-surface inventory

| Current surface | User task and entry point | Current state owner | Data dependencies and output | Overlap | Recommended role | Commercial value |
|---|---|---|---|---|---|---|
| Homepage/hero/dashboard | Start, continue, demo, inspect readiness; `/` | `app/page.tsx`, workflow session keys | Session/local context; hero, competing entry panels, readiness, decision panels | Guided journey, dashboard, viewing decision, next actions | Replace with three explicit entry paths plus recent cases | High as acquisition/return entry, low as analytical dashboard |
| Guided Property Journey | Move through property → location → price → affordability → decision | `GuidedPropertyJourney` plus root `ClosedLoopJourneyState` | All analysis results; renders one visited stage at a time | Duplicates workspace navigation and repeated headers/status strips | Remove from primary navigation; retain orchestration logic during migration | Medium transitional value |
| Property Finder | Explore by geography, budget, area, type, age; journey step or dashboard anchor | Local component state; result lifted to journey | `/valuation/property-search`; suggestions, transactions, distribution charts | Market comparables and known-address entry | Separate `/explore` workflow; selected candidate creates a case | High for discovery, harmful as a mandatory gate |
| Property Context headers | Remind user which property/price is active | Several journey header components | `JourneyPropertyContext` | Repeated across location, price, affordability, decision | Merge into one persistent workspace header | Essential trust infrastructure |
| Location Insight | Resolve address, summarize amenities, buyer fit, demographics | Component local state plus callback/session key | `/location/insight`; geocoding acceptance, POIs, scores, demographics | Map, commute, terrain, valuation context | Primary evidence engine inside Location & Commute | High, after reducing generic scores |
| Map Insight | Search/geocode, inspect nearby POIs on map | Root-defined component local state | `/map/search`, `/map/nearby`, Google health, road catalogs; Leaflet map/list | Location Insight POIs and source badges | Merge into map-first Location & Commute | High |
| Demographics | Understand village population context | Presentational child of Location result | Location response village resolution and demographics | Location context | Secondary contextual evidence | Medium |
| Commute station lookup | Check nearest station/lines/distance | `CommuteLivabilityCard` local state | `/commute/address-lookup` | Location transit category | Primary subsection of Location & Commute | High when production closure lands |
| Commute route | Estimate duration/distance to user destination | `CommuteRouteCard` local state | `/commute/route` | Station lookup | Primary configurable evidence, destination-dependent | High |
| Market Insight | Understand area/road price, history, volume, scope and freshness | Root-defined component local state; callbacks into journey | `/market-insights`; evidence panel, charts, scope, segmentation | Property Finder transactions and Valuation | Merge into Market & Price | High |
| Market segmentation/comparables | Filter and inspect similar historical transactions | `MarketSegmentationPanel` local state | `/market-insights/segment` and comparables | Property Finder and valuation comparables | Main analytical evidence in Market & Price; filters advanced | High |
| Valuation | Estimate range and confidence for one property | Root-defined component with extensive local/session/event state | road catalogs, `/valuation/estimate`, trend, status; range/confidence/charts | Market Insight, price basis, Loan/Holding handoff | Merge into Market & Price; calculation remains independent | High |
| Active price basis | Choose asking, system estimate, or manual assumption | `ClosedLoopJourneyState` | `JourneyPriceBasis`, valuation midpoint, asking/manual values | Valuation and finance | Persistent shared case assumption; always labeled | Essential |
| Terrain/Risk | Investigate terrain and seven hazard layers | `TerrainRiskAnalysis` local state plus journey callback | `/terrain-risk/analyze`, parcel upload/consistency/spatial APIs | Location, map, risk summary | Primary Risk & Environment view | High |
| Cadastral/parcel evidence | Inspect point, user geometry, cadastral overlay and consistency | Terrain child; VNext professional shell has separate Case Parcel Set | Leaflet overlay, parcel upload, graph cross-reference | Identity and terrain | Advanced detail in Risk; identity mismatch can become blocker | Medium/high professionally |
| Satellite Evidence | Inspect bounded 90-day imagery | Component local state | `/terrain/satellite-reference`; image, date, caveats | Terrain map | Secondary contextual evidence in Risk | Medium |
| Risk Summary | Combine price, finance, location, terrain into signal/actions | Pure `buildRiskSummary()` model | Cross-domain results | Decision summary/readiness/attention panels | Do not use as a safety score; reuse factor extraction for Overview | Medium after refactor |
| Loan | Estimate down payment, loan, monthly payment, burden | `LoanCalculator` local state plus session/events | mortgage/bank rates and `/loan/calculate`; charts/sensitivity | Holding Cost and price basis | Primary Finance & Transaction analysis | High |
| Holding Cost | Estimate recurring known costs and income burden | `HoldingCostCalculator` local state plus session/events | `/holding-cost/calculate`; composition and affordability visualization | Loan and affordability | Primary Finance & Transaction analysis | High |
| Affordability status | Interpret loan/holding results if income exists | Journey context and visualization components | Loan/Holding income burden | Finance completion/readiness | Conditional finance summary, never a completion synonym | High when inputs exist |
| TaxOracle | Evaluate a bounded transaction-tax scenario | Root-defined local state; standalone nav and embedded tool | `/taxoracle/analyze`, demo cases, rule traces, HTML report | Holding cost and transaction context | Contextual transaction detail; advanced standalone entry removed | Medium, scenario-dependent |
| Decision stage | Synthesize evidence, readiness, attention, save/list cases | `DecisionCaseStage` plus several derived models | All journey statuses | Dashboard viewing decision, risk summary, case overview | Replace with Overview & Next Actions | High concept, currently repetitive |
| Property Case manager | Save/load/delete local cases, select comparison | `CaseManager` plus `localStorage` | compact `SavedCaseData`, browser events | VNext cases and case command center | Saved Cases library; adapt to durable repository | Essential |
| Property Case command center | Financial scenarios, viewing log, due diligence, offer, timeline | Component local state initialized per mount | Pure property-case models | Decision stage, finance, overview, report | Advanced case planning; selected portions move/contextualize | Medium/high for professionals |
| Compare | Compare 2–3 local cases, score/rank, export HTML | `CaseComparisonPanel`; pure comparison libs | compact saved cases | Report and saved cases | Separate workflow; remove rank/winner, emphasize material deltas | High |
| Decision Report | Rule-based summary/checklist | Presentational component | valuation required; cross-domain inputs | Valuation HTML export and comparison report | Merge into one case report model | High |
| Valuation HTML export | Download valuation-led HTML | Root page and `valuation-share.ts` | selected saved/live evidence | Decision Report | Replace with case report route and print stylesheet | Medium transitional |
| Comparison report | Print comparison synopsis | comparison report libs/components | comparison result | Compare | Keep as compare output, separate from single-case report | Medium |
| Property Identity workflow/review | Resolve, confirm, reject, graph and attach case | Authenticated VNext client/component state | workspace/property/case/evidence contracts | Property context, cadastral evidence | Identity confirmation is entry gate; graph review is advanced | Essential future anchor |
| Professional Workspace shell | Authenticated case/identity/parcel evidence shell | Route component local load state | workspace, PropertyEntity, graph, evidence, Case Parcel Set | Proposed workspace and identity | Reuse contracts/load boundaries; replace technical IA | High foundation, low current commercial usability |
| Sidebar/AppShell | Navigate standalone root tools | `AppPage` local state | Translation keys only | Guided journey stepper | Replace with route links and case actions | Essential shell, current taxonomy obsolete |
| Responsive components | Mobile drawer, swipe tables, stacked grids, responsive maps | Individual components | CSS/Tailwind and Playwright tests | Inconsistent across modules | Reuse tested primitives; redesign workspace-level behavior | High quality requirement |

### 3.3 Current strengths to preserve

- `closed-loop-journey.ts` already distinguishes address-dependent, valuation-dependent, and price-dependent invalidation.
- Market has explicit no-data, partial, stale, and network-error states and does not invent zero metrics.
- Terrain keeps hazard layers independent and records missing sources and recommended checks.
- VNext identity uses strict contracts, authorization, case attachment, and explicit human confirmation.
- Existing visual models separate data transformation from rendering in several domains.
- Mobile tests already target 390×844 overflow and key interactions.
- Case compaction has an explicit trusted-evidence boundary rather than storing arbitrary payloads.

### 3.4 Current architectural liabilities

- Root `page.tsx` is both router, state store, event bus, data coordinator, and presentation layer.
- The URL does not identify the selected root tool or guided step.
- Browser events and session keys create hidden coupling between tools.
- Local case persistence and VNext durable cases are parallel models with no repository boundary.
- Guided-stage status strips, readiness summary, attention panel, dashboard decision panel, and risk summary repeat interpretations.
- Current comparison calculates a weighted rank and “best” case, contrary to the commercial requirement for explainable differences.
- Saved-case compaction intentionally drops data required by full reopened analytical views.
- Source/provider names are visible in primary cards and technical VNext readiness language dominates the professional shell.

## 4. Module classification

| Module | Classification | Decision |
|---|---|---|
| Property Finder | Separate workflow | Keep at `/explore`; candidate selection creates/opens a case. Remove from required known-address path. |
| Location Insight | Primary workspace view | Core evidence engine within Location & Commute. |
| Map Insight | Primary workspace view | Becomes the main canvas for Location & Commute, not a separate nav item. |
| Market Insight | Primary workspace view | Combined with Valuation under Market & Price. |
| Valuation | Primary workspace view | One evidence block within Market & Price; preserve estimate versus observed transactions. |
| Terrain / Risk | Primary workspace view | Unified Risk & Environment, with independent layers. |
| Satellite Evidence | Secondary contextual evidence | Risk visual context; clearly non-statutory. |
| Demographics | Secondary contextual evidence | Area context within Location & Commute. |
| Commute | Primary workspace view | Destination-specific evidence within Location & Commute. |
| Loan | Primary workspace view | Finance & Transaction. |
| Holding Cost | Primary workspace view | Finance & Transaction. |
| TaxOracle | Advanced detail/contextual evidence | Show when transaction scenario requires it; retain direct advanced-tool access outside primary nav. |
| Property Case | Separate workflow/foundation | Durable workspace container and Saved Cases library, not an analytical tab. |
| Compare | Separate workflow | Cross-case route and action. |
| Decision Summary | Primary workspace view after merge | Its useful synthesis becomes Overview; repeated readiness shells are retired. |
| Report / Export | Report-only output | Case action and route; not a tab. |
| Property Identity graph review | Advanced detail | Entry confirmation and blocker handling are primary; graph internals live under identity details. |
| Aegis-Credit, pilot/evidence/demo tools | Remove from primary navigation but retain functionality | Place under Advanced tools or internal/pilot routes. |

## 5. Entry architecture

### 5.1 Homepage

The homepage has one product narrative and three paths:

1. **Analyze an address** — primary CTA and address field.
2. **Explore an area** — secondary CTA to `/explore`.
3. **Open a saved case** — recent cases plus “View all saved cases” to `/cases`.

Marketing/demo/pilot evidence is below the primary entry area or on explicit internal routes. It does not compete with the main CTA.

### 5.2 Known address

1. User enters an address on `/` or `/properties/new`.
2. The system resolves identity candidates without running every analysis.
3. A compact confirmation step displays entered address, normalized address, map pin/administrative context, and any mismatch.
4. On a confident single match, the primary action is **Confirm and open workspace**; on ambiguity, candidates require selection; on unavailable identity service, the user may create an explicitly unconfirmed draft if policy allows.
5. Confirmation creates/attaches a case and redirects to `/workspace/[caseId]/overview`.
6. Overview immediately shows available cached evidence and the single most useful next action. Evidence requests remain user-controlled or follow a documented lightweight default; no hidden full-suite auto-run.

### 5.3 Area exploration

1. `/explore` hosts Property Finder filters and results.
2. Results show candidate/location scope and observed price evidence, not a property case yet.
3. Selecting **Analyze this property** opens the same confirmation step.
4. Confirmation creates the case and redirects to its Overview.

### 5.4 Saved case

1. Homepage recent cases or `/cases` lists address/title, active price, identity state, last updated, and next action.
2. Selecting a case routes directly to `/workspace/[caseId]/overview`.
3. The repository loads case identity first, then evidence slices independently. A failed slice does not block the shell.

### 5.5 Time-to-first-useful-evidence target

- Known address: address → confirmation → Overview in two committed actions.
- Saved case: one selection → Overview.
- Exploration: filters → candidate → confirmation → Overview.

## 6. Canonical case and evidence state

The workspace needs a single repository interface independent of storage implementation:

```ts
type WorkspaceSection = "overview" | "market" | "location" | "risk" | "finance";

type EvidenceState<T> =
  | { status: "not_requested" }
  | { status: "loading"; previous?: T }
  | { status: "available" | "partial" | "stale"; data: T; checkedAt: string }
  | { status: "no_data"; checkedAt: string; reason: string }
  | { status: "unavailable"; previous?: T; error: WorkspaceError; checkedAt?: string };

type PropertyCaseWorkspace = {
  caseId: string;
  revision: number;
  identity: PropertyIdentitySummary;
  assumptions: { askingPriceWan?: number; manualPriceWan?: number; activePriceBasis: "asking" | "estimate" | "manual" };
  evidence: {
    market: EvidenceState<MarketEvidence>;
    valuation: EvidenceState<ValuationEvidence>;
    location: EvidenceState<LocationEvidence>;
    commute: EvidenceState<CommuteEvidence>;
    terrain: EvidenceState<TerrainEvidence>;
    satellite: EvidenceState<SatelliteEvidence>;
    loan: EvidenceState<LoanEvidence>;
    holdingCost: EvidenceState<HoldingCostEvidence>;
    transactionTax: EvidenceState<TransactionTaxEvidence>;
  };
  saveState: "saved" | "saving" | "unsaved" | "save_failed";
};
```

The interface is implemented first by a compatibility adapter over current `SavedCase` plus in-memory live results, then by the approved VNext case APIs. Components consume the repository, not `localStorage`, session keys, or window events directly.

### 6.1 Invalidation matrix

| Changed input | Invalidate | Preserve |
|---|---|---|
| Confirmed PropertyEntity/address/coordinates | Market, valuation, location, commute origin, risk, satellite; finance results whose property facts or price basis changed | User-authored notes/checklists only after explicit confirmation they should carry; otherwise attach to old revision |
| Area/building type/age/floor | Valuation and dependent estimate price basis; finance if active price was estimate | Location, commute, risk, market geography |
| Asking price | Asking-price comparison; finance using asking basis | Location, commute, risk, market, valuation calculation |
| Active price basis/manual price | Loan, holding cost, dependent affordability and transaction estimates | All property/location/market/risk evidence |
| Income | Affordability interpretation only | Loan payment itself, holding cost composition, other evidence |
| Commute destination/mode | That commute query only | Location and all other commute destinations |
| Risk radius/layers | Requested risk layers only | Location, market, finance, previously valid independent layers |

Every result stores the case revision and input fingerprint used to calculate it. Late responses with an older fingerprint are ignored, preserving the race protections already tested in current flows.

## 7. Persistent Property Context Header

### 7.1 Desktop

The header sits below the global top bar and above section content. It contains:

- one-line property display address/title;
- identity state: `Confirmed`, `Needs confirmation`, or `Conflict—review required`;
- active price, explicitly labeled `Asking`, `Estimate midpoint`, or `Manual assumption`;
- save state and last saved time;
- one compact freshness phrase such as “3 sections refreshed today” only when useful;
- actions: change property, save, more.

Provider names, source badges, internal IDs, readiness enums, and a badge per evidence slice are excluded.

At desktop widths it becomes sticky below the global bar and compresses after approximately 48 px of vertical scroll: title, identity state, active price, and save state remain; supporting metadata collapses.

### 7.2 Mobile (~390 px)

The first row contains truncated property title plus identity state. The second row contains active price basis/value and save state. A single overflow menu exposes change property and details. It is sticky, at most two compact rows, and never horizontally scrolls.

### 7.3 Property change and revalidation

**Change property** opens a confirmation sheet/modal rather than editing the header inline. The user sees which evidence will become stale. On confirmation, the case revision advances and affected slices move to `not_requested` or `stale`; unrelated user-authored content is never silently deleted.

When identity requires revalidation, the header shows a persistent warning state and the Overview shows a blocker. Evidence calculated for the prior identity remains visible but marked “Based on the previous property confirmation” until refreshed. New identity-sensitive analysis is disabled where using the old identity could mislead.

## 8. Overview & Next Actions

Overview is the decision cockpit, not a list of module completion percentages.

Content order:

1. **Decision question and current posture.** Neutral language such as “Worth further investigation,” “Resolve blockers first,” or “Not enough evidence yet”; never investment advice or a safety score.
2. **Major findings.** Maximum five material, evidence-backed findings across price, place, risk, and finance. Each links to its evidence section.
3. **Major unknowns.** Only unknowns that could change interpretation, such as missing property area, insufficient comparable sample, or unassessed flood evidence.
4. **Blocking issues.** Identity conflict, unusable price basis, or required input that makes a requested calculation invalid. Optional unopened modules are not blockers.
5. **Next useful actions.** Three to five specific actions ordered by decision impact and effort, each with one destination.

The synthesis reads evidence states and deterministic facts. It may reuse factor extraction from `risk-summary.ts` and decision models, but retires the duplicate dashboard decision, readiness summary, status-strip, and “every module incomplete” patterns. A finding always links to evidence; an unknown is not rendered as zero or “failed”; a provider error appears locally and becomes a next action only if material.

## 9. Market & Price

**User question:** Is this price reasonable, and what evidence supports that?

### 9.1 Primary summary

One summary row distinguishes:

- **Asking/reference price** — user or listing input;
- **Estimated range** — system model, with midpoint and confidence;
- **Observed comparable range/median** — historical transactions;
- **Evidence scope** — property/road/district fallback;
- **Sample and period** — effective count and date range;
- **Active finance basis** — explicitly selected basis.

The three price concepts never share the same unlabeled visual treatment. If one is unavailable, its state is explanatory, not `0`.

### 9.2 Main analytical surface

1. Range band showing asking price, estimate range/midpoint, and comparable quartiles on the same unit scale.
2. Comparable table as the primary evidence: transaction period, location scope, building type, area, age/floor relationship, total price, unit price, and why it is comparable. Default 5–12 rows; no opaque similarity score.
3. Price distribution by unit price and total price where sample size supports it.
4. Market trend and transaction volume as supporting charts, with scope and effective period fixed above the charts.

### 9.3 Advanced details

Filters, segmentation, methodology, raw source/provider labels, retention rules, exclusions, and sample-quality limitations live under disclosures. Provider status does not lead the page. Market and valuation may fail independently; the surviving evidence remains visible.

## 10. Location & Commute

**User question:** What is living or working around this property actually like?

### 10.1 Desktop map-first layout

- Map occupies approximately two-thirds of the first viewport; a 360–400 px side panel occupies the remainder.
- Map shows property, selected POI category, and commute destination/route layers. Layer controls are compact and mutually understandable.
- Side panel begins with actual evidence: nearest relevant facility, distance/time, route availability, and data status. Generic category scores are secondary.
- Selecting a list result focuses the map; selecting a marker focuses the list without changing the case identity.

### 10.2 Evidence hierarchy

1. Address/geocoding confirmation and map.
2. Commute destinations saved per case: mode, duration, distance, and route status.
3. Relevant POIs by type, with name and distance; counts are supporting context.
4. Area context/demographics with geography, statistic month, and caveats.
5. Source details and scoring methodology disclosure.

`Location Insight` and `Map Insight` share one resolved location. They do not issue competing geocodes. Demographics is never a standalone nav item. Generic buyer-fit prose and arbitrary livability scores do not dominate the view.

## 11. Risk & Environment

**User question:** What environmental or geological issues should I investigate before proceeding?

The view contains:

1. **Evidence map** with independently toggled flood, landslide, debris flow, liquefaction, geological sensitivity, active fault, cadastral/parcel, and satellite context where available.
2. **Ordered evidence table** with columns: issue, finding, match/distance, evidence state, coverage/date, and next check. Order is matched/high-concern findings, partial/unknown evidence, clear observations, then unavailable/not assessed.
3. **Matched findings** with plain-language consequence and a link to map context.
4. **Unknown/unavailable evidence** that distinguishes no match, no coverage, not assessed, and service failure.
5. **Manual verification checklist** for survey, official map, title/parcel boundary, site visit, or specialist review.
6. **Source details** under disclosure, including agency/provider, version/date, coverage, and caveat.

There is no “property safety score.” The current overall terrain level may be retained only as a cautious summary label derived from explicit layers and never as proof of safety. Satellite imagery remains visual reference, not statutory or cadastral evidence. A single layer failure does not change another layer’s result.

## 12. Finance & Transaction

**User question:** What will this property cost me, and what assumptions are still missing?

### 12.1 Primary summary

- estimated cash required, including down payment and currently modeled upfront costs;
- monthly loan payment;
- monthly known holding cost;
- unestimated cost categories listed by name;
- affordability status only when verified user income exists;
- active price basis and last calculation time.

“Loan calculated” and “affordable” are distinct states. Without income, show payment/cost evidence and “Affordability not assessed.”

### 12.2 Main analysis

- cost composition: cash at purchase, financed amount, recurring payment, recurring non-loan costs;
- editable loan assumptions and rate source/vintage;
- holding-cost assumptions and included/excluded items;
- sensitivity for interest rate, term, down payment, and price where it changes a decision;
- explicit units: property prices in `萬元`, recurring payments in `NT$/month`, rates in `%`, area in `坪` (with conversion only where supplied).

### 12.3 TaxOracle

Transaction tax is a contextual drawer/detail block when a sale/purchase scenario or eligibility question makes it relevant. Its rule traces and official source detail remain available under transaction details. It is removed from primary global and workspace navigation but retained under Advanced tools.

## 13. Compare

Compare is reached from Saved Cases or a workspace action and uses `/compare?cases=<id>,<id>[,<id>]`. Two cases are required; three are the maximum for v1.

### 13.1 Selection and integrity

- The case picker shows property title/address, identity state, active price basis, and last updated.
- Duplicate case IDs are ignored; cases with unresolved identity can be selected but visibly flagged.
- Each metric carries its unit and observation time. Incompatible units or scopes are not coerced silently.

### 13.2 Comparison hierarchy

1. Material differences likely to change which property is inspected first.
2. Side-by-side summaries for price, commute, risk evidence, and cash/monthly cost.
3. Missing or non-comparable evidence.
4. Full detail disclosure.

Deterministic emphasis rules are explainable, for example: price/cash/monthly deltas of at least 10%, commute deltas of at least 10 minutes, different matched risk findings, or a difference between assessed and unknown evidence. These thresholds highlight; they do not score.

Missing states render `Not assessed`, `Unavailable`, `No data`, or `Different scope`, never zero. Price comparisons use the same chosen field and unit across cases (asking-to-asking, estimate-to-estimate, or explicit active-price basis). The current weighted ranking, rank number, score, `bestCaseId`, and “top candidate” presentation are retired.

## 14. Report

Report is `/workspace/[caseId]/report` and always represents the current saved case revision.

Professional structure:

1. property identity and case context;
2. executive findings and current decision posture;
3. market and price evidence;
4. location and commute evidence;
5. risk and environment evidence;
6. finance and transaction assumptions/results;
7. material unknowns and unavailable evidence;
8. verification checklist and next actions;
9. source/date notes.

The report omits internal provider IDs, API paths, HTTP states, stack/diagnostic text, raw payloads, and internal readiness enums. Public source names and dates may appear in end notes when they help verification.

Print/PDF uses a dedicated print stylesheet: A4-friendly sections, repeated property title/page footer, page-break avoidance inside evidence rows, monochrome-safe status text, no navigation/forms/buttons, and URLs rendered only for user-relevant verification links. Browser print is the v1 PDF mechanism; server-generated PDF is deferred.

## 15. Navigation and route architecture

### 15.1 Exact desktop navigation

Persistent workspace navigation:

```text
Overview
Market & Price
Location & Commute
Risk & Environment
Finance & Transaction
```

Global/case actions, visually separate from sections:

```text
Saved Cases
Compare
Report / Export
Advanced tools
Help
Settings
```

### 15.2 Canonical routes

| Purpose | Route |
|---|---|
| Homepage/known address | `/` and optional dedicated `/properties/new` |
| Regional exploration | `/explore` |
| Saved cases | `/cases` |
| Workspace overview | `/workspace/[caseId]/overview` |
| Market & Price | `/workspace/[caseId]/market` |
| Location & Commute | `/workspace/[caseId]/location` |
| Risk & Environment | `/workspace/[caseId]/risk` |
| Finance & Transaction | `/workspace/[caseId]/finance` |
| Case report | `/workspace/[caseId]/report` |
| Compare | `/compare?cases=id1,id2[,id3]` |
| Identity correction | `/workspace/[caseId]/identity` or linked VNext review route |

`/workspace/[caseId]` redirects to `/workspace/[caseId]/overview`. Route segments own durable navigation state. Query parameters are limited to shareable view state such as selected compare cases, map layer, or a safe filter—not the active property identity. Ephemeral drawers, selected POI, and disclosure state remain local.

Next.js layouts own the case repository and property header. Each section is a nested route so Back, Forward, refresh, and deep links work naturally. Invalid or unauthorized case IDs render a route-level not-found/access state; individual evidence failures remain inside the loaded shell.

## 16. Mobile and narrow behavior (~390 px)

- **Property header:** sticky two-row compact header described in section 7; identity details open a sheet.
- **Workspace navigation:** horizontally scrollable top-level chips with scroll snapping and visible current item, plus a section menu; the page itself must not overflow. No nested left drawer for five sections.
- **Map:** 300 px default map with full-screen expansion. A collapsed results sheet follows in document flow; expanding the sheet replaces map focus rather than creating two independently scrolling panes.
- **Tables:** replace wide comparison/market tables with a field-priority row card or one-axis scroll region with sticky first column. The page never scrolls horizontally. A visible “More fields” disclosure exposes lower-priority columns.
- **Comparison:** case-by-case vertical sections with a sticky metric selector; do not squeeze three columns into 390 px. The same metric is shown for all cases before moving to the next metric.
- **Forms:** one column, labels above fields, numeric unit suffixes, 44 px minimum controls, persistent values, and a single full-width primary action at the end of the active form.
- **Evidence details:** accordion sections with state text in the summary; only one large evidence detail needs to be open at a time.
- **Primary CTA:** sticky bottom action only when the user has a clear incomplete action (confirm, calculate, save). It must not cover content and disappears when the native keyboard is open where detectable.
- **No nested scrolling:** the document is the primary scroll owner. Full-screen map is the only deliberate temporary exception.

## 17. Failure model

| Failure | Workspace behavior | Recovery |
|---|---|---|
| Valuation fails | Market observations, asking price, location, risk, and finance with another explicit price basis remain usable. Estimate card shows local error. | Retry valuation; choose asking/manual basis. |
| Commute fails | Map, POIs, address, and demographics remain. Only affected destination/mode shows unavailable. | Retry that route or edit destination/mode. |
| One terrain provider/layer fails | Other layers, map, previous valid evidence, and their dates remain visible. Failed layer is `Unavailable`, not “no risk.” | Retry layer or follow manual check. |
| Market unavailable | Asking/manual price, valuation if available, location, risk, and finance remain. | Retry market or proceed with explicit limitation. |
| Identity needs revalidation | Header and Overview show blocker; prior identity-sensitive evidence is marked stale and retained. Unrelated notes remain. | Review/confirm identity, then selectively refresh. |
| Save fails | Current client state remains; header shows `Save failed`; navigation does not discard work. | Retry; warn before leaving if unsaved. |
| Case shell load fails | Render access/not-found/retry at route level only when the case itself cannot load. | Retry or return to Saved Cases. |

Errors use plain language, a bounded cause where known, one recovery action, and an optional support reference in details. They never show API paths, provider implementation, HTTP codes, or raw exceptions in primary UI. A retry mutates only its evidence slice.

## 18. Visual information structure

Every primary section follows this rhythm:

```text
Section heading and user question
Concise summary row
Main analysis surface
Evidence map/table/chart
One next useful action
Details / methodology disclosure
```

Dominant content by section:

| Content type | Where it dominates |
|---|---|
| Summary | Overview and top row of every section |
| Map | Location & Commute; Risk & Environment |
| Table | Market comparables; ordered risk evidence; comparison details |
| Chart | Price distribution/trend; finance sensitivity/composition |
| Checklist | Overview next actions; risk manual checks; report verification |
| Form | Entry confirmation; finance assumptions; commute destination |
| Details disclosure | Methodology, provider/source metadata, filters, diagnostics |

Use page sections and dividers before containers. Cards are reserved for independently actionable or repeatable records. Avoid card-inside-card layouts, badge clouds, repeated alerts, and four simultaneous status summaries.

## 19. Existing component reuse map and future file-touch map

| Proposed surface | Reuse | Wrap/merge/move | Leave primary navigation / obsolete shell |
|---|---|---|---|
| Entry and Saved Cases | `PropertyFinder`, `CaseManager` logic, identity workflow contracts | Extract finder result list; add address confirmation; wrap case storage behind repository | Root dashboard entry cards, mandatory journey property stage |
| Workspace shell/header | VNext route validation, auth gate, identity DTO/client, professional shell load classification | New nested layout, one `PropertyContextHeader`, case repository/provider | `AppPage`, root `setPage`, technical `MODULES` navigation, repeated journey headers |
| Overview | Pure decision/risk/property-case view models, missing-data logic | New deterministic synthesis model; merge readiness/attention/decision panels | Dashboard viewing decision, repeated status strips, completion-centric shells |
| Market & Price | Market evidence panel, segmentation/comparables, trend/volume charts, valuation visual components, price basis selector | Extract root-defined Market/Valuation into focused modules; shared price summary | Standalone Market and Valuation nav/pages; valuation-led workspace shell |
| Location & Commute | `GeoMap`, POI list concepts, Location result, commute cards, demographics | One geocode/location controller; map-first wrapper; route results per destination | Standalone Map/Location nav, generic score-first panels |
| Risk & Environment | Terrain analysis, terrain map, cadastral evidence, satellite, terrain reference model | Separate layer view models/statuses; unified risk table/map | Provider-specific modules in nav; aggregate safety score presentation |
| Finance & Transaction | Loan/Holding visual panels and calculators, tax presentation model | Shared assumptions wrapper; contextual TaxOracle; explicit affordability gate | Standalone Loan/Holding/Tax navigation and repeated transfer shells |
| Compare | Case selector, comparison field extraction, print primitives | Replace scoring/ranking with delta model; responsive metric-group views | Rank cards, `bestCaseId`, weighted winner logic |
| Report | Decision report inputs, valuation HTML formatting concepts, print comparison styles | One case report view model and print route | Multiple overlapping export buttons and raw HTML report variants |

Likely new files:

```text
frontend_next/app/properties/new/page.tsx
frontend_next/app/explore/page.tsx
frontend_next/app/cases/page.tsx
frontend_next/app/compare/page.tsx
frontend_next/app/workspace/[caseId]/layout.tsx
frontend_next/app/workspace/[caseId]/page.tsx
frontend_next/app/workspace/[caseId]/overview/page.tsx
frontend_next/app/workspace/[caseId]/market/page.tsx
frontend_next/app/workspace/[caseId]/location/page.tsx
frontend_next/app/workspace/[caseId]/risk/page.tsx
frontend_next/app/workspace/[caseId]/finance/page.tsx
frontend_next/app/workspace/[caseId]/report/page.tsx
frontend_next/components/workspace/property-context-header.tsx
frontend_next/components/workspace/workspace-navigation.tsx
frontend_next/components/workspace/workspace-shell.tsx
frontend_next/components/workspace/evidence-state-boundary.tsx
frontend_next/components/workspace/overview/*
frontend_next/components/workspace/market/*
frontend_next/components/workspace/location/*
frontend_next/components/workspace/risk/*
frontend_next/components/workspace/finance/*
frontend_next/components/workspace/report/*
frontend_next/components/compare/*
frontend_next/lib/workspace/case-repository.ts
frontend_next/lib/workspace/legacy-case-adapter.ts
frontend_next/lib/workspace/workspace-model.ts
frontend_next/lib/workspace/invalidation.ts
frontend_next/lib/workspace/overview-model.ts
frontend_next/lib/workspace/comparison-model.ts
frontend_next/lib/workspace/report-model.ts
```

Likely modified files include `app/page.tsx`, `app/globals.css`, `components/app-shell.tsx`, `components/topbar.tsx`, `components/property-finder.tsx`, domain calculators/evidence components, `lib/case-storage.ts`, `lib/closed-loop-journey.ts`, `lib/api.ts`, and Playwright configuration/tests. The root page should shrink to entry composition; domain implementations currently declared inside it should move before old navigation is removed.

## 20. Active-branch dependencies and conflict analysis

All four named worktrees currently point to `1095135`, three commits behind this design baseline, with no committed branch delta visible from this worktree. Their uncommitted work is intentionally not inspected or altered. File conflicts below are therefore risk forecasts based on scope.

| Active work | Required outcome | Likely conflict files | Implementation timing |
|---|---|---|---|
| Valuation / Holding Cost reliability closure | Stable result/status contracts, invalidation, and calculation reliability | `app/page.tsx`, `components/holding-cost-calculator.tsx`, valuation/holding visualization libs, `lib/api.ts`, reliability E2E tests | Phase 1 shell can proceed after rebase, but Phase 3 and Phase 6 domain extraction must wait for merge and consume the final contracts. |
| Commute production closure | Production station/route semantics, failure/status behavior | `components/commute-livability-card.tsx`, `components/commute-route-card.tsx`, `lib/api.ts`, commute backend/tests | Phase 4 must wait. Do not freeze the current mock/source labels into the new IA. |
| Journey Property Identity anchor | Confirmed PropertyEntity/case attachment and propagation | VNext identity clients/contracts/workflows, `app/workspace/[caseId]/page.tsx`, professional shell, journey identity tests, potentially `closed-loop-journey.ts` | Phase 1 should start only after this merges or be limited to non-overlapping route tests/models. Its durable case/identity contract is authoritative over the legacy adapter. |
| Geological Sensitivity | New layer contract, ETL/runtime states and evidence dates | `components/terrain-risk-analysis.tsx`, `lib/api.ts`, terrain models/tests, backend terrain providers | Phase 5 waits for merge; risk table must consume the final layer state rather than infer it from stale current-main shapes. |

Each implementation phase begins by rebasing/merging current `origin/main` into its own isolated feature worktree, reviewing these closures, and updating contracts before editing overlapping files. Do not copy code from another worktree or resolve its uncommitted state.

## 21. Phased implementation strategy

1. **Workspace foundation:** durable/adapter case repository, nested routes, property header, navigation, local evidence boundaries.
2. **Overview:** one synthesis model and explicit next actions; retire duplicate summary surfaces only after parity tests.
3. **Market & Price:** extract root modules and combine their presentation after valuation reliability closure.
4. **Location & Commute:** one resolved location and map-first view after commute closure.
5. **Risk & Environment:** independent layer model after geological sensitivity merge.
6. **Finance & Transaction:** shared assumptions, loan/holding summaries, conditional affordability and tax.
7. **Compare and Report:** explainable deltas, case report model, print behavior.
8. **Responsive/accessibility/commercial acceptance:** 390 px, keyboard/focus, print, language and final route migrations.

The detailed task/file/test/rollback plan is in `docs/superpowers/plans/2026-09-27-commercial-property-workspace.md`.

## 22. Commercial UX acceptance criteria

### Known-address path

- From `/`, entering an address and confirming it opens `/workspace/[caseId]/overview` without rendering or requiring Property Finder.
- The system does not run every analysis automatically during confirmation.

### Same-property integrity

- Every workspace route shows the same case ID/property title/identity revision in the persistent header.
- A response with an outdated property fingerprint cannot replace current evidence.

### Property change

- The user sees an invalidation preview before confirmation.
- Address/identity change invalidates property-dependent evidence; price-only change invalidates finance and price comparison only; user notes are retained safely.

### Local failure

- Valuation, commute, market, and individual terrain failures are independently simulated; unrelated sections and previously saved evidence remain accessible.
- Retry updates only the failing slice.

### Unit consistency

- Property price, unit price, monthly currency, rates, area, distance, and time display explicit units.
- Compare never places unlike price bases or units in one unlabeled row.

### Save and reopen

- A case reopened after refresh restores property identity, active price basis, evidence state/freshness, and next actions.
- Save failure does not erase local work.

### Compare

- Two or three saved cases can be selected.
- Significant deltas and missing/non-comparable data are explicit; no rank, score, winner, or black-box recommendation appears.

### Report

- The current case revision produces a client-readable report with all nine defined sections and print styling.
- No API path, HTTP code, internal provider ID, raw payload, or engineering diagnostic appears.

### Navigation

- Direct load, refresh, Back, and Forward work for every workspace section and report route.
- `/workspace/[caseId]` redirects deterministically to Overview.

### Mobile

- At 390×844, all primary workflows are usable, no page-level horizontal overflow exists, maps can expand, comparison is readable, and the document remains the only normal scroll owner.

### Professional language

- Primary UI uses property, price, place, risk, cost, evidence, unknown, and next-action language.
- Provider/API/HTTP/internal enum terminology appears only in bounded source/method details where appropriate.

## 23. Intentionally deferred

- detailed visual design tokens, final typography, illustration, and motion;
- server-generated PDFs and document templates beyond browser print;
- four-or-more-property comparison and portfolio analytics;
- CRM, contacts, assignments, document vault, title/ownership workflows, and AI chat;
- automated purchase recommendation, investment ranking, or property safety scoring;
- replacing public units or adding currency/area conversion without a product requirement;
- irreversible migration from local cases until VNext production case persistence and identity closure are approved.

## 24. Self-review

- No placeholders or unresolved product choices remain in the proposed IA.
- The route model, persistent property context, and invalidation rules use the same case-first architecture throughout.
- All requested modules are classified and represented in the reuse map.
- Compare explicitly removes the current rank/winner behavior.
- Risk explicitly rejects a synthetic safety score.
- The design preserves provider capability while removing provider-led navigation.
- The implementation is decomposed into independently reversible phases and waits for active closure branches where contracts are expected to change.
