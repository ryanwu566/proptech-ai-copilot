import type {
  TerrainHazardLayer,
  TerrainRiskLevel,
  TerrainRiskResult,
  TerrainRiskSource,
  TerrainRiskSourceTransparencyLayer,
} from "../api";
import type { EvidenceUsabilityState, RiskInterpretationState } from "../commercial/state";
import type { StoredTerrainReferenceEvidenceV1 } from "../terrain-reference-evidence";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildInputFingerprint, canCommitEvidence } from "./invalidation.ts";
import type { InputFingerprint, PropertyCaseWorkspace } from "./workspace-model";

export const RISK_QUERY_LAYERS = [
  "terrain",
  "flood",
  "landslide",
  "debris_flow",
  "liquefaction",
  "geological_sensitivity",
  "active_fault",
] as const;

export type RiskEvidenceKey = (typeof RISK_QUERY_LAYERS)[number];

export type GeologicalSensitivityCategory = {
  official: string;
  canonical: string;
};

export type RiskEvidenceRow = {
  key: RiskEvidenceKey;
  label: string;
  queryStatus: "succeeded";
  usability: EvidenceUsabilityState;
  interpretation: RiskInterpretationState;
  matched: boolean | null;
  result: string;
  source: string;
  sourceAgency?: string;
  sourceUrl?: string;
  sourceClassification?: string;
  sourceLevel: TerrainRiskLevel | "not_applicable";
  effectivePeriod: string;
  limitation: string;
  nextVerification: string;
  coverage: "covered" | "not_covered" | "unknown";
  datasetVersion?: string;
  queryCondition?: string;
  sourceUpdatedAt?: string;
  categories?: GeologicalSensitivityCategory[];
};

export type RiskOverviewHandoff = {
  materialMatchedEvidence: Array<{ key: RiskEvidenceKey; label: string; result: string }>;
  noMatchEvidence: Array<{ key: RiskEvidenceKey; label: string; result: string }>;
  unknownOrUnavailableEvidence: Array<{ key: RiskEvidenceKey; label: string; usability: EvidenceUsabilityState; result: string }>;
  unknownOrUnavailableCount: number;
  outstandingVerificationActions: string[];
  evidenceFreshness: string | null;
  freshnessStatus: "current_query" | "saved_summary" | "stale";
};

export type RiskEvidenceModel = {
  rows: RiskEvidenceRow[];
  materialEvidenceCount: number;
  unknownEvidenceCount: number;
  verificationActions: string[];
  freshness: { checkedAt: string | null; status: "current_query" | "saved_summary" | "stale" };
  overview: RiskOverviewHandoff;
};

export type RiskQueryContext = {
  caseId: string;
  revision: number;
  fingerprint: InputFingerprint;
  payload: {
    latitude: number;
    longitude: number;
    city?: string;
    district?: string;
    radius_m: 500;
    include_layers: string[];
  };
};

const UNKNOWN_STATES = new Set<EvidenceUsabilityState>([
  "limited",
  "no_coverage",
  "unavailable",
  "stale",
  "unverified",
  "unsupported",
]);

const SOURCE_ACTIONS: Record<RiskEvidenceKey, string> = {
  terrain: "現場確認基地坡度、排水與擋土設施，必要時請專業人員判讀。",
  flood: "開啟水利署來源詳情，並查證現場排水與過往積淹水紀錄。",
  landslide: "檢視農村水保署圖資，並確認基地周邊邊坡與擋土設施。",
  debris_flow: "檢視農村水保署土石流圖資與影響範圍，必要時請專業人員判讀。",
  liquefaction: "檢視地質雲的區域分類，個案仍應配合現地調查與工程評估。",
  geological_sensitivity: "核對地質調查及礦業管理中心的公告類別與資料版本。",
  active_fault: "目前自動比對未完成；請改至官方地質圖台人工確認。",
};

function record(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function text(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function safeSource(source: TerrainRiskSource | undefined): { name: string; agency?: string; url?: string; period: string } {
  const agency = text(source?.agency);
  const name = agency ?? text(source?.name) ?? "未提供來源名稱";
  const url = text(source?.source_url);
  const period = text(source?.data_updated_at) ?? text(source?.data_vintage) ?? "未提供";
  return { name, agency, url, period };
}

function transparencyFor(result: TerrainRiskResult, key: string): TerrainRiskSourceTransparencyLayer | undefined {
  return result.source_transparency?.layers.find((layer) => layer.layer_id === key);
}

function sourceValue(hazard: TerrainHazardLayer): Record<string, unknown> | null {
  return record(hazard.value as unknown);
}

function geologicalCategories(hazard: TerrainHazardLayer): GeologicalSensitivityCategory[] {
  const matches = sourceValue(hazard)?.matches;
  if (!Array.isArray(matches)) return [];
  return matches.flatMap((match) => {
    const item = record(match);
    const official = text(item?.official_category);
    const canonical = text(item?.canonical_category);
    return official && canonical ? [{ official, canonical }] : [];
  });
}

function classificationFor(hazard: TerrainHazardLayer): string | undefined {
  const value = sourceValue(hazard);
  return text(value?.official_classification)
    ?? text(value?.classification)
    ?? text(hazard.source && (hazard.source as unknown as Record<string, unknown>).official_classification);
}

function hazardUsability(hazard: TerrainHazardLayer, transparency?: TerrainRiskSourceTransparencyLayer): EvidenceUsabilityState {
  if (hazard.key === "active_fault") return "unsupported";
  if (hazard.status === "unavailable" || hazard.status === "error") return "unavailable";
  if (hazard.status === "skipped") return "unsupported";
  if (hazard.status === "limited") return "limited";
  if (transparency?.coverage_status === "not_covered") return "no_coverage";
  if (hazard.status === "available" && !hazard.matched) return "no_match";
  if (hazard.status === "available") return "usable";
  return "unverified";
}

function hazardInterpretation(
  hazard: TerrainHazardLayer,
  usability: EvidenceUsabilityState,
  transparency?: TerrainRiskSourceTransparencyLayer,
): RiskInterpretationState {
  if (hazard.key === "active_fault") return "unknown";
  if (hazard.matched && usability === "usable") {
    if (hazard.key === "geological_sensitivity") return "caution_signal";
    return hazard.level === "high" ? "elevated_signal" : "caution_signal";
  }
  if (hazard.matched && usability === "limited") return "caution_signal";
  if (
    !hazard.matched
    && usability === "no_match"
    && transparency?.assessment_status === "not_matched"
    && transparency.coverage_status === "covered"
  ) return "no_identified_signal";
  return "unknown";
}

function matchedResult(hazard: TerrainHazardLayer, categories: GeologicalSensitivityCategory[]): string {
  if (hazard.key === "geological_sensitivity") {
    const names = categories.map((category) => category.official).join("、");
    return names
      ? `符合 ${categories.length} 項官方公告類別：${names}。公告交集不代表高、中或低風險分級。`
      : "符合官方公告地質敏感區；目前來源未提供可辯護的風險分級。";
  }
  const classification = classificationFor(hazard);
  if (classification) return `本次位置符合來源分類「${classification}」。`;
  return "本次位置符合此來源定義的圖層資料，需進一步查證。";
}

function hazardResult(
  hazard: TerrainHazardLayer,
  usability: EvidenceUsabilityState,
  categories: GeologicalSensitivityCategory[],
): string {
  if (hazard.key === "active_fault") return "目前自動查詢路徑尚未提供完成的活動斷層判讀結果。";
  if (hazard.matched) return matchedResult(hazard, categories);
  if (usability === "no_match") return "本次查詢範圍未比對到來源定義的符合資料；此結果僅限已確認的涵蓋與查詢範圍。";
  if (usability === "no_coverage") return "此位置不在目前資料涵蓋範圍，無法形成風險判讀。";
  if (usability === "limited") return "目前僅取得部分來源結果，無法形成完整判讀。";
  if (usability === "unavailable") return "目前無法取得此項證據，風險仍無法判定。";
  return "目前資料不足，風險仍無法判定。";
}

function hazardLimitation(hazard: TerrainHazardLayer, usability: EvidenceUsabilityState): string {
  if (hazard.key === "active_fault") return "目前未設定可直接比對座標的官方查詢；請至官方圖台人工確認。";
  if (hazard.key === "geological_sensitivity") {
    const version = text(sourceValue(hazard)?.dataset_version);
    if (!version || version === "not_configured") return "功能已實作，但正式資料版本尚未設定或目前無法驗證；不得視為已有生產證據。";
    return `使用明確資料版本 ${version}；命中只代表公告範圍交集，不提供嚴重度。`;
  }
  if (usability === "no_match") return "未命中不等於不存在其他災害條件；仍需核對來源範圍與現場。";
  return text(hazard.source?.limitation) ?? text(hazard.explanation) ?? "此項結果僅限來源的資料範圍與方法。";
}

function hazardRow(result: TerrainRiskResult, key: Exclude<RiskEvidenceKey, "terrain">): RiskEvidenceRow {
  const hazard = result.hazards[key];
  const transparency = transparencyFor(result, key);
  const usability = hazardUsability(hazard, transparency);
  const categories = key === "geological_sensitivity" ? geologicalCategories(hazard) : [];
  const source = safeSource(hazard.source);
  const value = sourceValue(hazard);
  const datasetVersion = key === "geological_sensitivity" ? text(value?.dataset_version) : undefined;
  return {
    key,
    label: hazard.label,
    queryStatus: "succeeded",
    usability,
    interpretation: hazardInterpretation(hazard, usability, transparency),
    matched: usability === "unavailable" || usability === "unsupported" ? null : hazard.matched,
    result: hazardResult(hazard, usability, categories),
    source: source.name,
    ...(source.agency ? { sourceAgency: source.agency } : {}),
    ...(source.url ? { sourceUrl: source.url } : {}),
    ...(classificationFor(hazard) ? { sourceClassification: classificationFor(hazard) } : {}),
    sourceLevel: key === "geological_sensitivity" || usability === "unavailable" || usability === "unsupported"
      ? "unknown"
      : hazard.level,
    effectivePeriod: source.period,
    limitation: hazardLimitation(hazard, usability),
    nextVerification: SOURCE_ACTIONS[key],
    coverage: transparency?.coverage_status ?? (usability === "unavailable" ? "unknown" : "covered"),
    ...(datasetVersion ? { datasetVersion } : {}),
    ...(categories.length ? { categories } : {}),
  };
}

function terrainRow(result: TerrainRiskResult): RiskEvidenceRow {
  const terrain = result.terrain;
  const source = safeSource(terrain.source);
  const transparency = transparencyFor(result, "terrain");
  const unusable = terrain.status === "unavailable" || terrain.status === "error";
  const limited = terrain.status === "limited";
  const usability: EvidenceUsabilityState = unusable ? "unavailable" : limited ? "limited" : terrain.status === "available" ? "usable" : "unsupported";
  const slope = typeof terrain.slope_value === "number" && Number.isFinite(terrain.slope_value)
    ? `${terrain.slope_value.toLocaleString("zh-TW", { maximumFractionDigits: 1 })}°`
    : undefined;
  return {
    key: "terrain",
    label: "地形／坡度",
    queryStatus: "succeeded",
    usability,
    interpretation: unusable || limited ? "unknown" : "not_assessed",
    matched: null,
    result: slope ? `來源提供坡度 ${slope}${terrain.slope_class ? `（${terrain.slope_class}）` : ""}。` : unusable ? "目前無法取得地形／坡度證據。" : "已取得地形／坡度參考資料。",
    source: source.name,
    ...(source.agency ? { sourceAgency: source.agency } : {}),
    ...(source.url ? { sourceUrl: source.url } : {}),
    sourceLevel: "not_applicable",
    effectivePeriod: source.period,
    limitation: text(terrain.source?.limitation) ?? text(terrain.explanation) ?? "地形資料不等同基地工程鑑定。",
    nextVerification: SOURCE_ACTIONS.terrain,
    coverage: transparency?.coverage_status ?? (unusable ? "unknown" : "covered"),
  };
}

function uniqueActions(rows: RiskEvidenceRow[]): string[] {
  return [...new Set(rows
    .filter((row) => row.matched || UNKNOWN_STATES.has(row.usability))
    .map((row) => row.nextVerification))];
}

function assemble(rows: RiskEvidenceRow[], checkedAt: string | null, status: RiskEvidenceModel["freshness"]["status"]): RiskEvidenceModel {
  const material = rows.filter((row) => row.matched === true);
  const noMatch = rows.filter((row) => row.usability === "no_match");
  const unknown = rows.filter((row) => row.matched !== true && row.usability !== "no_match" && (UNKNOWN_STATES.has(row.usability) || row.interpretation === "unknown"));
  const verificationActions = uniqueActions(rows);
  return {
    rows,
    materialEvidenceCount: material.length,
    unknownEvidenceCount: unknown.length,
    verificationActions,
    freshness: { checkedAt, status },
    overview: {
      materialMatchedEvidence: material.map((row) => ({ key: row.key, label: row.label, result: row.result })),
      noMatchEvidence: noMatch.map((row) => ({ key: row.key, label: row.label, result: row.result })),
      unknownOrUnavailableEvidence: unknown.map((row) => ({ key: row.key, label: row.label, usability: row.usability, result: row.result })),
      unknownOrUnavailableCount: unknown.length,
      outstandingVerificationActions: verificationActions,
      evidenceFreshness: checkedAt,
      freshnessStatus: status,
    },
  };
}

export function buildRiskEvidenceModel(result: TerrainRiskResult): RiskEvidenceModel {
  const rows: RiskEvidenceRow[] = [
    hazardRow(result, "flood"),
    hazardRow(result, "landslide"),
    hazardRow(result, "debris_flow"),
    hazardRow(result, "liquefaction"),
    hazardRow(result, "geological_sensitivity"),
    hazardRow(result, "active_fault"),
    terrainRow(result),
  ];
  rows.sort((left, right) => {
    const priority = (row: RiskEvidenceRow) => row.matched ? 0 : UNKNOWN_STATES.has(row.usability) || row.interpretation === "unknown" ? 1 : 2;
    return priority(left) - priority(right) || RISK_QUERY_LAYERS.indexOf(left.key) - RISK_QUERY_LAYERS.indexOf(right.key);
  });
  return assemble(rows, text(result.data_quality.checked_at) ?? null, "current_query");
}

function storedKey(value: string): RiskEvidenceKey | null {
  return (RISK_QUERY_LAYERS as readonly string[]).includes(value) ? value as RiskEvidenceKey : null;
}

export function buildStoredRiskEvidenceModel(
  reference: StoredTerrainReferenceEvidenceV1,
  options: { stale: boolean; checkedAt: string | null },
): RiskEvidenceModel {
  const rows = reference.layers.flatMap((layer): RiskEvidenceRow[] => {
    const key = storedKey(layer.layer_id);
    if (!key) return [];
    const usability: EvidenceUsabilityState = options.stale
      ? "stale"
      : layer.evidence_metadata ? layer.evidence_metadata.usability
      : layer.state === "no_match"
        ? "no_match"
        : layer.state === "unavailable" || layer.state === "error"
          ? "unavailable"
          : "limited";
    const matched = options.stale ? null : layer.evidence_metadata ? layer.evidence_metadata.matched : layer.state === "available" ? true : usability === "no_match" ? false : null;
    const result = options.stale
      ? "此摘要屬於先前物件狀態，不能作為目前證據。"
      : usability === "no_match"
        ? "已儲存的查詢摘要為未命中；此結果不代表安全。"
        : usability === "unavailable"
          ? "目前無法取得此項已儲存證據，風險仍無法判定。"
          : matched
            ? "已儲存摘要記錄此來源曾有符合資料；需重新查詢才能檢視完整結果。"
            : "此為已儲存的摘要證據；需重新查詢才能檢視完整結果。";
    return [{
      key,
      label: layer.display_name,
      queryStatus: "succeeded",
      usability,
      interpretation: "unknown",
      matched,
      result,
      source: layer.source_agency ?? layer.source_name,
      ...(layer.source_agency ? { sourceAgency: layer.source_agency } : {}),
      sourceLevel: key === "terrain" ? "not_applicable" : "unknown",
      effectivePeriod: layer.data_updated_at ?? layer.data_version ?? "未提供",
      limitation: layer.caveat,
      nextVerification: SOURCE_ACTIONS[key],
      coverage: layer.coverage_status,
      ...(layer.data_version ? { datasetVersion: layer.data_version } : {}),
      ...(layer.data_updated_at ? { sourceUpdatedAt: layer.data_updated_at } : {}),
      ...(layer.evidence_metadata?.source_url ? { sourceUrl: layer.evidence_metadata.source_url } : {}),
      queryCondition: layer.evidence_metadata?.query_condition ?? "查詢條件未保存",
    }];
  });
  return assemble(rows, options.checkedAt, options.stale ? "stale" : "saved_summary");
}

export function buildStoredRiskEvidenceSnapshot(model: RiskEvidenceModel): StoredTerrainReferenceEvidenceV1 {
  const hasMaterial = model.rows.some((row) => row.matched === true);
  const hasUnknown = model.rows.some((row) => UNKNOWN_STATES.has(row.usability) || row.interpretation === "unknown");
  const allNoMatch = model.rows.every((row) => row.usability === "no_match");
  return {
    schema_version: 1,
    kind: "terrain_reference",
    status: hasMaterial && hasUnknown ? "partial" : hasMaterial ? "available" : allNoMatch ? "no_match" : "limited",
    summary: hasMaterial
      ? `保留 ${model.materialEvidenceCount} 項已比對證據；未知或受限項目 ${model.unknownEvidenceCount} 項。`
      : `未保留可下結論的風險證據；未知或受限項目 ${model.unknownEvidenceCount} 項。`,
    notice: "此為有界的已儲存摘要；重新開啟時僅供追溯，必須重新查詢才能取得即時完整證據。",
    layers: model.rows.map((row) => ({
      layer_id: row.key,
      display_name: row.label,
      state: row.usability === "no_match" ? "no_match" : row.usability === "unavailable" ? "unavailable" : row.matched && row.usability === "usable" ? "available" : "limited",
      source_name: row.source,
      ...(row.sourceAgency ? { source_agency: row.sourceAgency } : {}),
      ...(row.effectivePeriod !== "未知" ? { data_updated_at: row.effectivePeriod } : {}),
      ...(row.datasetVersion ? { data_version: row.datasetVersion } : {}),
      coverage_status: row.coverage,
      caveat: `${row.result} ${row.limitation}`.trim(),
      evidence_metadata: {
        version: 1,
        usability: row.usability,
        matched: ["stale", "unavailable", "unsupported", "no_coverage"].includes(row.usability) ? null : row.matched,
        source_url: row.sourceUrl ?? null,
        query_condition: row.queryCondition ?? (model.freshness.status === "current_query" ? "查詢半徑 500 公尺；依各官方來源比對條件" : "查詢條件未保存"),
      },
    })),
  };
}

export function buildRiskQueryContext(workspace: PropertyCaseWorkspace): RiskQueryContext | null {
  const anchor = workspace.identity.anchor;
  const coordinates = anchor?.coordinates;
  if (workspace.identity.state !== "confirmed" || !anchor || !coordinates || anchor.revalidation.status !== "current") return null;
  const payload = {
    latitude: coordinates.latitude,
    longitude: coordinates.longitude,
    ...(anchor.administrative_location.city ? { city: anchor.administrative_location.city } : {}),
    ...(anchor.administrative_location.district ? { district: anchor.administrative_location.district } : {}),
    radius_m: 500 as const,
    include_layers: [...RISK_QUERY_LAYERS],
  };
  return {
    caseId: workspace.caseId,
    revision: workspace.revision,
    fingerprint: buildInputFingerprint({
      caseId: workspace.caseId,
      revision: workspace.revision,
      journeyAnchorId: anchor.journey_anchor_id,
      coordinates,
      layers: RISK_QUERY_LAYERS,
    }),
    payload,
  };
}

export function canCommitRiskResponse(current: RiskQueryContext, response: RiskQueryContext): boolean {
  return current.caseId === response.caseId && canCommitEvidence({
    currentRevision: current.revision,
    responseRevision: response.revision,
    currentFingerprint: current.fingerprint,
    responseFingerprint: response.fingerprint,
  });
}
