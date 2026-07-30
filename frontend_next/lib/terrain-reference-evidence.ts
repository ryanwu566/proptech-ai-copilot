import type { TerrainHazardLayer, TerrainRiskResult, TerrainRiskSourceTransparencyLayer } from "@/lib/api";

export type TerrainReferenceState = "available" | "partial" | "limited" | "unknown" | "not_assessed" | "unavailable" | "error" | "no_match";

export type TerrainReferenceLayer = {
  layer_id: string;
  display_name: string;
  state: TerrainReferenceState;
  source_name: string;
  source_agency?: string;
  data_updated_at?: string;
  data_version?: string;
  coverage_status: "covered" | "not_covered" | "unknown";
  caveat: string;
};

export type TerrainReferenceEvidence = {
  status: TerrainReferenceState;
  notice: string;
  summary: string;
  layers: TerrainReferenceLayer[];
  attachable: boolean;
  attachDisabledReason: string;
};

export type StoredTerrainReferenceLayerV1 = {
  layer_id: string;
  display_name: string;
  state: TerrainReferenceState;
  source_name: string;
  source_agency?: string;
  data_updated_at?: string;
  data_version?: string;
  coverage_status: "covered" | "not_covered" | "unknown";
  caveat: string;
};

export type StoredTerrainReferenceEvidenceV1 = {
  schema_version: 1;
  kind: "terrain_reference";
  status: TerrainReferenceState;
  summary: string;
  notice: string;
  layers: StoredTerrainReferenceLayerV1[];
};

export const TERRAIN_REFERENCE_NOTICE = "地勢與災害資料僅供看房風險參考，資料不足或暫時不可用不代表沒有風險。";

const BLOCKING_STATES = new Set<TerrainReferenceState>(["unavailable", "error", "not_assessed", "unknown"]);

export function buildTerrainReferenceEvidence(result?: TerrainRiskResult | null): TerrainReferenceEvidence {
  if (!result) return emptyEvidence("not_assessed", "尚未完成地勢與災害資料檢查。", "尚未有可附加的參考資料。", "尚未完成檢查，不能附加。", []);

  const layers = result.source_transparency?.layers?.map(toTransparencyLayer) ?? buildFallbackLayers(result);
  const status = overallReferenceState(result, layers);
  const attachable = layers.length > 0 && !layers.some((layer) => BLOCKING_STATES.has(layer.state));
  const summary = status === "available"
    ? "目前有可供查看的資料圖層；這些結果只作看房風險參考，不形成安全結論。"
    : status === "no_match"
      ? "目前圖層未比對到明確訊號；這不代表沒有風險。"
      : status === "partial" || status === "limited"
        ? "目前只有部分資料可用；資料涵蓋有限，不代表沒有風險。"
        : "目前資料不足或暫時不可用，不代表沒有風險。";
  const attachDisabledReason = attachable ? "" : status === "not_assessed" ? "尚未完成檢查，不能附加。" : "資料不足或暫時不可用，不能附加。";
  return { status, notice: TERRAIN_REFERENCE_NOTICE, summary, layers, attachable, attachDisabledReason };
}

export function terrainReferenceStateLabel(state: TerrainReferenceState): string {
  return {
    available: "可用",
    partial: "部分可用",
    limited: "涵蓋有限",
    unknown: "未知",
    not_assessed: "未評估",
    unavailable: "暫時不可用",
    error: "檢查失敗",
    no_match: "未命中",
  }[state];
}

function toTransparencyLayer(layer: TerrainRiskSourceTransparencyLayer): TerrainReferenceLayer {
  const state: TerrainReferenceState = layer.assessment_status === "matched"
    ? "available"
    : layer.assessment_status === "not_matched"
      ? "no_match"
      : layer.assessment_status;
  return {
    layer_id: layer.layer_id,
    display_name: layer.display_name,
    state,
    source_name: layer.source_name || "未提供來源名稱",
    source_agency: undefined,
    data_updated_at: layer.data_updated_at || undefined,
    data_version: undefined,
    coverage_status: layer.coverage_status,
    caveat: layer.caveat || TERRAIN_REFERENCE_NOTICE,
  };
}

function buildFallbackLayers(result: TerrainRiskResult): TerrainReferenceLayer[] {
  const terrain = result.terrain;
  const layers: TerrainReferenceLayer[] = [{
    layer_id: "terrain",
    display_name: "地勢",
    state: layerState(terrain.status, false, terrain.status === "available"),
    source_name: safeSourceName(terrain.source),
    source_agency: terrain.source?.agency || undefined,
    data_updated_at: terrain.source?.data_updated_at || undefined,
    data_version: terrain.source?.data_vintage || undefined,
    coverage_status: terrain.status === "unavailable" || terrain.status === "error" ? "unknown" : "covered",
    caveat: terrain.explanation || TERRAIN_REFERENCE_NOTICE,
  }];
  for (const hazard of Object.values(result.hazards)) layers.push(hazardLayer(hazard));
  return layers;
}

function hazardLayer(hazard: TerrainHazardLayer): TerrainReferenceLayer {
  return {
    layer_id: hazard.key,
    display_name: hazard.label,
    state: layerState(hazard.status, hazard.matched, hazard.status === "available" && hazard.matched),
    source_name: safeSourceName(hazard.source),
    source_agency: hazard.source?.agency || undefined,
    data_updated_at: hazard.source?.data_updated_at || undefined,
    data_version: hazard.source?.data_vintage || undefined,
    coverage_status: hazard.status === "unavailable" || hazard.status === "error" ? "unknown" : hazard.matched ? "covered" : "not_covered",
    caveat: hazard.explanation || TERRAIN_REFERENCE_NOTICE,
  };
}

function layerState(status: string, matched: boolean, available: boolean): TerrainReferenceState {
  if (status === "error") return "error";
  if (status === "unavailable") return "unavailable";
  if (status === "skipped") return "not_assessed";
  if (status === "limited") return "limited";
  if (available && matched) return "available";
  if (status === "available" && !matched) return "no_match";
  return "unknown";
}

function overallReferenceState(result: TerrainRiskResult, layers: TerrainReferenceLayer[]): TerrainReferenceState {
  if (result.data_quality.status === "unavailable") return "unavailable";
  const distinctStates = new Set(layers.map((layer) => layer.state));
  if (distinctStates.size === 1 && layers.length > 0) return layers[0].state;
  if (layers.some((layer) => layer.state === "error")) return "error";
  if (layers.some((layer) => layer.state === "unavailable")) return "unavailable";
  if (layers.some((layer) => layer.state === "not_assessed" || layer.state === "unknown")) return "unknown";
  if (layers.some((layer) => layer.state === "limited")) return "limited";
  if (layers.some((layer) => layer.state === "partial")) return "partial";
  if (layers.length > 0 && layers.every((layer) => layer.state === "no_match")) return "no_match";
  if (layers.some((layer) => layer.state === "no_match")) return "no_match";
  return "available";
}

function safeSourceName(source: TerrainRiskResult["terrain"]["source"]): string {
  return source?.agency || source?.name || "未提供來源名稱";
}

function emptyEvidence(status: TerrainReferenceState, summary: string, reason: string, attachDisabledReason: string, layers: TerrainReferenceLayer[]): TerrainReferenceEvidence {
  return { status, notice: TERRAIN_REFERENCE_NOTICE, summary, layers, attachable: false, attachDisabledReason: attachDisabledReason || reason };
}

const STORED_STATES = new Set<TerrainReferenceState>(["available", "partial", "limited", "no_match"]);
const EVIDENCE_KEYS = new Set(["status", "notice", "summary", "layers", "attachable", "attachDisabledReason"]);
const TERRAIN_REFERENCE_KEYS = new Set(["schema_version", "kind", "status", "summary", "notice", "layers"]);
const TERRAIN_REFERENCE_LAYER_KEYS = new Set(["layer_id", "display_name", "state", "source_name", "source_agency", "data_updated_at", "data_version", "coverage_status", "caveat"]);
const UNSAFE_REFERENCE_TEXT = /(address|latitude|longitude|resolved_location|coordinate|distance_m|raw|geometry|tile[_ ]?id|map_layers|source_url|https?:\/\/|token|credential|api[_ ]?key|sql|stack[_ ]?trace|risk_factors|recommended_checks)/i;

function safeStoredText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0 && !UNSAFE_REFERENCE_TEXT.test(value);
}

function safeOptionalMetadata(value: unknown): value is string {
  return safeStoredText(value) && value.trim().toLowerCase() !== "unknown";
}

function validReferenceState(value: unknown): value is TerrainReferenceState {
  return typeof value === "string" && ["available", "partial", "limited", "unknown", "not_assessed", "unavailable", "error", "no_match"].includes(value);
}

function validCoverageStatus(value: unknown): value is StoredTerrainReferenceLayerV1["coverage_status"] {
  return value === "covered" || value === "not_covered" || value === "unknown";
}

function storedLayerFromEvidence(layer: TerrainReferenceLayer): StoredTerrainReferenceLayerV1 | null {
  if (!STORED_STATES.has(layer.state) || !safeStoredText(layer.layer_id) || !safeStoredText(layer.display_name) || !safeStoredText(layer.source_name) || !safeStoredText(layer.caveat) || !validCoverageStatus(layer.coverage_status)) return null;
  const stored: StoredTerrainReferenceLayerV1 = {
    layer_id: layer.layer_id.trim(),
    display_name: layer.display_name.trim(),
    state: layer.state,
    source_name: layer.source_name.trim(),
    coverage_status: layer.coverage_status,
    caveat: layer.caveat.trim(),
  };
  if (layer.source_agency !== undefined) {
    if (!safeOptionalMetadata(layer.source_agency)) return null;
    stored.source_agency = layer.source_agency.trim();
  }
  if (layer.data_updated_at !== undefined) {
    if (!safeOptionalMetadata(layer.data_updated_at)) return null;
    stored.data_updated_at = layer.data_updated_at.trim();
  }
  if (layer.data_version !== undefined) {
    if (!safeOptionalMetadata(layer.data_version)) return null;
    stored.data_version = layer.data_version.trim();
  }
  return stored;
}

export function toStoredTerrainReferenceEvidence(evidence: TerrainReferenceEvidence): StoredTerrainReferenceEvidenceV1 | null {
  if (!evidence || typeof evidence !== "object" || [...Object.keys(evidence)].some((key) => !EVIDENCE_KEYS.has(key)) || !evidence.attachable || !STORED_STATES.has(evidence.status) || !safeStoredText(evidence.summary) || !safeStoredText(evidence.notice) || !Array.isArray(evidence.layers) || evidence.layers.length === 0) return null;
  if (evidence.layers.some((layer) => !layer || typeof layer !== "object" || [...Object.keys(layer)].some((key) => !TERRAIN_REFERENCE_LAYER_KEYS.has(key)))) return null;
  const layers = evidence.layers.map(storedLayerFromEvidence);
  if (layers.some((layer): layer is null => layer === null)) return null;
  return { schema_version: 1, kind: "terrain_reference", status: evidence.status, summary: evidence.summary.trim(), notice: evidence.notice.trim(), layers: layers as StoredTerrainReferenceLayerV1[] };
}

export function normalizeStoredTerrainReferenceEvidence(value: unknown): StoredTerrainReferenceEvidenceV1 | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const record = value as Record<string, unknown>;
  if ([...Object.keys(record)].some((key) => !TERRAIN_REFERENCE_KEYS.has(key)) || record.schema_version !== 1 || record.kind !== "terrain_reference" || !STORED_STATES.has(record.status as TerrainReferenceState) || !safeStoredText(record.summary) || !safeStoredText(record.notice) || !Array.isArray(record.layers) || record.layers.length === 0) return undefined;
  const layers: StoredTerrainReferenceLayerV1[] = [];
  for (const valueLayer of record.layers) {
    if (!valueLayer || typeof valueLayer !== "object" || Array.isArray(valueLayer)) return undefined;
    const layer = valueLayer as Record<string, unknown>;
    if ([...Object.keys(layer)].some((key) => !TERRAIN_REFERENCE_LAYER_KEYS.has(key)) || !STORED_STATES.has(layer.state as TerrainReferenceState) || !safeStoredText(layer.layer_id) || !safeStoredText(layer.display_name) || !safeStoredText(layer.source_name) || !safeStoredText(layer.caveat) || !validCoverageStatus(layer.coverage_status)) return undefined;
    const normalized: StoredTerrainReferenceLayerV1 = { layer_id: layer.layer_id.trim(), display_name: layer.display_name.trim(), state: layer.state as TerrainReferenceState, source_name: layer.source_name.trim(), coverage_status: layer.coverage_status, caveat: layer.caveat.trim() };
    for (const key of ["source_agency", "data_updated_at", "data_version"] as const) {
      if (layer[key] !== undefined) {
        if (!safeOptionalMetadata(layer[key])) return undefined;
        normalized[key] = (layer[key] as string).trim();
      }
    }
    layers.push(normalized);
  }
  return { schema_version: 1, kind: "terrain_reference", status: record.status as TerrainReferenceState, summary: (record.summary as string).trim(), notice: (record.notice as string).trim(), layers };
}

export function migrateLegacyTerrainReference(result?: TerrainRiskResult | null): StoredTerrainReferenceEvidenceV1 | undefined {
  const evidence = buildTerrainReferenceEvidence(result);
  return toStoredTerrainReferenceEvidence(evidence) ?? undefined;
}
