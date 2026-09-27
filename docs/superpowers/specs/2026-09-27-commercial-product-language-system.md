# PropTech AI Copilot Commercial Product Language System

**Status:** Canonical product-language contract for future implementation
**Primary locale:** `zh-TW`
**Supported locales:** `zh-TW`, `en`, `ja`, `ko`
**Audit baseline:** branch `docs/commercial-copy-system-v1`, commit `7f442f8aa9f2217b872fa703065ea522dd8a8457`
**Scope:** customer-facing terminology, UX states, units, source disclosure, warnings, errors, loading, empty states, navigation, comparison, and reports
**Non-goal:** this document does not change backend contracts or production copy.

## 1. Product-language objective

PropTech AI Copilot must help a property professional or buyer answer six questions without understanding the implementation:

1. What is known?
2. What is estimated?
3. What is unavailable?
4. What requires confirmation?
5. What changed?
6. What should I do next?

The voice is professional, concise, calm, analytical, precise, trustworthy, and understandable to a non-technical reader. Primary UI copy must not rely on API names, HTTP methods, provider classes, raw enums, internal IDs, database concepts, or engineering error codes. Technical detail remains available only in a deliberately opened diagnostics or methodology view.

The governing rule is:

> Describe the user result first, its decision meaning second, its evidence third, and its implementation only in diagnostics.

## 2. Repository audit and current architecture

### 2.1 Copy locations inspected

The current interface does not have one copy authority. User-visible language is distributed across:

- `frontend_next/lib/experience-i18n.ts`: navigation, homepage, guided journey, trust statements, and shared experience states.
- `frontend_next/lib/runtime-copy.ts`: most domain labels and zh-TW/EN/JA/KO strings.
- `frontend_next/lib/runtime-copy-overrides.ts` and `frontend_next/lib/experience-i18n-overrides.ts`: later corrections that can disagree with base resources.
- `frontend_next/lib/surface-copy.ts`: Terrain, Holding Cost, and shell copy in a separate typed resource.
- `frontend_next/lib/dynamic-copy-localizers.ts`, `frontend_next/lib/market-insight-copy.ts`, `frontend_next/lib/parcel-geometry-copy.ts`, `frontend_next/lib/vnext-identity-copy.ts`, and `frontend_next/lib/taxoracle-presentation.ts`: domain-specific presentation layers.
- Direct JSX literals in homepage, guided journey, Property Finder, Location, map, Market, Valuation, Terrain, Satellite, Demographics, Commute, Loan, Holding Cost, TaxOracle, Case, Decision, Compare, Report, and workspace components.
- Generated HTML in `frontend_next/lib/valuation-share.ts` and report/print components.
- Backend-originated messages rendered directly, including disclaimers, explanations, warnings, status values, source names, and reasons.

Existing positive foundations should be retained: `experience-architecture.ts` distinguishes several empty/error states; `market-result-state.ts` and `valuation-result-state.ts` gate insufficient evidence; Terrain explicitly says unavailable data is not safety; TaxOracle separates preliminary screening from official determination; and the guided journey notes that viewed progress is not completeness. The problem is that these safeguards are not expressed through one shared state contract.

### 2.2 Actual high-impact findings

| Current visible wording or pattern | Context | Problem | Recommended commercial wording | Technical term retained internally? |
|---|---|---|---|---|
| `TaxOracle API`, `POST /taxoracle/analyze` | Tax loading/help/error | Exposes transport before outcome | `正在進行稅務條件初步檢查` | Yes: route and method in diagnostics/logs |
| `TX001–TX009` | Tax loading and primary tabs | Rule IDs are implementation detail | `正在檢查目前條件` | Yes: advanced rule trace |
| `deterministic 規則` | Tax methodology | Mixed language and engineering framing | `依固定規則與目前輸入進行初步篩選` | Yes |
| `provider raw data` | Case note placeholders | Internal vocabulary in an instruction | `請勿貼入未整理的系統回應` | Yes |
| `Direct Market Query Mode (county 必填、district 選填)` | Case command center | Debug-mode and schema-field leakage | `如需市場資料，請另行查詢區域行情；縣市為必填` | Yes |
| `ready / pending`, `yes / no` | Case readiness | Untranslated and semantically vague | `可進行比較 / 尚缺比較資料`; `可列印 / 尚不可列印` | Yes |
| raw `result.data_quality.status` | Location detail | Leaks enum and collapses quality into availability | localized evidence-status label | Yes |
| `available`, `unavailable`, `partial` used across execution, evidence, charts, and readiness | Many surfaces | One word represents unrelated concepts | Use axis-qualified labels defined below | Yes |
| `No official data`, `No data`, `No match`, `Unavailable` used interchangeably | Market, Valuation, Location, charts | Hides whether query succeeded, coverage is absent, or service failed | `查詢完成，查無符合資料`; `此資料不涵蓋目前位置`; `目前無法取得資料` | Yes |
| `Map Insight Lite`, `Market Insight Lite`, `Terrain Risk`, `Property Finder` | sidebar/navigation | Mixed-language feature names and “Lite” implementation positioning | customer names in §12 | Yes |
| `Urban Copilot` vs `PropTech AI Copilot` | sidebar vs app resource | Product identity inconsistency | one approved product name; use `PropTech AI Copilot` until branding decides otherwise | Yes |
| `AI`, `intelligence`, `smart` in hero/capabilities | homepage | Hype obscures deterministic GIS, rules, and calculations | describe the task: `整合物件資料與查核證據` | Product brand may retain `Copilot` |
| `服務狀態 可用` | global sidebar | “Available” has no defined subject and looks like system assurance | `系統連線正常` only if based on real health; otherwise omit | Yes |
| `資料可用` mapped from generic `ready` | shared state | Can mean request completion, usable evidence, or task readiness | axis-specific status | Yes |
| `已完成` based on object presence | workflow status | A returned object may be demo, partial, stale, or unusable | `已取得結果`; readiness evaluated separately | Yes |
| `完成目前流程` | journey | Implies analytical completion | `結束本次瀏覽` or `查看待確認事項` | No |
| Location score and category scores | Location | Formula and interpretation are not visible; may imply overall property quality | rename to qualified indices or replace with raw proximity evidence | Internal score yes |
| ranked cards, `#1`, `Top candidate`, overall comparison score | Compare | Implies a defensible winner/recommendation | `重點差異`; no ordinal rank by default | Internal scoring only if required |
| `risk score / 100` and red/yellow/green | Tax and decision | Can be mistaken for legal certainty or overall property safety | `需複核條件數` plus explicit outcome state | Rule result yes; composite score not primary |
| `官方估價` | case evidence | PLVR-based model is not an official appraisal | `實價登錄推估` | `official_valuation` remains internal |
| `合理價格`, `合理價格估算` | decision/journey | May overstate model authority | `市場參考區間` or `成交資料推估區間` | Yes |
| `估值` without method | comparison | Confusable with appraisal | `成交資料推估中位值` | Yes |
| price values labeled `萬` or unlabeled | Property Finder and tables | Inconsistent unit grammar; unit-price fields sometimes omit `/坪` | `1,850 萬元`; `52.4 萬元／坪` | Field names retain `_wan` |
| market values mix `元／平方公尺` and `萬元／坪` | Market | Correct but difficult to compare without explicit basis | choose a primary unit per view and show conversion in detail | Yes |
| `NT$0` or zero for absent costs | holding/visualization risk | Unknown can appear authoritative | `尚未估算` or `未納入` | Null remains internal |
| raw metres such as `450m`, `500 m` | Location/Map/Terrain | Spacing and conversion inconsistent | `450 公尺`; at 1,000 m use `1.0 公里` | Metres remain storage unit |
| multiple `checked_at`, `retrieved_at`, update labels | sources/workspace | Technical timestamps compete with effective period | primary `資料期間`; detail `查詢時間` | Yes |
| raw `quality_status`, `Retrieved`, `Unknown` | professional workspace | English enums in customer workspace | `證據品質`; localized value; `取得時間` | Yes |
| `google_geocoding`, `mock`, fallback reason codes | location/satellite/terrain | Provider/origin details precede user result | `定位來源` in evidence detail; `示範資料` visibly qualified | Yes |
| Satellite fallback object with `reason_code: provider_error` | Satellite Evidence | Engineering reason can leak; fallback may look like evidence | `目前無法取得衛星參考影像` and no evidence claim | Yes |
| repeated amber limitation paragraphs | Journey, Terrain, Loan, Holding, Tax, report | Warning fatigue reduces salience | one material limitation near result; full methodology in disclosure | Yes |
| English fragments such as `events`, `Rule IDs`, `Quality`, `Retrieved` | Case/workspace/visualization | Locale incompleteness | localized UI labels; proper nouns only remain untranslated | Yes |
| `jurisdiction` | official data status | Untranslated field label | `適用地區` | Yes |
| `Executive Decision Pack`, `Due Diligence Review Board` | Case readiness | Internal/enterprise naming over user task | `決策摘要` and `查核清單` | Yes |
| `INSUFFICIENT_SPECIFICITY` and reason/error-code family | potential dynamic errors | Machine reason is not actionable | `地址資訊不足，請補上縣市、行政區與路段` | Yes |
| backend `disclaimer`, `explanation`, `reason` displayed verbatim | several result panels | Locale, tone, and safety cannot be guaranteed | map stable codes/structured fields to curated copy; raw text only diagnostics | Yes |

### 2.3 Repetition and locale debt

The same limitation is frequently restated at journey level, module intro, result card, evidence disclosure, and report. Warnings should be deduplicated by meaning, not merely by identical string. The primary warning owner is the result boundary; journey copy provides only a short scope statement, and evidence details carry methodology.

The locale architecture also permits base resources, overrides, domain dictionaries, and direct literals to drift independently. Japanese and Korean currently retain English feature names and, in some cases, English helper sentences. This is not a translation-only defect; it is an ownership defect.

## 3. Four-level language hierarchy

| Level | Purpose | Content | Length and placement | Must not contain |
|---|---|---|---|---|
| 1. Primary result | enable the next decision | result, qualified status, unit, effective period, next action | heading plus one short line; always visible | providers, endpoints, raw codes, stacked disclaimers |
| 2. Supporting context | prevent material misinterpretation | what result means, one material limitation, missing item | one or two short sentences near result | full methodology, repeated warnings |
| 3. Evidence details | establish traceability | agency, dataset, coverage, effective period, checked time, method | disclosure opened on demand | HTTP status, internal route, request ID |
| 4. Diagnostics | support troubleshooting | provider ID, endpoint, HTTP status, request ID, raw reason/error code | support-only or explicit diagnostic view | decision claims or customer guidance |

Provider names never substitute for a result. For example, Level 1 says `目前位置未落在可用淹水圖資涵蓋內`; Level 3 identifies the Water Resources Agency dataset; Level 4 may show the provider adapter and response code.

## 4. Canonical state model

Every presentation model must carry separate axes. No generic `status` label may be rendered without knowing its axis.

```text
query_status          Did the system attempt and finish the request?
evidence_status       How usable is the returned evidence?
analysis_completeness Is the evidence sufficient for the stated task?
risk_interpretation   What, if anything, does evidence say about risk?
task_readiness        Can the user perform a named next task?
```

### 4.1 Query execution status

| Internal canonical state | zh-TW | English | Use when | Do not use when | Semantic treatment |
|---|---|---|---|---|---|
| `not_started` | 尚未查詢 | Not queried | no request has been attempted | input is missing but a request was attempted | neutral gray |
| `input_required` | 需要輸入資料 | Input required | request cannot start because required input is absent/invalid | provider rejected valid input | amber, action-oriented |
| `in_progress` | 查詢中 | Querying | a real request/calculation is active | only rendering a completed response | blue, non-pulsing where possible |
| `succeeded` | 查詢完成 | Query complete | request completed, including zero results or no coverage | evidence is necessarily usable | neutral/teal; never a safety green |
| `failed` | 查詢失敗 | Query failed | timeout, provider failure, application failure | query succeeded with no match | red for blocking, amber if non-blocking |
| `cancelled` | 已停止查詢 | Query stopped | user/replacement request cancelled execution | timeout or failure | neutral gray |

`succeeded` says nothing about coverage, evidence, completeness, or safety. A valid combination is `query_status=succeeded`, `evidence_status=no_coverage`, `analysis_completeness=insufficient`, `risk_interpretation=unknown`.

### 4.2 Evidence status

| Internal canonical state | zh-TW label | English label | Meaning |
|---|---|---|---|
| `usable` | 證據可供判讀 | Evidence usable | source, scope, period, and values meet the module's minimum contract |
| `limited` | 證據有限 | Limited evidence | some evidence is usable, but scope/sample/fields constrain interpretation |
| `no_match` | 查無符合資料 | No matching data | request succeeded and covered the query, but returned no matching record/signal |
| `no_coverage` | 不在資料涵蓋範圍 | Outside data coverage | source does not cover the location, period, or object |
| `unavailable` | 目前無法取得證據 | Evidence unavailable | source or application failed to provide evidence now |
| `stale` | 資料可能已過期 | Evidence may be outdated | evidence exists but exceeds its domain freshness rule |
| `unverified` | 來源尚未驗證 | Source not verified | demo, fallback, user-entered, or otherwise unverified evidence |
| `unsupported` | 目前不支援此項資料 | Evidence unsupported | the product cannot obtain this evidence for the requested case |

`no_match` is not `no_coverage`; `no_coverage` is not `unavailable`; none of them is `low risk`.

### 4.3 Analysis completeness

| Internal canonical state | zh-TW | English | Rule |
|---|---|---|---|
| `not_started` | 尚未分析 | Not analyzed | intended analysis has not run |
| `insufficient` | 資料不足，無法判讀 | Insufficient for analysis | evidence cannot support the intended interpretation |
| `partial` | 分析僅完成部分 | Partially complete | some material questions are answered, others remain open |
| `sufficient_for_task` | 已足以進行「{task}」 | Sufficient for {task} | named task's minimum evidence is met |
| `blocked` | 分析無法完成 | Analysis blocked | a required conflict/failure prevents safe completion |

Avoid a universal `完整` or `完成`. Completeness is always qualified by a task. An API response can make query execution complete while analysis remains insufficient.

### 4.4 Risk interpretation

| Internal canonical state | zh-TW | English | Meaning |
|---|---|---|---|
| `elevated_signal` | 發現需優先確認的風險訊號 | Elevated risk signal | evidence supports one or more material concerns |
| `caution_signal` | 發現需進一步確認的訊號 | Caution signal | evidence warrants follow-up but does not establish severity |
| `no_identified_signal` | 目前資料未發現明確風險訊號 | No identified signal in current evidence | usable, adequately covered evidence found no defined match; always include scope |
| `unknown` | 風險仍無法判定 | Risk remains unknown | evidence is absent, unavailable, uncovered, stale, or insufficient |
| `not_assessed` | 尚未評估風險 | Risk not assessed | no risk analysis attempted |

Hard rules:

- No match ≠ low risk.
- Unavailable ≠ safe.
- Query success ≠ safe.
- A green color must never communicate safety unless the copy states the exact checked scope.
- `no_identified_signal` must include the checked dataset, area, and period in evidence detail.

### 4.5 Task-specific readiness

There is no universal `ready`. The presentation contract exposes named booleans/states:

| Readiness dimension | Minimum required evidence | Optional evidence | User wording when ready | Missing wording |
|---|---|---|---|---|
| `viewing_preparation` | confirmed active property/address; material location conflicts resolved; open checks listed | market, loan, tax | `可準備看屋；仍有 {n} 項現場確認` | `補上物件位置後，才能整理看屋重點` |
| `comparison` | stable identity and same-basis price for at least two cases | valuation, location, finance | `可進行並列比較` | `至少需要 2 個物件及同一價格基準` |
| `client_discussion` | known/estimated/unknown separated; material limitations present | full technical sources | `可用於初步客戶討論` | `先補上 {item}，避免誤讀目前結果` |
| `report` | active identity; report period; all visible values have units/status; blocking conflicts resolved | optional modules may remain explicitly absent | `可產生目前資料摘要` | `需先解決 {blocking item}` |
| `offer_preparation` | confirmed asking price, financing assumptions, material due-diligence checks | demographics, satellite | `可整理出價前確認清單` | `尚缺 {item}，不宜形成出價依據` |

Optional modules must never block readiness unless that specific task names them as required. Readiness UI lists blockers separately from optional enhancements.

## 5. Confidence, quality, and completeness

Never show unqualified `信心`, `品質`, or `完整度`.

| Domain | Required label | What it measures | Presentation rule |
|---|---|---|---|
| address/location | `定位可信度` | confidence that the normalized address/coordinate identifies the intended place | pair with resolved address and confirmation action |
| valuation | `價格推估可信度` | sufficiency and similarity of transactions for the estimate | pair with comparable count, spread, period, and method; not property quality |
| evidence | `證據品質` | provenance, coverage, freshness, and completeness | prefer categorical label plus reasons over an opaque number |
| case | `案件資料完整度` | completion of defined case fields/modules | show completed/required counts; not investment merit or readiness |

`dataConfidence` in `risk-summary.ts` must be renamed at presentation to the domain it actually describes. It currently derives from valuation composition and score, so `整體資料信心` is inaccurate.

## 6. Visible score audit

| Score | Actual measure found | Interpretability / confusion risk | Recommendation |
|---|---|---|---|
| Location score | backend composite location measure | formula not visible; easily mistaken for overall location/property quality | rename `生活機能綜合指標` only after formula disclosure; otherwise replace with category evidence |
| Transit/convenience/education/green/medical indices | category composites | potentially useful if scale and inputs are documented | retain as qualified indices with `0–100` basis and methodology |
| Location risk score | category score mixed beside amenity scores | strongly confusable with hazard/safety risk | remove from score grid; show nearby risk-facility count and distance evidence |
| Property Finder suggestion score | candidate-road ranking | formula absent; implies recommendation | move to detail or replace with matched count, median price, area, and reason |
| Valuation confidence score | model evidence sufficiency | useful only with comparable count/spread/freshness | primary categorical `價格推估可信度`; number in methodology |
| Risk summary overall score | weighted valuation, price, burdens, location, completeness, then terrain gate | black-box overall property score; combines unlike concepts | remove from primary and comparison; show domain findings separately |
| Tax risk score | failed-rule count × weight in demo path | not a calibrated risk probability | replace with eligibility state, failed conditions, missing documents, review items |
| Financial burden score | derived burden thresholds | score hides the actual ratio | show monthly amount and income-burden ratio with assumption |
| Case completeness percentage | completed item ratio | useful for data entry but can look like property quality | retain as `案件資料完整度`, show numerator/denominator, neutral color |
| Comparison ranking/score | multi-domain composite | implies winner/best property | remove ordinal ranking; use `notable differences` and factual deltas |

No overall property score may be created. A score can remain only if its formula, range, input coverage, and decision boundary can be explained in one evidence disclosure.

## 7. Object and identity vocabulary

| Concept | zh-TW customer term | English customer term | Internal examples / notes |
|---|---|---|---|
| real-world home/building under review | `物件` | Property | default customer noun |
| active selected object | `目前物件` | Current property | always visible in workspace header |
| normalized identity record | `物件識別資料` | Property identity | `JourneyPropertyIdentityAnchorV1`, `PropertyEntity` remain internal |
| street address | `物件地址` | Property address | never use address as full identity by itself |
| saved analytical record | `物件案件` | Property case | not interchangeable with property |
| listing | `待售物件` | Listing | seller/portal offer, not canonical property identity |
| transaction record | `成交紀錄` | Transaction record | PLVR row; not a listing |
| parcel | `土地宗地` on first use, then `宗地` | Parcel | must not be called building/property |
| building | `建物` | Building | distinguish from parcel |
| identity anchor | not shown as a noun; use `目前分析的是：{address/label}` | Current analysis: {label} | technical term stays internal |
| identity conflict | `物件資料不一致，需要確認` | Property details conflict and need confirmation | show conflicting fields and choice |

Never expose `JourneyPropertyIdentityAnchorV1`. Every primary workspace/report must show the current property label and, where available, address plus parcel/building distinction.

## 8. Price vocabulary

| Concept | Required zh-TW label | English | Rule |
|---|---|---|---|
| asking price | `開價` | Asking price | seller/listing amount; never call estimate or value |
| recorded transaction price | `歷史成交總價` | Recorded transaction price | include transaction period |
| transaction unit price | `歷史成交單價` | Recorded transaction unit price | include `萬元／坪` or `元／平方公尺` |
| model point estimate | `成交資料推估中位值` | Transaction-based midpoint estimate | never `官方估價` |
| model range | `成交資料推估區間` | Transaction-based estimated range | preferred primary valuation result |
| user-entered comparison price | `比較基準價格` | Comparison-basis price | identify whether sourced from asking price or manual input |
| loan property price input | `貸款試算房價` | Price used for loan scenario | scenario input, not valuation |
| tax transaction amount | `稅務試算交易金額` | Transaction amount used for tax screening | scope to tax scenario |
| market median | `市場成交中位數` | Market transaction median | include geography, period, unit |

Never use `估價` to imply a licensed appraisal. Preferred module wording is `價格推估`; its limitation says `依目前成交資料推估，不是正式不動產估價報告`.

## 9. Financial vocabulary and units

### 9.1 Canonical labels

| Value | Label | Display example |
|---|---|---|
| property price / loan amount / down payment | explicit basis + `（萬元）` in inputs | `開價（萬元）`; value `1,850` |
| primary result in ten-thousands | suffix `萬元` | `1,850 萬元` |
| detailed NTD amount | prefix `NT$` | `NT$18,500,000` |
| monthly payment | `每月房貸支出` | `NT$60,752／月` |
| monthly income | `每月收入` | `NT$120,000／月` |
| monthly holding cost | `每月持有成本估算` | `NT$12,400／月` |
| annual holding cost | `每年持有成本估算` | `NT$148,800／年` |
| tax | name the tax and period | `房屋稅估算：NT$…／年` |
| insurance | `保險費估算` plus period | `NT$…／年` or `未提供` |
| affordability | `房貸占月收入比例` or `總住宅支出占月收入比例` | `50.6%` plus included items |

### 9.2 Rules

- Do not place `60752` under `萬元`. Either show `6.08 萬元／月` with deliberate conversion or, preferably, `NT$60,752／月`.
- Use comma grouping for NTD integers. Use no more than one decimal for `萬元` and `萬元／坪` unless source precision materially requires two.
- `%` attaches to the number (`35%`). State whether a ratio uses gross or net income and which costs are included.
- Missing is never zero. Use `未提供`, `尚未估算`, `不適用`, or `未納入`, according to cause.
- If area is missing, management fee is `尚未估算（缺少坪數）`, not `NT$0`.
- If income is missing, burden is `未評估（未提供月收入）`; calculation completion remains separate.
- User-entered values must be labeled `依輸入條件`; demo/fallback values must say `示範資料，不可作為案件依據` next to the value.

## 10. Distance, time, dates, and freshness

### 10.1 Distance and duration

- `< 1,000 m`: rounded whole number plus space, e.g. `450 公尺`.
- `≥ 1,000 m`: kilometres with one decimal below 10 km and whole kilometres at 10 km or above, e.g. `1.2 公里`, `12 公里`.
- Area: `平方公尺` in customer UI; `m²` is acceptable only in dense technical map detail.
- Duration under 60 minutes: whole minutes, e.g. `約 28 分鐘`.
- Duration 60 minutes or more: `1 小時 15 分鐘`; do not show decimal hours.
- Qualify method: `預估開車時間`, `大眾運輸時間`, `直線距離`; never call straight-line distance walking distance.
- Avoid false precision. Raw metres remain in data contracts.

### 10.2 Dates

| Meaning | Primary pattern | Expanded pattern |
|---|---|---|
| transaction | `成交日期：2025/01` | exact date only if source provides and it matters |
| source effective period | `資料期間：2025/01–2026/07` | include coverage geography |
| latest statistic | `最新統計期：2026/06` | agency/dataset in evidence detail |
| source vintage | `圖資版本：2025 年版` | exact publication date where available |
| query time | usually hidden | `查詢時間：2026/09/27 14:30` |
| stale evidence | `資料可能已過期` | `資料截至 2024/12；請於決策前重新確認` |
| ROC source date | customer UI converts to Gregorian | preserve original ROC notation in evidence detail if legally meaningful |

Use `資料期間`/`生效日期` before `查詢時間`. Never show both `checked_at` and `retrieved_at` in primary UI.

## 11. Source and provenance language

### 11.1 General disclosure

- Primary: result, evidence status, effective period, one material coverage limitation.
- Expanded: official agency, dataset, geographic/temporal coverage, vintage, methodology, checked time.
- Diagnostics: provider adapter, endpoint, HTTP status, request ID, raw source/reason/error codes.

`官方資料` is permitted only when the named agency/dataset is actually official. It does not make a model output an official appraisal or determination.

### 11.2 Progressive-disclosure examples

#### Market / PLVR

- Primary UI: `大安區住宅大樓成交中位單價：52.4 萬元／坪` · `資料期間：2025/01–2026/07` · `樣本 18 筆`.
- Expanded evidence: `來源：內政部不動產實價登錄開放資料（PLVR）`; filters, included/excluded count, building type, area band, update date, median method.
- Diagnostics: internal source ID `official_plvr_opendata`, ingestion version, request ID, endpoint/HTTP status.

#### WRA Flood

- Primary UI: `目前資料未發現淹水圖層符合訊號` plus `這不代表沒有淹水風險`.
- Expanded evidence: Water Resources Agency name, layer name/vintage, checked radius or geometry, coverage, query time.
- Diagnostics: provider ID, layer ID, response status, raw match/reason code.

#### Liquefaction

- Primary UI: `土壤液化潛勢：需進一步確認` or `目前位置不在資料涵蓋範圍`.
- Expanded evidence: publishing agency, map edition, resolution/scale, point-versus-parcel limitation.
- Diagnostics: service name, layer key `liquefaction`, request/HTTP details.

#### RIS demographics

- Primary UI: `里別人口資料：{period}` with population/household metrics and `里界定位已確認` or qualified limitation.
- Expanded evidence: Department of Household Registration/RIS dataset, resolved village, statistic period, retrieval date, coverage rule.
- Diagnostics: provider/source ID, village code, raw response status.

#### Google route

- Primary UI: `預估開車時間：約 28 分鐘` and route time basis; say `非即時路況` when applicable.
- Expanded evidence: origin/destination, travel mode, route checked time, whether live traffic was used, `Google Maps` attribution where contractually required.
- Diagnostics: route provider, API response status, fallback flag, request ID.

#### Valuation

- Primary UI: `成交資料推估區間：1,720–1,980 萬元`; `價格推估可信度：中等`; period and comparable count.
- Expanded evidence: PLVR source, selection criteria, 3+ comparables, spread, model method, excluded rows, freshness.
- Diagnostics: model/version, raw `confidence_score`, result origin, source IDs, request ID.

## 12. Commercial module and navigation naming

| Current name | Recommended customer name (zh-TW) | English customer name | Internal technical name | Primary navigation? | Reason |
|---|---|---|---|---|---|
| Property Finder | 找物件 | Find properties | `property-finder` / property search | entry/action, not persistent top-level | describes outcome |
| Location Insight | 區位與生活機能 | Location & amenities | location insight | under property workspace | includes POI and location evidence |
| Map Insight / GeoMap | 地圖與周邊 | Map & surroundings | map insight / geo map | secondary view | removes “Insight/Lite” branding |
| Market Insight | 區域成交行情 | Local transactions | market insight | workspace section | says what data is shown |
| Valuation | 價格推估 | Price estimate | valuation | workspace section | avoids formal appraisal implication |
| Terrain Risk | 地勢與災害資料 | Terrain & hazard data | terrain risk | workspace section | evidence, not definitive risk rating |
| Satellite Evidence | 衛星影像參考 | Satellite imagery reference | satellite evidence | evidence detail | prevents evidentiary overclaim |
| Demographics | 人口與家戶資料 | Demographics | RIS demographics | location detail | explicit data type |
| Commute | 通勤時間 | Commute time | commute route/livability | location detail | outcome-oriented |
| Loan | 房貸試算 | Mortgage scenario | loan calculator | finance section | scenario, not approval |
| Holding Cost | 持有成本估算 | Holding-cost estimate | holding cost | finance section | makes estimate explicit |
| TaxOracle | 稅務條件初步檢查 | Preliminary tax check | TaxOracle | advanced/conditional | avoids brand dominating normal path |
| Property Case | 物件案件 | Property case | property case | workspace | consistent object vocabulary |
| Viewing Decision | 看屋前確認 | Viewing preparation | viewing decision | workspace summary | does not promise recommendation |
| Decision Summary | 決策摘要 | Decision summary | decision summary | workspace summary | neutral synthesis |
| Compare | 物件比較 | Property comparison | comparison | top-level workspace action | task language |
| Report | 物件分析摘要 | Property analysis summary | report/export | top-level workspace action | avoids decision authority |
| Aegis-Credit | 資金條件評估 | Financing profile | Aegis-Credit | advanced only | current heuristic is not lending approval |

Recommended primary workspace navigation:

1. `物件總覽`
2. `價格與市場`
3. `區位與周邊`
4. `風險與待確認`
5. `資金與持有成本`
6. `比較與摘要`

`稅務條件初步檢查` appears contextually when transaction/use conditions make it relevant, or under advanced tools. Provider-specific tools and raw map layers are evidence details, not primary navigation.

## 13. Warning hierarchy

| Class | When used | Tone / prominence | Length | Example |
|---|---|---|---|---|
| Inline note | small interpretation detail | gray, adjacent | ≤ 60 zh-TW characters | `距離為直線距離。` |
| Material limitation | could change interpretation | one amber block at result boundary | heading + 1–2 sentences | `資料涵蓋有限：目前僅有點位資料，不能判定宗地是否與圖層相交。` |
| Confirmation required | user action needed | amber action row with button | one issue + one action | `物件地址與地圖位置不一致。請確認目前物件。` |
| Blocking issue | task cannot safely complete | red, focused, no other result claim | what/meaning/action | `無法確認目前物件，因此不能產生案件摘要。請重新選擇物件。` |
| Diagnostic detail | support/debug | neutral collapsed panel | as needed | `Request ID…; HTTP…` |

Do not repeat the same warning in module intro, result, evidence panel, and footer. Link from the concise primary limitation to one expanded explanation.

## 14. Error, loading, and empty-state copy

### 14.1 Error formula

Every error answers: what happened, what it means, what the user can do.

| Condition | Recommended zh-TW copy |
|---|---|
| invalid input | `輸入格式不正確。請檢查 {field example} 後再試。` |
| missing input | `需要 {field} 才能開始 {task}。` |
| provider timeout | `資料來源回應時間過長，本次查詢未完成。請稍後重試；目前結果不代表沒有資料。` |
| provider unavailable | `目前無法取得 {data type}。你可以稍後重試，或先查看其他已取得資料。` |
| data not covered | `此資料目前不涵蓋 {location/period}。這不代表沒有相關事件或風險。` |
| no result | `查詢完成，但目前條件下查無符合資料。請調整 {condition} 後再查。` |
| internal application error | `系統無法完成這項操作。已保留你的輸入，請重試；若持續發生，請提供問題發生時間。` |
| identity conflict | `物件資料不一致，需要確認。請選擇正確的地址／宗地後再繼續。` |
| stale evidence | `這項資料截至 {period}，可能已過期。請重新查詢或向來源機關確認。` |

Raw exception text, reason codes, endpoints, and provider names do not appear in the error body.

### 14.2 Loading

- Name the real task: `正在查詢區域成交資料…`, `正在計算房貸情境…`, `正在整理風險資料…`.
- Do not claim provider-level progress unless actual stages are observable.
- Do not use fake percentages.
- Long waits may add `通常需要數秒；離開此頁會停止本次查詢` only if true.
- Rendering a completed response is `正在整理結果…`, not `等待資料來源`.

### 14.3 Empty states

| State | Heading | Example support/action |
|---|---|---|
| not started | `尚未查詢` | `輸入物件地址後查詢區位資料。` |
| input required | `需要物件地址` | `補上縣市、行政區與路段。` |
| no data found | `查無符合資料` | `查詢已完成；可調整期間或條件。` |
| outside coverage | `不在資料涵蓋範圍` | `查看涵蓋說明或改用人工查核。` |
| temporarily unavailable | `目前無法取得資料` | `稍後重試；這不代表沒有資料或風險。` |
| unsupported | `目前不支援這項查詢` | `查看可支援的地區或資料類型。` |
| no match | `目前未發現符合訊號` | `僅代表已檢查資料與範圍；仍請查看限制。` |

Never use `無資料` as a catch-all.

## 15. Completion language

- `查詢完成`: execution ended successfully, even with zero results.
- `已取得結果`: a result object exists; not necessarily usable.
- `計算完成`: arithmetic completed under stated inputs.
- `已足以進行 {task}`: task readiness threshold met.
- `尚待確認`: an unresolved item remains.
- `已完成`: reserved for a clearly named user action such as `已完成看屋紀錄`; never a generic module state.

Examples:

- Loan: `房貸試算完成` and, if income missing, `負擔能力尚未評估（未提供月收入）`.
- Terrain: `資料查詢完成`; if coverage is partial, `風險仍無法完整判定`.
- Report: `摘要已產生`; optional modules remain listed as `尚未分析`, not silently complete.

## 16. TaxOracle language contract

Customer name: `稅務條件初步檢查`. `TaxOracle` may appear as a secondary product label in advanced detail.

Visibility triggers:

- user opens advanced tools;
- transaction type, ownership, residence, holding period, or exemption conditions make tax checks relevant;
- a report has a material unresolved tax item.

Primary UI shows current preliminary outcome, confirmed facts, missing information, items for professional review, and next action. Advanced detail may show rule trace and version. Diagnostics may show rule IDs, endpoint, provider/source configuration, and request ID.

Required boundary: `依目前輸入與固定規則進行初步篩選，不是主管機關核定、個人稅務紀錄或稅務／法律意見。` Do not say `AI 判定`; if AI rewrites an explanation, label that function separately and never let it alter the rule result.

## 17. AI terminology

`PropTech AI Copilot` may remain the product brand. Elsewhere, mention AI only when it explains a real user-facing function, such as summarizing already cited evidence or drafting a client explanation.

Do not apply AI language to deterministic rules, financial calculations, GIS intersections, government-data lookup, filters, or unit conversion. Prefer `依固定規則計算`, `依地圖圖層查核`, `依公開成交資料推估`, and `整理已取得證據`.

Every generated narrative must remain traceable to evidence, distinguish facts from estimates, and say when source evidence is insufficient. Avoid `AI-powered`, `智能`, `智慧` as empty quality claims.

## 18. Translation architecture and zh-TW style

### 18.1 Ownership

- Backend enum and API identifiers are never translated in contracts.
- All user-facing labels are localized at the presentation boundary.
- Official agency names use the agency's official localized name; dataset names may preserve recognized acronyms such as PLVR/RIS after a translated first use.
- Product feature names follow the customer names in §12; internal component names remain unchanged.
- Proper nouns such as Google Maps remain as required.
- Financial unit symbols are locale-aware, but the semantic basis must remain equivalent.
- No locale falls back to English silently in a primary flow. Missing keys fail a parity test.

Future architecture should converge on one canonical key registry and typed domain dictionaries. Overrides are temporary migration tools, not permanent competing authorities. Dynamic backend strings require stable reason keys, not machine translation at render time.

### 18.2 zh-TW style guide

- One UI sentence should usually stay below 32 Chinese characters; split material explanations into two sentences.
- Use full-width Chinese punctuation in sentences: `，。；：`; avoid terminal punctuation on short labels/buttons.
- Add a half-width space between Chinese and Latin/acronyms/numbers when it improves legibility: `PLVR 資料`, `2026/09`, `50 公尺`; `%` stays attached.
- Use Arabic numerals and explicit units. Use en dash `–` for ranges.
- Neutral, direct tone: `請確認物件地址`; avoid bureaucratic `敬請惠予確認` and childish reassurance.
- Buttons use outcome verbs: `查詢區域成交`, `計算每月房貸`, `加入物件比較`, `產生分析摘要`.
- Warnings state the limitation, consequence, and next action without alarmist language.
- Avoid mixed-language headings when a customer term exists.

## 19. Button/action vocabulary

| Ambiguous/current pattern | Preferred outcome label |
|---|---|
| 開始 / 執行 / 送出 | `查詢區域成交`, `開始地勢資料查核` |
| 分析 | `分析區位與生活機能` |
| 計算 | `計算每月房貸`, `估算持有成本` |
| 套用 | `帶入房貸試算`, `帶入價格推估` |
| 查看 | qualify object: `查看證據細節`, `查看待確認事項` |
| 繼續 | qualify destination: `前往價格與市場` |
| 完成 | `結束本次瀏覽` or named completion |
| Compare | `加入物件比較` / `開始比較` |
| Report | `產生分析摘要` / `列印目前摘要` |

Buttons describe what changes or what view opens. Destructive or persistent actions explicitly name saving/removing.

## 20. Report and comparison language

### 20.1 Client report

Reports are more self-contained than in-app copy. Every result includes label, value and unit, known/estimated/unknown state, effective period, and material limitation. Reports group `已確認`, `估算／推估`, `尚待確認`, and `下一步查核`.

Reports exclude provider adapters, endpoints, HTTP states, raw enums/codes, debug IDs, and promotional copy. An appendix may list agencies, datasets, methods, and retrieval times. The title is `物件分析摘要`, not an appraisal or recommendation.

### 20.2 Comparison

Do not use `winner`, `best property`, `recommended property`, `top candidate`, ranks, or a composite score. Use factual phrases:

- `主要差異`
- `可用證據較完整`
- `每月住宅支出較高`
- `待確認項目較多`
- `成交資料期間不同`
- `目前無法直接比較（價格基準不同）`

Comparison must normalize units and state the basis. Missing data never sorts as zero or favorable.

## 21. Product-language migration inventory

| File/component | Current issue | Future migration |
|---|---|---|
| `frontend_next/lib/surface-copy.ts` | separate Terrain/Holding/Shell vocabulary; generic states; provider-origin labels | consume canonical axis labels and formatters; retain domain copy only |
| `frontend_next/lib/runtime-copy.ts` | very large multilingual resource; API/debug and mixed terms; parity drift | migrate to canonical keys by domain; remove technical primary copy |
| `frontend_next/lib/runtime-copy-overrides.ts` | hidden precedence and duplicate ownership | fold approved strings into canonical resources, then retire overrides |
| `frontend_next/lib/experience-i18n.ts` | generic `ready/available`; English module names | adopt customer navigation and state axes |
| `frontend_next/lib/experience-i18n-overrides.ts` | competing wording authority | fold and retire after parity tests |
| `frontend_next/lib/experience-architecture.ts` | one `ExperienceState` mixes evidence/execution/completeness | replace presentation mapping with separate canonical axes |
| `frontend_next/app/page.tsx` | page identities and direct module routing use technical names | keep internal IDs, map to customer names and contextual tools |
| `frontend_next/components/hero-intro.tsx`, `workflow-entry-cards.tsx` | AI/marketing and mixed feature names | task-first homepage copy |
| `frontend_next/components/sidebar.tsx` | `Lite`, TaxOracle, Aegis, generic service “Available”, brand mismatch | workspace navigation in §12; health only when real |
| `frontend_next/components/guided-journey/*` | viewed/completed/readiness language overlaps; repeated amber notes | render the five axes and named readiness |
| `frontend_next/components/property-finder.tsx` | unlabeled score; `萬`; result reasons; demo actions | remove score prominence; canonical money/source/demo labels |
| `frontend_next/components/location-insight.tsx` | raw data-quality status, score grid, raw metres/sources | evidence mapping, qualified indices, distance formatter |
| `frontend_next/components/map/geo-map.tsx`, map surfaces | raw `m`, provider-centric details | canonical distance and progressive source disclosure |
| `frontend_next/components/market-segmentation-panel.tsx`, Market components | available/partial/no-data overlap | execution/evidence/completeness separation |
| `frontend_next/lib/market-result-state.ts` | combines coverage, evidence, freshness into one display state | preserve derivation but expose separate presentation axes |
| Valuation components and `valuation-result-state.ts` | “official valuation”, confidence ambiguity | price vocabulary and valuation-confidence contract |
| `frontend_next/components/terrain-risk-analysis.tsx` | status layers are strong but warnings repeat; raw metres/provider source | risk axis, one limitation, source detail, formatters |
| `frontend_next/components/satellite-evidence.tsx` | fallback/reason semantics | evidence-unavailable state; no fallback authority |
| `frontend_next/components/demographics-insight-card.tsx` | source/vintage/status consistency | RIS example and freshness language |
| `frontend_next/components/commute-*.tsx` | `無資料`, fallback, route source ambiguity | route-specific state and time/distance qualifiers |
| `frontend_next/components/loan-calculator.tsx` | calculation completion can imply affordability | separate calculation result and affordability completeness |
| `frontend_next/components/holding-cost-calculator.tsx` | unknown/omitted/zero risks | explicit missing reasons and unit formatter |
| `frontend_next/lib/taxoracle-presentation.ts`, Tax components | deterministic/API/rule-ID language and score | preliminary tax-check contract |
| `frontend_next/lib/workflow-status.ts` | object presence equals completion; one overall percentage | named readiness and evidence gating |
| `frontend_next/lib/risk-summary.ts` | black-box cross-domain overall score | domain findings; no primary composite score |
| `frontend_next/lib/property-case-evidence.ts` | `official_valuation`, trusted, raw signal color | commercial labels and evidence status mapping |
| `frontend_next/lib/property-case-readiness.ts`, Case components | universal ready, English internal names/booleans | task-specific readiness |
| Decision components and `decision-summary.ts` | recommendation wording can exceed evidence | neutral preparation/next-check wording |
| Compare components and `property-comparison.ts` | rank/top candidate/score | factual differences, normalized basis |
| Report/print components and `valuation-share.ts` | static copy bypasses locale; units/source status vary | report language contract and localized formatters |
| `frontend_next/components/professional-workspace-shell.tsx` | raw quality/retrieved enums and English diagnostics | localized evidence summary; diagnostics disclosure |

## 22. Parallel-branch dependencies

Implementation must rebase its inventory after these streams land; do not encode current contracts as permanent assumptions:

- **Valuation / Holding Cost reliability:** wait before finalizing price-status adapters, missing-cost semantics, confidence thresholds, and money fields.
- **Commute production closure:** wait before finalizing fallback, route freshness, travel-mode, and provider-attribution wording.
- **Journey Property Identity:** wait before implementing active-property labels, identity conflict copy, and report identity header.
- **Geological Sensitivity:** wait before freezing hazard evidence/risk mappings and coverage/no-match distinctions.
- **Commercial Workspace Architecture:** wait before changing primary navigation or module placement.
- **Commercial Design System:** wait before binding semantic colors, warning components, badges, and disclosure layout.

Safe work before those merges: canonical taxonomy types, pure formatters, copy lint rules, glossary documentation, and test fixtures that do not assume pending response shapes.

## 23. Commercial acceptance criteria

1. **No engineering leakage:** primary paths contain no API/HTTP/method/provider class, endpoint, raw enum, internal code, source ID, request ID, or schema field.
2. **Independent states:** query completion never automatically yields usable evidence, complete analysis, low risk, or task readiness.
3. **Risk safety:** no-match, no-coverage, unavailable, stale, unknown, and not-assessed never read as safe.
4. **Units:** every financial value names currency and period/basis; distance/time follows §10; missing values never render as zero.
5. **Price semantics:** opening price, transaction price, estimate range, midpoint, scenario price, and tax amount are never interchangeable.
6. **Completion:** calculation completion is distinct from affordability completion and report readiness.
7. **Identity:** every workspace, comparison, and report makes the active property unmistakable; conflicts block unsafe synthesis.
8. **Sources:** primary results are understandable without source detail; expanded evidence names agency, dataset, period, coverage, and method.
9. **Warnings:** one material limitation is shown at the result boundary; duplicate amber warnings are absent.
10. **Scores:** no black-box overall property ranking/score is primary; qualified scores disclose domain and method.
11. **Locale:** zh-TW primary workflows contain no accidental English fragments except approved proper nouns; EN/JA/KO key parity is complete.
12. **Errors:** every visible failure says what happened, what it means, and what to do next.
13. **Demo/fallback:** illustrative, fallback, user-entered, and unverified evidence cannot appear authoritative or transfer as verified case evidence.
14. **Reports/comparison:** reports distinguish known/estimated/unknown and comparisons state differences without declaring a winner.

## 24. Contract summary

The commercial language system is not a synonym list. It is a presentation architecture. Internal contracts may continue to use domain enums such as `available`, `not_started`, provider identifiers, and source codes, but the UI must translate them through explicit axis-specific adapters. The customer sees the result, meaning, evidence boundary, and next action. Technical implementation remains traceable without becoming the product's primary language.
