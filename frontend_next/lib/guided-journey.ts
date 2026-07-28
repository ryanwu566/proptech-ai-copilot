export type JourneyStepId = "property" | "location" | "price" | "affordability" | "decision";

export type JourneyStepDefinition = {
  id: JourneyStepId;
  number: number;
  title: string;
  question: string;
  description: string;
  nextLabel: string;
  previousLabel: string;
  toolLabels: readonly string[];
};

export type JourneyRenderActions = {
  activeStep: JourneyStepId;
  selectStep: (step: JourneyStepId) => void;
  goToPreviousStep: () => void;
  goToNextStep: () => void;
  goToTool: (toolId: string) => void;
};

export const JOURNEY_STEPS: readonly JourneyStepDefinition[] = [
  {
    id: "property",
    number: 1,
    title: "找到物件",
    question: "我現在看的是哪一間房？",
    description: "先輸入物件條件，或從歷史成交中找到可進一步分析的物件。",
    nextLabel: "看地點與市場",
    previousLabel: "返回首頁",
    toolLabels: ["Property Finder", "Property Search"],
  },
  {
    id: "location",
    number: 2,
    title: "看地點與市場",
    question: "住在這裡方便嗎？區域市場有什麼資料？",
    description: "分開查看生活機能、通勤、地形與官方市場資料，這些資訊只供研究參考，不會合成分數或自動影響估價。",
    nextLabel: "確認合理價格",
    previousLabel: "找到物件",
    toolLabels: ["Location Insight", "Terrain Risk", "Commute Livability", "Market Insight"],
  },
  {
    id: "price",
    number: 3,
    title: "確認合理價格",
    question: "這間房的開價有沒有官方成交依據？",
    description: "先確認官方可比成交與估價狀態，再決定是否繼續進行資金試算。",
    nextLabel: "計算資金與稅務",
    previousLabel: "看地點與市場",
    toolLabels: ["Valuation", "Official trend", "Comparable evidence", "Property Search"],
  },
  {
    id: "affordability",
    number: 4,
    title: "計算資金與稅務",
    question: "頭期、月付、持有成本與稅務條件如何？",
    description: "分開查看貸款試算、每月持有成本與稅務快篩，不將試算結果當作正式結論。",
    nextLabel: "儲存並比較",
    previousLabel: "確認合理價格",
    toolLabels: ["Loan", "Holding Cost", "TaxOracle"],
  },
  {
    id: "decision",
    number: 5,
    title: "儲存、比較與決定下一步",
    question: "資料是否足夠，我接下來要做什麼？",
    description: "將已確認資料整理成案件，查看缺少項目、看屋問題、出價方案與其他案件差異。",
    nextLabel: "回到第一步",
    previousLabel: "計算資金與稅務",
    toolLabels: ["Viewing Decision", "Property Case", "Comparison", "Print / export"],
  },
];

const TOOL_STEP_MAP: Readonly<Record<string, JourneyStepId>> = {
  "property-finder": "property",
  "property-search": "property",
  "location-insight": "location",
  commute: "location",
  "terrain-risk": "location",
  "market-insight": "location",
  valuation: "price",
  loan: "affordability",
  "holding-cost": "affordability",
  taxoracle: "affordability",
  "property-case": "decision",
  comparison: "decision",
};

export function getPreviousJourneyStep(step: JourneyStepId): JourneyStepId | undefined {
  const index = JOURNEY_STEPS.findIndex((item) => item.id === step);
  return index > 0 ? JOURNEY_STEPS[index - 1]?.id : undefined;
}

export function getNextJourneyStep(step: JourneyStepId): JourneyStepId | undefined {
  const index = JOURNEY_STEPS.findIndex((item) => item.id === step);
  return index >= 0 && index < JOURNEY_STEPS.length - 1 ? JOURNEY_STEPS[index + 1]?.id : undefined;
}

export function addVisitedJourneyStep(visited: readonly JourneyStepId[], step: JourneyStepId): JourneyStepId[] {
  return visited.includes(step) ? [...visited] : [...visited, step];
}

export function getJourneyStepForTool(tool: string): JourneyStepId | undefined {
  return TOOL_STEP_MAP[tool];
}
