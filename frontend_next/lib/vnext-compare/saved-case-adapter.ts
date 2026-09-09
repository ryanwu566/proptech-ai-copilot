import type { SavedCase } from "@/lib/case-storage";
import {
  getHoldingEvidence,
  getLoanEvidence,
  getLocationEvidence,
  getStoredTerrainReferenceEvidence,
  getTaxEvidence,
  getTrustedValuationEvidence,
  type PropertyCaseEvidenceStatus,
} from "@/lib/property-case-evidence";
import { terrainReferenceStateLabel } from "@/lib/terrain-reference-evidence";
import type { CaseAttachmentDTO, CaseDTO, PropertyDTO } from "@/lib/vnext-identity-contract";
import type {
  CompareDataState,
  CompareIdentity,
  CompareMetric,
  CompareSourceDisclosure,
  PropertyCompareCase,
} from "@/lib/vnext-compare/types";

export type SuppliedSavedCaseIdentity = {
  caseRecord?: CaseDTO;
  attachment?: CaseAttachmentDTO;
  property?: PropertyDTO;
};

export type SavedCaseCompareOptions = {
  identity?: SuppliedSavedCaseIdentity;
};

/**
 * Presentation-only bridge for the legacy SavedCase format. It deliberately
 * differs from the ranked comparison adapter: no score/rank is copied, stored
 * valuations must pass both stored and current transferability gates, and a
 * SavedCase id/address can never become a confirmed PropertyEntity identity.
 */
export function adaptSavedCaseForComparison(saved: SavedCase, options: SavedCaseCompareOptions = {}): PropertyCompareCase {
  const valuationGate = getTrustedValuationEvidence(saved.data.valuation);
  const storedValuationGate = saved.data.valuationEvidence;
  const storedValuationValues = saved.data.valuation
    ? [saved.data.valuation.price_range.low, saved.data.valuation.price_range.mid, saved.data.valuation.price_range.high]
    : [];
  const valuationTransferable = Boolean(
    saved.data.valuation
    && storedValuationGate?.transferable === true
    && storedValuationGate.status === "trusted"
    && storedValuationGate.source === "official_valuation"
    && storedValuationValues.length === 3
    && storedValuationValues.every((value) => typeof value === "number" && Number.isFinite(value) && value > 0),
  );
  const storedValuationState = evidenceState(storedValuationGate?.status ?? valuationGate.status);
  const valuationState = valuationTransferable ? "known" : storedValuationState === "known" ? "unavailable" : storedValuationState;
  const valuationReason = storedValuationGate?.reason || valuationGate.reason;
  const locationEvidence = getLocationEvidence(saved.data.locationInsight);
  const loanEvidence = getLoanEvidence(saved.data.loan);
  const holdingEvidence = getHoldingEvidence(saved.data.holdingCost);
  const terrainEvidence = getStoredTerrainReferenceEvidence(saved.data.terrainReference);
  const taxEvidence = getTaxEvidence(saved.data.taxOracle);
  const terrain = saved.data.terrainReference;
  const riskFactors = saved.data.riskSummary?.riskFactors ?? [];
  const nextChecks = new Set<string>();

  const askingPrice = metric(saved.inputSummary.propertyPrice, "known", "currency_10k", "TWD", "one_time", "asking_price");
  const area = metric(saved.data.inputs.area_ping || saved.inputSummary.areaPing, "known", "ping", null, null, "floor_area");
  const downPayment = metric(saved.data.loan?.down_payment_wan, evidenceState(loanEvidence.status), "currency_10k", "TWD", "one_time", "down_payment");
  const monthlyMortgage = metric(saved.data.loan?.monthly_payment, evidenceState(loanEvidence.status), "currency", "TWD", "monthly", "mortgage_payment");
  const monthlyHoldingCost = metric(saved.data.holdingCost?.monthly_total_holding_cost, evidenceState(holdingEvidence.status), "currency", "TWD", "monthly", "holding_cost");

  if (askingPrice.value === null) nextChecks.add("確認開價、幣別與價格基礎");
  if (area.value === null) nextChecks.add("確認權狀面積與面積單位");
  if (!valuationTransferable) nextChecks.add("重新取得可移轉且通過可信度門檻的估價證據");
  if (!saved.data.loan) nextChecks.add("補齊貸款條件與月付試算");
  if (!saved.data.holdingCost) nextChecks.add("補齊持有成本項目與期間");
  if (!terrain || ["unknown", "not_assessed", "unavailable", "error", "no_match"].includes(terrain.status)) nextChecks.add("重新查核地勢與災害圖層；未命中不代表安全");
  if (!saved.data.taxOracle) nextChecks.add("確認稅務參考狀態；本比較不新增稅額計算");

  const sources: CompareSourceDisclosure[] = [
    {
      sourceId: "case-input",
      label: "案件輸入",
      state: "unverified",
      coverage: "partial",
      retrievedAt: null,
      effectiveAt: null,
      limitation: "使用者或案件內容，未在此比較介面獨立查證。",
    },
  ];
  if (saved.data.valuation || storedValuationGate) {
    sources.push(source("valuation", storedValuationGate?.label || valuationGate.label, valuationState, valuationReason));
  }
  if (saved.data.loan) sources.push(source("loan", loanEvidence.label, evidenceState(loanEvidence.status), loanEvidence.reason));
  if (saved.data.holdingCost) sources.push(source("holding", holdingEvidence.label, evidenceState(holdingEvidence.status), holdingEvidence.reason));
  if (saved.data.locationInsight) sources.push(source("location", locationEvidence.label, evidenceState(locationEvidence.status), locationEvidence.reason));
  if (terrain) {
    terrain.layers.forEach((layer, index) => sources.push({
      sourceId: `terrain-${layer.layer_id || index}`,
      label: layer.source_name,
      state: terrainState(layer.state),
      coverage: layer.coverage_status === "covered" ? "known" : layer.coverage_status === "not_covered" ? "partial" : "unknown",
      retrievedAt: null,
      effectiveAt: validDate(layer.data_updated_at),
      limitation: layer.caveat,
    }));
  }
  if (saved.data.taxOracle) sources.push(source("tax", taxEvidence.label, evidenceState(taxEvidence.status), taxEvidence.reason));

  return {
    caseId: saved.id,
    title: saved.title,
    locationSummary: [saved.inputSummary.city, saved.inputSummary.district, saved.inputSummary.road].filter((value) => value?.trim()).join("") || "未提供位置摘要",
    identity: suppliedIdentity(options.identity),
    caseUpdatedAt: saved.updatedAt,
    askingPrice,
    area,
    buildingType: {
      value: saved.data.inputs.building_type?.trim() || null,
      state: saved.data.inputs.building_type?.trim() ? "known" : "unknown",
      limitation: saved.data.inputs.building_type?.trim() ? undefined : "未提供建物型態。",
    },
    valuation: {
      state: valuationState,
      transferable: valuationTransferable,
      low: metric(valuationTransferable ? saved.data.valuation?.price_range.low : null, valuationState, "currency_10k", "TWD", "one_time", "official_valuation", valuationReason),
      midpoint: metric(valuationTransferable ? saved.data.valuation?.price_range.mid : null, valuationState, "currency_10k", "TWD", "one_time", "official_valuation", valuationReason),
      high: metric(valuationTransferable ? saved.data.valuation?.price_range.high : null, valuationState, "currency_10k", "TWD", "one_time", "official_valuation", valuationReason),
      statusLabel: valuationTransferable ? "可供比較" : "不可供比較",
      limitation: valuationReason,
    },
    downPayment,
    monthlyMortgage,
    monthlyHoldingCost,
    location: {
      state: evidenceState(locationEvidence.status),
      items: [
        ...(saved.data.locationInsight?.strengths ?? []),
        ...(saved.data.locationInsight?.weaknesses ?? []),
      ].slice(0, 4),
      limitation: locationEvidence.reason,
    },
    terrain: {
      state: terrain?.status ?? "not_assessed",
      riskLevel: "unknown",
      summary: terrain?.summary ?? terrainEvidence.reason,
      observations: terrain?.layers.map((layer) => `${layer.display_name}：${terrainReferenceStateLabel(layer.state)}`) ?? [],
      limitation: terrain?.notice ?? "已保存的地勢參考不是即時風險評估；資料不足不代表沒有風險。",
    },
    tax: {
      state: evidenceState(taxEvidence.status),
      summary: saved.data.taxOracle ? `參考訊號：${saved.data.taxOracle.signal_color}` : "尚未提供稅務參考",
      limitation: taxEvidence.reason,
    },
    warnings: [
      ...riskFactors.slice(0, 4).map((item) => ({ severity: item.level === "high" ? "high" as const : "caution" as const, label: item.title })),
      ...(saved.data.taxOracle?.signal_color === "red" ? [{ severity: "high" as const, label: "稅務參考出現紅色訊號，需另行確認。" }] : []),
    ],
    sources,
    nextChecks: [...nextChecks],
  };
}

function suppliedIdentity(input?: SuppliedSavedCaseIdentity): CompareIdentity {
  const caseRecord = input?.caseRecord ?? input?.attachment?.case;
  const attachment = input?.attachment;
  const property = input?.property;
  const confirmed = Boolean(
    caseRecord?.identity_status === "confirmed"
    && attachment
    && property
    && attachment.case.case_id === caseRecord.case_id
    && attachment.link.case_id === caseRecord.case_id
    && attachment.link.property_entity_id === property.property_entity_id
    && property.confirmation_summary.human_confirmed,
  );
  if (confirmed && property) {
    return {
      status: "confirmed",
      displayLabel: property.display_label,
      propertyEntityId: property.property_entity_id,
      note: "已提供並交叉核對 CaseAttachment 與人工確認的 PropertyEntity。",
    };
  }
  const status = caseRecord?.identity_status;
  return {
    status: status === "resolving" ? "resolving" : status === "unverified" ? "unverified" : "legacy_unverified",
    displayLabel: null,
    propertyEntityId: null,
    note: "SavedCase ID 不是 PropertyEntity ID；地址或座標相近也不構成身分確認。",
  };
}

function metric(
  value: number | null | undefined,
  state: CompareDataState,
  unit: CompareMetric["unit"],
  currency: CompareMetric["currency"],
  period: CompareMetric["period"],
  basis: CompareMetric["basis"],
  limitation?: string,
): CompareMetric {
  return { value: typeof value === "number" ? value : null, state: typeof value === "number" ? state : state === "known" ? "unknown" : state, unit, currency, period, basis, limitation };
}

function evidenceState(status: PropertyCaseEvidenceStatus): CompareDataState {
  const states: Record<PropertyCaseEvidenceStatus, CompareDataState> = {
    trusted: "known",
    manual: "unverified",
    partial: "partial",
    unavailable: "unavailable",
    not_assessed: "not_assessed",
  };
  return states[status];
}

function terrainState(status: string): CompareDataState {
  if (status === "available") return "known";
  if (status === "partial" || status === "limited" || status === "unavailable" || status === "unknown" || status === "no_match" || status === "not_assessed") return status;
  return "unavailable";
}

function source(sourceId: string, label: string, state: CompareDataState, limitation: string): CompareSourceDisclosure {
  return { sourceId, label, state, coverage: state === "known" ? "known" : state === "unavailable" ? "unavailable" : "partial", retrievedAt: null, effectiveAt: null, limitation };
}

function validDate(value: string | undefined): string | null {
  return value && !Number.isNaN(Date.parse(value)) ? value : null;
}
