import type { CommuteAddressLookupResult, LocationInsightResult, MarketResult, TerrainRiskResult } from "@/lib/api";

export type JourneyPropertyContext = {
  city?: string;
  district?: string;
  road?: string;
  addressSummary?: string;
  buildingType?: string;
  areaPing?: number;
  buildingAgeYears?: number;
  floor?: number;
  askingPriceWan?: number;
  sourceLabel: string;
  selectionStatus: "not_selected" | "selected" | "partial";
};

export type LocationMarketToolId = "commute" | "terrain" | "market";
export type LocationMarketDisplayStatus = "not_started" | "loading" | "available" | "no_data" | "unavailable" | "partial" | "unknown" | "stale";

export type AmenityCategoryModel = {
  id: string;
  label: string;
  count: number | null;
  status: LocationMarketDisplayStatus;
  statusLabel: string;
};

export type LocationMarketStatusItem = {
  id: "location" | LocationMarketToolId;
  label: string;
  status: LocationMarketDisplayStatus;
  statusLabel: string;
  summary: string;
};

const STATUS_LABELS: Record<LocationMarketDisplayStatus, string> = {
  not_started: "尚未分析",
  loading: "分析中",
  available: "資料可用",
  no_data: "目前資料不足",
  unavailable: "資料暫時無法取得",
  partial: "部分資料可用",
  unknown: "尚未評估",
  stale: "資料更新時間較早",
};

function safeText(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function safeNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : undefined;
}

export function getSafeJourneyPropertyContext(input: Partial<JourneyPropertyContext> | null | undefined): JourneyPropertyContext {
  const city = safeText(input?.city);
  const district = safeText(input?.district);
  const road = safeText(input?.road);
  const addressSummary = safeText(input?.addressSummary);
  const hasLocation = Boolean(city || district || road || addressSummary);
  const requestedStatus = input?.selectionStatus;
  const selectionStatus = requestedStatus === "selected" && hasLocation ? "selected" : hasLocation ? "partial" : "not_selected";
  return {
    ...(city ? { city } : {}),
    ...(district ? { district } : {}),
    ...(road ? { road } : {}),
    ...(addressSummary ? { addressSummary } : {}),
    ...(safeText(input?.buildingType) ? { buildingType: safeText(input?.buildingType) } : {}),
    ...(safeNumber(input?.areaPing) !== undefined ? { areaPing: safeNumber(input?.areaPing) } : {}),
    ...(safeNumber(input?.buildingAgeYears) !== undefined ? { buildingAgeYears: safeNumber(input?.buildingAgeYears) } : {}),
    ...(safeNumber(input?.floor) !== undefined ? { floor: safeNumber(input?.floor) } : {}),
    ...(safeNumber(input?.askingPriceWan) !== undefined ? { askingPriceWan: safeNumber(input?.askingPriceWan) } : {}),
    sourceLabel: safeText(input?.sourceLabel) ?? "使用者輸入",
    selectionStatus,
  };
}

export function addVisitedLocationMarketTool(visited: readonly LocationMarketToolId[], tool: LocationMarketToolId): LocationMarketToolId[] {
  return visited.includes(tool) ? [...visited] : [...visited, tool];
}

function locationStatus(result: LocationInsightResult | null | undefined): LocationMarketDisplayStatus {
  if (!result) return "not_started";
  if (result.data_quality.status === "unavailable") return "unavailable";
  if (result.data_quality.status === "limited") return "partial";
  return "available";
}

function commuteStatus(result: CommuteAddressLookupResult | null | undefined, status: LocationMarketDisplayStatus): LocationMarketDisplayStatus {
  if (status === "loading") return status;
  if (!result) return status;
  if (result.status === "resolved") return "available";
  if (result.status === "unresolved") return "no_data";
  return "unavailable";
}

function terrainStatus(result: TerrainRiskResult | null | undefined, status: LocationMarketDisplayStatus): LocationMarketDisplayStatus {
  if (status === "loading") return status;
  if (!result) return status;
  if (result.data_quality.status === "unavailable") return "unavailable";
  if (result.data_quality.status === "limited") return "partial";
  if (result.overall.level === "unknown") return "unknown";
  return "available";
}

function marketStatus(result: MarketResult | null | undefined, status: LocationMarketDisplayStatus): LocationMarketDisplayStatus {
  if (status === "loading") return status;
  if (!result) return status;
  if (result.data_status === "no_data") return "no_data";
  if (result.data_status !== "available") return "unavailable";
  if (result.coverage_status === "partial") return "partial";
  const freshness = (result as MarketResult & { freshness_status?: string }).freshness_status;
  if (freshness === "stale") return "stale";
  return "available";
}

export function buildAmenityCategoryModel(result: LocationInsightResult | null | undefined): AmenityCategoryModel[] {
  const summary = result?.poi_summary;
  const status = locationStatus(result);
  const categories: Array<[string, string, keyof LocationInsightResult["poi_summary"]]> = [
    ["transit", "交通", "transit_count"],
    ["school", "學校", "school_count"],
    ["park", "公園", "park_count"],
    ["medical", "醫療", "medical_count"],
    ["convenience", "商圈／購物", "convenience_count"],
  ];
  return categories.map(([id, label, key]) => ({
    id,
    label,
    count: status === "unavailable" || status === "not_started" || status === "unknown" ? null : typeof summary?.[key] === "number" ? summary[key] : null,
    status,
    statusLabel: STATUS_LABELS[status],
  }));
}

export function buildLocationMarketStatusItems(input: {
  locationResult?: LocationInsightResult | null;
  commuteResult?: CommuteAddressLookupResult | null;
  commuteDisplayStatus?: LocationMarketDisplayStatus;
  terrainResult?: TerrainRiskResult | null;
  terrainDisplayStatus?: LocationMarketDisplayStatus;
  marketResult?: MarketResult | null;
  marketDisplayStatus?: LocationMarketDisplayStatus;
}): LocationMarketStatusItem[] {
  const statuses = {
    location: locationStatus(input.locationResult),
    commute: commuteStatus(input.commuteResult, input.commuteDisplayStatus ?? "not_started"),
    terrain: terrainStatus(input.terrainResult, input.terrainDisplayStatus ?? "not_started"),
    market: marketStatus(input.marketResult, input.marketDisplayStatus ?? "not_started"),
  } satisfies Record<LocationMarketStatusItem["id"], LocationMarketDisplayStatus>;
  const summaries: Record<LocationMarketStatusItem["id"], string> = {
    location: statuses.location === "not_started" ? "輸入地點後按下分析" : "位置洞察與生活機能摘要",
    commute: statuses.commute === "not_started" ? "需要手動開啟通勤查詢" : "通勤資訊僅供生活安排參考",
    terrain: statuses.terrain === "not_started" ? "需要手動開啟地形分析" : "保留各風險圖層的獨立狀態",
    market: statuses.market === "not_started" ? "需要手動查詢官方市場資料" : "市場資料僅供研究參考",
  };
  return ([
    ["location", "生活機能", statuses.location],
    ["commute", "通勤", statuses.commute],
    ["terrain", "地形與環境", statuses.terrain],
    ["market", "市場資料", statuses.market],
  ] as const).map(([id, label, status]) => ({ id, label, status, statusLabel: STATUS_LABELS[status], summary: summaries[id] }));
}

export function buildLocationMarketSnapshot(items: readonly LocationMarketStatusItem[]) {
  return {
    title: "地點與市場資料概況",
    description: "各項資料彼此獨立，僅整理目前已知狀態，不代表綜合評價。",
    evidenceAvailable: items.some((item) => ["available", "partial", "stale", "no_data", "unavailable"].includes(item.status)),
    items: items.map((item) => ({ id: item.id, label: item.label, status: item.status, statusLabel: item.statusLabel })),
  };
}

export function locationMarketStatusLabel(status: LocationMarketDisplayStatus): string {
  return STATUS_LABELS[status];
}
