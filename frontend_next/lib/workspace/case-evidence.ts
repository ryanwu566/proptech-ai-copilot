import type { PropertyCaseWorkspace, WorkspaceSection } from "./workspace-model";
import type { RiskEvidenceKey } from "./risk-evidence-model";
// @ts-expect-error Native TS runner extension.
import { RISK_QUERY_LAYERS } from "./risk-evidence-model.ts";
// @ts-expect-error Native TS runner extension.
import { safePublicEvidenceUrl } from "../terrain-reference-evidence.ts";

export type EvidenceStatus = "available" | "limited" | "not_run" | "unavailable" | "unsupported" | "no_coverage" | "no_match" | "stale" | "insufficient";
export type GapReason = "missing_input" | "not_run" | "unavailable" | "unsupported" | "no_coverage" | "stale" | "insufficient" | "not_preserved";
export type EvidenceFreshness = {
  origin: "saved_snapshot";
  inputRelation: "matches" | "stale" | "unknown";
  timeRelation: "within_source_policy" | "stale" | "unknown";
  checkedAt: string | null;
  sourceUpdatedAt: string | null;
};
export type EvidenceField<T extends string | number> = {
  id: string; label: string; domain: WorkspaceSection; unit: string;
  value: T | null; historicalValue: T | null; status: EvidenceStatus;
  freshness: EvidenceFreshness; missingReason: GapReason | null;
  source: string; limitation: string; nextAction: string; sourceReason?: string | null;
};
export type EvidenceGap = {
  caseId: string; domain: WorkspaceSection; id: string; item: string; reason: GapReason;
  impact: string; nextAction: string; href: string;
};
export type EvidenceSource = {
  id: string; name: string; url: string | null; checkedAt: string | null; updatedAt: string | null;
  period: string | null; version: string | null; coverage: string; queryCondition: string; limitation: string;
};
type Numeric = EvidenceField<number>;
type Text = EvidenceField<string>;
export type CaseEvidenceModel = {
  schemaVersion: 1; caseId: string; snapshotToken: string; title: string; displayAddress: string; savedAt: string;
  identity: { state: PropertyCaseWorkspace["identity"]["state"]; scope: "journey_browser_anchor" | "unconfirmed"; limitation: string };
  price: {
    asking: Numeric; active: Numeric; basis: Text; area: Numeric; marketMedianTotal: Numeric; marketMedianUnit: Numeric;
    marketP25: Numeric; marketP75: Numeric; sampleSize: Numeric; scope: Text; period: Text; valuationEstimate: Numeric; valuationLow: Numeric; valuationHigh: Numeric; comparables: Text;
  };
  location: { radius: Numeric; coverage: Text; transit: Numeric; convenience: Numeric; school: Numeric; park: Numeric; medical: Numeric; riskFacility: Numeric; poiDetails: Text; population: Numeric; demographicsContext: Text };
  commute: { duration: Numeric; distance: Numeric; destination: Text; mode: Text; transitContext: Text };
  risk: Array<{ key: RiskEvidenceKey; evidence: Text; matched: boolean | null; coverage: string; version: string | null; queryCondition: string }>;
  finance: {
    price: Numeric; basis: Text; downPaymentRatio: Numeric; downPayment: Numeric; principal: Numeric; interestRate: Numeric; term: Numeric; gracePeriod: Numeric;
    monthlyPayment: Numeric; gracePayment: Numeric; postGracePayment: Numeric; knownMonthlyHousing: Numeric; monthlyIncome: Numeric; affordability: Text; burdenRatio: Numeric;
    managementRate: Numeric; repairRate: Numeric; homeTaxRate: Numeric; landTaxRate: Numeric; annualInsurance: Numeric;
    missingCosts: Text; tax: Text; breakdown: Array<{ key: string; amount: Numeric }>;
  };
  gaps: EvidenceGap[]; sources: EvidenceSource[];
};

// @ts-expect-error Native TS runner extension.
import { PRICE_BASIS_LABELS, EVIDENCE_STATUS_LABELS } from "./evidence-labels.ts";
// @ts-expect-error Native TS runner extension.
import { financePriceSourceLabel } from "../finance-price-provenance.ts";
const ACTIONS: { [D in WorkspaceSection]: string } = { overview: "回到物件總覽確認案件條件", market: "回到價格與市場，明確執行查詢確認證據", location: "回到區位與通勤，確認條件後明確查詢", risk: "回到風險與環境，核對官方來源與現場條件", finance: "回到資金與成本，補齊假設後明確計算" };
const riskLabels: { [K in RiskEvidenceKey]: string } = { terrain: "地形／坡度", flood: "淹水", landslide: "山崩", debris_flow: "土石流", liquefaction: "土壤液化", geological_sensitivity: "地質敏感區", active_fault: "活動斷層／人工查證" };
function number(value: unknown): number | null { return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : null; }
function text(value: unknown): string | null { return typeof value === "string" && value.trim() ? value.trim().slice(0, 4000) : null; }
export function safeEvidenceUrl(value: unknown): string | null {
  return safePublicEvidenceUrl(value);
}
type FieldOptions = Partial<Pick<EvidenceField<string>, "status" | "source" | "limitation" | "missingReason" | "sourceReason" | "nextAction">> & { checkedAt?: string | null; updatedAt?: string | null; inputRelation?: EvidenceFreshness["inputRelation"]; timeRelation?: EvidenceFreshness["timeRelation"] };
function field<T extends string | number>(id: string, label: string, domain: WorkspaceSection, value: T | null, unit = "", options: FieldOptions = {}): EvidenceField<T> {
  const status = options.status ?? (value === null ? "not_run" : "limited");
  const stale = status === "stale" || options.inputRelation === "stale" || options.timeRelation === "stale";
  const unavailable = ["unavailable", "unsupported", "no_coverage", "not_run", "insufficient"].includes(status);
  const primary = stale || unavailable ? null : value;
  const missingReason = options.missingReason ?? (stale ? "stale" : primary === null ? ["not_run", "unavailable", "unsupported", "no_coverage", "insufficient"].includes(status) ? status as GapReason : "not_preserved" : null);
  return { id, label, domain, unit, value: primary, historicalValue: stale ? value : null, status: stale ? "stale" : status,
    freshness: { origin: "saved_snapshot", inputRelation: options.inputRelation ?? "unknown", timeRelation: options.timeRelation ?? "unknown", checkedAt: text(options.checkedAt), sourceUpdatedAt: text(options.updatedAt) },
    missingReason, ...(options.sourceReason ? { sourceReason: options.sourceReason } : {}), source: options.source ?? "來源未保存", limitation: options.limitation ?? "僅依已儲存摘要；不是即時重新查詢。", nextAction: options.nextAction ?? ACTIONS[domain] };
}
function status(value: string | undefined): EvidenceStatus { return value === "not_started" ? "not_run" : value === "usable" ? "available" : value === "unverified" ? "limited" : value && value in EVIDENCE_STATUS_LABELS ? value as EvidenceStatus : "limited"; }

/** Pure projection of the current normalized workspace contracts; no provider calls or calculators. */
export function projectCaseEvidence(workspace: PropertyCaseWorkspace): CaseEvidenceModel {
  const validIdentity = workspace.identity.state === "confirmed";
  const inputRelation = validIdentity ? "matches" : workspace.identity.state === "revalidation_required" || workspace.identity.state === "conflict" ? "stale" : "unknown";
  const market = workspace.marketPrice.market;
  const result = market.result;
  const marketOptions: FieldOptions = { status: status(market.status), inputRelation, source: workspace.marketPrice.source.sourceName ?? "市場來源未保存", updatedAt: workspace.marketPrice.source.updatedAt, timeRelation: ["fresh", "current"].includes(result?.freshness_status ?? "") ? "within_source_policy" : ["stale", "failed_latest_update", "update_available"].includes(result?.freshness_status ?? "") ? "stale" : "unknown", limitation: text(result?.caveat) ?? "區域成交分布，不代表目標物件公平價值。" };
  const valuation = workspace.marketPrice.valuation;
  const valuationOptions: FieldOptions = { status: status(valuation.status), inputRelation, source: "成交資料推估摘要", limitation: "依成交資料推估，非正式估價或銀行鑑價；可比明細未保存。" };
  const contextOptions: FieldOptions = { status: "limited", inputRelation, source: "使用者保存的案件條件", limitation: "開價与基準價格為案件條件，不等同成交價。" };
  const price: CaseEvidenceModel["price"] = {
    asking: field("price-asking", "開價", "market", number(workspace.assumptions.askingPriceWan), "萬元", contextOptions),
    active: field("price-active", "目前選定價格", "market", number(validIdentity ? workspace.assumptions.activePriceWan : undefined), "萬元", contextOptions),
    basis: field("price-basis", "價格基準", "market", PRICE_BASIS_LABELS[workspace.assumptions.activePriceBasis], "", contextOptions),
    area: field("property-area", "面積", "overview", number(workspace.assumptions.areaPing), "坪", contextOptions),
    marketMedianTotal: field("market-total", "市場成交總價中位數", "market", number(result?.median_total_price), "萬元", marketOptions),
    marketMedianUnit: field("market-unit", "市場成交單價中位數", "market", number(result?.median_unit_price_per_ping), "萬元／坪", marketOptions),
    marketP25: field("market-p25", "市場單價分布 P25", "market", number(result?.p25_unit_price_per_ping), "萬元／坪", marketOptions),
    marketP75: field("market-p75", "市場單價分布 P75", "market", number(result?.p75_unit_price_per_ping), "萬元／坪", marketOptions),
    sampleSize: field("market-samples", "市場樣本數", "market", number(result?.effective_sample_count), "筆", marketOptions),
    scope: field("market-scope", "實際市場範圍", "market", text(market.scopeLabel), "", marketOptions),
    period: field("market-period", "成交資料期間", "market", text(workspace.marketPrice.source.effectivePeriod), "", marketOptions),
    valuationEstimate: field("valuation-estimate", "成交資料推估中點", "market", number(valuation.result?.estimate_total_price), "萬元", valuationOptions),
    valuationLow: field("valuation-low", "成交資料推估下界", "market", number(valuation.result?.price_range?.low), "萬元", valuationOptions),
    valuationHigh: field("valuation-high", "成交資料推估上界", "market", number(valuation.result?.price_range?.high), "萬元", valuationOptions),
    comparables: field<string>("valuation-comparables", "可比成交明細", "market", null, "", { ...valuationOptions, status: "limited", missingReason: "not_preserved", limitation: "已儲存快照未保存可比成交明細；不能從摘要重建。" }),
  };
  const location = workspace.location;
  const insight = location.insight;
  const locationOptions: FieldOptions = { inputRelation: "unknown", status: !insight ? "not_run" : insight.data_quality?.status === "unavailable" ? "unavailable" : "limited", source: "已保存區位摘要（個別 POI 來源未保存）", limitation: "POI 明細已移除；計數受查詢半徑、類別與來源覆蓋限制。" };
  const poi = insight?.poi_summary;
  const demographic = insight?.demographics;
  const locationModel: CaseEvidenceModel["location"] = {
    radius: field("poi-radius", "POI 查詢半徑", "location", number(insight?.radius_m), "公尺", locationOptions),
    coverage: field("poi-coverage", "POI 覆蓋與限制", "location", insight ? (insight.data_quality?.missing_sources?.length ? `未取得來源：${insight.data_quality.missing_sources.join("、")}` : "來源覆蓋未完整保存") : null, "", locationOptions),
    transit: field("poi-transit", "交通設施", "location", number(poi?.transit_count), "處", locationOptions),
    convenience: field("poi-convenience", "生活便利設施", "location", number(poi?.convenience_count), "處", locationOptions),
    school: field("poi-school", "學校", "location", number(poi?.school_count), "處", locationOptions),
    park: field("poi-park", "公園", "location", number(poi?.park_count), "處", locationOptions),
    medical: field("poi-medical", "醫療設施", "location", number(poi?.medical_count), "處", locationOptions),
    riskFacility: field("poi-risk", "需留意設施", "location", number(poi?.risk_facility_count), "處", { ...locationOptions,
      status: !insight ? "not_run" : insight.risk_facility_evidence?.status === "no_match" ? "no_match" : ["available", "unknown"].includes(insight.risk_facility_evidence?.status ?? "") ? "limited" : insight.risk_facility_evidence?.status === "no_coverage" ? "no_coverage" : "unavailable",
      inputRelation: inputRelation === "stale" ? "stale" : "unknown", source: insight?.risk_facility_evidence?.source ?? "設施來源未保存", checkedAt: insight?.risk_facility_evidence?.checked_at,
      sourceReason: insight?.risk_facility_evidence?.reason,
      limitation: `${insight?.risk_facility_evidence?.limitation ?? "未知涵蓋不等於零處設施。"} 物件關聯未完整保存。`, }),
    poiDetails: field<string>("poi-details", "POI 明細与個別來源", "location", null, "", { ...locationOptions, missingReason: "not_preserved" }),
    population: field("demographics-population", "行政區人口（次要脈絡）", "location", demographic?.status === "available" ? number(demographic.total_population) : null, "人", { ...locationOptions, source: demographic?.status === "available" ? demographic.source_provider : "人口資料來源未保存", status: demographic?.status === "available" ? "limited" : demographic ? "insufficient" : "not_run", limitation: "行政區域統計，不代表本物件住戶特徵。" }),
    demographicsContext: field("demographics-context", "人口資料範圍", "location", demographic?.status === "available" ? `${location.property.village.name ?? "行政區"}；${demographic.last_month ?? "期間未保存"}` : null, "", { ...locationOptions, limitation: "僅為行政區次要脈絡；不能推論本物件住戶。" }),
  };
  const route = location.routeEvidence;
  const validRoute = validIdentity && route?.status === "resolved" && route.source === "google_routes" && !route.partial && !route.fallback;
  const routeOptions: FieldOptions = { status: inputRelation === "stale" || location.routeInvalidated ? "stale" : !route ? "not_run" : validRoute ? "limited" : route.status === "unavailable" || route.status === "unresolved" ? "unavailable" : "insufficient", inputRelation: location.routeInvalidated ? "stale" : inputRelation, checkedAt: route?.checked_at, source: route?.source === "google_routes" ? "Google Routes 已保存路線" : "路線來源未保存", limitation: "已保存的路線估算，不保證目前路況；出發時間與交通時段條件未保存。" };
  const transit = location.transitContext;
  const commute: CaseEvidenceModel["commute"] = {
    duration: field("commute-duration", "目的地通勤時間", "location", validRoute ? number(route.duration_min) : null, "分鐘", routeOptions),
    distance: field("commute-distance", "路線距離", "location", validRoute ? number(route.distance_m) : null, "公尺", routeOptions),
    destination: field("commute-destination", "通勤目的地", "location", text(route?.destination.address), "", routeOptions),
    mode: field("commute-mode", "交通方式", "location", route ? { driving: "開車", transit: "大眾運輸", walking: "步行" }[route.mode] : null, "", routeOptions),
    transitContext: field("transit-context", "次要大眾運輸資料", "location", transit?.status === "resolved" ? text(transit.station_name) : null, "", { status: !transit ? "not_run" : transit.status === "resolved" ? "limited" : "unavailable", source: "TDX 周邊資料", updatedAt: transit?.source_updated_at, limitation: "次要周邊資料獨立於 Google Routes 路線；無法取得不使有效路線失效。" }),
  };
  const risk = RISK_QUERY_LAYERS.map((key): CaseEvidenceModel["risk"][number] => {
    const row = workspace.risk?.rows.find((item) => item.key === key);
    const unsupported = key === "active_fault" && (!row || row.usability === "unsupported");
    return { key, evidence: field(`risk-${key}`, riskLabels[key], "risk", text(row?.result), "", { status: row ? status(row.usability) : unsupported ? "unsupported" : "not_run", inputRelation, checkedAt: workspace.risk?.freshness.checkedAt, updatedAt: row?.sourceUpdatedAt, source: row?.source ?? "來源摘要未保存", limitation: row?.limitation ?? (unsupported ? "自動比對未支援；需至官方圖台人工查證。" : "尚未取得此項證據；不能推論安全。"), nextAction: row?.nextVerification ?? ACTIONS.risk }), matched: row?.matched ?? null, coverage: row?.coverage ?? "unknown", version: row?.datasetVersion ?? null, queryCondition: row?.queryCondition ?? "查詢半徑與條件未保存" };
  });
  const finance = workspace.finance;
  const financeOptions: FieldOptions = { status: finance?.freshness.status === "stale" ? "stale" : finance?.calculation.query === "failed" ? "unavailable" : finance?.calculation.usability && ["unavailable", "unsupported", "no_coverage"].includes(finance.calculation.usability) ? status(finance.calculation.usability) : finance?.calculation.completeness === "blocked" || finance?.calculation.completeness === "insufficient" ? "insufficient" : finance?.freshness.status === "not_calculated" || !finance ? "not_run" : "limited", inputRelation: finance?.freshness.status === "stale" ? "stale" : inputRelation, checkedAt: finance?.freshness.calculatedAt, source: "已保存財務試算", limitation: "依已保存假設試算，非銀行核貸；已知每月住宅支出已含保存的房貸，不能再加一次。" };
  const n = (id: string, label: string, value: unknown, unit: string) => field(`finance-${id}`, label, "finance", number(value), unit, financeOptions);
  const holding = finance?.holding.assumptions;
  const financeModel: CaseEvidenceModel["finance"] = {
    price: n("price", "試算採用價格", finance?.loan.propertyPriceWan ?? finance?.savedAssumptions?.amountWan, "萬元"),
    basis: field("finance-basis", "試算價格基準", "finance", finance ? financePriceSourceLabel(finance.priceSource) : null, "", financeOptions),
    downPaymentRatio: n("down-ratio", "自備款比例", finance?.loan.downPaymentRatio === null || finance?.loan.downPaymentRatio === undefined ? null : finance.loan.downPaymentRatio * 100, "%"),
    downPayment: n("down", "自備款金額", finance?.loan.downPaymentWan, "萬元"), principal: n("principal", "貸款本金", finance?.loan.principalWan, "萬元"), interestRate: n("rate", "年利率", finance?.loan.annualInterestRate, "%"), term: n("term", "貸款年限", finance?.loan.loanYears, "年"), gracePeriod: n("grace", "寬限期", finance?.loan.gracePeriodYears, "年"),
    monthlyPayment: n("payment", "房貸月付", finance?.loan.monthlyPaymentTwd, "元／月"), gracePayment: n("grace-payment", "寬限期月付（適用時）", finance?.loan.gracePeriodMonthlyPaymentTwd, "元／月"), postGracePayment: n("post-grace", "寬限期後月付（適用時）", finance?.loan.postGraceMonthlyPaymentTwd, "元／月"),
    knownMonthlyHousing: n("housing", "已知每月住宅支出（含房貸）", finance?.comparison.knownRecurringMonthlyTwd, "元／月"), monthlyIncome: n("income", "月收入", finance?.loan.monthlyIncomeWan ?? holding?.monthlyIncomeWan, "萬元／月"),
    affordability: field("finance-affordability", "負擔能力評估狀態", "finance", finance?.affordability.status === "assessed" ? "依保存假設已評估" : finance ? "未評估（收入或假設不足）" : null, "", financeOptions), burdenRatio: n("burden", "保存的負擔比例", finance?.affordability.ratio == null ? null : finance.affordability.ratio * 100, "%"),
    managementRate: n("management", "管理費假設", holding?.managementFeePerPingTwd, "元／坪／月"), repairRate: n("repair", "修繕準備假設", holding?.repairReservePerPingTwd, "元／坪／月"), homeTaxRate: n("home-tax", "房屋稅率假設", holding?.annualHomeTaxRatePercent, "%"), landTaxRate: n("land-tax", "土地稅率假設", holding?.annualLandTaxRatePercent, "%"), annualInsurance: n("insurance", "年保險假設", holding?.annualInsuranceTwd, "元／年"),
    missingCosts: field("finance-missing-costs", "未納入或未估算成本", "finance", finance?.missingCosts.length ? finance.missingCosts.join("；") : null, "", financeOptions),
    tax: field("finance-tax", "稅務補充檢查", "finance", finance?.tax.summary ? ({ eligible: "初步符合條件", manual_review: "需人工複核", not_eligible: "初步不符合條件" }[finance.tax.summary.outcome]) : null, "", { ...financeOptions, status: finance?.tax.query === "failed" ? "unavailable" : finance?.tax.query === "succeeded" ? financeOptions.status : "not_run" }),
    breakdown: (finance?.holding.breakdown ?? []).map((row) => ({ key: row.key, amount: field(`finance-cost-${row.key}`, row.label, "finance", row.status === "estimated" ? number(row.monthlyAmountTwd) : null, "元／月", { ...financeOptions, ...(row.status === "unestimated" ? { missingReason: "missing_input" as const } : {}) }) })),
  };
  const sources: EvidenceSource[] = [
    { id: "identity", name: "瀏覽器案件關聯錨點", url: null, checkedAt: location.property.checkedAt, updatedAt: null, period: null, version: null, coverage: "瀏覽器本機", queryCondition: "地址與定位關聯", limitation: "不代表地號、建物、所有權或法律身分確認。" },
    { id: "market", name: marketOptions.source!, url: null, checkedAt: null, updatedAt: marketOptions.updatedAt ?? null, period: workspace.marketPrice.source.effectivePeriod, version: null, coverage: text(result?.coverage_status) ?? "unknown", queryCondition: text(market.scopeLabel) ?? "市場查詢條件未保存", limitation: marketOptions.limitation! },
    { id: "valuation", name: "成交資料推估", url: null, checkedAt: null, updatedAt: null, period: null, version: null, coverage: "可比明細未保存", queryCondition: "僅保留可採用推估摘要", limitation: valuationOptions.limitation! },
    { id: "location", name: locationOptions.source!, url: null, checkedAt: null, updatedAt: null, period: null, version: null, coverage: locationModel.coverage.value ?? "unknown", queryCondition: locationModel.radius.value === null ? "半徑未保存" : `半徑 ${locationModel.radius.value} 公尺`, limitation: locationOptions.limitation! },
    { id: "commute", name: routeOptions.source!, url: null, checkedAt: routeOptions.checkedAt ?? null, updatedAt: null, period: null, version: null, coverage: "保存路線", queryCondition: `${commute.destination.value ?? "目的地未保存"}；${commute.mode.value ?? "方式未保存"}`, limitation: routeOptions.limitation! },
    { id: "finance", name: "保存的財務試算", url: null, checkedAt: finance?.freshness.calculatedAt ?? null, updatedAt: null, period: null, version: null, coverage: "依假設試算", queryCondition: "採用各項保存假設，未重新計算", limitation: financeOptions.limitation! },
    ...risk.map((item): EvidenceSource => ({ id: item.evidence.id, name: item.evidence.source, url: safeEvidenceUrl(workspace.risk?.rows.find((row) => row.key === item.key)?.sourceUrl), checkedAt: item.evidence.freshness.checkedAt, updatedAt: item.evidence.freshness.sourceUpdatedAt, period: null, version: item.version, coverage: item.coverage, queryCondition: item.queryCondition, limitation: item.evidence.limitation })),
  ];
  const model: CaseEvidenceModel = { schemaVersion: 1, caseId: workspace.caseId, snapshotToken: "", title: workspace.title, displayAddress: workspace.displayAddress, savedAt: workspace.updatedAt, identity: { state: workspace.identity.state, scope: workspace.identity.scope, limitation: "已確認僅指瀏覽器案件關聯；不代表地號、建物、所有權或法律身分確認。" }, price, location: locationModel, commute, risk, finance: financeModel, gaps: [], sources };
  model.gaps = evidenceFields(model).filter((item) => item.missingReason !== null && !["finance-grace-payment", "finance-post-grace"].includes(item.id)).map((item) => ({ caseId: model.caseId, domain: item.domain, id: item.id, item: item.label, reason: item.missingReason!, impact: item.limitation, nextAction: item.nextAction, href: `/cases/${encodeURIComponent(model.caseId)}/${item.domain}` }));
  for (const cost of finance?.missingCosts ?? []) model.gaps.push({ caseId: model.caseId, domain: "finance", id: `cost-${encodeURIComponent(cost)}`, item: cost, reason: "missing_input", impact: "已知住宅支出未涵蓋所有成本。", nextAction: ACTIONS.finance, href: `/cases/${encodeURIComponent(model.caseId)}/finance` });
  model.snapshotToken = JSON.stringify(model); // Canonical projection order, in memory only; no durable revision claim.
  return model;
}

export function evidenceFields(model: CaseEvidenceModel): Array<EvidenceField<string | number>> {
  return [...Object.values(model.price), ...Object.values(model.location), ...Object.values(model.commute), ...model.risk.map((row) => row.evidence), ...Object.entries(model.finance).flatMap(([key, value]) => key === "breakdown" ? [] : [value as EvidenceField<string | number>]), ...model.finance.breakdown.map((row) => row.amount)];
}
