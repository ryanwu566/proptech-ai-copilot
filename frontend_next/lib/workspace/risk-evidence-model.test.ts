import assert from "node:assert/strict";
import test from "node:test";

import type { TerrainHazardLayer, TerrainRiskResult } from "../api";
import type { PropertyCaseWorkspace } from "./workspace-model";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildRiskEvidenceModel, buildRiskQueryContext, buildStoredRiskEvidenceModel, buildStoredRiskEvidenceSnapshot, canCommitRiskResponse } from "./risk-evidence-model.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { normalizeStoredTerrainReferenceEvidence } from "../terrain-reference-evidence.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildMarketPriceModel } from "./market-price-model.ts";

const SOURCE = {
  name: "官方測試圖層",
  agency: "測試機關",
  source_url: "https://example.gov.tw/layer",
  status: "available",
  data_updated_at: "2026-06-30",
  data_vintage: "2026 年版",
};

test("partial positive hazard coverage remains partial through Save/Reopen", () => {
  const snapshot = { kind: "terrain_reference", schema_version: 1, status: "partial", notice: "Partial source", summary: "Positive point match", layers: [{ layer_id: "flood", display_name: "Flood", state: "partial", source_name: "WRA", coverage_status: "partial", caveat: "Partial source; manual verification required" }] };
  const restored = normalizeStoredTerrainReferenceEvidence(snapshot);
  assert.equal(restored?.layers[0].coverage_status, "partial");
});

function hazard(overrides: Partial<TerrainHazardLayer> & Pick<TerrainHazardLayer, "key" | "label">): TerrainHazardLayer {
  return {
    status: "available",
    level: "unknown",
    matched: false,
    distance_m: null,
    value: null,
    explanation: "已完成指定範圍查詢。",
    source: SOURCE,
    ...overrides,
  };
}

function terrainResult(overrides: Partial<TerrainRiskResult> = {}): TerrainRiskResult {
  const { hazards: hazardOverrides, ...resultOverrides } = overrides;
  const hazards = {
    flood: hazard({ key: "flood", label: "淹水潛勢" }),
    landslide: hazard({ key: "landslide", label: "大規模崩塌潛勢" }),
    debris_flow: hazard({ key: "debris_flow", label: "土石流潛勢溪流" }),
    liquefaction: hazard({ key: "liquefaction", label: "土壤液化潛勢" }),
    geological_sensitivity: hazard({ key: "geological_sensitivity", label: "地質敏感區" }),
    active_fault: hazard({
      key: "active_fault",
      label: "活動斷層",
      status: "unavailable",
      explanation: "目前未設定可直接比對座標的官方圖資查詢。",
      source: { ...SOURCE, status: "unavailable" },
    }),
  };
  return {
    input: { latitude: 25.033, longitude: 121.5654, radius_m: 500 },
    resolved_location: { latitude: 25.033, longitude: 121.5654, geocoding_source: "provided_coordinates" },
    overall: { level: "unknown", label: "不採用的舊總評", summary: "不採用", confidence: "unknown" },
    terrain: { status: "available", slope_value: 3, slope_class: "平緩", explanation: "官方坡度查詢完成。", source: SOURCE },
    risk_factors: [],
    missing_sources: [],
    recommended_checks: [],
    map_layers: [],
    source_transparency: {
      notice: "圖層結果需逐項判讀。",
      layers: Object.values(hazards).map((item) => ({
        layer_id: item.key,
        display_name: item.label,
        source_name: item.source?.name ?? "未提供",
        source_kind: item.source?.agency ?? "未提供",
        assessment_status: item.status === "available" ? (item.matched ? "matched" : "not_matched") : "unavailable",
        coverage_status: item.status === "available" ? "covered" : "unknown",
        data_updated_at: item.source?.data_updated_at ?? "unknown",
        caveat: item.explanation,
      })),
    },
    official_data_sources: [],
    data_quality: { status: "limited", warnings: [], checked_at: "2026-10-01T02:00:00.000Z" },
    disclaimer: "僅供查證規劃。",
    ...resultOverrides,
    hazards: { ...hazards, ...hazardOverrides },
  };
}

function workspace(overrides: Partial<PropertyCaseWorkspace> = {}): PropertyCaseWorkspace {
  return {
    caseId: "case-risk-1",
    revision: 4,
    title: "信義區商用物件",
    displayAddress: "臺北市信義區市府路1號",
    updatedAt: "2026-10-01T01:00:00.000Z",
    identity: {
      state: "confirmed",
      scope: "journey_browser_anchor",
      anchor: {
        version: 1,
        scope: "journey_browser_anchor",
        journey_anchor_id: "journey-browser-123e4567-e89b-42d3-a456-426614174000",
        address_input: "臺北市信義區市府路1號",
        normalized_address: "臺北市信義區市府路1號",
        coordinates: { latitude: 25.033, longitude: 121.5654 },
        administrative_location: { city: "臺北市", district: "信義區", village: null, village_code: null },
        location_status: "candidate",
        parcel: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: [], confirmation: null },
        building: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: [], confirmation: null },
        confidence: { level: "medium", domain: "address_spatial_correlation", basis: ["accepted_coordinates"], limitations: [] },
        evidence: { sources: [], checked_at: "2026-10-01T01:00:00.000Z", limitations: [] },
        revalidation: { status: "current", conflicts: [] },
      },
    },
    assumptions: { activePriceBasis: "asking" },
    evidence: {
      market: { query: "not_started", completeness: "not_started", summaryOnly: false },
      valuation: { query: "not_started", completeness: "not_started", summaryOnly: false },
      location: { query: "succeeded", usability: "limited", completeness: "partial", summaryOnly: true },
      commute: { query: "not_started", completeness: "not_started", summaryOnly: false },
      risk: { query: "not_started", completeness: "not_started", summaryOnly: false },
      finance: { query: "not_started", completeness: "not_started", summaryOnly: false },
    },
    marketPrice: buildMarketPriceModel({ activePriceBasis: "asking", stale: false }),
    location: {
      property: {
        address: "臺北市信義區市府路1號",
        normalizedAddress: "臺北市信義區市府路1號",
        coordinates: { latitude: 25.033, longitude: 121.5654 },
        checkedAt: "2026-10-01T01:00:00.000Z",
        village: { name: null, code: null },
        sourceIds: [],
      },
      routeInvalidated: false,
    },
    risk: null,
    saveState: "saved",
    ...overrides,
  } as PropertyCaseWorkspace;
}

test("matched flood is material evidence without using the backend aggregate score", () => {
  const flood = hazard({ key: "flood", label: "淹水潛勢", matched: true, level: "high", value: "2.0–3.0 公尺", distance_m: 0 });
  const model = buildRiskEvidenceModel(terrainResult({ hazards: { ...terrainResult().hazards, flood } }));
  const row = model.rows.find((item) => item.key === "flood");

  assert.equal(row?.usability, "usable");
  assert.equal(row?.interpretation, "elevated_signal");
  assert.equal(row?.matched, true);
  assert.match(row?.result ?? "", /符合/);
  assert.equal(model.materialEvidenceCount, 1);
  assert.equal("overallScore" in model, false);
});

test("landslide and debris-flow remain independent during a partial provider failure", () => {
  const result = terrainResult();
  result.hazards.landslide = hazard({ key: "landslide", label: "大規模崩塌潛勢", matched: true, level: "medium" });
  result.hazards.debris_flow = hazard({ key: "debris_flow", label: "土石流潛勢溪流", status: "error", explanation: "來源查詢失敗。", source: { ...SOURCE, status: "error" } });
  const model = buildRiskEvidenceModel(result);

  assert.equal(model.rows.find((item) => item.key === "landslide")?.interpretation, "caution_signal");
  assert.equal(model.rows.find((item) => item.key === "debris_flow")?.usability, "unavailable");
  assert.equal(model.rows.find((item) => item.key === "debris_flow")?.interpretation, "unknown");
  assert.equal(model.materialEvidenceCount, 1);
  assert.ok(model.unknownEvidenceCount >= 2);
});

test("liquefaction preserves the official source classification", () => {
  const result = terrainResult();
  result.hazards.liquefaction = hazard({
    key: "liquefaction",
    label: "土壤液化潛勢",
    matched: true,
    level: "medium",
    value: { official_classification: "中潛勢", queried_area: "臺北" } as never,
  });
  const row = buildRiskEvidenceModel(result).rows.find((item) => item.key === "liquefaction");

  assert.equal(row?.sourceClassification, "中潛勢");
  assert.match(row?.result ?? "", /中潛勢/);
});

test("geological sensitivity retains every overlap and explicit dataset version without inventing severity", () => {
  const result = terrainResult();
  result.hazards.geological_sensitivity = hazard({
    key: "geological_sensitivity",
    label: "地質敏感區",
    matched: true,
    level: "unknown",
    value: {
      dataset_version: "2024-06-27",
      matched_count: 2,
      matches: [
        { official_category: "活動斷層地質敏感區", canonical_category: "active_fault_sensitive_area" },
        { official_category: "山崩與地滑地質敏感區", canonical_category: "landslide_sensitive_area" },
      ],
    } as never,
  });
  const row = buildRiskEvidenceModel(result).rows.find((item) => item.key === "geological_sensitivity");

  assert.equal(row?.interpretation, "caution_signal");
  assert.equal(row?.sourceLevel, "unknown");
  assert.equal(row?.datasetVersion, "2024-06-27");
  assert.deepEqual(row?.categories, [
    { official: "活動斷層地質敏感區", canonical: "active_fault_sensitive_area" },
    { official: "山崩與地滑地質敏感區", canonical: "landslide_sensitive_area" },
  ]);
});

test("covered no-match is a scoped no-signal state and never a safety conclusion", () => {
  const model = buildRiskEvidenceModel(terrainResult());
  const flood = model.rows.find((item) => item.key === "flood");

  assert.equal(flood?.usability, "no_match");
  assert.equal(flood?.interpretation, "no_identified_signal");
  assert.match(flood?.result ?? "", /本次查詢範圍/);
  assert.doesNotMatch(flood?.result ?? "", /安全|低風險/);
});

test("outside source coverage remains unknown instead of becoming a no-match", () => {
  const result = terrainResult();
  const transparency = result.source_transparency!;
  transparency.layers = transparency.layers.map((layer) => layer.layer_id === "flood"
    ? { ...layer, coverage_status: "not_covered", assessment_status: "unavailable" }
    : layer);
  const flood = buildRiskEvidenceModel(result).rows.find((item) => item.key === "flood");

  assert.equal(flood?.usability, "no_coverage");
  assert.equal(flood?.interpretation, "unknown");
  assert.match(flood?.result ?? "", /不在.*涵蓋範圍/);
});

test("unavailable evidence and successful queries do not become low risk", () => {
  const result = terrainResult();
  result.hazards.flood = hazard({ key: "flood", label: "淹水潛勢", status: "unavailable", source: { ...SOURCE, status: "unavailable" } });
  const model = buildRiskEvidenceModel(result);
  const flood = model.rows.find((item) => item.key === "flood");

  assert.equal(flood?.usability, "unavailable");
  assert.equal(flood?.interpretation, "unknown");
  assert.doesNotMatch(JSON.stringify(model), /low risk|低風險|安全/iu);
});

test("active fault remains explicitly unsupported by the current automated path", () => {
  const row = buildRiskEvidenceModel(terrainResult()).rows.find((item) => item.key === "active_fault");

  assert.equal(row?.usability, "unsupported");
  assert.equal(row?.interpretation, "unknown");
  assert.match(row?.limitation ?? "", /官方圖台|未.*直接比對/);
});

test("query context requires current confirmed coordinates and rejects an older property fingerprint", () => {
  const first = buildRiskQueryContext(workspace());
  const changed = buildRiskQueryContext(workspace({
    revision: 5,
    identity: {
      ...workspace().identity,
      anchor: { ...workspace().identity.anchor!, coordinates: { latitude: 24.1477, longitude: 120.6736 } },
    },
  }));

  assert.ok(first);
  assert.ok(changed);
  assert.equal(first?.payload.include_layers?.includes("active_fault"), true);
  assert.equal(canCommitRiskResponse(changed!, first!), false);
  assert.equal(canCommitRiskResponse(first!, first!), true);
  assert.equal(buildRiskQueryContext(workspace({ identity: { ...workspace().identity, state: "revalidation_required" } })), null);
});

test("freshness and overview handoff expose material, unknown, action, and checked-at facts only", () => {
  const result = terrainResult();
  result.hazards.flood = hazard({ key: "flood", label: "淹水潛勢", matched: true, level: "high" });
  const model = buildRiskEvidenceModel(result);

  assert.equal(model.freshness.checkedAt, "2026-10-01T02:00:00.000Z");
  assert.equal(model.overview.materialMatchedEvidence.length, 1);
  assert.equal(model.overview.unknownOrUnavailableCount, model.unknownEvidenceCount);
  assert.ok(model.overview.outstandingVerificationActions.length > 0);
  assert.equal(model.overview.evidenceFreshness, "2026-10-01T02:00:00.000Z");
});

test("reopened compact evidence stays limited or stale and does not reconstruct raw results", () => {
  const stored = {
    schema_version: 1 as const,
    kind: "terrain_reference" as const,
    status: "available" as const,
    summary: "已有一項可供查看的參考圖層。",
    notice: "僅供查證規劃。",
    layers: [{
      layer_id: "flood",
      display_name: "淹水潛勢",
      state: "available" as const,
      source_name: "經濟部水利署",
      coverage_status: "covered" as const,
      caveat: "保存內容為摘要。",
    }],
  };

  const limited = buildStoredRiskEvidenceModel(stored, { stale: false, checkedAt: null });
  const stale = buildStoredRiskEvidenceModel(stored, { stale: true, checkedAt: "2026-09-30T00:00:00.000Z" });
  assert.equal(limited.freshness.checkedAt, null);
  assert.equal(limited.rows[0].usability, "limited");
  assert.equal(limited.rows[0].interpretation, "unknown");
  assert.equal(stale.rows[0].usability, "stale");
  assert.equal(stale.rows[0].interpretation, "unknown");
  assert.equal(stale.freshness.checkedAt, "2026-09-30T00:00:00.000Z");
});

test("fresh mixed risk evidence compacts matched and unavailable rows without raw provider data", () => {
  const result = terrainResult();
  result.hazards.flood = hazard({ key: "flood", label: "淹水潛勢", matched: true, level: "high" });
  result.hazards.debris_flow = hazard({
    key: "debris_flow",
    label: "土石流潛勢溪流",
    status: "error",
    explanation: "來源查詢失敗。",
    source: { ...SOURCE, status: "error" },
  });

  const snapshot = buildStoredRiskEvidenceSnapshot(buildRiskEvidenceModel(result));
  const debrisFlow = snapshot.layers.find((row) => row.layer_id === "debris_flow");

  assert.equal(snapshot.status, "partial");
  assert.equal(debrisFlow?.state, "unavailable");
  assert.match(debrisFlow?.caveat ?? "", /無法取得|無法判定/);
  assert.equal("hazards" in snapshot, false);
  assert.equal("hazard_geometries" in snapshot, false);
  assert.equal("checked_at" in snapshot, false);
  assert.ok(normalizeStoredTerrainReferenceEvidence(snapshot));
});

test("saved risk handoff preserves no-match separately from unknown and never turns it into safety", () => {
  const model = buildStoredRiskEvidenceModel({
    schema_version: 1,
    kind: "terrain_reference",
    status: "no_match",
    summary: "已保存查詢摘要。",
    notice: "未命中不代表沒有風險。",
    layers: [{
      layer_id: "flood",
      display_name: "淹水潛勢",
      state: "no_match",
      source_name: "水利署",
      coverage_status: "covered",
      caveat: "未命中不代表安全。",
    }],
  }, { stale: false, checkedAt: "2026-10-07T03:00:00.000Z" });

  assert.equal(model.rows[0]?.usability, "no_match");
  assert.equal(model.rows[0]?.interpretation, "unknown");
  assert.deepEqual(model.overview.noMatchEvidence, [{ key: "flood", label: "淹水潛勢", result: "已儲存的查詢摘要為未命中；此結果不代表安全。" }]);
  assert.deepEqual(model.overview.unknownOrUnavailableEvidence, []);
  assert.equal(model.freshness.status, "saved_summary");
});

test("saved risk handoff preserves unavailable instead of flattening it to limited", () => {
  const model = buildStoredRiskEvidenceModel({
    schema_version: 1,
    kind: "terrain_reference",
    status: "partial",
    summary: "部分來源未完成。",
    notice: "未知仍為未知。",
    layers: [{
      layer_id: "geological_sensitivity",
      display_name: "地質敏感區",
      state: "unavailable",
      source_name: "地質調查及礦業管理中心",
      coverage_status: "unknown",
      caveat: "來源目前無法取得。",
    }],
  }, { stale: false, checkedAt: "2026-10-07T03:00:00.000Z" });

  assert.equal(model.rows[0]?.usability, "unavailable");
  assert.equal(model.rows[0]?.interpretation, "unknown");
  assert.deepEqual(model.overview.unknownOrUnavailableEvidence, [{
    key: "geological_sensitivity",
    label: "地質敏感區",
    usability: "unavailable",
    result: "目前無法取得此項已儲存證據，風險仍無法判定。",
  }]);
});
