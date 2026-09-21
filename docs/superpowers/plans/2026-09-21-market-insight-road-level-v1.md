# Market Insight Road Level V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add truthful normalized road-level official-PLVR analysis to the existing Market Insight query, with explicit district fallback and no fabricated precision.

**Architecture:** Keep `POST /market-insights/query` and the existing Market Insight repository. A new pure analysis module owns road normalization, 36-month validity filtering, exact scope selection, and statistics; the existing Postgres repository supplies only bounded, address-free transaction fields and import metadata. The frontend adds an optional road input, scope/fallback evidence, and an explicit Property Finder handoff without auto-running analysis.

**Tech Stack:** Python 3, FastAPI/Pydantic, psycopg/PostgreSQL, pytest, TypeScript, React 19, Next.js 16, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-21-market-insight-road-level-v1-design.md`

## Global Constraints

- Analysis levels are exactly `ROAD`, `DISTRICT`, and `NOT_AVAILABLE`.
- The ROAD and fallback DISTRICT thresholds are exactly 10 valid official rows after the rolling 36-month and quality filters.
- Do not add `DISTRICT_BUILDING_TYPE`, city/neighbor fallback, fuzzy matching, period widening, a migration, provider, endpoint, dependency, scraper, active-listing feature, or Community Finder behavior.
- Do not expose raw addresses, coordinates, transaction IDs, raw notes, connection details, or provider exceptions.
- District-only callers retain the existing request and response behavior.
- Property Finder only pre-fills city/district/road; the user explicitly submits Market Insight.
- Do not push, merge, or rebase.
- Produce one implementation commit only after verification and independent review.

## Review Focus

- A supplied blank/coordinate/address-like road must fail closed instead of silently becoming a district-only request; pin this in Task 1 route/service tests.
- Unicode whitespace and `臺/台` variants must normalize deterministically without merging different roads or sections; pin this in Task 1 normalization tests.
- A database result larger than an incidental client-side limit must not truncate sample counts; pin the aggregate-row query shape in Task 3 repository tests.
- A fallback response must contain district-only primary metrics while retaining road count only as metadata; pin this in Task 2 contamination tests.
- Property Finder handoff must reset stale Market Insight results and must not trigger a network request until submit; pin this in Task 6 E2E.

---

### Task 1: Pure Road Normalization and Valid-Evidence Filtering

**Files:**
- Create: `services/market_road_analysis.py`
- Create: `tests/test_market_road_analysis.py`
- Modify: `services/valuation_service.py` to delegate its existing `normalize_road` function to the shared normalizer without changing valuation behavior.

**Interfaces:**
- Consumes: transaction-shaped dictionaries with `source`, `transaction_period`, `city`, `district`, `road`, `unit_price_per_ping`, `total_price`, and `area_ping`.
- Produces: `normalize_market_road(value: str) -> str`, `is_valid_market_road(value: str) -> bool`, `effective_window(as_of=None) -> tuple[str, str]`, and `valid_market_rows(rows, county, district, as_of=None) -> tuple[list[dict[str, Any]], dict[str, int]]`.

- [ ] **Step 1: Write failing normalization tests**

```python
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" 和平東路2段 ", "和平東路二段"),
        ("臺 灣 大 道 3 段", "台灣大道三段"),
        ("文化路二段", "文化路二段"),
    ],
)
def test_normalize_market_road_preserves_exact_section_identity(raw, expected):
    assert normalize_market_road(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "25.03,121.54", "和平東路二段100號", "和平東路二段/文化路"])
def test_invalid_market_road_is_rejected(raw):
    assert is_valid_market_road(raw) is False


def test_different_roads_and_sections_do_not_collide():
    values = {normalize_market_road(value) for value in ["文化路一段", "文化路二段", "文華路二段"]}
    assert len(values) == 3
```

- [ ] **Step 2: Run the normalization tests and verify RED**

Run: `python -m pytest -q tests/test_market_road_analysis.py -k "normalize or invalid or collide"`

Expected: collection/import failure because `services.market_road_analysis` does not exist.

- [ ] **Step 3: Implement the bounded shared normalizer**

```python
ROAD_PATTERN = re.compile(r"^[\u4e00-\u9fffA-Za-z0-9]+(?:大道|路|街)(?:[一二三四五六七八九十百]+段)?$")
SECTION_NUMBERS = {"10": "十", "1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六", "7": "七", "8": "八", "9": "九"}

def normalize_market_road(value: str) -> str:
    normalized = re.sub(r"\s+", "", str(value or "").strip()).replace("臺", "台")
    for number, chinese in SECTION_NUMBERS.items():
        normalized = normalized.replace(f"{number}段", f"{chinese}段")
    return normalized

def is_valid_market_road(value: str) -> bool:
    normalized = normalize_market_road(value)
    return 0 < len(normalized) <= 80 and ROAD_PATTERN.fullmatch(normalized) is not None
```

- [ ] **Step 4: Write failing valid-sample tests**

Use a frozen `as_of=date(2026, 9, 21)` and assert that only official rows from `2023-10` through `2026-09` with positive bounded prices/areas and the requested canonical region survive. Include sample rows, malformed months, `2026-10`, `2023-09`, zero/negative metrics, unit price above 500, and a mismatched district.

```python
def test_valid_market_rows_filters_before_threshold_count():
    valid, quality = valid_market_rows(rows, "台北市", "大安區", as_of=date(2026, 9, 21))
    assert [row["transaction_period"] for row in valid] == ["2023-10", "2026-09"]
    assert quality["excluded_future_period_count"] == 1
    assert quality["excluded_out_of_window_count"] == 1
```

- [ ] **Step 5: Run the valid-sample test and verify RED**

Run: `python -m pytest -q tests/test_market_road_analysis.py::test_valid_market_rows_filters_before_threshold_count`

Expected: FAIL because `valid_market_rows` is missing.

- [ ] **Step 6: Implement the 36-month filter and valuation compatibility delegation**

The implementation must calculate an inclusive 36-month window with `current_transaction_period(as_of)` and reject rows before counting. Change `services.valuation_service.normalize_road` to return `normalize_market_road(value)` so valuation trend keeps its established behavior while sharing canonical rules.

- [ ] **Step 7: Run Task 1 tests**

Run: `python -m pytest -q tests/test_market_road_analysis.py tests/test_valuation_trend_service.py tests/test_valuation_service.py`

Expected: PASS.

### Task 2: Pure Scope Selection and Statistics

**Files:**
- Modify: `services/market_road_analysis.py`
- Modify: `tests/test_market_road_analysis.py`

**Interfaces:**
- Consumes: `analyze_market_road(rows, county, district, requested_road, latest_import_status=None, latest_imported_at=None, as_of=None) -> dict[str, Any]`.
- Produces: the road-aware fields listed in the spec, plus backward-compatible Market Insight aliases and address-free `history`, `monthly_series`, and `yearly_series`.

- [ ] **Step 1: Write threshold and fallback RED tests**

Create row builders that make distinct road and district prices. Add tests for road counts 11, 10, 9, and 0; district counts 10 and 9; no city fallback; and no time-window widening.

```python
def test_exactly_ten_valid_road_rows_select_road():
    result = analyze_market_road(road_rows(10) + other_district_rows(4), "台北市", "大安區", "和平東路2段", as_of=AS_OF)
    assert result["effective_analysis_level"] == "ROAD"
    assert result["road_sample_count"] == 10
    assert result["effective_sample_count"] == 10
    assert result["fallback_applied"] is False


def test_nine_road_rows_fall_back_to_district_without_mixing_metrics():
    result = analyze_market_road(road_rows(9, price=70) + other_district_rows(11, price=30), "台北市", "大安區", "和平東路二段", as_of=AS_OF)
    assert result["effective_analysis_level"] == "DISTRICT"
    assert result["road_sample_count"] == 9
    assert result["district_sample_count"] == 20
    assert result["median_unit_price_per_ping"] == 30
    assert result["fallback_reason"] == "road_sample_below_threshold"
```

- [ ] **Step 2: Run threshold tests and verify RED**

Run: `python -m pytest -q tests/test_market_road_analysis.py -k "select or fallback or available or widening"`

Expected: FAIL because `analyze_market_road` is missing.

- [ ] **Step 3: Implement exact scope selection**

```python
ROAD_MINIMUM_SAMPLE = 10

road_rows = [row for row in district_rows if normalize_market_road(row["road"]) == normalized_road]
if len(road_rows) >= ROAD_MINIMUM_SAMPLE:
    level, selected, fallback_reason = "ROAD", road_rows, None
elif len(district_rows) >= ROAD_MINIMUM_SAMPLE:
    level, selected, fallback_reason = "DISTRICT", district_rows, "road_sample_below_threshold"
else:
    level, selected, fallback_reason = "NOT_AVAILABLE", [], "district_sample_below_threshold"
```

Return requested and effective scope fields on every path. `NOT_AVAILABLE` returns null metrics and empty series.

- [ ] **Step 4: Write statistics and contamination RED tests**

Assert median, linear-interpolated P25/P75, median total price, median area, period min/max, latest period, monthly counts, yearly counts/medians, ROAD-only metrics, and DISTRICT-only metrics. Assert raw `address_text` is absent recursively from the result.

```python
def test_road_metrics_never_include_other_district_roads():
    result = analyze_market_road(road_rows(10, price=80) + other_district_rows(40, price=20), "台北市", "大安區", "和平東路二段", as_of=AS_OF)
    assert result["median_unit_price_per_ping"] == 80
    assert result["transaction_count"] == 10
    assert "address_text" not in json.dumps(result)
```

- [ ] **Step 5: Write conditional trend-metric RED tests**

Assert YoY is `None` unless the latest two yearly buckets each contain at least 10 selected rows. Assert volatility is `None` with fewer than three monthly medians and finite when three or more exist.

- [ ] **Step 6: Implement aggregate statistics and freshness evaluation**

Use `statistics.median`, the existing percentile interpolation formula, grouped monthly/yearly series, and the existing annualized monthly-median volatility formula. Call `evaluate_plvr_freshness` with the selected effective scope's newest period and supplied import metadata. Do not synthesize unsupported values.

- [ ] **Step 7: Run Task 2 tests**

Run: `python -m pytest -q tests/test_market_road_analysis.py`

Expected: PASS.

### Task 3: Existing Repository and Service Integration

**Files:**
- Modify: `services/plvr_market_aggregate_service.py`
- Modify: `services/market_insight_service.py`
- Modify: `tests/test_market_direct_query_postgres.py`
- Modify: `tests/test_market_read_model_workflow.py`
- Modify: `tests/test_market_query_runtime_diagnostics.py`

**Interfaces:**
- Add repository method `road_evidence(county: str, district: str) -> dict[str, Any]` returning `rows`, `latest_import_status`, and `latest_imported_at`.
- Extend `get_market_summary(..., road: str | None = None, ...)` and its wrapper. A missing road follows the old path unchanged; a supplied road calls the pure analyzer.

- [ ] **Step 1: Write repository SQL RED tests**

Assert the query is read-only, filters by canonical city/district and official source, returns only `transaction_period`, `city`, `district`, `road`, `unit_price_per_ping`, `total_price`, `area_ping`, `source`, and `imported_at`, and never selects `address_text`, latitude/longitude, IDs, or raw notes. Assert there is no row limit that can truncate threshold counts.

- [ ] **Step 2: Run repository tests and verify RED**

Run: `python -m pytest -q tests/test_market_direct_query_postgres.py -k road`

Expected: FAIL because `road_evidence` is missing.

- [ ] **Step 3: Implement the read-only repository method**

Use the existing `_market_query_cursor` and canonical region storage rules. Query the district pool with the existing indexed city/district predicates and fetch the latest completed `valuation_import_runs` metadata in the same read-only connection. Do not apply a truncating `LIMIT`.

- [ ] **Step 4: Write service branching RED tests**

Use a fake repository to assert:

```python
legacy = get_market_summary("台北市", "大安區", repository=repo)
road = get_market_summary("台北市", "大安區", road="和平東路2段", repository=repo, as_of=AS_OF)
assert repo.summary_called is True
assert road["normalized_road"] == "和平東路二段"
assert road["effective_analysis_level"] in {"ROAD", "DISTRICT", "NOT_AVAILABLE"}
```

Also assert invalid roads fail closed and repository exceptions produce bounded unavailable results with support references.

- [ ] **Step 5: Implement the road branch without altering the legacy branch**

Normalize and validate road input, preserve the coverage gate, call `repo.road_evidence`, pass evidence to `analyze_market_road`, and attach existing diagnostics. Leave the no-road summary/history code path byte-for-byte behaviorally compatible.

- [ ] **Step 6: Run backend service/repository regressions**

Run: `python -m pytest -q tests/test_market_road_analysis.py tests/test_market_direct_query_postgres.py tests/test_market_read_model_workflow.py tests/test_market_query_runtime_diagnostics.py tests/test_market_insight_service.py`

Expected: PASS.

### Task 4: API Contract and Safe Allowlist

**Files:**
- Modify: `backend/api/routes_market.py`
- Modify: `tests/test_market_insight_api_bridge.py`
- Modify: `tests/test_official_market_api.py`

**Interfaces:**
- `MarketInsightQuery.road: str | None` accepts only a nonempty, bounded, structurally valid road when present.
- The route forwards `road` to `get_market_summary` and allowlists all approved public road-analysis fields.

- [ ] **Step 1: Write API RED tests**

Add tests for normalized road forwarding, exact ROAD response, DISTRICT fallback, NOT_AVAILABLE, blank/coordinate/address-like rejection, raw-address stripping, bounded fallback reason, and the unchanged district-only request.

```python
def test_market_query_forwards_road_and_exposes_separate_scopes(monkeypatch):
    response = client.post("/market-insights/query", json={"county": "台北市", "district": "大安區", "road": "和平東路2段"})
    payload = response.json()
    assert payload["requested_road"] == "和平東路2段"
    assert payload["normalized_road"] == "和平東路二段"
    assert payload["effective_analysis_level"] == "ROAD"
    assert "address_text" not in response.text
```

- [ ] **Step 2: Run API tests and verify RED**

Run: `python -m pytest -q tests/test_market_insight_api_bridge.py -k road`

Expected: FAIL because the request forbids `road` and the response strips new fields.

- [ ] **Step 3: Extend request validation and response allowlisting**

Add only the approved road field to the request. Extend `MARKET_QUERY_SAFE_FIELDS` with requested/effective scope, counts, periods, road metrics, conditional trend metrics, series, and freshness reason fields. Keep `extra="forbid"` and existing safe-result validation.

- [ ] **Step 4: Make NOT_AVAILABLE clearing explicit**

Ensure `_safe_market_no_data` preserves safe explanatory scope/count/fallback metadata while setting all primary metrics to `None` and all chart series to empty arrays.

- [ ] **Step 5: Run API regressions**

Run: `python -m pytest -q tests/test_market_insight_api_bridge.py tests/test_official_market_api.py tests/test_market_insight_metric_semantics.py`

Expected: PASS.

### Task 5: Frontend Contract, Road Input, and Truthful Result Presentation

**Files:**
- Modify: `frontend_next/lib/api.ts`
- Modify: `frontend_next/app/page.tsx`
- Modify: `frontend_next/components/data-visualization/market-insight-evidence-panel.tsx`
- Modify: `frontend_next/lib/market-insight-visualization.ts`
- Modify: `frontend_next/lib/market-insight-copy.ts`
- Modify: `frontend_next/lib/market-result-state.ts`
- Modify: `tests/test_market_insight_visual_storytelling.py`
- Modify: `tests/test_market_insight_metric_semantics.py`
- Modify: `tests/test_location_market_accessibility.py`

**Interfaces:**
- Extend `MarketResult` with the safe road-analysis fields and `MarketAnalysisLevel`.
- Extend `api.marketInsight(county, district, road?, period?, signal?)` and send road only when present.
- Extend `MarketInsight` props with `initialRoad?: string`.

- [ ] **Step 1: Write frontend static RED tests**

Assert the source contains a labeled, bounded road input; sends `road`; clears road/results on parent geography changes; renders requested location, effective level/scope, counts, fallback reason, period, source, and freshness; and contains no active-listing claim.

- [ ] **Step 2: Run frontend static tests and verify RED**

Run: `python -m pytest -q tests/test_market_insight_visual_storytelling.py tests/test_market_insight_metric_semantics.py tests/test_location_market_accessibility.py`

Expected: FAIL on the missing road contract and evidence fields.

- [ ] **Step 3: Extend the TypeScript API contract**

Add typed fields including:

```ts
export type MarketAnalysisLevel = "ROAD" | "DISTRICT" | "NOT_AVAILABLE";

requested_scope?: "ROAD" | "DISTRICT";
requested_city?: string;
requested_district?: string;
requested_road?: string | null;
normalized_road?: string | null;
effective_analysis_level?: MarketAnalysisLevel;
effective_scope_label?: string;
effective_sample_count?: number | null;
road_sample_count?: number | null;
district_sample_count?: number | null;
fallback_applied?: boolean;
fallback_reason?: string | null;
period_min?: string | null;
period_max?: string | null;
median_unit_price_per_ping?: number | null;
p25_unit_price_per_ping?: number | null;
p75_unit_price_per_ping?: number | null;
median_total_price?: number | null;
median_area_ping?: number | null;
volatility?: number | null;
monthly_series?: MarketMonthlyPoint[];
yearly_series?: MarketYearlyPoint[];
```

- [ ] **Step 4: Add the optional road input and request lifecycle**

Use a native labeled text input with `maxLength={80}`, `autoComplete="street-address"` disabled or omitted, and no coordinate/geocoder behavior. Pre-fill from `initialRoad`; clear it when county/district changes; clear stale results when it changes; require explicit form submission.

- [ ] **Step 5: Add scope-first evidence presentation**

Place a compact evidence block above primary metrics. ROAD shows the normalized road as actual scope. DISTRICT shows district as actual scope plus a fallback notice containing the road sample count and 10-record threshold. NOT_AVAILABLE remains metric-free. Add localized copy for all four supported locales.

- [ ] **Step 6: Preserve charts and accessibility**

Map the effective-scope `history` only; do not build chart points from explanatory road counts. Keep existing chart roles, accessible table, focusable points, `aria-live` loading state, and overflow containers.

- [ ] **Step 7: Run frontend static tests and TypeScript check**

Run: `python -m pytest -q tests/test_market_insight_visual_storytelling.py tests/test_market_insight_metric_semantics.py tests/test_location_market_accessibility.py`

Run: `npm.cmd --prefix frontend_next run typecheck`

Expected: PASS.

### Task 6: Explicit Property Finder Handoff

**Files:**
- Modify: `frontend_next/components/property-finder.tsx`
- Modify: `frontend_next/app/page.tsx`
- Modify: `tests/test_frontend_property_finder.py`
- Modify: `tests/test_property_search_visual_storytelling.py`
- Modify: `frontend_next/e2e/market-insight-analysis.spec.ts`

**Interfaces:**
- Add optional `onUseForMarketInsight?: (selection: PropertyFinderSelection) => void`.
- The journey callback copies only city/district/road context and navigates to Market Insight without submitting it.

- [ ] **Step 1: Write handoff RED tests**

Assert Property Finder renders an explicit historical-market action when the callback exists, passes city/district/road, does not use listing language, and does not mention 591 or active inventory.

- [ ] **Step 2: Run Property Finder tests and verify RED**

Run: `python -m pytest -q tests/test_frontend_property_finder.py tests/test_property_search_visual_storytelling.py`

Expected: FAIL because the handoff callback/action is absent.

- [ ] **Step 3: Implement the optional action and journey wiring**

Add the action without changing existing valuation, loan, holding-cost, or location actions. In the journey, apply the selection, navigate to the location/market stage, and pass `initialRoad={context.road}` to Market Insight. Do not call `api.marketInsight` from Property Finder or from a mount effect.

- [ ] **Step 4: Add E2E handoff and road-result cases**

Extend `market-insight-analysis.spec.ts` to assert:

- Property Finder selection pre-fills city/district/road.
- No Market Insight request occurs before submit.
- The submitted request contains the normalized input field.
- ROAD and DISTRICT fallback presentations show distinct requested/effective scopes.
- NOT_AVAILABLE renders no charts or fake metrics.
- Mobile width has no page-level overflow and controls remain keyboard accessible.

- [ ] **Step 5: Run focused Property Finder and Market Insight E2E**

Run: `npm.cmd --prefix frontend_next run build:e2e`

Run: `node frontend_next/e2e/run-e2e.cjs frontend_next/e2e/market-insight-analysis.spec.ts`

Expected: PASS.

### Task 7: Documentation and Full Regression

**Files:**
- Modify: `docs/market-insight-methodology.md`
- Modify: `docs/nationwide-market-read-model-v1.md`
- Modify: implementation/test files only if verification identifies a defect.

**Interfaces:**
- Documents the 10-row post-filter threshold, 36-month window, exact normalization, ROAD → DISTRICT → NOT_AVAILABLE selection, conditional YoY/volatility, and direct road read path.

- [ ] **Step 1: Update methodology/read-path documentation**

State explicitly that road analysis uses official PLVR rows, exact normalized road identity, no read-model road aggregate assumption, no period widening, and no listing implication.

- [ ] **Step 2: Run focused backend suites**

Run:

```powershell
python -m pytest -q tests/test_market_road_analysis.py tests/test_market_insight_api_bridge.py tests/test_market_direct_query_postgres.py tests/test_market_read_model_workflow.py tests/test_market_query_runtime_diagnostics.py tests/test_market_insight_service.py tests/test_market_insight_metric_semantics.py tests/test_valuation_trend_service.py tests/test_postgres_valuation_provider.py tests/test_property_search_service.py tests/test_property_search_api.py tests/test_frontend_property_finder.py
```

Expected: PASS.

- [ ] **Step 3: Run relevant Python regression**

Run: `python -m pytest -q`

Expected: PASS.

- [ ] **Step 4: Run frontend static/type/lint/build verification**

Run:

```powershell
npm.cmd --prefix frontend_next run typecheck
npm.cmd --prefix frontend_next run lint
npm.cmd --prefix frontend_next run build
```

Expected: all commands exit 0.

- [ ] **Step 5: Run Market Insight and Property Finder E2E**

Run: `npm.cmd --prefix frontend_next run build:e2e`

Run: `node frontend_next/e2e/run-e2e.cjs frontend_next/e2e/market-insight-analysis.spec.ts`

Run the existing Property Finder regression spec(s) selected by `rg -l "Property Finder|property-finder" frontend_next/e2e -g '*.spec.ts'` through the same E2E runner.

Expected: PASS.

- [ ] **Step 6: Run whitespace and working-tree checks**

Run: `git diff --check`

Run: `git status --short`

Expected: no whitespace errors; only planned implementation/plan changes are present.

### Task 8: Independent Review, Test-First Fixes, and Single Implementation Commit

**Files:**
- Review all changes since baseline `82394b7` and the design commit `18d3322`.
- Modify only files implicated by Critical or Important findings.

**Interfaces:**
- Produces a reviewed candidate with no Critical or Important findings and one implementation commit after the design commit.

- [ ] **Step 1: Request independent whole-branch review**

The reviewer must inspect fake road precision, district-as-road labeling, hidden fallback, mixed-scope metrics, unsupported YoY/volatility, normalization collision, raw-address leakage, future/out-of-window contamination, active-listing implication, duplicate data paths, backward compatibility, and chart regressions.

- [ ] **Step 2: Convert every Critical/Important finding into a failing test**

Run the new focused test and confirm RED before editing production code.

- [ ] **Step 3: Implement the minimal fix and rerun focused/full verification**

Repeat Tasks 7.2 through 7.6 after the final fix.

- [ ] **Step 4: Create the single implementation commit**

```powershell
git add -- docs/superpowers/plans/2026-09-21-market-insight-road-level-v1.md docs/market-insight-methodology.md docs/nationwide-market-read-model-v1.md services backend frontend_next tests
git commit -m "feat: add truthful Market Insight road analysis"
```

- [ ] **Step 5: Verify final branch state without pushing**

Run: `git status --short --branch`

Run: `git log -3 --oneline --decorate`

Expected: clean branch with the design commit followed by one implementation commit; no push, merge, or rebase.
