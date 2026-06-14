import type { HoldingCostResult, LoanCalculationResult, PropertySearchResult, ValuationResult, ValuationTrendResult } from "@/lib/api";
import { HOLDING_COST_SESSION_KEY } from "@/components/holding-cost-calculator";
import { LOCATION_INSIGHT_SESSION_KEY } from "@/components/location-insight";
import type { LocationInsightResult } from "@/lib/api";
import { buildDecisionSummary } from "@/lib/decision-summary";
import { buildRiskSummary } from "@/lib/risk-summary";
import { readWorkflowSession } from "@/lib/workflow-status";

export type ValuationInputs = {
  city: string;
  district: string;
  road: string;
  building_type: string;
  area_ping: number;
  building_age_years: number;
  floor: number;
};

const SHARE_FIELDS: (keyof ValuationInputs)[] = [
  "city", "district", "road", "building_type", "area_ping", "building_age_years", "floor",
];

export function parseValuationShareParams(search: string): ValuationInputs | null {
  const params = new URLSearchParams(search);
  const city = params.get("city")?.trim();
  const district = params.get("district")?.trim();
  const road = params.get("road")?.trim();
  const buildingType = params.get("building_type")?.trim();
  if (!city || !district || !road || !buildingType) return null;
  const area = finiteNumber(params.get("area_ping"));
  const age = finiteNumber(params.get("building_age_years"));
  const floor = finiteNumber(params.get("floor"));
  if (area === null || age === null || floor === null) return null;
  return { city, district, road, building_type: buildingType, area_ping: area, building_age_years: age, floor };
}

export function buildValuationShareUrl(baseUrl: string, inputs: ValuationInputs): string {
  const url = new URL(baseUrl);
  url.search = "";
  for (const field of SHARE_FIELDS) {
    const value = inputs[field];
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      url.searchParams.set(field, String(value));
    }
  }
  return url.toString();
}

export function buildValuationSummaryHtml(
  inputs: ValuationInputs,
  result: ValuationResult,
  trend?: ValuationTrendResult,
  propertySearch?: PropertySearchResult,
  loan?: LoanCalculationResult,
  holdingCost?: HoldingCostResult,
  locationInsight?: LocationInsightResult,
): string {
  const holding = holdingCost ?? readHoldingCostResult();
  const location = locationInsight ?? readLocationInsightResult();
  const decision = buildDecisionSummary(propertySearch, result, loan, holding, location);
  const risk = buildRiskSummary({ propertySearch, valuation: result, trend, loan, holding, location });
  const taxOracle = readWorkflowSession().taxOracleResult;
  const comparableRows = result.comparables.slice(0, 5).map((row) => `
    <tr><td>${escapeHtml(row.transaction_period)}</td><td>${escapeHtml(row.source_label || row.source)}</td>
    <td>${escapeHtml(row.road)}</td><td>${escapeHtml(row.building_type)}</td><td>${row.area_ping}</td>
    <td>${row.unit_price_per_ping} 萬</td><td>${row.total_price.toLocaleString()} 萬</td></tr>`).join("");
  const trendRows = trend ? (["conservative", "base", "optimistic"] as const).flatMap((key) =>
    trend.scenario_forecast[key].map((item) => `
      <tr><td>${({ conservative: "保守", base: "中性", optimistic: "樂觀" })[key]}</td>
      <td>${item.horizon_months} 個月</td><td>${item.projected_unit_price_per_ping} 萬</td>
      <td>${item.projected_total_price.toLocaleString()} 萬</td><td>${(item.growth_rate_used * 100).toFixed(1)}%</td></tr>`),
  ).join("") : "";
  const propertyRows = propertySearch?.road_suggestions.slice(0, 5).map((item) => `
    <tr><td>${escapeHtml(item.city)}</td><td>${escapeHtml(item.district)}</td><td>${escapeHtml(item.road ?? "")}</td>
    <td>${item.sample_count}</td><td>${item.median_total_price.toLocaleString()} 萬</td>
    <td>${item.median_area_ping} 坪</td><td>${escapeHtml(item.reason)}</td></tr>`).join("") ?? "";
  const propertySection = propertySearch ? `<h2>找房雷達摘要</h2>
    <p>本次由官方 PLVR 歷史成交篩選出 ${propertySearch.summary.matched_count.toLocaleString()} 筆符合條件的交易；不代表目前有待售物件。</p>
    <div class="scroll"><table><thead><tr><th>縣市</th><th>行政區</th><th>路段</th><th>成交筆數</th><th>中位總價</th><th>中位坪數</th><th>推薦原因</th></tr></thead><tbody>${propertyRows}</tbody></table></div>` : "";
  const loanRows = loan?.sensitivity.map((item) => `<tr><td>${item.annual_interest_rate.toFixed(2)}%</td><td>${item.monthly_payment.toLocaleString()} 元</td><td>${item.total_interest.toLocaleString()} 元</td><td>${item.difference_from_base.toLocaleString()} 元</td></tr>`).join("") ?? "";
  const loanSection = loan ? `<h2>貸款月付試算</h2><dl>
    ${summaryItem("房屋總價", `${loan.property_price_wan.toLocaleString()} 萬`)}
    ${summaryItem("頭期款", `${loan.down_payment_wan.toLocaleString()} 萬`)}
    ${summaryItem("貸款金額", `${loan.loan_amount_wan.toLocaleString()} 萬`)}
    ${summaryItem("月付", `${loan.monthly_payment.toLocaleString()} 元`)}
    ${summaryItem("總利息", `${loan.total_interest.toLocaleString()} 元`)}
    ${summaryItem("負擔率", loan.income_burden_ratio === null ? "未輸入月收入" : `${(loan.income_burden_ratio * 100).toFixed(1)}%`)}
    ${summaryItem("負擔等級", loan.affordability_level)}
    </dl><h3>利率敏感度</h3><div class="scroll"><table><thead><tr><th>年利率</th><th>月付</th><th>總利息</th><th>相對基準月付差</th></tr></thead><tbody>${loanRows}</tbody></table></div>
    <p class="notice">${escapeHtml(loan.disclaimer)}</p>` : "";
  const holdingSection = holding ? `<h2>每月持有成本</h2><dl>
    ${summaryItem("每月總持有成本", `${holding.monthly_total_holding_cost.toLocaleString()} 元`)}
    ${summaryItem("年持有成本", `${holding.annual_total_holding_cost.toLocaleString()} 元`)}
    ${summaryItem("房貸月付", `${holding.loan_monthly_payment.toLocaleString()} 元`)}
    ${summaryItem("管理費", `${holding.monthly_management_fee.toLocaleString()} 元`)}
    ${summaryItem("修繕預備金", `${holding.monthly_repair_reserve.toLocaleString()} 元`)}
    ${summaryItem("每月稅費簡化估算", `${holding.monthly_tax_estimate.toLocaleString()} 元`)}
    ${summaryItem("每月保險", `${holding.monthly_insurance.toLocaleString()} 元`)}
    ${summaryItem("負擔率", holding.income_burden_ratio === null ? "未輸入月收入" : `${(holding.income_burden_ratio * 100).toFixed(1)}%`)}
    ${summaryItem("負擔等級", holding.affordability_level)}</dl>
    <p class="notice">${escapeHtml(holding.disclaimer)}</p>` : "";
  const locationSection = location ? `<h2>區位分析</h2><dl>
    ${summaryItem("區位總分", location.location_score === null ? "資料不足" : String(location.location_score))}
    ${summaryItem("交通／生活機能", `${location.category_scores.transit_score}／${location.category_scores.convenience_score}`)}
    ${summaryItem("教育／公園／醫療", `${location.category_scores.education_score}／${location.category_scores.green_space_score}／${location.category_scores.medical_score}`)}
    ${summaryItem("POI 摘要", `交通 ${location.poi_summary.transit_count}、便利 ${location.poi_summary.convenience_count}、學校 ${location.poi_summary.school_count}、公園 ${location.poi_summary.park_count}、醫療 ${location.poi_summary.medical_count}`)}
    ${summaryItem("資料品質", location.data_quality.status)}</dl>
    <h3>區位優點</h3><ul>${location.strengths.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    <h3>區位缺點</h3><ul>${location.weaknesses.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    <p class="notice">${escapeHtml(location.data_quality.warnings.join("；"))}<br>${escapeHtml(location.disclaimer)}</p>` : "";
  const decisionSection = `<section class="decision"><h2>快速結論</h2><div class="verdict">${escapeHtml(decision.recommendation)}</div>
    <div class="columns"><div><h3>主要理由</h3><ol>${decision.reasons.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol></div>
    <div><h3>主要風險</h3><ol>${decision.risks.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol></div></div>
    <p><strong>資料信心：</strong>${decision.dataConfidence}</p></section>`;
  const riskSection = `<section class="risk ${risk.overallSignal}"><h2>風險總評 / 開價合理性</h2>
    <div class="verdict">${escapeHtml(risk.overallLabel)} · ${risk.overallScore === null ? "資料不足" : `${risk.overallScore} 分`}</div>
    <p>${escapeHtml(risk.decisionSuggestion)}</p><dl>
    ${summaryItem("開價合理性", risk.priceReasonableness.label)}
    ${summaryItem("資料信心", risk.dataConfidence)}</dl>
    <div class="columns"><div><h3>主要加分</h3><ul>${risk.positiveFactors.map((item) => `<li>${escapeHtml(`${item.title}：${item.message}`)}</li>`).join("") || "<li>尚無明確加分因素</li>"}</ul></div>
    <div><h3>主要風險</h3><ul>${risk.riskFactors.map((item) => `<li>${escapeHtml(`${item.title}：${item.message}`)}</li>`).join("") || "<li>尚無明確高風險訊號</li>"}</ul></div></div>
    <div class="columns"><div><h3>補查清單</h3><ul>${risk.missingChecks.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>核心分析已完成，仍建議實地確認</li>"}</ul></div>
    <div><h3>下一步建議</h3><ul>${risk.nextActions.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>完成更多分析後再判斷</li>"}</ul></div></div>
    <p class="notice">本總評為規則式買房決策提醒，不代表正式鑑價、銀行核貸或投資建議。</p></section>`;
  const taxSection = `<h2>TaxOracle 稅務補充檢查</h2>${taxOracle ? `<dl>
    ${summaryItem("稅務風險燈號", taxOracle.signal_color)}
    ${summaryItem("資格結果", taxOracle.eligibility_status)}
    ${summaryItem("風險分數", String(taxOracle.risk_score))}
    ${summaryItem("需複核規則", taxOracle.manual_review_rules.join("、") || "無")}</dl>` : "<p>稅務快篩尚未完成，建議完成看屋決策後再進行 TaxOracle 補充檢查。</p>"}`;
  const checklistRows = decision.checklist.map((item) => `<tr><td>${escapeHtml(item.label)}</td><td>${item.status}</td><td>${escapeHtml(item.detail)}</td></tr>`).join("");
  const checklistSection = `<h2>決策 checklist</h2><div class="scroll"><table><thead><tr><th>檢查項目</th><th>狀態</th><th>提醒</th></tr></thead><tbody>${checklistRows}</tbody></table></div>`;
  const disclaimer = "固定免責聲明：本報告不代表銀行核貸、不代表正式鑑價、不代表正式稅務申報、不代表即時待售物件；區位資料與實際屋況需實地確認。本結果為非正式鑑價、非銀行估價、非投資保證。";
  return `<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>看屋決策報告 v2</title><style>
  body{font-family:Arial,"Noto Sans TC",sans-serif;color:#172033;background:#f7f5f0;margin:0;padding:32px}
  main{max-width:960px;margin:auto;background:#fff;padding:32px;border:1px solid #e2e8f0;border-radius:12px}
  h1{margin-top:0}h2{margin-top:28px;font-size:18px}dl{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
  dt{color:#64748b;font-size:12px}dd{margin:2px 0 0;font-weight:700}table{width:100%;border-collapse:collapse;font-size:12px}
  th,td{padding:9px;border-bottom:1px solid #e2e8f0;text-align:left}.notice{margin-top:28px;padding:14px;background:#fffbeb;color:#92400e}.cover{padding:28px;background:#0f172a;color:#fff;border-radius:12px}.cover p{color:#cbd5e1}.decision,.risk{margin-top:24px;padding:18px;border:1px solid #bae6fd;background:#f0f9ff;border-radius:10px}.risk.green{border-color:#86efac;background:#f0fdf4}.risk.yellow{border-color:#fde047;background:#fffbeb}.risk.red{border-color:#fda4af;background:#fff1f2}.risk.unknown{border-color:#cbd5e1;background:#f8fafc}.verdict{display:inline-block;padding:7px 12px;background:#fff;border-radius:999px;font-weight:700}.columns{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  @media(max-width:640px){body{padding:12px}main{padding:18px}dl,.columns{grid-template-columns:1fr}.scroll{overflow-x:auto}table{min-width:680px}}
  </style></head><body><main><section class="cover"><p>PropTech AI Copilot 估價摘要升級版</p><h1>看屋決策報告 v2</h1>
  <p>${escapeHtml(`${inputs.city}${inputs.district}${inputs.road}`)} · ${result.price_range.mid.toLocaleString()} 萬 · ${inputs.area_ping} 坪 · ${escapeHtml(inputs.building_type)}</p>
  <p>產生時間：${escapeHtml(new Date().toLocaleString("zh-TW"))}</p><p>資料來源：估價可比成交、找房雷達、趨勢、貸款、持有成本與區位分析之既有結果。</p></section>
  ${riskSection}${decisionSection}
  <h2>查詢條件</h2><dl>${summaryItem("縣市", inputs.city)}${summaryItem("行政區", inputs.district)}
  ${summaryItem("路段", inputs.road)}${summaryItem("建物型態", inputs.building_type)}
  ${summaryItem("坪數", `${inputs.area_ping} 坪`)}${summaryItem("屋齡／樓層", `${inputs.building_age_years} 年／${inputs.floor} 樓`)}</dl>
  <h2>估價結果</h2><dl>${summaryItem("估價區間", `${result.price_range.low.toLocaleString()} ～ ${result.price_range.high.toLocaleString()} 萬`)}
  ${summaryItem("估算總價", `${result.estimate_total_price.toLocaleString()} 萬`)}${summaryItem("信心分數", `${result.confidence_score}（${result.confidence}）`)}
  ${summaryItem("信心原因", result.confidence_reason)}${summaryItem("估價資料組成", result.estimate_data_composition)}
  ${summaryItem("本次估算使用", result.estimate_source_label)}${summaryItem("官方／樣本資料數量", `${result.data_status.official_records_count ?? 0}／${result.data_status.sample_records_count ?? 0}`)}</dl>
  <h2>可比成交前 5 筆</h2><div class="scroll"><table><thead><tr><th>期間</th><th>來源</th><th>路段</th><th>型態</th><th>坪數</th><th>每坪單價</th><th>總價</th></tr></thead><tbody>${comparableRows}</tbody></table></div>
  ${trend ? `<h2>市場趨勢摘要／市場趨勢情境</h2><p>資料期間：${escapeHtml(trend.effective_period_min ?? "資料不足")} ～ ${escapeHtml(trend.effective_period_max ?? "資料不足")}；${escapeHtml(trend.confidence_reason)}</p><div class="scroll"><table><thead><tr><th>情境</th><th>期間</th><th>每坪單價</th><th>總價參考</th><th>採用年率</th></tr></thead><tbody>${trendRows}</tbody></table></div><p class="notice">${escapeHtml(trend.disclaimer)}</p>` : ""}
  ${propertySection}${loanSection}${holdingSection}${locationSection}${checklistSection}${taxSection}<p class="notice">${disclaimer}</p></main></body></html>`;
}

function readHoldingCostResult(): HoldingCostResult | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const value = window.sessionStorage.getItem(HOLDING_COST_SESSION_KEY);
    return value ? JSON.parse(value) as HoldingCostResult : undefined;
  } catch {
    return undefined;
  }
}

function readLocationInsightResult(): LocationInsightResult | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const value = window.sessionStorage.getItem(LOCATION_INSIGHT_SESSION_KEY);
    return value ? JSON.parse(value) as LocationInsightResult : undefined;
  } catch {
    return undefined;
  }
}

export function valuationSummaryFilename(now = new Date()): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `valuation_summary_${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}.html`;
}

function finiteNumber(value: string | null): number | null {
  if (value === null || value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function summaryItem(label: string, value: string): string {
  return `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[character] ?? character);
}
