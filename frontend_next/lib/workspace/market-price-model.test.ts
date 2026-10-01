import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildMarketPriceModel } from "./market-price-model.ts";

const NOW = "2026-09-27T08:00:00.000Z";

function savedCase() {
  return {
    id: "market-case",
    title: "市府路案件",
    createdAt: NOW,
    updatedAt: NOW,
    version: 1,
    workflowMode: "buying_wizard",
    activeWizardStep: "report",
    progress: 80,
    inputSummary: { city: "臺北市", district: "信義區", road: "市府路1號", propertyPrice: 2480, areaPing: 30 },
    data: {
      inputs: { city: "臺北市", district: "信義區", road: "市府路1號", building_type: "住宅大樓", area_ping: 30, building_age_years: 5, floor: 8 },
      journeyContext: {
        version: 1,
        propertyContext: { city: "臺北市", district: "信義區", road: "市府路1號", addressSummary: "臺北市信義區市府路1號", sourceLabel: "Saved case", selectionStatus: "selected", askingPriceWan: 2480 },
        priceBasis: "asking",
        activePriceWan: 2480,
      },
      marketInsight: {
        city: "臺北市",
        county: "臺北市",
        district: "信義區",
        period: "2025-01–2026-07",
        average_unit_price: 53.1,
        avg_price_per_ping: 53.1,
        transaction_count: 18,
        transaction_volume: 18,
        record_count: 18,
        summary: "近期成交單價集中於每坪 50 至 55 萬元。",
        source_name: "內政部不動產實價登錄",
        source_updated_at: "2026-08-31",
        coverage_status: "covered",
        data_status: "available",
        caveat: "樣本僅供初步比較。",
        disclaimer: "成交資料不等同正式估價。",
        history: [
          { period: "2026-07", average_unit_price: 53.1, transaction_count: 8 },
          { period: "2026-06", average_unit_price: 51.8, transaction_count: 10 },
        ],
        sample_status: "sufficient",
        freshness_status: "fresh",
        period_min: "2025-01",
        period_max: "2026-07",
        median_unit_price_per_ping: 52.4,
        p25_unit_price_per_ping: 49.8,
        p75_unit_price_per_ping: 55.6,
        median_total_price: 1850,
        effective_scope_label: "臺北市信義區",
      },
    },
  };
}

test("saved Market evidence keeps asking price, observed median, units, and source separate", () => {
  const workspace = adaptSavedCaseToWorkspace(savedCase() as never);

  assert.equal(workspace.marketPrice.priceContext.askingPrice?.formatted, "2,480 萬元");
  assert.equal(workspace.marketPrice.priceContext.activePrice.label, "開價");
  assert.equal(workspace.marketPrice.priceContext.marketMedianTotal?.formatted, "1,850 萬元");
  assert.equal(workspace.marketPrice.priceContext.marketMedianUnit?.formatted, "52.4 萬元／坪");
  assert.equal(workspace.marketPrice.market.status, "limited");
  assert.equal(workspace.marketPrice.source.sourceName, "內政部不動產實價登錄");
  assert.equal(workspace.marketPrice.source.effectivePeriod, "2025/01–2026/07");
  assert.equal(workspace.marketPrice.source.updatedAt, "2026-08-31");
  assert.equal(workspace.identity.state, "unconfirmed");
  assert.match(workspace.marketPrice.primaryFinding, /物件身分尚未確認/);
  assert.doesNotMatch(workspace.marketPrice.primaryFinding, /高於|低於|接近/);
});

function storedValuation() {
  return {
    valuation_status: "available",
    valuation_reason_code: "ok",
    result_origin: "official",
    is_actionable: true,
    estimate_data_composition: "official",
    estimate_total_price: 1850,
    estimate_unit_price_per_ping: 52.4,
    price_range: { low: 1720, mid: 1850, high: 1980 },
    confidence_score: 82,
    confidence: "high",
    comparables: [],
    valuation_explanation: {
      sample_count: 18,
      average_similarity_score: 82,
    },
    data_status: { freshness_as_of: "2026-08-31" },
  };
}

test("stored official valuation summary remains separate from asking price and row-level comparables", () => {
  const model = buildMarketPriceModel({
    activePriceBasis: "asking",
    activePriceWan: 2480,
    askingPriceWan: 2480,
    market: savedCase().data.marketInsight as never,
    valuation: storedValuation() as never,
    stale: false,
  });

  assert.equal(model.priceContext.estimateRange?.formatted, "1,720–1,980 萬元");
  assert.equal(model.valuation.status, "limited");
  assert.equal(model.valuation.estimate?.formatted, "1,850 萬元");
  assert.equal(model.valuation.comparablesAvailable, false);
  assert.equal(model.overview.estimateRange, "1,720–1,980 萬元");
  assert.equal(model.overview.marketRange, "49.8–55.6 萬元／坪");
});

test("nullable or malformed valuation metrics fail closed without becoming zero", () => {
  const malformed = storedValuation();
  malformed.price_range.mid = null as never;
  const model = buildMarketPriceModel({
    activePriceBasis: "asking",
    activePriceWan: 2480,
    askingPriceWan: 2480,
    valuation: malformed as never,
    stale: false,
  });

  assert.equal(model.priceContext.estimateRange, null);
  assert.equal(model.valuation.status, "unavailable");
  assert.equal(model.valuation.estimate, null);
  assert.ok(model.overview.unresolvedChecks.includes("重新取得可安全判讀的價格推估"));
});

test("legacy adapter drops an untrusted valuation-basis active price", () => {
  const row = savedCase();
  row.data.journeyContext.priceBasis = "valuation" as never;
  row.data.journeyContext.activePriceWan = 9999;
  (row.data as typeof row.data & { valuation: unknown }).valuation = {
    ...storedValuation(),
    is_actionable: false,
  };

  const workspace = adaptSavedCaseToWorkspace(row as never);

  assert.equal(workspace.assumptions.activePriceWan, undefined);
  assert.match(workspace.marketPrice.priceContext.activePrice.formatted, /未提供/);
});

test("identity change marks property-bound Market and valuation evidence stale", () => {
  const model = buildMarketPriceModel({
    activePriceBasis: "asking",
    activePriceWan: 2480,
    askingPriceWan: 2480,
    market: savedCase().data.marketInsight as never,
    valuation: storedValuation() as never,
    stale: true,
  });

  assert.equal(model.isStale, true);
  assert.equal(model.market.status, "stale");
  assert.equal(model.valuation.status, "stale");
  assert.equal(model.overview.evidenceStatus, "stale");
  assert.ok(model.overview.unresolvedChecks.includes("重新確認目前物件後再採用價格證據"));
});

test("Market no-data and unavailable states never retain price metrics", () => {
  const noData = { ...savedCase().data.marketInsight, data_status: "no_data" };
  const unavailable = { ...savedCase().data.marketInsight, data_status: "unavailable" };

  const insufficientModel = buildMarketPriceModel({ activePriceBasis: "asking", market: noData as never, stale: false });
  const unavailableModel = buildMarketPriceModel({ activePriceBasis: "asking", market: unavailable as never, stale: false });

  assert.equal(insufficientModel.market.status, "insufficient");
  assert.equal(insufficientModel.priceContext.marketMedianTotal, null);
  assert.equal(insufficientModel.priceContext.marketMedianUnit, null);
  assert.equal(unavailableModel.market.status, "unavailable");
  assert.equal(unavailableModel.priceContext.marketMedianTotal, null);
  assert.equal(unavailableModel.priceContext.marketMedianUnit, null);
});

test("source-declared stale Market evidence remains visible but explicitly stale", () => {
  const staleMarket = { ...savedCase().data.marketInsight, freshness_status: "update_available" };
  const model = buildMarketPriceModel({ activePriceBasis: "asking", market: staleMarket as never, stale: false });

  assert.equal(model.market.status, "stale");
  assert.equal(model.overview.evidenceStatus, "stale");
  assert.equal(model.source.updatedAt, "2026-08-31");
});

test("uncovered or structurally invalid Market payloads fail closed", () => {
  const uncovered = { ...savedCase().data.marketInsight, coverage_status: "not_covered" };
  const invertedRange = {
    ...savedCase().data.marketInsight,
    p25_unit_price_per_ping: 60,
    p75_unit_price_per_ping: 50,
  };
  const malformedHistory = { ...savedCase().data.marketInsight, history: [null] };

  const uncoveredModel = buildMarketPriceModel({ activePriceBasis: "asking", market: uncovered as never, stale: false });
  const invertedRangeModel = buildMarketPriceModel({ activePriceBasis: "asking", market: invertedRange as never, stale: false });
  const malformedHistoryModel = buildMarketPriceModel({ activePriceBasis: "asking", market: malformedHistory as never, stale: false });

  assert.equal(uncoveredModel.market.status, "unavailable");
  assert.equal(uncoveredModel.priceContext.marketMedianTotal, null);
  assert.equal(uncoveredModel.priceContext.marketMedianUnit, null);
  assert.deepEqual(uncoveredModel.market.history, []);
  assert.equal(uncoveredModel.overview.marketRange, null);
  assert.equal(invertedRangeModel.overview.marketRange, null);
  assert.deepEqual(malformedHistoryModel.market.history, []);
});

test("an untrusted or stale valuation cannot remain the active estimate", () => {
  const invalidValuation = storedValuation();
  invalidValuation.is_actionable = false;
  invalidValuation.comparables = [{ total_price: 9999 }] as never;

  const invalidModel = buildMarketPriceModel({
    activePriceBasis: "estimate",
    activePriceWan: 9999,
    valuation: invalidValuation as never,
    stale: false,
  });
  const staleModel = buildMarketPriceModel({
    activePriceBasis: "estimate",
    activePriceWan: 1850,
    valuation: storedValuation() as never,
    stale: true,
  });

  assert.match(invalidModel.priceContext.activePrice.formatted, /未提供/);
  assert.equal(invalidModel.valuation.comparablesAvailable, false);
  assert.deepEqual(invalidModel.valuation.comparables, []);
  assert.match(staleModel.priceContext.activePrice.formatted, /未提供/);
});
