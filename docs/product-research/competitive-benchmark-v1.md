# Competitive Benchmark & Feature Gap Matrix V1

Source acquisition date: **2026-10-10, Asia/Taipei**. Final review/validation: **2026-10-11**. Repository: `ryanwu566/proptech-ai-copilot`; branch: `research/competitive-benchmark-gap-matrix-v1`; starting SHA: `c2ddf1890897f44659b91079a563691fe337295e`. Scope: current worktree, research artifacts only. One research commit; no push, merge, deployment, production infrastructure mutation or ML-B.

PropTech AI Copilot has a substantial evidence decision workflow. Its most useful next move is to close hosted acceptance and make the case a better place to record, compare and review a property. Broad listing search, opaque AI scores and premature AVMs would dilute that position. The current production verdict remains **NO-GO**; this report does not change it.

The benchmark contains **13 established product families, 7 emerging AI product surfaces and 10 public GitHub repositories**, with **64 capability rows × 21 product columns = 1,344 cells**. HouseCanary and CanaryAI are separate surfaces of the same company; they are not independent market votes. The corpus includes 41 established-market sources, 22 emerging/lifecycle sources, 79 repository sources and 25 internal source records. These are source records, not all unique URLs.

## Evidence and scope

The target is Taiwan residential evidence-grounded property decisions, not a generic listing marketplace. Inventory was documentation-first with selective reads of current case, finance, comparison, storage, commute and template-AI contracts; this is not a full repository audit. External research used current opened first-party pages, help articles, releases and GitHub metadata/source. No competitor account, paid workspace, mobile app or document workflow was executed. No local application test/build or deployed product evaluation was performed in this lane.

`VERIFIED_CURRENT` means the current primary source was retrieved and documents a shipped/available capability **within its stated scope**. It does not verify accuracy, end-to-end execution or universal rollout. `ANNOUNCED` covers unconfirmed expansion/beta availability; `INFERRED` covers adjacent patterns; `UNVERIFIED` covers unresolved current claims. Matrix values are `YES`, `PARTIAL`, `NO`, `UNKNOWN`; no external absence is asserted without explicit primary evidence. `UNKNOWN` has an acquisition target and never means `NO`. Promotional precision, model error and security/performance claims are not independently validated.

The pasted Taiwan names contained encoding corruption. “Leju” is resolved as 樂居; the garbled broker is interpreted as 信義房屋/Sinyi, explicitly an assumption. 永慶 is added as another relevant major broker platform. CoreLogic-type research uses current Cotality product pages; no stale company label is treated as current proof.

## Current product inventory

The [authoritative inventory](current-capability-inventory-v1.json) records 22 categories and 64 specific capabilities, with current local source references. `STRONG` describes implemented repository behavior with bounded documented local validation, not production certification. `PARTIAL` includes conditional data and legacy-only/incomplete integration. Gated VNext accounts/roles are `FOUNDATION_ONLY`; production acceptance and ML are `BLOCKED`.

| Category | Classification | Boundary |
| --- | --- | --- |
| Property discovery | PARTIAL | Official transactions/address intake; no licensed listing clone. |
| Case management | PARTIAL | Mature local snapshots; no durable multi-device room. |
| Market evidence | PARTIAL | Strong semantics; partial/conditional accepted hosted coverage. |
| Valuation | PARTIAL | Comparable-based estimates, not approved ML model or appraisal. |
| Comparable transparency | STRONG | Inclusion/exclusion and method explanations. |
| Location | PARTIAL | POI/maps/demographics; runtime proof missing. |
| Commute | PARTIAL | Single route plus secondary TDX evidence. |
| Risk | PARTIAL | Good unknown handling; artifact and hosted acceptance missing. |
| Finance | PARTIAL | Strong mortgage/holding; acquisition and unified scenarios incomplete. |
| Evidence verification | STRONG | Source-based actions and manually reported recheck workflow. |
| Viewing workflow | PARTIAL | Generic notes/readiness; no structured viewing log. |
| Documents | NOT_IMPLEMENTED | Document proposals and geometry upload do not establish a property vault. |
| Notes | PARTIAL | Legacy free text; no integrated rich viewing record. |
| Comparison | STRONG | 2–4 snapshots with consistent missing and assumption semantics. |
| Reports | STRONG | Frozen evidence pack and A4 export; long-document usability still a pilot test. |
| Collaboration | FOUNDATION_ONLY | Gated role/workspace foundations; no accepted consumer collaboration. |
| Monitoring | PARTIAL | Static freshness and saved shortlist; no scheduler/alerts. |
| AI assistance | FOUNDATION_ONLY | Deterministic structured explanations; no live grounded LLM Q&A. |
| ML | BLOCKED | Target A/B blocked; PIT-valid 0; approved cohort 0. |
| Accounts | FOUNDATION_ONLY | VNext auth is gated and separate from consumer cases. |
| Sharing | PARTIAL | Allowlisted input URL and local export; no revocable hosted evidence room. |
| Commercial operations | BLOCKED | Local controls meaningful; hosted global security/cost/recovery unaccepted. |

Important corrections: notes, renovation reserves and manual buyer-cost inputs exist in the legacy command center; they are integration gaps. Current Finance explicitly excludes acquisition costs from totals. Current Compare is 2–4 cases, superseding the historical 2–3 surface. The consumer repository is browser-local, capped at ten saved cases; same-browser storage events are not cross-device sync. Four-language guided Tour/Simulation exists; deterministic explanation templates do not establish a live copilot. [L05](../../frontend_next/lib/workspace/case-repository.ts), [L07](../../frontend_next/lib/workspace/finance-model.ts), [L08](../../frontend_next/components/property-case-command-center.tsx), [L18](../guided-tour-i18n-motion-v2.md), [L15](../../services/llm_service.py).

The latest release/guardrail documents retain unverified hosted identity/providers and 15 externally blocked owner-control dimensions. Older September live data and successful local synthetic recovery/full-suite records cannot replace release-bound hosted evidence. The tour integration record reports 2,998,938 aggregate static bytes, only 1,062 below the unchanged 3,000,000-byte ceiling; this is historical build evidence, not a fresh measurement of this research checkout. [L11](../operations/final-production-acceptance-evidence-v1.json), [L12](../operations/production-guardrails-recovery-v1.md), [L13](../operations/production-guardrails-recovery-v1-evidence.json), [L18](../guided-tour-i18n-motion-v2.md).

**ML boundary:** Target A BLOCKED; Target B BLOCKED; PIT-valid=0; approved cohort=0; no approved geography/cohort/splits/model; ML-B may not begin. Neither a competitor AVM nor this report can waive those gates. [L16](../ml/valuation-target-reframing-evidence-v1.md), [L17](../ml/valuation-semantic-temporal-closure-evidence-v1.json).

## Established market benchmark

Every family below has a full capability/source register in [market-source-register-v1.json](market-source-register-v1.json). The table describes patterns and restrictions, not a certified ranking. Market-product sources were checked on 2026-10-10; supplemental GitHub activity review on 2026-10-11 is dated separately.

| Product / geography | Public pattern worth studying | Scope / limitation | Primary evidence |
| --- | --- | --- | --- |
| 591 / Taiwan | Saved listings, map/transaction context, mortgage tools and price reminders. | Contract downloads are templates, not document upload; community records are not complete individual history. | [S591-01](https://www.591.com.tw/), [S591-02](https://help.591.com.tw/content/74/291/tw/關於我們.html) |
| 樂居 Leju / Taiwan | Community/transaction-led investigation and map context. | Linked report contents unverified; not a verified document or copilot workflow. | [SLJ-01](https://www.leju.com.tw/), [SLJ-02](https://www.leju.com.tw/faq/5) |
| 信義房屋 Sinyi / Taiwan | Sales research, finance and AI-to-human brokerage handoff. | Agent chat does not establish family case rooms; do not assume autonomous buyer agent. | [SSY-01](https://www.sinyi.com.tw/tradeinfo/list), [SSY-02](https://www.sinyi.com.tw/ai-proptech/?sinfrom=sinyi_banner_m) |
| 永慶 / Taiwan | AI search, listing remarks, viewing workflow and family-invited LINE discussion. | Restricted i特助 geography/service differs from web AI search; no granular case ACL proof. | [SYC-01](https://buy.yungching.com.tw/aiassistant), [SYC-02](https://knowhow.yungching.com.tw/article/3229) |
| Zillow / US | Saved-home comparison, actual property history and assistant/search patterns. | AI mode is restricted beta; wider rollout announced. Historical native climate scoring not assumed current. | [SZL-01](https://www.zillow.com/learn/zillow-advanced-search/), [SZL-02](https://www.zillow.com/zestimate/) |
| Realtor.com / Realtor.com+ / US | Shared persistent listing notes and restricted assistant/commute comparison. | RealAssist beta and participating MLS/RPR entitlements; not universal consumer functionality. | [SRC-01](https://mediaroom.realtor.com/2026-06-02-Realtor-com-R-Launches-RealAssist-TM-AI-A-Completely-Reimagined-Way-to-Find-A-Home), [SRC-02](https://www.realtor.com/plus-learn/product-updates/fall2026/) |
| Redfin / US | Account-linked partner comments/searches and conversational commute preferences. | Commute examples do not prove route timing/multi-stop calculation; subscriptions are not custom A4 reports. | [SRF-01](https://support.redfin.com/hc/en-us/articles/12559140934939-Favorites-Favorite-Lists), [SRF-02](https://support.redfin.com/hc/en-us/articles/360007862251-Shared-Saved-Searches) |
| Homes.com / US | Co-shopper notes/messages/favorite comparisons and individual property history. | Report-generation control observed, not executed; eligibility/data still apply. | [SHM-01](https://www.homes.com/real-estate-app/), [SHM-02](https://www.homes.com/support/2022/07/19/how-do-i-save-my-search/) |
| HouseCanary / US professional | Adjustable comp valuation and report-sharing workflows; recorded property history APIs. | Professional US data; no Taiwan model/data applicability or accuracy validation. | [SHC-01](https://www.housecanary.com/products/property-explorer), [SHC-02](https://www.housecanary.com/products/data-explorer) |
| PriceHubble / supported professional markets | AVM/comparable context and branded PDF/property-page/permalink outputs. | Comparable data is not a consumer shortlist; output sharing is not proven team editing. | [SPH-01](https://www.pricehubble.com/uk/use-cases/automated-valuation-model-uk), [SPH-02](https://support.pricehubble.com/hc/en-gb/articles/27048508370961-Understanding-the-Overview-section-of-a-Dossier) |
| Cotality / CoreLogic / US professional | AVM confidence/forecast/last-sale context. | Last sale/HPI is not full history; model metrics remain vendor claims. | [SCT-01](https://www.cotality.com/products/total-home-value-x), [SCT-02](https://www.cotality.com/uk/press-releases/meet-cotality) |
| Quantarium / US professional | Valuation/CMA tiers with histories and adjusted comparable output. | Tier-specific; no independent accuracy or report execution. | [SQM-01](https://www.quantarium.com/valuation-models/), [SQM-02](https://www.quantarium.com/marketplace/) |
| ATTOM / US professional data | AVM/property-data API and analytical delivery patterns. | Data platform, not a consumer case workspace; licensing/coverage separate. | [SAT-01](https://www.attomdata.com/solutions/ai-powered/valuation-analytics/avm/), [SAT-02](https://cloud-help.attomdata.com/article/510-avm) |

## Recent / emerging scan

The [emerging registry](emerging-source-register-v1.json) preserves company, target user, geography, launch/update date (or UNKNOWN), source and lifecycle per claim. These products were found and checked through first-party research, not treated as active from memory. UK developer/legal and US lender products are adjacent pattern benchmarks, not direct Taiwan substitutes.

| Product / target | Observed pattern | Availability qualification | Evidence |
| --- | --- | --- | --- |
| Jitty / UK buyers | Natural-language/visual-attribute and commute discovery; shared collections/notes/photos pattern. | Current search page documented; organization page has placeholder/stale cards, so collaboration pattern INFERRED, current execution unknown. | [EM-S01](https://jitty.com/), [EM-S02](https://jitty.com/about) |
| reAlpha Claire / US buyers | Preference refinement, match explanations, concierge and licensed-professional handoff. | Current promotion and 2025 update; inspection/settlement summary documented in 2024 only, current retention UNKNOWN. | [EM-S03](https://ir.realpha.com/press-release/re-alpha-expands-claire-its-ai-powered-concierge-to-guide-the-homebuying-journey), [EM-S22](https://ir.realpha.com/press-release/realpha-super-app-nar-changes) |
| Orbital / US/UK professional legal/property teams | Connected document review, issue/checklist extraction, source-linked outputs and property visualization. | Current professional documentation; no legal accuracy or Taiwan applicability established. | [EM-S05](https://www.orbital.tech/solutions/real-estate-businesses), [EM-S06](https://www.orbital.tech/uk) |
| LandTech AI Assistant / UK site teams | Q&A on saved sites with official-record citations and reports. | Explicitly live only in LandInsight Unlimited; no Taiwan planning translation assumed. | [EM-S08](https://land.tech/assess-sites/ai-assistant), [EM-S09](https://land.tech/) |
| Coadjute Clara / UK AML participants | Document guidance/follow-up with qualified human sign-off. | 2026-04-13 limited new-customer rollout documented; wider rollout unconfirmed. AML guidance is not property legal clearance. | [EM-S10](https://www.coadjute.com/resources/coadjutes-first-digital-human-to-help-battle-against-money-laundering) |
| HeyLeo / US Real agents/buyers | 2025-11-04 consumer conversational beta and current agent concierge. | Consumer entry inaccessible; current mobile listing agent-only. Consumer beta treated ANNOUNCED/current availability unconfirmed. | [EM-S11](https://s205.q4cdn.com/544743641/files/doc_news/Real-Doubles-Down-on-AI-With-Launch-of-HeyLeo--A-Gamechanging-Conversational-Search-Experience-for-Consumers-2025.pdf), [EM-S12](https://play.google.com/store/apps/details?id=com.realbrokerage.airm) |
| CanaryAI / US property professionals | Property/neighborhood Q&A, valuation/comps, photo-condition and after-repair scenarios. | Current paid plan includes access; 2025 shipped-update record; vendor valuations/condition adjustments are not independently calibrated. | [EM-S15](https://www.housecanary.com/products/canary-ai), [EM-S17](https://www.housecanary.com/blog/h1-2025-housecanary-product-highlights-innovation-in-action) |

Lifecycle traps: Flyhomes moved its search technology to Real and stated the original portal would operate only through 2025-07-02; it is not counted as a currently active independent portal. LocalizeOS produced insufficient readable current primary content; its active features remain UNVERIFIED and an acquisition target, not an included verified competitor. [EM-S14](https://flyhomes.com/insights/a-new-chapter-for-flyhomes-search-and-how-well-continue-working-together), [EM-S19](https://localizeos.com/solutions/), [EM-S20](https://localizeos.com/).

## GitHub / open-source scan

The [GitHub register](github-research-v1.json) includes exact API snapshots, default-branch heads, selected substantive source updates within inspected history, licenses/files, architecture, Taiwan fit and conditional reuse. Stars were observed on 2026-10-10; a pushed/metadata date is not a meaningful code-update date. No repository was installed, executed or copied. Code licenses do not grant rights to data, provider services, models or bundled assets.

| Repository | Stars | Selected substantive update (UTC) | License | Reuse stance / pattern |
| --- | ---: | --- | --- | --- |
| [agentic-ops/real-estate-mcp](https://github.com/agentic-ops/real-estate-mcp) | 68 | 2026-07-05 | [AGPL-3.0](https://github.com/agentic-ops/real-estate-mcp/blob/main/LICENSE) | pattern-only; FastMCP transport with category feature flags |
| [zedd75/mcp-imo](https://github.com/zedd75/mcp-imo) | 0 | 2026-08-17 | [MIT](https://github.com/zedd75/mcp-imo/blob/main/LICENSE) | conditional-component; Weighted median with distance, area, recency and market adjustments |
| [felixfu824/taiwan-property-price-cli](https://github.com/felixfu824/taiwan-property-price-cli) | 0 | 2026-07-06 | [Apache-2.0](https://github.com/felixfu824/taiwan-property-price-cli/blob/master/LICENSE) | conditional-component; Playwright chrome-headless-shell reused across queries |
| [ccao-data/model-res-avm](https://github.com/ccao-data/model-res-avm) | 72 | 2026-09-11 | [AGPL-3.0](https://github.com/ccao-data/model-res-avm/blob/master/LICENSE) | pattern-only; R/tidymodels pipeline with DVC stage dependencies |
| [murraystokely/mortgagemath](https://github.com/murraystokely/mortgagemath) | 5 | 2026-05-06 | [MIT](https://github.com/murraystokely/mortgagemath/blob/main/LICENSE) | conditional-component; Pure Python dataclasses; zero runtime dependency claim |
| [geopandas/geopandas](https://github.com/geopandas/geopandas) | 5276 | 2026-10-05 | [BSD-3-Clause](https://github.com/geopandas/geopandas/blob/main/LICENSE.txt) | conditional-dependency; GeoDataFrame carries geometry and CRS |
| [docling-project/docling](https://github.com/docling-project/docling) | 68635 | 2026-10-10 | [MIT](https://github.com/docling-project/docling/blob/main/LICENSE) | conditional-dependency; Format backends and processing pipelines separated |
| [dgtlmoon/changedetection.io](https://github.com/dgtlmoon/changedetection.io) | 34876 | 2026-10-08 | [Apache-2.0](https://github.com/dgtlmoon/changedetection.io/blob/master/LICENSE) | conditional-component; Domain-specific post-processors separate fetching from comparison |
| [g0v/posland](https://github.com/g0v/posland) | 29 | 2015-04-19 | [GPL-3.0](https://github.com/g0v/posland/blob/master/LICENSE) | pattern-only; Separates land-number lookup through NLSC from Google address geocoding |
| [quarto-dev/quarto-cli](https://github.com/quarto-dev/quarto-cli) | 6073 | 2026-10-09 | [MIT](https://github.com/quarto-dev/quarto-cli/blob/main/COPYING.md) | conditional-tool-use; Data analysis and rendered narrative share one source |

Property-specific MCPs illustrate provider adapters and pure financial tools; the Taiwan CLI is a zero-star prototype, not validated official coverage. Cook County AVM offers model/evaluation architecture for study without authorizing our blocked ML lane. GeoPandas/Docling/Quarto/change detection are enabling tools, not competing property products. g0v/posland is an old Taiwan reference pattern. AGPL/GPL projects remain pattern-only for this lane; permissive components still require dependency, data-rights, safety and performance review. Quarto core COPYING is MIT while GitHub API reports NOASSERTION; bundled licenses need separate review.

## Comprehensive feature matrix and scores

The single authoritative [feature matrix JSON](competitive-feature-matrix-v1.json) contains all 64 rows and 21 columns, with supporting source IDs on every non-UNKNOWN cell. The [CSV view](competitive-feature-matrix-v1.csv) carries identical values for spreadsheet review; use JSON for evidence and qualifications. Each unknown external cell has a precise acquisition target. Narrow mapping deliberately distinguishes downloaded contracts from uploaded documents, professional comps from saved-case comparison, agent chat from family rooms, and regional sales from individual history.

**Current research parity index: 36.4/100**, 4.0 capability equivalents across 11 rows. Formula: `100 × (YES + 0.5 × PARTIAL) / eligible rows`. Predeclared task-compatible candidates qualify only with current documented evidence from at least two of the eight established consumer products. Professional-only and AI-announcement demand is excluded. The denominator and all peer/source cells are in JSON. This is an explicitly narrow selected-sample repository index, not a statistically representative market score or deployed readiness.

**Current internal differentiation-strength index: 90.0/100**. Ten predeclared trust/decision capabilities weight ten each, with the same YES/PARTIAL credits. Official Taiwan evidence and global cost controls are partial, so earn five each. It is an analyst-selected repository strength index, not proof of uniqueness, measured user benefit or the next Work score. Unknown competitor functionality never establishes that we are ahead.

| Parity row | Copilot | Documented consumer peer evidence |
| --- | --- | --- |
| Viewing notes | PARTIAL | [SHM-01](https://www.homes.com/real-estate-app/), [SRC-02](https://www.realtor.com/plus-learn/product-updates/fall2026/), [SRF-02](https://support.redfin.com/hc/en-us/articles/360007862251-Shared-Saved-Searches) |
| Property-specific price / listing history | NO | [SHM-03](https://www.homes.com/property/8808-quadro-ct-las-vegas-nv/mqhln5sjwrb01/), [SSY-01](https://www.sinyi.com.tw/tradeinfo/list), [SZL-06](https://www.zillow.com/homedetails/223-1st-St-SW-Naples-FL-34117/103038983_zpid/) |
| Mortgage scenarios | YES | [S591-01](https://www.591.com.tw/), [S591-03](https://mortgage.591.com.tw/calculator), [SHM-01](https://www.homes.com/real-estate-app/) |
| Neighborhood context / demographics | PARTIAL | [S591-01](https://www.591.com.tw/), [SHM-01](https://www.homes.com/real-estate-app/), [SLJ-01](https://www.leju.com.tw/) |
| Map context | PARTIAL | [S591-01](https://www.591.com.tw/), [SHM-01](https://www.homes.com/real-estate-app/), [SLJ-01](https://www.leju.com.tw/) |
| Property change monitoring | NO | [S591-01](https://www.591.com.tw/), [SHM-01](https://www.homes.com/real-estate-app/), [SRF-01](https://support.redfin.com/hc/en-us/articles/12559140934939-Favorites-Favorite-Lists) |
| Price-drop alerts | NO | [S591-01](https://www.591.com.tw/), [SHM-01](https://www.homes.com/real-estate-app/), [SRF-01](https://support.redfin.com/hc/en-us/articles/12559140934939-Favorites-Favorite-Lists) |
| Watchlists | PARTIAL | [S591-01](https://www.591.com.tw/), [SHM-01](https://www.homes.com/real-estate-app/), [SLJ-01](https://www.leju.com.tw/) |
| Multi-property comparison | YES | [SHM-01](https://www.homes.com/real-estate-app/), [SHM-03](https://www.homes.com/property/8808-quadro-ct-las-vegas-nv/mqhln5sjwrb01/), [SZL-01](https://www.zillow.com/learn/zillow-advanced-search/) |
| Family / advisor collaboration | NO | [SHM-01](https://www.homes.com/real-estate-app/), [SRC-02](https://www.realtor.com/plus-learn/product-updates/fall2026/), [SRF-02](https://support.redfin.com/hc/en-us/articles/360007862251-Shared-Saved-Searches) |
| Consumer accounts | NO | [S591-01](https://www.591.com.tw/), [S591-02](https://help.591.com.tw/content/74/291/tw/關於我們.html), [SHM-01](https://www.homes.com/real-estate-app/) |

## Top ten real gaps

| Gap | Backlog | Why it matters / sequencing |
| --- | --- | --- |
| Hosted release, provider and global-control acceptance | G01–G05 | Release prerequisite; current production NO-GO. |
| Integrated viewing notes, questions and evidence status | G06 | P1 Decision Room; extend existing notes, not start from zero. |
| Preference continuity | G07 | P1 explicit budget/commute/risk priorities, user-controlled. |
| Multi-property trade-off explanation | G08 | P1 deterministic cited differences before a model. |
| Multi-destination commute | G09 | P1 bounded explicit household routes after accepted provider evidence. |
| Unified acquisition / renovation / holding-period scenarios | G10 | P1 integrates partial legacy inputs and discloses unknown costs. |
| Grounded property and cross-case Q&A | G11–G12 | P1 citation adapter → P2 assistant; templates are not live AI. |
| Document / photo evidence | G13 | P2 private, page-cited intake; requires account/isolation/privacy gates. |
| Cross-device continuity and revocable advisor sharing | G14–G15/G17 | P2 genuine consumer product gap; gated RLS schemas do not close it. |
| Watchlist and evidence change monitoring | G16 | P2 release-aware freshness/change signals; licensed price drops later. |

These are research-backed user-workflow hypotheses, not completed customer-demand validation. P0 comes from current categorical acceptance; the remaining proposals trace their benchmark source IDs in [ranked backlog](competitive-gap-backlog-v1.json). Closing a commercial blocker is not equivalent to adding competitor functionality.

## Top ten differentiators to protect

The product has demonstrated repository strengths in **trust semantics and their integration into the Taiwan decision workflow**. It may be ahead of listing-centric portals on this combination, but comparative leadership and deployed task outcomes remain untested. Established/professional products also offer provenance or reports. Protect the combination and test the benefit with users rather than claiming unique leadership.

| Strength | Current state | Evidence / practical value |
| --- | --- | --- |
| Evidence Verification Checklist | STRONG | Manual actions are source-linked, dated and invalidated when identity/evidence changes. [L04](../evidence-verification-checklist-v1.md) |
| Comparable inclusion explanations | STRONG | Understand basis and limitations instead of only receiving a value. [L02](../commercial-uiux-v1-acceptance.md) |
| Comparable exclusion explanations | STRONG | Retain rejected-evidence reasons rather than hiding selection. [L02](../commercial-uiux-v1-acceptance.md) |
| Provider provenance | STRONG | Source, date, version and coverage remain visible in evidence/report. [L10](../DATA_SOURCES.md) |
| Explicit unknown states | STRONG | Missing, unavailable, no-match, stale and zero carry distinct meanings. [L04](../evidence-verification-checklist-v1.md) |
| Deterministic multi-case comparison | STRONG | Saved facts/assumptions compare without hidden ranking or fresh provider fan-out. [L09](../../frontend_next/lib/workspace/compare-report-model.ts) |
| Frozen professional report | STRONG | Sources, limits and manual status survive export; newer data requires explicit load. [L03](../commercial-compare-report-e9-validation.md) |
| Manual next verification steps | STRONG | Users see what remains missing and retain judgment/control. [L04](../evidence-verification-checklist-v1.md) |
| Official Taiwan evidence focus | PARTIAL | Relevant regional public evidence, with acceptance/coverage limits rather than national completeness claims. [L10](../DATA_SOURCES.md) |
| Cost-aware provider boundaries | PARTIAL | Explicit provider action, cache/coalescing and passive snapshot workflow; fleet spend control remains blocked. [L21](../operations/api-cost-optimization-v1.md) |

Do not commoditize away source lineage, distinction between official/provider/manual evidence, explicit unknowns, comparable selection reasons, user review authority, frozen snapshot integrity, deterministic calculations or explicit cost-bearing actions. AI explanation, attractive maps and collaborative UX must preserve these contracts.

## Parity gaps versus deliberate differentiation

**Parity gaps:** shortlist/watch notifications, integrated listing/viewing notes, shared discussion, account continuity and reusable preferences are documented market patterns. Local PDF export and comparison already close part of parity. Property price history is a real market capability but rights-bound; it is not automatically the next priority. Broad consumer document upload and granular case permissions were not established across the portal sample, so those are professional/workflow opportunities rather than claimed universal commodity expectations.

**Differentiation:** evidence-linked Decision Room, recheck invalidation, cited explanation of why comparable/price/route/finance assumptions differ, accepted Taiwan risk sources with unknown coverage, bounded deterministic scenario cash costs, and a grounded assistant that identifies missing evidence rather than inventing conclusions. Professional source-backed products support these patterns, but their US/UK data/legal logic cannot be copied into Taiwan.

**Competitor noise:** opaque desirability/safety scores, generic social feeds, listing breadth for its own sake, autonomous buy verdicts, photo-generated appraisal confidence and unvalidated forecasts. Virtual renovation is not a verified repair budget; a vendor confidence claim is not our calibrated uncertainty. Investor portfolio/developer entitlement/AML/legal automation are adjacent segments, not first-beta requirements.

## Prioritization and candidate scoring

The backlog records ten 1–5 dimensions per proposal: user value (20), competitive necessity (10), differentiation (15), evidence availability (10), monetization (5), complexity (12), legal/data risk (10), provider cost (7), frontend/bundle impact (5), operations (6). Weights sum to 100. Benefit ratings contribute `weight × rating / 5`; costs contribute `weight × (6 − rating) / 5`. The attainable desirability index is 20–100. Ratings are analyst estimates; validate with pilot task outcomes, interviews, lawful data access and sizing. Priority gates override numeric score.

| Priority / rank | Item | Score | Dependencies |
| --- | --- | ---: | --- |
| P0 #1 | G01 — Close exact hosted release identity and regression evidence | 90.2 | none |
| P0 #2 | G05 — Recover bundle headroom and verify deployed mobile / print journey | 84.4 | G01 |
| P0 #3 | G04 — Prove managed recovery and named incident/support ownership | 82.4 | G01 |
| P0 #4 | G02 — Accept official provider bytes and bounded hosted evidence | 79.8 | G01 |
| P0 #5 | G03 — Close fleet ingress, quotas, cost and emergency control proof | 78.6 | G01 |
| P1 #1 | G06 — Property Decision Room: viewing log, questions and local case continuity | 92.4 | G05 |
| P1 #2 | G08 — Deterministic multi-property trade-off explanation | 92.4 | G07 |
| P1 #3 | G11 — Evidence contract / citation adapter for future grounded copilot | 84.8 | G02, G06 |
| P1 #4 | G10 — Unify acquisition / renovation / holding-period scenario | 84.0 | G06 |
| P1 #5 | G07 — Reusable Preference Profile with explicit user priorities | 79.4 | G06 |
| P1 #6 | G09 — Multi-destination household commute | 72.0 | G02, G07 |
| P2 #1 | G12 — Grounded Property Copilot and cross-case questions | 75.0 | G11, G08, G03 |
| P2 #2 | G15 — Revocable read-only report sharing and permissions | 73.0 | G14, G04 |
| P2 #3 | G25 — Transparent comparable-assumption sensitivity workbench | 70.0 | G02, G10, G11 |
| P2 #4 | G14 — Consumer accounts and cross-device case sync | 69.0 | G06, G04 |
| P2 #5 | G16 — Watchlist and evidence freshness/change monitoring | 67.8 | G14, G02, G03 |
| P2 #6 | G13 — Private document intake with page-cited extraction | 66.8 | G06, G14, G15, G11 |
| P2 #7 | G17 — Shared comments / advisor review | 63.0 | G15 |
| P3 #1 | G18 — Paid entitlements, support and privacy-preserving activation metrics | 58.6 | G14, G15, G04 |
| P3 #2 | G24 — Official canonical identity integration | 53.8 | G02 |
| P3 #3 | G20 — Legally appropriate school catchment / context | 53.2 | G02 |
| P3 #4 | G21 — Homeowner lifecycle review | 48.2 | G16 |
| P3 #5 | G23 — Natural-language search over licensed listings | 42.4 | G19 |
| P3 #6 | G19 — Licensed listing price history / price-drop alerts | 42.2 | G16 |
| P3 #7 | G22 — Portfolio monitoring for residential investors | 35.4 | G16 |
| DO_NOT_BUILD #1 | D01 — Fake AI property / desirability score | 22.0 | none |
| DO_NOT_BUILD #2 | D02 — Unsupported safety score or no-hazard clearance | 22.0 | none |
| DO_NOT_BUILD #3 | D03 — Unauthorized scraping of commercial listing data | 22.0 | none |
| DO_NOT_BUILD #4 | D04 — AI buy/no-buy verdict or generated price facts/comps | 22.0 | none |
| DO_NOT_BUILD #5 | D05 — False valuation confidence or rushed ML-B | 22.0 | none |
| DO_NOT_BUILD #6 | D06 — Generic social feed / portal clone | 22.0 | none |
| DO_NOT_BUILD #7 | D07 — Legal/title/disclosure approval from extracted documents | 22.0 | none |
| DO_NOT_BUILD #8 | D08 — Protected-class neighborhood ranking or guaranteed school admission | 22.0 | none |

Candidates A–J are all assessed: A Decision Room G06; B Preference Profile G07; C Grounded Copilot G11→G12; D trade-offs G08; E multi-destination commute G09; F document ingestion G13; G watch/change monitoring G16; H Scenario Simulator G10; I sharing/collaboration G14→G15/G17; J homeowner lifecycle G21. Only A/B/D/E/H and citation preparation are P1; this is not approval to implement all candidates.

## Three bounded roadmap waves

| Wave | Lane 1 | Lane 2 | Dependencies / exit |
| --- | --- | --- | --- |
| A: Release closure + Decision Room | G01–G05: exact hosted identity/providers, fleet cost/security, managed recovery, bundle and deployed UX closure | G06: bounded integrated notes/questions/manual evidence room | Lane 2 starts only after its G05 prerequisite; no new providers/storage infrastructure in the local-room slice. Exit: P0 hard gates pass and real beta cohort completes save/reopen/compare/report. |
| B: Preference / scenario intelligence + grounded explanation | G07–G10: one staged decision-context lane: profile → deterministic trade-offs → bounded commute and scenario integration | G11→G12: citation adapter, then optional grounded copilot | Wave A acceptance; accepted routes/cost budgets for multi-commute; exact evidence citation contract and adversarial eval before model. Cap each release to a measured slice; stop if task benefit/budget fails. |
| C: Durable collaboration + evidence continuity | G14→G15/G17: consumer accounts/sync, revocable read-only sharing, then comments | G16; optionally G13: release-aware monitoring, with private document intake only after storage/isolation/retention acceptance | Wave B user evidence, identity/RLS recovery; sharing before coediting, accepted release events before polling. Documents are a gated sub-slice, not a third parallel lane. |

Payments/metrics/support commercialization G18 is a separate post-pilot decision after Wave C, not an automatically approved fourth feature wave. G19–G24 require explicit demand/data-rights/business proof and remain outside these waves. Each wave has at most two major lanes; sequence sub-slices and remove lower-value ones rather than expanding the number of concurrent subsystems.

## Architecture and refusal boundary

LLM MAY explain structured evidence, summarize, compare, draft verification questions and report prose. It MAY NOT create official identity, price facts, comparables, disaster results, risk evidence or unsupported valuation. A citation adapter must bind claims to exact saved field/source/date/coverage and expose missing compacted comparable details. User notes/documents stay unverified until a lawful authoritative source supports them; external document text is untrusted input, not instructions. Templates/deterministic comparison should provide fallback.

Explicit DO_NOT_BUILD decisions: Fake AI property / desirability score; Unsupported safety score or no-hazard clearance; Unauthorized scraping of commercial listing data; AI buy/no-buy verdict or generated price facts/comps; False valuation confidence or rushed ML-B; Generic social feed / portal clone; Legal/title/disclosure approval from extracted documents; Protected-class neighborhood ranking or guaranteed school admission. No incompatible-license code, unauthorized listings or premature ML-B. All excluded proposals have scoring records for transparency, but numeric desirability never reverses an exclusion.

## Next Work evaluation and readiness distance

The [new 100-point Work rubric](work-commercial-rubric-v2.md) tests the deployed site. Points cover core journey (7), transparency (7), trust (10), market (7), risk/location (5), finance (5), case workflow (6), Compare (5), Report (5), onboarding (3), accessibility (3), mobile (4), performance (4), reliability (6), security/cost (6), accounts/collaboration (4), AI usefulness (4), parity (3), differentiation (3) and commercial readiness (3). Bands: <60 prototype/NO-GO; 60–74 advanced research; 75–84 Controlled Beta candidate; 85–91 advisor/pilot; 92+ early paid SaaS candidate. Hard gates override score; untested weight is not normalized away.

| Stage | Current evidence-based estimate | Minimum remaining distance |
| --- | --- | --- |
| Controlled Beta | Advanced repository research product; **NOT READY / NO-GO**, numerical deployed score unknown | Five P0 work packages G01–G05, including 15 owner controls and advertised provider/artifact gates; fresh successor full regression and deployed Work task acceptance ≥75 with hard gates passed. A narrowly scoped anonymous/local cohort can launch without paid accounts/LLM if honestly disclosed. |
| Advisor Pilot | **NOT READY**; potentially reachable after closure and focused room/context workflow validation | Controlled Beta acceptance + real advisor review of report/manual evidence and user-observed task value; Work ≥85 with hard gates. Minimum sharing can be explicit customer-controlled PDF; claims of hosted collaboration require G14/G15 permission proof. Grounded AI/documents are optional and separately gated, not automatic pilot requirements. |
| Paid SaaS | **NOT READY**; materially farther away than a beta | Pilot evidence of willingness to pay/repeat use + durable accounts/recovery/isolation, lawful entitlements/billing/refund, staffed support, deletion/retention, measured unit economics and sustained fleet cost/reliability. Work ≥92 with hard gates; Wave C and G18 acceptance. |

These are gate-based readiness estimates, not fabricated percentage completion or calendar dates. No current deployed Work test, customer research, staffing, provider rights/quotas or implementation sizing justifies a numeric stage probability or delivery date. P0 ownership/accepted source evidence, not feature count, determines beta distance. Advisor/Paid ambitions must not be used to rush ML or add every competitor feature.

## Limitations and research PR disposition

First-party evidence can describe intended/shipped functionality without proving end-to-end quality. Most competitor capabilities outside the opened sample remain UNKNOWN. Betas, paid plans, region restrictions, inaccessible pages and current consumer/agent branding are preserved rather than erased. Taiwan/US/UK markets differ in data access, legal meanings and housing workflow. No scraped commercial dataset, paid API trial, live quota or customer document was used. Licensing classifications are scoped research observations, not blanket legal clearance; license/data/dependency review precedes reuse.

The parity and differentiation indices are transparent research heuristics with different denominators; compare neither to each other as a commercial maturity scale nor to old UI scores. Product analytics/customer interviews are missing, so prioritization is a hypothesis. Latest repository records establish local strengths and hosted blockers; historical test results are not claimed as fresh tests of this branch.

**Safe for a research PR: YES**, subject to the fresh research artifact validation recorded in [validation record](research-validation-v1.json). The deliverable is documentation and machine-readable research only; no production application/infrastructure/dependency changes. This is not release approval. Exactly one research commit is required; the final commit SHA is supplied in the delivery response (embedding it in its own committed tree would be self-referential). No push, merge or deployment.
