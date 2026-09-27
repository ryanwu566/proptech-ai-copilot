# PropTech AI Copilot Commercial Design System v1

**Status:** implementation-ready specification; no application styling is changed by this document

**Audience:** product design, frontend engineering, QA, accessibility review, and commercial acceptance reviewers

**Baseline audited:** `docs/commercial-design-system-v1` at `7f442f8aa9f2217b872fa703065ea522dd8a8457`

**Product intent:** make the product feel like credible, quiet, analytical PropTech decision-support software for client-facing use, while preserving useful density and truthful uncertainty.

## 1. Scope and success criteria

This system governs the visual presentation of the current Next.js/Tailwind frontend. It does not change product behavior, provider contracts, calculation logic, risk classification, or copy semantics. It applies to the legacy shell, guided journey, analytical tools, case/decision surfaces, reports, and the newer professional/property-identity workspaces.

Success means:

- a user can identify the property, current task, major conclusion, uncertainty, and next action without reading every container;
- the same status, unit, action hierarchy, and evidence hierarchy look and mean the same thing in every module;
- maps, tables, and charts are first-class analytical surfaces rather than content inside layers of decorative cards;
- dense evidence remains scannable on desktop and usable at 390 px without nested scrolling;
- green communicates successful completion only, never safety, investment quality, or a purchase recommendation;
- visual treatment does not imply greater confidence than the underlying data supports.

Non-goals: a marketing rebrand, decorative illustration system, new workflow architecture, copy rewrite, or immediate CSS/component implementation.

## 2. Current frontend audit

### 2.1 Architecture observed

- `frontend_next/app/globals.css` is only 44 lines. It sets the canvas, Arial/`Noto Sans TC`, a cyan focus outline, Leaflet fixes, and numerous hero/onboarding animations. Most styling lives in component-local Tailwind strings.
- `frontend_next/tailwind.config.ts` defines only five named colors and one card shadow. Components therefore use many raw Tailwind palette roles and arbitrary hex/shadow values directly.
- `frontend_next/components/ui.tsx` supplies `Card`, `Metric`, `Button`, `Badge`, `Notice`, and one generic `EmptyState`; `frontend_next/components/product-ui.tsx` adds `MetricTile`, `SectionCard`, `ResultSummaryPanel`, page/hero patterns, status badges, and additional loading/error patterns. These two layers overlap.
- `frontend_next/app/page.tsx` is both the route controller and the principal style composition surface. It contains the homepage, dashboard, Market, Map, Valuation, Finance, Tax, and supporting panels, with additional one-off primitives.
- Newer workspaces use independent CSS modules (`professional-workspace-shell.module.css`, `property-identity-review.module.css`, `vnext-property-identity-workflow.module.css`) with different greens, radii, focus colors, shadows, widths, and breakpoints.
- The repository has useful semantic/model code for market, valuation, risk, case readiness, and visualizations. The main debt is presentation consolidation, not a lack of analytical data.

### 2.2 Source-level styling signals

An audit of 151 TSX/CSS files under `frontend_next/app` and `frontend_next/components` found 671 `rounded-*`, 68 `shadow-*`, 24 gradient declarations/usages, 479 cyan, 303 amber/yellow, 92 emerald, 79 rose, and 61 violet occurrences. It also found 99 `<details>`/`DetailDisclosure` uses, 16 tables, and 16 `overflow-x-auto` table wrappers. These counts are code occurrences, not rendered-element counts, but they show the degree of visual repetition and local styling.

`frontend_next/app/page.tsx` alone contains 94 rounded, 12 shadow, 11 gradient, 76 cyan, and 43 amber/yellow occurrences. `property-case-command-center.tsx` contains 65 rounded and 15 shadow occurrences. `terrain-risk-analysis.tsx` contains 24 rounded elements plus several nested warning/evidence/status treatments.

### 2.3 Surface findings

- **Homepage and guided journey:** `HeroIntro`, `DecisionHero`, hero flow nodes, pills, animated orbs/grid, gradient module tiles, competition banner, and multiple rounded disclosure entry points create several simultaneous focal points. Journey stages inherit cards from the embedded tools, causing card-within-stage-within-workspace nesting.
- **Location and maps:** `LocationInsight` starts with a card, then a four-item flow strip, a two-column form/result layout, metric tiles, disclosures, Google visual context, Terrain, Commute, and case actions. `GeoMap` has useful 360/500/650 px heights, but other map surfaces sit inside rounded panels or simulated decorative maps. Location may legitimately be map-dominant.
- **Market and valuation:** rich evidence exists, but results are repeated as status banners, metric cards, section cards, chart cards, disclosure cards, provenance blocks, and wide tables. Numerical units are embedded inconsistently in strings.
- **Terrain and risk:** warnings are repeated above, within, and below results. Completeness, priority follow-up, cadastral evidence, satellite evidence, source transparency, hazard cards, reference attachment, layer tables, and missing-source notices compete visually. Green/red/amber treatments risk looking evaluative rather than evidentiary.
- **Finance:** Loan and Holding Cost use a narrow input column plus result column, then summary cards, four metric tiles, multiple chart shells, breakdown cards/tables, and warning notices. Full-width buttons and empty boxes add height before results exist.
- **Decision and case:** `DecisionReport`, `ViewingDecisionPanel`, readiness, command center, case manager, comparison workbench, comparison report, and print report each introduce their own bordered container. Recommendation/status colors sometimes encode business meaning with green, conflicting with completion semantics.
- **Navigation:** the 192 px dark sidebar, topbar controls, global amber limitation strip, module tabs, and disclosure-based dashboard navigation use several different selected/active treatments. Navigation sometimes resembles a grid of feature buttons.
- **States and accessibility:** loading/error/empty implementations are fragmented (`EmptyState`, `LoadingState`, `ErrorState`, chart-specific states, inline paragraphs, dashed boxes). Focus is generally present, tables often have headers, and charts include text alternatives, but focus color and error/status semantics vary. `prefers-reduced-motion` exists globally and must remain authoritative.

## 3. Visual debt inventory

| Current pattern | Why it reduces commercial credibility | User impact | Replacement | Likely components/files |
|---|---|---|---|---|
| Nearly every section is `rounded-xl`/`rounded-2xl` + border + white | All content appears equally separable and equally important | Users scan shells, not conclusions | Plain page sections with dividers; reserve panels for stateful units | `ui.tsx`, `product-ui.tsx`, `app/page.tsx` |
| Cards nested inside cards/disclosures | Repeats padding and borders without adding meaning | Lost width, excessive scrolling, weak hierarchy | One structural boundary; inner content becomes rows, table, or plain section | `ValuationVisualPanel`, `LocationInsight`, `DecisionReport`, journey stages |
| Radii from `rounded-md` through 24 px/arbitrary values | Multiple redesign layers remain visible | Product feels assembled rather than governed | Four semantic radius tokens; 0 radius for section/table rows | CSS modules, shared UI, page-local JSX |
| Cyan, emerald, amber, rose, blue, violet, sky, yellow used as accents | Module identity and status semantics collide | Color cannot be trusted | One action blue plus fixed semantic colors | `app/page.tsx`, `product-ui.tsx`, visualization panels |
| Green used for eligibility, readiness, safety-like risk states, and success | Completion can be mistaken for a positive recommendation | Decision risk | Green only for completed/verified process state; risk uses text + neutral/amber/red evidence semantics | `Badge`, `ViewingDecisionPanel`, `RiskSummaryPanel`, comparison rankings |
| Hero gradients, orbs, grids, flow animation, decorative mini-map | Signals startup/demo energy over analysis | Client-facing credibility drops | Compact product header; one concise orientation block | `HeroIntro`, `DecisionHero`, `globals.css`, `product-ui.tsx` |
| Oversized homepage/identity heroes | Pushes active work below fold | Slower task entry | Page title + context + one primary action within 120–180 px | `hero-intro.tsx`, property identity CSS modules |
| Typography uses 9/10/11 px arbitrary sizes and `font-black`/all-caps widely | Microcopy and emphasis become noisy; Chinese readability suffers | Strain and poor hierarchy | Defined 12–32 px scale; 12 px minimum for persistent UI | Many components; `product-ui.tsx` |
| Financial units embedded ad hoc in strings | `萬`, `元`, `%`, and periods are hard to compare | Misreading values | Numeric component/format policy; tabular figures, explicit unit columns | Valuation, loan, holding cost, market, comparison |
| Primary buttons frequently full-width and tall | Actions dominate forms and add vertical mass | Primary analysis is visually secondary | 36/40 px controls; full width only on narrow mobile or linear submit flows | calculators, `Button`, identity CSS modules |
| Grid stretch creates tall blank result/empty areas | Layout looks unfinished before analysis | Users misread empty space as missing UI | Content-sized forms and state-specific compact guidance | Loan, Holding Cost, Location, Terrain |
| Repeated amber banners | Everything looks risky or provisional | Warning fatigue | Four-level warning hierarchy; methodology in disclosure | `AppShell`, Terrain, Valuation, Finance, reports |
| Repeated source/provenance cards | Evidence competes with findings | Important result is harder to find | Compact evidence table + quiet metadata + details disclosure | Market, Terrain, Satellite, Valuation |
| Long limitations inside primary results | Legal/source copy interrupts analysis | Reduced comprehension | One-line inline limitation; full text in details unless material | `RiskSummaryPanel`, `SatelliteEvidence`, finance panels |
| Tables use minimal cell rules and inconsistent alignment | Analytical comparisons feel less rigorous | Slow cross-row comparison | Shared dense table with numeric alignment, units, sticky headers | Market, valuation, terrain, case comparison, finance |
| Every mobile table becomes horizontal scroll | Repeated side-scroll and nested page/map gestures | Important columns are hidden | Choose stacked rows, selective scroll, pinning, or drawer per use case | All 16 table wrappers |
| Maps live in decorative shells or compete with long side lists | Spatial evidence loses priority | Users cannot maintain location context | Map-first layouts, bounded overlays, independent detail drawer | `GeoMap`, `TerrainEvidenceLeafletMap`, Location, professional workspace |
| Charts repeat border/radius/padding shells | More chart chrome than information | Low-value charts fill space | Analytical section owns title/unit/source; chart itself is unboxed | data-visualization components |
| Form controls duplicate classes and omit consistent unit affordances | Inconsistent focus, height, labels, and validation | Entry errors and unit ambiguity | Shared Field/Input/Select/UnitInput primitives | calculators, Market segmentation, `app/page.tsx` |
| Badge/pill for headings, sources, filters, states, and hero copy | Excessive “tag” language | Visual noise, weak semantics | Inline metadata or plain label; pills only for bounded state/filter/category | `Badge`, `HeroPill`, data status badges, module surfaces |
| Generic empty/loading/error boxes | Distinct situations look identical | Users do not know whether to act or wait | Typed state patterns with cause and next action | `ui.tsx`, `product-ui.tsx`, chart states |
| Independent CSS-module design languages | New workspaces do not look like the same product | Trust breaks during navigation | Consume the same tokens and primitives; retain layout-specific CSS | three CSS modules |
| Multiple sticky/scroll regions | Potential nested scrolling and orientation loss | Keyboard/touch navigation becomes difficult | Page scroll by default; one intentional sticky region; no nested vertical scroll | shell, professional workspace, maps |

## 4. Design principles

1. **Structure before decoration.** Establish meaning with order, headings, alignment, whitespace, dividers, tables, charts, and maps before adding a surface.
2. **Fewer containers.** A section does not become a card merely because it has a heading.
3. **One primary action color.** Product blue identifies actionable controls and focus, never product modules.
4. **Consistent semantic states.** Every semantic color has one meaning across every module.
5. **Numbers carry explicit units.** Comparable quantities share formatting, alignment, precision, and unit placement.
6. **Evidence is quieter than conclusions.** Provenance remains available and trustworthy without competing with the result.
7. **Useful density is professional.** Tables and financial inputs may be compact; whitespace is used to reveal hierarchy, not inflate components.
8. **Unknown is not safe.** Missing, limited, and unavailable data must not inherit positive visual treatment.
9. **One visual language, multiple layouts.** Market, map, risk, finance, and decision surfaces may differ structurally while using the same tokens and primitives.

## 5. Typography

Use one system sans family: `Inter, "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", system-ui, sans-serif`. If Inter is not shipped, begin with the system stack; do not add a second display family. Chinese text must remain at normal tracking and at least 12 px for persistent UI.

| Role/token | Size / line-height | Weight | Usage |
|---|---:|---:|---|
| Product/page title `text-page` | 30/38 px desktop; 26/34 mobile | 700 | One per page |
| Workspace section title `text-section` | 20/28 px | 700 | Major workflow section |
| Subsection title `text-subsection` | 16/24 px | 650–700 | Table/chart/panel heading |
| Body `text-body` | 14/22 px | 400 | Default prose |
| Dense analytical body `text-dense` | 13/20 px | 400–500 | Tables, evidence, compact forms |
| Form label `text-label` | 13/18 px | 600 | Sentence case |
| Metadata `text-meta` | 12/18 px | 500 | Timestamps, secondary context |
| Evidence/source metadata `text-evidence` | 12/18 px | 400 | Provider, vintage, methodology |
| Table header `text-table-head` | 12/16 px | 650 | Sentence case; no forced uppercase |
| Table body `text-table-body` | 13/18 px | 400–500 | Default dense table |
| KPI `text-kpi` | 28/34 px; 24/30 mobile | 700 | At most 1–2 values per section |
| Secondary numeric `text-number` | 18/24 px | 650 | Summary strip and comparisons |
| Warning/error `text-message` | 13/20 px | 500 | Plain language; title may be 650 |
| Helper `text-helper` | 12/18 px | 400 | Input guidance and limitations |

Apply `font-variant-numeric: tabular-nums lining-nums` to tables, KPIs, monetary values, dates, percentages, durations, and coordinates. Use `letter-spacing: -0.015em` only for page titles/KPIs in Latin text; Chinese stays at `normal`. Uppercase is limited to short product codes, dataset codes, and export labels of at most three words; do not uppercase navigation, statuses, or Chinese labels. Avoid `font-black` as a general hierarchy mechanism.

## 6. Numerical typography and units

### 6.1 Rules

- The number and unit form one semantic value and do not wrap separately. Use a non-breaking space (`NT$ 2,180 萬`, `650 m`) in prose and KPIs.
- Use locale-aware thousands separators. Do not mix `NTD`, `NT$`, `元`, and `萬` within one table or summary.
- Recommended display currency for total property values: `NT$ 2,180 萬`. Recommended base currency in detailed breakdowns: `NT$ 21,800,000` or `21,800,000 元`, selected once per surface.
- Use `萬/坪` for market and valuation unit price, `元/月` for recurring monthly amounts, `元/年` for annual charges, and `%` for ratios. Never show a bare number when the label could be separated from it.
- Use `坪` for product-facing property area; if `m²` is required, show it as a secondary conversion: `72.4 坪（239.3 m²）`.
- Use at most one decimal for 坪, percentages, km, years, and calculated rates unless a regulated/source value requires more. De-emphasize extra decimals with the secondary numeric style; never enlarge them.
- Right-align numeric table cells and their headers. Align decimal places where comparison matters. Put a stable unit in the column header (`單價（萬/坪）`) rather than repeating it in every row.
- Use `—` for unavailable, not `0`. Use `未提供`, `無涵蓋`, or `無符合資料` when the reason matters.

### 6.2 Canonical formats

```text
NT$ 2,180 萬
NT$ 60,752 / 月
72.4 坪
18.7%
650 m
1.4 km
23 min
2026-09-27
2026 Q2
資料版本：2026-08-31
```

Dates use `YYYY-MM-DD`; month-level vintages use `YYYY-MM`; quarters use `YYYY Qn`. Relative time may supplement but never replace the absolute vintage. Durations use `min` in compact analytical UI and localized words in prose. Coordinates use a consistent 5–6 decimal precision only in evidence details.

## 7. Spacing and sizing

Use a 4 px base: `0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64`.

| Purpose | Desktop | Tablet | Mobile 390 px |
|---|---:|---:|---:|
| Page gutter | 32 px | 24 px | 16 px |
| Standard workspace max width | 1440 px | fluid | fluid |
| Reading/report max width | 960 px | fluid | fluid |
| Map/GIS max width | 1680 px or full workspace | fluid | full bleed within page gutter |
| Major section gap | 32 px | 28 px | 24 px |
| Subsection gap | 20 px | 20 px | 16 px |
| Panel padding | 20 px | 16–20 px | 16 px |
| Dense table row | 40 px target | 40 px | 44 px touch target where interactive |
| Form field gap | 16 px groups; 12 px fields | same | 12 px |
| Navigation item | 36–40 px high | 40 px | 44 px |
| Inline icon gap | 8 px | 8 px | 8 px |
| Disclosure heading | 12 px vertical | 12 px | 14 px |

No arbitrary spacing is introduced without documenting a layout constraint. Grid children default to content height; do not stretch forms/buttons to match an adjacent empty/result column. Full-width tall buttons are reserved for single-path mobile forms.

## 8. Radius, border, and elevation

### 8.1 Radius tokens

- `radius-control: 6px` — inputs, compact buttons, segmented controls.
- `radius-panel: 8px` — independently stateful panels, dialogs, map frames.
- `radius-dialog: 12px` — modal/dialog only.
- `radius-pill: 999px` — status/filter/category chips only.
- Tooltip radius: 4 px. Table, section divider, evidence row, and inline alert radius: 0–6 px as specified by their primitive.

Use radius when a boundary represents a discrete interactive/stateful object, a floating overlay, or a clipped media/map viewport. Do not use radius for every subsection, metric, paragraph, evidence source, table row, form group, chart, or disclaimer. Adjacent content groups should usually use spacing and a top border.

### 8.2 Border and shadow tokens

- Standard border: 1 px neutral `border-subtle`.
- Emphasized boundary: 1 px `border-strong`.
- Selected: 1 px action border plus a 2 px outer selection ring; do not add shadow.
- Focus: 2 px `focus` ring with 2 px offset; 3:1 contrast against adjacent colors.
- Error: 1 px `error-border` plus icon/text; never color alone.
- Elevation: `shadow-overlay` only for menus, popovers, dialogs, sticky overlays, and map floating controls. Optional `shadow-raised` is allowed for one sticky side panel. No default card shadow, glow, or decorative elevation ladder.

## 9. Color system

Tokens define roles; implementation values below are starting values subject to contrast verification.

| Role | Recommended value | Meaning |
|---|---|---|
| `canvas` | `#F5F6F7` | Neutral application background |
| `surface-primary` | `#FFFFFF` | Main reading/working surface |
| `surface-secondary` | `#F8FAFB` | Subtle grouped rows and controls |
| `text-primary` | `#172033` | Main content |
| `text-secondary` | `#475569` | Supporting content |
| `text-muted` | `#64748B` | Metadata; must still meet contrast |
| `border-subtle` | `#DCE2E7` | Default structure |
| `border-strong` | `#B8C2CC` | Emphasized structure |
| `action` | `#155E75` | Primary action and active navigation |
| `action-hover` | `#164E63` | Hover/pressed action |
| `focus` | `#0284C7` | Keyboard focus only |
| `success` | `#16794B` | Query/action completed or completion verified |
| `information` | `#2563A6` | Informational/active/in-progress |
| `warning` | `#9A6700` | Needs confirmation, incomplete, limited |
| `error` | `#B42318` | Error or blocker |
| `disabled` | neutral surface/text pair | Unavailable control; never status |

Module identity is expressed by title and navigation context, not separate colors. Risk interpretation uses explicit wording such as `已比對到風險圖層`, `未比對到`, `資料有限`, or `未檢查`; green is prohibited for “safe property”, “good investment”, “low hazard”, or purchase advice.

## 10. Status semantics

| State | Color | Required wording pattern | Icon |
|---|---|---|---|
| Neutral | neutral | `尚未開始`, `不適用`, `未檢查` | circle/minus as appropriate |
| Blue | information | `分析中`, `目前步驟`, `資訊` | spinner/info |
| Amber | warning | `需要確認`, `資料不完整`, `涵蓋有限` | alert triangle |
| Red | error | `無法完成`, `阻擋`, `錯誤` | error/octagon |
| Green | success | `查詢完成`, `已驗證完成`, `已儲存` | check |

Every status includes text and, for compact presentation, an icon or explicit label. Color is supplementary. Data availability and analytical interpretation are distinct fields: a query may be successfully completed (green process state) while returning a material risk match (red evidence state) or no coverage (amber availability state).

## 11. Card decision tree

Ask in order:

1. Does the content have its own interaction, action, state, or lifecycle?
2. Can it be moved/reused independently without losing meaning?
3. Does a visible boundary prevent confusion with adjacent content?

Use a card/panel only when at least one of 1–2 is true and 3 is justified. Otherwise use a page section, section divider, metric row, description list, evidence table, inline status, or details disclosure.

Never create a card solely for a paragraph, metric, source, disclaimer, subsection, form group, table row, or heading. A card must have one owner, one purpose, and at most one dominant action.

## 12. Structural patterns

- **Summary strip:** 3–5 compact values in a single bordered row; one may be primary. On mobile it becomes a two-column grid or vertical description list, not separate cards.
- **Analytical section:** heading, one-sentence question/context, main table/chart/map, then source/date metadata. The analytical surface is unboxed unless it needs independent state.
- **Evidence section:** dense table or ordered rows with source, result, status, vintage, and limitation.
- **Action section:** explicit next actions after findings; one primary, optional secondary/text actions.
- **Details disclosure:** methodology, full sources, limitations, advanced filters, or support/debug data.
- **Side panel:** only for context that must remain visible while interacting with a map/comparison/form. It may be sticky but must not create a second vertical scroll by default.

## 13. Table system

All tables use sentence-case headers, 12 px headers, 13 px body, tabular numerics, 40 px default rows, horizontal separators, no zebra striping by default, and hover only when a row is interactive. Numeric columns are right-aligned; units live in headers. Sticky headers are used when more than approximately 10 visible rows or inside a fixed analytical viewport. Row highlighting indicates selected, changed, matched, blocked, or stale state only.

| Use case | Desktop | Mobile |
|---|---|---|
| Comparable transactions | Sticky header; location first; numeric columns right-aligned; expandable evidence row | Pin location/price if selective scroll is retained; otherwise stacked transaction row + detail drawer |
| Hazard evidence | Ordered severity/confirmation table; availability separate from match | Stacked rows with status, finding, source; map selection opens detail drawer |
| Market evidence | Compact period/price/count table; trend adjacent, not duplicated | Selective horizontal scroll for time series; summary remains outside scroll |
| Property comparison | Cases as columns only up to 3; attributes as rows | One case at a time with sticky case selector or attribute cards; no 980 px nested table by default |
| Source/provenance | Source, status, vintage, coverage, limitation | Stacked evidence rows; details disclosure for identifiers |
| Financial breakdown | Line item, monthly, annual, share; totals pinned visually | Stacked label/value rows; no chart required for very short breakdowns |

Use expandable detail rows instead of cards inside tables. One scroll container per table, never nested inside another horizontal scroller. Key-column pinning is appropriate only for comparison/transaction tables; drawers are appropriate when row detail exceeds four fields.

## 14. Chart system

Each chart states one question in its heading and includes measure, period, unit, missing-data behavior, and materially relevant source/vintage. Use direct labels where possible; legends are limited to three series before another form is chosen.

- **Price distribution:** dot/box/range plot showing P25, median, P75, and subject estimate; state `萬/坪` explicitly.
- **Market trend:** line chart for continuous comparable periods; gaps remain gaps, never zero. Pair with current/period change values.
- **Loan sensitivity:** line or compact table of payment versus rate; base case directly marked. Avoid a chart when fewer than three scenarios.
- **Holding-cost composition:** sorted bar or financial table; donut/pie only when exact comparison is not required and there are at most five stable categories.
- **Demographic trend:** line for time, bar for category/cohort. Show geography and vintage.
- **Comparison:** aligned dot plot or table for common units; never mix incompatible units on one axis.

Charts have no independent decorative card shell. Empty charts state whether input is required, data is unavailable, or the chart is unsupported. Provide an accessible summary/table for every nontrivial chart.

## 15. Map system

- Location & Commute: map is the primary analytical surface, minimum 520 px desktop height and 360 px mobile height; use full workspace width or a 65/35 split.
- Risk & Environment: 55/45 or 60/40 map/evidence split; selecting a layer/feature synchronizes the evidence row.
- Overlay controls group base map, evidence layers, and filters separately. Controls are 36–40 px desktop, 44 px mobile, with labels/tooltips and keyboard focus.
- Selected feature detail appears in a side panel on desktop and bottom sheet/drawer on mobile. Do not rely on tiny map popups for full evidence.
- Attribution remains visible in a quiet footer/control area. Source/vintage details may expand without covering primary controls.
- On mobile, map and evidence use one page scroll. The map may be temporarily sticky during interaction but cannot trap vertical scroll. Long lists never push the map permanently out of context; use a bounded preview plus “show all evidence”.
- Avoid decorative map backgrounds, double frames, nested scroll, and maps smaller than the task requires.

## 16. Form system

Labels sit above controls. Required fields use `(必填)` or a documented required marker explained once; optional fields use `(選填)` only where ambiguity exists. Helper text sits below the label or control and stays under two concise lines; longer instruction moves to an intro/disclosure.

Inputs are 40 px high desktop and 44 px mobile. Unit suffixes/prefixes are visually inside a joined field (`NT$`, `萬`, `%`, `坪`, `年`) and are announced accessibly. Related financial inputs use fieldsets with plain group headings, not card shells. Errors appear below the field, name the problem, and preserve entered values. Submit failure appears at panel level and focuses or links to the first problem.

Dirty state is communicated only when leaving/resetting would lose material edits. Disabled controls remain legible and explain why when the reason is not obvious. Buttons do not grow vertically to fill grids. Advanced coordinates/layers live in disclosure.

## 17. Button hierarchy

- **Primary:** filled action color, one dominant action per section. Default 40 px; compact 36 px in dense toolbars.
- **Secondary:** neutral surface with strong border; for alternative action of comparable scope.
- **Tertiary/text:** no container until hover/focus; for navigation, reveal, or low-risk utility.
- **Destructive:** red text/border; filled red only in final destructive confirmation.
- **Icon-only:** 36 px desktop/44 px mobile target, required accessible name and tooltip when unfamiliar.
- **Disabled:** neutral and noninteractive; do not use disabled styling to represent status.

No multiple competing filled cyan/blue actions. Full-width is a responsive layout behavior, not a hierarchy. Buttons never serve as status labels.

## 18. Badge and pill rules

Allowed: compact status, selected filter, category needed for disambiguation, bounded metadata such as `官方資料`. Every badge must retain meaning when read as text.

Remove pills from hero claims, headings, every source, every metric, flow nodes, and ordinary actions. Convert active filter pills to removable chips only if they actually remove a filter; otherwise present a sentence/definition list. Convert source pills in valuation/market tables to a plain source column. Replace module-colored pills with navigation state.

## 19. Empty, loading, and error states

### Empty states

| State | Required message |
|---|---|
| Not started | What the analysis will do + primary start action |
| Input required | Exact missing input + link/focus action |
| No data / no coverage | Query completed; area/time/source has no coverage; suggest valid alternative |
| Temporarily unavailable | Provider/system unavailable + retained context + retry |
| Unsupported | Capability is not supported and what can be done instead |
| Error | Specific recoverable failure in user language + retry/help |
| No match | Query completed and no records matched filters; retain filters and suggest adjustments |

Do not reuse one dashed empty card for all states. Keep empty states compact unless the page truly contains no other work.

### Loading

Retain property context and unrelated completed results. Show which analysis is loading locally. Use an inline spinner for actions expected under 2 seconds; show a skeleton only after 300 ms for content with stable geometry. Do not show fake percentages. After the provider-specific timeout, change to a timeout state with local retry; do not block the full page.

### Errors

- Field error: adjacent message and `aria-describedby`.
- Panel error: compact alert with retry and preserved input.
- Source unavailable: evidence row/status, not application error.
- Provider timeout: identifies affected analysis, not raw provider/API details.
- Major application error: stable shell, plain-language recovery, reference ID for support.

Normal users never see stack traces, provider codes, API paths, or raw reason codes. Debug/support information is disclosed separately and only where authorized.

## 20. Alerts, warnings, and disclosure

- **Inline limitation:** one sentence next to the affected value/source; neutral or amber text with icon.
- **Material warning:** bounded amber alert placed once before the affected conclusion.
- **Confirmation required:** amber action block with the exact fact to confirm and a primary confirmation action.
- **Blocking error:** red alert with recovery; no downstream positive conclusion.
- **System notification:** transient toast or persistent top-level notice depending on duration; never repeated in each panel.

Avoid repeated amber boxes. Methodology, source details, full limitation text, advanced filters, and debug/support data belong in disclosure. Do not hide major findings, risk matches, price units, critical missing inputs, or the fact that coverage is absent.

## 21. Icons and motion

Adopt one 1.5–2 px stroke SVG icon family (for example Lucide) at 16 px dense, 20 px standard, and 24 px empty-state size. Icons support recognition; they do not decorate every header. Status icons follow the semantics table. Emoji are not used on professional analytical surfaces.

Motion tokens: 120 ms feedback, 180 ms disclosure/tab, 240 ms panel/drawer. Use standard ease-out for entry and ease-in for exit. Animate opacity/transform only. Allowed: tab/section transition, loading indicator, expand/collapse, and status transition. Remove workspace hero loops, glow pulses, parallax, floating mascots, and auto-rotating sequences. Under `prefers-reduced-motion: reduce`, transitions become effectively immediate and all loops stop.

## 22. Navigation

Workspace navigation is a stable list/tab system, not feature cards. Selected state uses action-colored text/indicator plus `aria-current`; hover uses secondary surface; focus uses the global focus ring. The sidebar, if retained, may stay dark but uses the same type and state tokens. Group labels are sentence case and visually subordinate.

At tablet/mobile, use a horizontal step/tab strip only when it can expose the active item without nested page scroll; otherwise use a drawer/menu with the current module named in the header. The property switcher is a dedicated control showing property name/address and status text, not a generic action button. Preserve access to the primary action when navigation collapses.

## 23. Responsive behavior

### Desktop — 1280–1440+ px

- 1440 px general workspace; up to 1680 px for GIS.
- Property header remains compact and sticky only if it does not exceed 88 px.
- Use 60/40 or 65/35 map/evidence layouts; finance uses 320–360 px inputs plus fluid results.
- Comparison supports up to three cases; report uses a 960 px reading width.

### Tablet — 768–1024 px

- Collapse persistent sidebar; retain current page/property in top bar.
- Maps stack above evidence unless a landscape split remains at least 480/320 px.
- Tables use the use-case strategy, not universal scroll.
- Finance forms use two columns where labels/units fit; charts remain full width.

### Mobile — 390 px reference

- 16 px page gutter; 44 px interactive targets.
- Property header becomes two rows: identity/context then compact actions.
- Workspace nav becomes current-step control/drawer; no giant sticky header.
- Map is 360 px minimum and full width inside gutters; selected details open in a bottom drawer.
- Charts simplify labels and retain units; accessible summary remains visible.
- Finance forms are one column; suffix units remain joined to inputs.
- Comparison uses a case selector plus one case/attribute view, not nested horizontal scroll.
- Reports preserve reading order: conclusion, findings, evidence, next actions, details.
- Primary action stays reachable but is not permanently overlaid on content.

## 24. Accessibility minimums

- WCAG 2.2 AA contrast: 4.5:1 normal text, 3:1 large text and UI boundaries/focus.
- Visible keyboard focus on every interactive element; focus is not clipped by overflow.
- Complete keyboard operation for navigation, disclosures, tables with interactive rows, maps controls, dialogs, and drawers.
- Status is never color-only. Icons include accessible text or are hidden when redundant.
- Icon-only controls have `aria-label`; unfamiliar icons have a tooltip.
- Tables use captions or accessible names, `<th scope>`, and announced sort state.
- Form errors use `aria-invalid`, `aria-describedby`, and an error summary when multiple fields fail.
- Dialogs/drawers trap focus, provide labelled title, close with Escape, and restore focus.
- Loading announcements use polite live regions and do not repeatedly announce unchanged state.
- `prefers-reduced-motion` is honored; zoom/reflow at 200% must not require two-dimensional page scrolling except an intentionally scrollable data table/map.

## 25. Visual rhythm by content

Default rhythm:

```text
Page heading
→ compact summary
→ main analysis
→ table / map / chart
→ ordered evidence
→ next action
→ details
```

- **Market:** summary strip → comparable transactions table → price distribution/trend → source/method details.
- **Location:** property/location context → dominant map → compact relevant evidence list → commute/amenity details.
- **Risk:** explicit coverage/unknown state → map → ordered evidence table → material matches → recommended checks → source details.
- **Finance:** assumptions/form → payment/holding summary → breakdown/sensitivity → next action → calculation details.
- **Overview/Decision:** findings → unresolved unknowns → recommended next actions → supporting evidence → report details.

Monotony is solved by alternating content forms and density, not by adding module colors.

## 26. Structural before/after examples

### Market

```text
Current: SectionCard → status banner → MetricTile grid → evidence cards → chart cards → disclosure table
Target:  Market heading + scope
         Median price | transaction count | period | coverage
         Comparable transactions table
         Price distribution and trend
         Source, vintage · Methodology
```

### Risk

```text
Current: Warning card → completeness card → follow-up card → map card → hazard cards → source card → warning
Target:  Risk & environment heading · coverage status
         Map | ordered evidence table
         Material matches and unknowns
         Recommended checks
         Methodology and sources
```

### Location

```text
Current: SectionCard → flow badges → form → empty card → metric cards → POI disclosure → Terrain/Commute cards
Target:  Location heading + confirmed address
         Map-dominant split | relevant evidence list
         Commute and amenities summary
         Next location action · Details
```

### Finance

```text
Current: Loan card + empty card → result card → four metric cards → three chart cards → warning card
Target:  Financing heading
         Compact assumptions form | payment summary
         Sensitivity and cost breakdown
         Transfer to holding-cost action
         Calculation assumptions and limitations
```

### Decision

```text
Current: Decision card → recommendation pill → reason cards → ViewingDecision card → risk/tax banners → checklist card
Target:  Decision status in text
         Findings | unresolved items | confidence
         Evidence checklist table
         One recommended next action
         Report methodology and sources
```

## 27. Pattern consolidation inventory

| # | Current pattern | Problem | Target pattern | Likely files/components |
|---:|---|---|---|---|
| 1 | `Card` and `SectionCard` | Overlapping generic shells | `Section`, `Panel` with explicit semantics | `ui.tsx`, `product-ui.tsx` |
| 2 | `Metric`, `MetricTile`, `PreviewMetric`, `MiniMetric` | Four+ metric shells | `SummaryStrip`, `MetricItem` | shared UI, `immersive-viewing-workspace.tsx` |
| 3 | `Badge`, `StatusBadge`, local pills | Color semantics drift | `StatusLabel`, `FilterChip`, `MetadataLabel` | `ui.tsx`, `product-ui.tsx`, page-local badges |
| 4 | `Notice`, `ErrorState`, inline alert classes | Fragmented warning hierarchy | `InlineMessage`, `Alert`, `PanelError` | shared UI, `app/page.tsx` |
| 5 | `EmptyState`, dashed local empties, chart empties | Cause/action not differentiated | Typed `EmptyState` variants | shared UI, chart states, calculators |
| 6 | `LoadingState`, `AnalysisProgress`, inline loading text | Orientation and geometry vary | `InlineLoading`, `PanelLoading`, stable skeleton | shared UI, analysis components |
| 7 | Repeated input class strings | Control height/focus inconsistency | `Field`, `Input`, `Select`, `UnitInput` | calculators, Market, `app/page.tsx` |
| 8 | Local filled cyan buttons | Multiple primaries | shared `Button` variants/sizes | all modules |
| 9 | `DetailDisclosure` plus raw styled `<details>` | 99 inconsistent disclosures | `Disclosure` variants: standard/compact | shared UI, Market, Terrain, workspace |
| 10 | Repeated overflow table wrappers | Universal side-scroll | `DataTable` + responsive strategy | Market, valuation, risk, comparison, finance |
| 11 | Valuation metric/card stack | Nested analytical shells | valuation summary + unboxed sections | `valuation-visual-panel.tsx`, `app/page.tsx` |
| 12 | Market distributions as mini cards | Low-value chart shells | analytical distribution section/table | `market-insight-evidence-panel.tsx` |
| 13 | Terrain `HazardCard`/`SourceLayerCard`/`ListCard` | Evidence card soup | ordered `EvidenceTable` | `terrain-risk-analysis.tsx` |
| 14 | Google/Satellite/Cadastral separate panel languages | Map evidence inconsistency | `MapFrame`, `MapState`, `EvidenceDrawer` | map and terrain components |
| 15 | Loan/Holding four-card KPI grids | Repeated metric dominance | shared financial summary strip | visual panels |
| 16 | Chart components with own borders/radii | Double-shell charts | unboxed `ChartFrame` metadata contract | data-visualization components |
| 17 | `DecisionReport` + `ViewingDecisionPanel` nested | Duplicate conclusions | one decision summary with evidence sections | decision components |
| 18 | `CaseComparisonPanel` ranking cards + two tables | Multiple comparison models | one comparison workbench/table + detail | comparison components |
| 19 | `PrintComparisonReport` block cards | Report looks like dashboard | editorial report sections/dividers | print/report components |
| 20 | Dashboard module tiles | Module colors and gradients | plain navigation/list with descriptions | `product-ui.tsx`, `app/page.tsx` |
| 21 | Hero pills/flow nodes/animated backdrop | Promotional visual noise | compact orientation header | hero components, `globals.css` |
| 22 | Global amber limitation strip plus local warnings | Warning fatigue | one product boundary disclosure + local material warnings | `app-shell.tsx`, modules |
| 23 | Sidebar feature buttons and workspace tabs | Inconsistent navigation model | shared navigation item/selected state | `sidebar.tsx`, guided journey, workspace shell |
| 24 | Three CSS-module token sets | Parallel design systems | shared global tokens consumed by CSS modules | workspace/property identity CSS modules |
| 25 | Property guide mascot | Decorative emphasis in professional workspace | optional help callout without character styling | `property-guide-mascot.tsx` |
| 26 | Simulated decorative `MiniMap`/`MapSummary` | Map-like decoration competes with real maps | real context summary or neutral placeholder | `product-ui.tsx`, immersive workspace |
| 27 | Full-width primary buttons in calculators | Inflated action weight | content-width desktop, full-width mobile only | loan, holding, valuation |
| 28 | Source-specific colored pills in tables | Source looks like status | plain source column + verified status field | valuation/market tables |

## 28. Token recommendations

Future implementation should expose semantic tokens, not Tailwind palette names, in CSS variables and Tailwind aliases.

```text
Typography: font-sans; text-page/section/subsection/body/dense/label/meta/evidence/table-head/table-body/kpi/number/message/helper
Spacing: space-0/1/2/3/4/5/6/8/10/12/16 = 0/4/8/12/16/20/24/32/40/48/64 px
Radius: radius-control 6; radius-panel 8; radius-dialog 12; radius-pill 999 px
Surfaces: canvas; surface-primary; surface-secondary; surface-raised; surface-disabled
Text: text-primary; text-secondary; text-muted; text-disabled; text-inverse
Borders: border-subtle; border-strong; border-selected; border-error
Semantic: action/action-hover/focus; info; warning; error; success and matching subtle surfaces
Z-index: base 0; sticky 10; map-controls 20; header 30; drawer 40; popover 50; modal 60; toast 70
Motion: duration-feedback 120; duration-standard 180; duration-panel 240 ms
Widths: content 1440; reading 960; form 720; gis 1680 px
Control heights: compact 36; standard 40; touch 44 px
```

No component may consume `emerald`, `amber`, `rose`, `violet`, or arbitrary hex values directly after migration except inside the token definition layer or approved chart series palette. Chart series colors require a separate accessible categorical palette and may not be reused to imply status.

## 29. Acceptance checklist

- Page contains one page title and one dominant action per section.
- No nested generic card shells.
- Status wording and color match Section 10; green does not imply safety or recommendation.
- Every major number has an unambiguous unit and uses tabular figures where compared.
- Evidence/source metadata is present but quieter than the conclusion.
- Table/mobile strategy is explicitly selected per use case.
- Map remains a core surface at the specified size and does not create double scroll.
- Empty/loading/error states identify cause and next action.
- Focus, contrast, keyboard, table, form-error, dialog, and reduced-motion requirements pass.
- Screens at 1440, 1024, 768, 430, and 390 px preserve primary actions and avoid unintended two-dimensional page scrolling.

## 30. Parallel-branch constraints

At audit time the named branches are separate linked worktrees and several start behind this document's `origin/main` baseline. Treat their eventual merge output—not their current branch pointer—as authoritative.

- **Valuation / Holding Cost reliability:** likely conflicts in calculators, valuation/holding visual models, formatting, and result-state behavior. Token/primitives may proceed; detailed financial layout migration waits for merge and recertification.
- **Commute production closure:** likely conflicts in commute cards, Location stage composition, provider timeout/state copy, and map evidence. Do not finalize Location/Commute responsive structure before merge.
- **Journey Property Identity:** likely conflicts in context headers, guided journey stages, property identity workflow, and CSS modules. Do not replace identity/workspace shells until its final DOM and state contract lands.
- **Geological Sensitivity:** likely conflicts in Terrain risk evidence, layer status, map legends, unknown/limited semantics, and source tables. Risk layout waits for the final evidence model.
- **Commercial Workspace Architecture:** likely changes shell ownership, navigation, property header, route/layout boundaries, and panel placement. Workspace-shell migration must follow its approved spec/merge.

Foundation tokens, semantic status definitions, numerical formatting rules, and isolated primitives can be prepared in parallel. Page-level consolidation must re-audit the merged DOM before implementation.
