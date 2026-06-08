import type { PropertySearchResult, ValuationResult, ValuationTrendResult } from "@/lib/api";

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
): string {
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
  const disclaimer = "本結果為資料模型推估參考，非正式鑑價、非銀行估價、非投資保證。";
  return `<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>PropTech AI Copilot 估價摘要</title><style>
  body{font-family:Arial,"Noto Sans TC",sans-serif;color:#172033;background:#f7f5f0;margin:0;padding:32px}
  main{max-width:960px;margin:auto;background:#fff;padding:32px;border:1px solid #e2e8f0;border-radius:12px}
  h1{margin-top:0}h2{margin-top:28px;font-size:18px}dl{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
  dt{color:#64748b;font-size:12px}dd{margin:2px 0 0;font-weight:700}table{width:100%;border-collapse:collapse;font-size:12px}
  th,td{padding:9px;border-bottom:1px solid #e2e8f0;text-align:left}.notice{margin-top:28px;padding:14px;background:#fffbeb;color:#92400e}
  @media(max-width:640px){body{padding:12px}main{padding:18px}dl{grid-template-columns:1fr}.scroll{overflow-x:auto}table{min-width:680px}}
  </style></head><body><main><h1>PropTech AI Copilot 估價摘要</h1>
  <p>產生時間：${escapeHtml(new Date().toLocaleString("zh-TW"))}</p>
  <h2>查詢條件</h2><dl>${summaryItem("縣市", inputs.city)}${summaryItem("行政區", inputs.district)}
  ${summaryItem("路段", inputs.road)}${summaryItem("建物型態", inputs.building_type)}
  ${summaryItem("坪數", `${inputs.area_ping} 坪`)}${summaryItem("屋齡／樓層", `${inputs.building_age_years} 年／${inputs.floor} 樓`)}</dl>
  <h2>估價結果</h2><dl>${summaryItem("估價區間", `${result.price_range.low.toLocaleString()} ～ ${result.price_range.high.toLocaleString()} 萬`)}
  ${summaryItem("估算總價", `${result.estimate_total_price.toLocaleString()} 萬`)}${summaryItem("信心分數", `${result.confidence_score}（${result.confidence}）`)}
  ${summaryItem("信心原因", result.confidence_reason)}${summaryItem("估價資料組成", result.estimate_data_composition)}
  ${summaryItem("本次估算使用", result.estimate_source_label)}${summaryItem("官方／樣本資料數量", `${result.data_status.official_records_count ?? 0}／${result.data_status.sample_records_count ?? 0}`)}</dl>
  <h2>可比成交前 5 筆</h2><div class="scroll"><table><thead><tr><th>期間</th><th>來源</th><th>路段</th><th>型態</th><th>坪數</th><th>每坪單價</th><th>總價</th></tr></thead><tbody>${comparableRows}</tbody></table></div>
  ${trend ? `<h2>市場趨勢情境</h2><p>${escapeHtml(trend.confidence_reason)}</p><div class="scroll"><table><thead><tr><th>情境</th><th>期間</th><th>每坪單價</th><th>總價參考</th><th>採用年率</th></tr></thead><tbody>${trendRows}</tbody></table></div>` : ""}
  ${propertySection}<p class="notice">${disclaimer}</p></main></body></html>`;
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
