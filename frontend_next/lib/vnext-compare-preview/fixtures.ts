import type { SavedCase } from "@/lib/case-storage";
import { adaptSavedCaseForComparison } from "@/lib/vnext-compare/saved-case-adapter";
import type { CompareMetric, PropertyCompareCase } from "@/lib/vnext-compare/types";

export type ComparePreviewScenario = {
  id: "two-known" | "mixed-evidence" | "incompatible" | "invalid-inputs";
  label: string;
  description: string;
  cases: PropertyCompareCase[];
};

const NOW = "2026-09-08T08:00:00+08:00";
const SOURCE_TIME = "2026-08-31T00:00:00+08:00";

function moneyWan(value: number | null, state: CompareMetric["state"] = value === null ? "unknown" : "known", basis: CompareMetric["basis"] = "asking_price"): CompareMetric {
  return { value, state, unit: "currency_10k", currency: "TWD", period: "one_time", basis };
}

function money(value: number | null, state: CompareMetric["state"] = value === null ? "unknown" : "known", period: CompareMetric["period"] = "monthly", basis: CompareMetric["basis"] = "mortgage_payment"): CompareMetric {
  return { value, state, unit: "currency", currency: "TWD", period, basis };
}

function ping(value: number | null, state: CompareMetric["state"] = value === null ? "unknown" : "known"): CompareMetric {
  return { value, state, unit: "ping", currency: null, period: null, basis: "floor_area" };
}

function baseCase(caseId: string, title: string, locationSummary: string, price: number, area: number): PropertyCompareCase {
  return {
    caseId,
    title,
    locationSummary,
    identity: {
      status: "unverified",
      displayLabel: null,
      propertyEntityId: null,
      note: "合成情境僅提供案件識別；未提供可驗證的 PropertyEntity 關聯。",
    },
    caseUpdatedAt: NOW,
    askingPrice: moneyWan(price),
    area: ping(area),
    buildingType: { value: "住宅大樓", state: "known" },
    valuation: {
      state: "known",
      transferable: true,
      low: moneyWan(price - 90, "known", "official_valuation"),
      midpoint: moneyWan(price - 30, "known", "official_valuation"),
      high: moneyWan(price + 45, "known", "official_valuation"),
      statusLabel: "情境：假設已通過既有門檻",
      limitation: "合成值只驗證通過既有移轉門檻後的呈現；不是實際估價或權威來源。",
    },
    downPayment: { ...moneyWan(price * .2, "known", "down_payment") },
    monthlyMortgage: money(Math.round(price * 24.8), "known", "monthly", "mortgage_payment"),
    monthlyHoldingCost: money(Math.round(price * 28.2), "known", "monthly", "holding_cost"),
    location: {
      state: "known",
      items: ["步行生活機能情境完整", "通勤時間仍需於尖峰時段現場確認"],
      limitation: "合成位置觀察，未呼叫地理編碼或即時 POI 服務。",
    },
    terrain: {
      state: "available",
      riskLevel: "low",
      summary: "合成圖層狀態為可用、低風險情境",
      observations: ["淹水圖層：合成可用", "坡地圖層：合成可用"],
      limitation: "這是合成呈現狀態，不是新鮮風險評估，也不能作為安全保證。",
    },
    tax: {
      state: "known",
      summary: "已提供合成稅務參考狀態（未計算稅額）",
      limitation: "只顯示狀態；比較介面沒有新增稅務計算。",
    },
    warnings: [],
    sources: [{
      sourceId: `fixture-${caseId}`,
      label: "合成測試資料（非官方）",
      state: "unverified",
      coverage: "partial",
      retrievedAt: NOW,
      effectiveAt: SOURCE_TIME,
      limitation: "只供本機預覽與互動測試，不代表任何真實物件或權威資料。",
    }],
    nextChecks: ["核對權狀、謄本與案件身分", "向金融機構確認實際核貸條件", "現場確認噪音、採光與出入動線"],
  };
}

const riverCase = baseCase("synthetic-river-01", "河岸通勤宅", "合成位置 A · 僅顯示行政區層級", 1_980, 31.6);
const gardenCase: PropertyCompareCase = {
  ...baseCase("synthetic-garden-02", "綠園家庭宅", "合成位置 B · 僅顯示行政區層級", 2_120, 38.2),
  buildingType: { value: "華廈", state: "known" },
  location: {
    state: "known",
    items: ["公園與學校情境較近", "大眾運輸班距需現場確認"],
    limitation: "合成位置觀察，未呼叫地理編碼或即時 POI 服務。",
  },
};

const incompleteCase: PropertyCompareCase = {
  ...baseCase("synthetic-incomplete-03", "資料待補的邊間宅", "合成位置 C · 門牌未驗證", 1_760, 27.4),
  identity: { status: "legacy_unverified", displayLabel: null, propertyEntityId: null, note: "舊版 SavedCase 身分不可升級為已確認 PropertyEntity。" },
  valuation: {
    state: "unavailable",
    transferable: false,
    low: moneyWan(1_620, "known", "official_valuation"),
    midpoint: moneyWan(1_700, "known", "official_valuation"),
    high: moneyWan(1_780, "known", "official_valuation"),
    statusLabel: "不可供比較",
    limitation: "儲存估價未通過既有可移轉／可信度門檻；原數值不呈現。",
  },
  monthlyMortgage: { ...money(null, "unknown"), limitation: "貸款條件尚未提供；未知不是 0 元。" },
  monthlyHoldingCost: { ...money(null, "partial", "monthly", "holding_cost"), limitation: "僅有部分成本項目，不能視為 0 元。" },
  location: { state: "limited", items: ["僅有行政區層級描述"], limitation: "位置涵蓋有限，沒有精確地點可供核對。" },
  terrain: {
    state: "no_match",
    riskLevel: "unknown",
    summary: "保存的參考圖層未命中明確訊號",
    observations: [],
    limitation: "未命中不等於沒有災害風險；保存內容也不是即時評估。",
  },
  tax: { state: "not_assessed", summary: "尚未評估", limitation: "沒有稅務參考，不新增推算。" },
  warnings: [{ severity: "caution", label: "門牌與權狀範圍尚未核對。" }],
  sources: [{ sourceId: "fixture-incomplete", label: "合成不完整資料", state: "limited", coverage: "partial", retrievedAt: null, effectiveAt: null, limitation: "刻意保留缺漏，用於確認介面不把未知顯示為 0。" }],
  nextChecks: ["核對門牌與權狀範圍", "重新取得可移轉估價證據", "補齊貸款與持有成本", "重新查核地勢圖層"],
};

const highRiskCase: PropertyCompareCase = {
  ...baseCase("synthetic-risk-04", "坡地景觀宅", "合成位置 D · 坡地情境", 2_480, 46.8),
  askingPrice: { ...moneyWan(2_480, "stale"), limitation: "開價資料時點較舊，需向提供方重查。" },
  terrain: {
    state: "available",
    riskLevel: "high",
    summary: "合成情境：已知高風險訊號",
    observations: ["坡地圖層：高風險訊號", "覆蓋狀態：已知"],
    limitation: "合成警示只用來驗證高風險不被差異模式隱藏；仍需專業現勘。",
  },
  warnings: [
    { severity: "high", label: "已知高風險訊號：應先釐清坡地與排水條件。" },
    { severity: "caution", label: "開價來源較舊，不能直接與新資料下結論。" },
  ],
  sources: [{ sourceId: "fixture-risk", label: "合成高風險資料", state: "stale", coverage: "known", retrievedAt: "2026-08-01T00:00:00+08:00", effectiveAt: "2025-12-31T00:00:00+08:00", limitation: "合成且可能過期；警示保留不代表風險已完成確認。" }],
  nextChecks: ["委託專業人員現勘坡地與排水", "向提供方重查最新開價", "確認保險與融資限制"],
};

const conflictingCase: PropertyCompareCase = {
  ...baseCase("synthetic-conflict-05", "資料衝突的長名稱測試案件——用來確認欄寬、換行以及任何接近座標都不會被誤合併為同一物件", "合成位置 E · 兩份地址描述不一致且不應自動合併", 2_060, 34.1),
  askingPrice: { ...moneyWan(2_060, "conflicting"), limitation: "兩個合成來源提供不同開價，需先釐清。" },
  warnings: [{ severity: "caution", label: "地址與開價來源互相衝突；不可自動合併案件。" }],
  sources: [{ sourceId: "fixture-conflict", label: "合成衝突資料", state: "conflicting", coverage: "partial", retrievedAt: NOW, effectiveAt: SOURCE_TIME, limitation: "刻意建立的衝突；不選擇任一來源為正確答案。" }],
  nextChecks: ["逐一核對來源記錄與案件識別", "確認正確開價及其價格基礎"],
};

const incompatibleA = baseCase("synthetic-basis-01", "新臺幣開價基準", "合成位置 F", 1_900, 30);
const incompatibleB: PropertyCompareCase = {
  ...baseCase("synthetic-basis-02", "不同幣別與面積單位", "合成位置 G", 1_900, 30),
  askingPrice: { value: 62, state: "known", unit: "currency_10k", currency: "USD", period: "one_time", basis: "asking_price", limitation: "美元情境；未進行匯率換算。" },
  area: { value: 99.2, state: "known", unit: "sqm", currency: null, period: null, basis: "floor_area", limitation: "平方公尺情境；未換算為坪。" },
};
const incompatibleC: PropertyCompareCase = {
  ...baseCase("synthetic-basis-03", "成交價與年度金額基準", "合成位置 H", 1_880, 30),
  askingPrice: { ...moneyWan(1_880, "known", "transaction_price"), limitation: "此數值基礎是成交價，不可當成開價直接比較。" },
  monthlyMortgage: { ...money(420_000, "known", "annual", "mortgage_payment"), limitation: "年度總額情境，不可當成月付。" },
};

const legacySavedCase: SavedCase = {
  id: "synthetic-legacy-empty",
  title: "",
  createdAt: "not-a-date",
  updatedAt: "not-a-date",
  version: 1,
  workflowMode: "buying_wizard",
  activeWizardStep: "property_search",
  progress: 0,
  inputSummary: { propertyPrice: 0, areaPing: 0 },
  data: { inputs: { city: "", district: "", road: "", building_type: "", area_ping: 0, building_age_years: 0, floor: 0 } },
};
const invalidLegacy = adaptSavedCaseForComparison(legacySavedCase);
const malformedCase: PropertyCompareCase = {
  ...baseCase("synthetic-malformed", "非有限數值情境", "合成位置 I", 1_500, 25),
  askingPrice: { ...moneyWan(Number.POSITIVE_INFINITY), limitation: "輸入為 Infinity，必須拒絕。" },
  area: { ...ping(Number.NaN), limitation: "輸入為 NaN，必須拒絕。" },
};

export const COMPARE_PREVIEW_SCENARIOS: ComparePreviewScenario[] = [
  {
    id: "two-known",
    label: "兩案可比欄位",
    description: "兩個合成案件具有相容的幣別、單位、期間與價格基礎。",
    cases: [riverCase, gardenCase],
  },
  {
    id: "mixed-evidence",
    label: "四案候選／證據差異",
    description: "從四案明確選擇最多三案；含缺漏、未命中、高風險、過期與衝突。",
    cases: [riverCase, incompleteCase, highRiskCase, conflictingCase],
  },
  {
    id: "incompatible",
    label: "不相容單位與基礎",
    description: "幣別、萬／元、坪／平方公尺、月／年及開價／成交價不相容。",
    cases: [incompatibleA, incompatibleB, incompatibleC],
  },
  {
    id: "invalid-inputs",
    label: "重複 ID／空值／異常數字",
    description: "確認重複與空 ID 不會被合併，NaN、Infinity 與無效零值不會當成 0 顯示。",
    cases: [invalidLegacy, { ...invalidLegacy }, { ...malformedCase, caseId: "" }, malformedCase],
  },
];
