"use client";

import type { ReactNode } from "react";
import type { LocationInsightResult, MarketResult, TerrainRiskResult } from "@/lib/api";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { journeyPriceBasisLabel, journeyWorkflowStateLabel, type JourneyPriceBasis } from "@/lib/closed-loop-journey";
import type { JourneyPropertyContext, LocationMarketDisplayStatus } from "@/lib/location-market-journey";
import type { JourneyAffordabilityContext, JourneyPriceContext } from "@/lib/price-affordability-journey";

type WorkflowState = "complete" | "partial" | "not_available" | "needs_review";

export function DecisionEvidenceSynthesis({ propertyContext, locationResult, locationStatus, terrainResult, terrainStatus, marketResult, marketStatus, priceContext, priceBasis, activePriceWan, affordabilityContext }: { propertyContext: JourneyPropertyContext; locationResult?: LocationInsightResult; locationStatus: LocationMarketDisplayStatus; terrainResult?: TerrainRiskResult; terrainStatus: LocationMarketDisplayStatus; marketResult?: MarketResult; marketStatus: LocationMarketDisplayStatus; priceContext: JourneyPriceContext; priceBasis: JourneyPriceBasis; activePriceWan?: number; affordabilityContext: JourneyAffordabilityContext }) {
  const { locale, formatNumber } = useExperienceLocale();
  const copy = synthesisCopy(locale);
  const propertyAddress = propertyContext.addressSummary || [propertyContext.city, propertyContext.district, propertyContext.road].filter(Boolean).join("");
  const propertyState: WorkflowState = propertyContext.selectionStatus === "selected" ? "complete" : propertyContext.selectionStatus === "partial" ? "partial" : "needs_review";
  const locationState = evidenceWorkflowState(locationStatus);
  const priceState: WorkflowState = activePriceWan && priceContext.officialValuationStatus === "available" ? "complete" : activePriceWan || priceContext.officialValuationStatus !== "not_started" ? "partial" : "needs_review";
  const affordabilityState: WorkflowState = affordabilityContext.loanStatus === "available" ? affordabilityContext.holdingCostStatus === "available" ? "complete" : "partial" : affordabilityContext.loanStatus === "unavailable" ? "not_available" : "needs_review";
  const marketCount = marketResult?.transaction_count ?? marketResult?.record_count;
  const limitations = [
    !locationResult ? copy.locationMissing : "",
    !terrainResult ? copy.terrainMissing : "",
    !marketResult || ["unavailable", "not_started"].includes(marketStatus) ? copy.marketMissing : "",
    priceContext.officialValuationStatus !== "available" ? copy.valuationMissing : "",
    affordabilityContext.loanStatus !== "available" ? copy.loanMissing : "",
  ].filter(Boolean);
  return <section data-testid="decision-evidence-synthesis" aria-labelledby="decision-evidence-synthesis-heading" className="min-w-0 space-y-3 rounded-xl border border-slate-200 bg-white p-4">
    <div><p className="text-[10px] font-bold tracking-wider text-cyan-700">EVIDENCE SYNTHESIS</p><h3 id="decision-evidence-synthesis-heading" className="mt-1 text-lg font-black text-slate-950">{copy.title}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{copy.boundary}</p></div>
    <div className="grid min-w-0 gap-3 lg:grid-cols-2">
      <EvidenceSection id="property" title={copy.property} state={propertyState} locale={locale}><p data-testid="decision-property-address">{propertyAddress || copy.notProvided}</p><p>{[propertyContext.buildingType, propertyContext.areaPing ? `${propertyContext.areaPing}` : "", propertyContext.buildingAgeYears !== undefined ? `${propertyContext.buildingAgeYears}` : "", propertyContext.floor !== undefined ? `${propertyContext.floor}` : ""].filter(Boolean).join(" · ") || copy.notProvided}</p></EvidenceSection>
      <EvidenceSection id="location" title={copy.location} state={locationState} locale={locale}><p>{locationResult?.resolved_location?.address_label || propertyAddress || copy.notProvided}</p><p>{locationResult?.data_quality.status ?? locationStatus}</p><p>{copy.terrain}: {terrainResult?.overall.label ?? terrainStatus}</p><p>{copy.market}: {marketCount ? `${formatNumber(marketCount)} · ${marketResult?.period ?? copy.periodUnknown}` : marketStatus}</p></EvidenceSection>
      <EvidenceSection id="price" title={copy.price} state={priceState} locale={locale}><p data-testid="decision-price-basis">{journeyPriceBasisLabel(priceBasis, locale)}: {activePriceWan ? formatNumber(activePriceWan) : copy.notProvided}</p><p>{copy.valuation}: {priceContext.officialEstimateWan ? `${formatNumber(priceContext.officialEstimateWan)} (${priceContext.estimateLowWan ? formatNumber(priceContext.estimateLowWan) : "—"}–${priceContext.estimateHighWan ? formatNumber(priceContext.estimateHighWan) : "—"})` : priceContext.officialValuationStatus}</p></EvidenceSection>
      <EvidenceSection id="affordability" title={copy.affordability} state={affordabilityState} locale={locale}><p data-testid="decision-monthly-payment">{copy.monthlyPayment}: {affordabilityContext.monthlyPayment ? formatNumber(affordabilityContext.monthlyPayment) : copy.notProvided}</p><p>{copy.cashNeed}: {affordabilityContext.downPaymentWan ? formatNumber(affordabilityContext.downPaymentWan) : copy.notProvided}</p><p>{copy.holding}: {affordabilityContext.monthlyHoldingCost ? formatNumber(affordabilityContext.monthlyHoldingCost) : copy.notProvided}</p></EvidenceSection>
    </div>
    <div className="grid gap-3 lg:grid-cols-2">
      <EvidenceList title={copy.risks} items={limitations.length ? limitations : [copy.readSources]} />
      <EvidenceList title={copy.nextChecks} items={[copy.confirmAddress, copy.confirmPrice, copy.confirmFunding, copy.confirmProfessional]} />
    </div>
  </section>;
}

function EvidenceSection({ id, title, state, locale, children }: { id: string; title: string; state: WorkflowState; locale: "zh-TW" | "en" | "ja" | "ko"; children: ReactNode }) {
  return <article data-testid={`decision-evidence-${id}`} className="min-w-0 rounded-lg border border-stone-200 bg-stone-50 p-3"><div className="flex min-w-0 flex-wrap items-center justify-between gap-2"><h4 className="text-xs font-black text-slate-900">{title}</h4><span className="rounded-full bg-white px-2 py-1 text-[10px] font-bold text-slate-700">{journeyWorkflowStateLabel(state, locale)}</span></div><div className="mt-2 space-y-1 break-words text-xs leading-5 text-slate-700">{children}</div></article>;
}

function EvidenceList({ title, items }: { title: string; items: string[] }) {
  return <section className="rounded-lg border border-amber-100 bg-amber-50/60 p-3"><h4 className="text-xs font-black text-amber-950">{title}</h4><ul className="mt-2 space-y-1 text-xs leading-5 text-amber-950">{items.map((item) => <li key={item}>• {item}</li>)}</ul></section>;
}

function evidenceWorkflowState(status: LocationMarketDisplayStatus): WorkflowState {
  if (status === "available") return "complete";
  if (status === "partial" || status === "stale" || status === "no_data") return "partial";
  if (status === "unavailable") return "not_available";
  return "needs_review";
}

function synthesisCopy(locale: "zh-TW" | "en" | "ja" | "ko") {
  const rows = {
    "zh-TW": { title: "五步驟證據摘要", boundary: "只整合已取得的證據、限制與待確認事項，不產生購買分數或建議。", property: "物件", location: "位置", terrain: "地勢參考", market: "市場資料", price: "價格", valuation: "估價證據", affordability: "負擔情境", monthlyPayment: "每月還款", cashNeed: "自備款", holding: "每月持有成本", risks: "風險與限制", nextChecks: "下一步確認", notProvided: "尚未提供", periodUnknown: "期別未知", locationMissing: "位置證據尚未完成。", terrainMissing: "地勢參考尚未完成；未知不代表低風險。", marketMissing: "市場資料尚未取得或暫時不可用。", valuationMissing: "估價證據尚不完整。", loanMissing: "資金試算尚未完成。", readSources: "閱讀每項資料來源、期間與限制。", confirmAddress: "向謄本、現場或專業人員確認物件與地址。", confirmPrice: "比較開價、估價範圍與可比成交。", confirmFunding: "向金融機構確認利率、核貸與現金需求。", confirmProfessional: "依個案向地政、稅務、法律或工程專業人員確認。" },
    en: { title: "Five-step evidence summary", boundary: "This combines available evidence, limitations, and open checks without creating a purchase score or recommendation.", property: "Property", location: "Location", terrain: "Terrain reference", market: "Market evidence", price: "Price", valuation: "Valuation evidence", affordability: "Affordability scenario", monthlyPayment: "Monthly payment", cashNeed: "Down payment", holding: "Monthly holding cost", risks: "Risks and limitations", nextChecks: "Next checks", notProvided: "Not provided", periodUnknown: "Period unknown", locationMissing: "Location evidence is not complete.", terrainMissing: "Terrain reference is not complete; unknown is not low risk.", marketMissing: "Market evidence is missing or unavailable.", valuationMissing: "Valuation evidence is incomplete.", loanMissing: "The funding calculation is incomplete.", readSources: "Review every source, period, and limitation.", confirmAddress: "Confirm the property and address through records, an inspection, or a professional.", confirmPrice: "Compare the asking price, valuation range, and comparable transactions.", confirmFunding: "Confirm rates, lending eligibility, and cash needs with a lender.", confirmProfessional: "Use land, tax, legal, or engineering professionals as the case requires." },
    ja: { title: "5ステップの根拠要約", boundary: "取得済みの根拠、制限、確認事項のみを整理し、購入スコアや推奨は作りません。", property: "物件", location: "位置", terrain: "地形参考", market: "市場データ", price: "価格", valuation: "査定根拠", affordability: "資金シナリオ", monthlyPayment: "月々の返済", cashNeed: "頭金", holding: "月間保有コスト", risks: "リスクと制限", nextChecks: "次の確認", notProvided: "未入力", periodUnknown: "期間不明", locationMissing: "位置の根拠が未完了です。", terrainMissing: "地形参考が未完了です。未知は低リスクを意味しません。", marketMissing: "市場データが未取得または利用不可です。", valuationMissing: "査定根拠が不完全です。", loanMissing: "資金計算が未完了です。", readSources: "各情報源、期間、制限を確認してください。", confirmAddress: "登記、現地、専門家で物件と住所を確認してください。", confirmPrice: "売出価格、査定範囲、比較取引を確認してください。", confirmFunding: "金利、融資可否、必要資金を金融機関に確認してください。", confirmProfessional: "案件に応じて土地、税務、法律、工学の専門家に確認してください。" },
    ko: { title: "5단계 근거 요약", boundary: "확보된 근거, 제한, 확인 항목만 정리하며 구매 점수나 권고를 만들지 않습니다.", property: "물건", location: "위치", terrain: "지형 참고", market: "시장 자료", price: "가격", valuation: "평가 근거", affordability: "자금 시나리오", monthlyPayment: "월 상환액", cashNeed: "초기 자금", holding: "월 보유 비용", risks: "위험과 제한", nextChecks: "다음 확인", notProvided: "미제공", periodUnknown: "기간 알 수 없음", locationMissing: "위치 근거가 완료되지 않았습니다.", terrainMissing: "지형 참고가 완료되지 않았으며 알 수 없음은 낮은 위험이 아닙니다.", marketMissing: "시장 자료가 없거나 이용할 수 없습니다.", valuationMissing: "평가 근거가 불완전합니다.", loanMissing: "자금 계산이 완료되지 않았습니다.", readSources: "각 출처, 기간 및 제한을 확인하세요.", confirmAddress: "등기, 현장 또는 전문가를 통해 물건과 주소를 확인하세요.", confirmPrice: "희망가, 평가 범위 및 비교 거래를 확인하세요.", confirmFunding: "금리, 대출 가능 여부 및 현금 필요액을 금융기관에 확인하세요.", confirmProfessional: "사례에 따라 토지, 세무, 법률 또는 공학 전문가에게 확인하세요." },
  } as const;
  return rows[locale];
}
