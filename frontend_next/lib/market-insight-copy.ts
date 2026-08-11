export type MarketInsightLocale = "zh-TW" | "en" | "ja" | "ko";

export type MarketInsightCopy = {
  summary: string;
  median: string;
  averageDirect: string;
  averageNtdSqm: string;
  medianTotal: string;
  count: string;
  countUnit: string;
  period: string;
  source: string;
  sourceUpdated: string;
  coverage: string;
  covered: string;
  coverageUnknown: string;
  notCovered: string;
  freshness: string;
  sample: string;
  included: string;
  excluded: string;
  periodComparison: string;
  recentAverageSix: string;
  recentAverageN: string;
  highestAverage: string;
  lowestAverage: string;
  recentTransactionsSix: string;
  recentTransactionsN: string;
  priceTrend: string;
  volumeTrend: string;
  history: string;
  historyAverage: string;
  historyCount: string;
  chartNoHistory: string;
  chartOnePeriod: string;
  priceChartSummary: string;
  volumeChartSummary: string;
  initial: string;
  loading: string;
  noData: string;
  unavailable: string;
  networkError: string;
  supportReference: string;
  distributions: string;
  priceDistribution: string;
  buildingDistribution: string;
  ageDistribution: string;
  methodology: string;
  print: string;
  reportTitle: string;
  boundary: string;
  snapshot: string;
  generated: string;
  region: string;
  unitWanPerPing: string;
};

export const MARKET_INSIGHT_COPY: Record<MarketInsightLocale, MarketInsightCopy> = {
  "zh-TW": {
    summary: "市場摘要",
    median: "中位單價（元／平方公尺）",
    averageDirect: "平均單價（萬元／坪）",
    averageNtdSqm: "平均單價（元／平方公尺）",
    medianTotal: "中位總價（元）",
    count: "本期交易筆數",
    countUnit: "筆",
    period: "資料期別",
    source: "資料來源",
    sourceUpdated: "資料更新",
    coverage: "涵蓋狀態",
    covered: "已有資料涵蓋",
    coverageUnknown: "涵蓋狀態尚未確認",
    notCovered: "目前未確認有資料涵蓋",
    freshness: "資料新鮮度",
    sample: "樣本狀態",
    included: "納入筆數",
    excluded: "排除筆數",
    periodComparison: "較上期",
    recentAverageSix: "近六期平均單價",
    recentAverageN: "近 {{count}} 期平均單價",
    highestAverage: "最高平均單價",
    lowestAverage: "最低平均單價",
    recentTransactionsSix: "近六期交易筆數",
    recentTransactionsN: "近 {{count}} 期交易筆數",
    priceTrend: "平均單價趨勢",
    volumeTrend: "交易筆數趨勢",
    history: "最近期別市場資料",
    historyAverage: "平均單價（萬元／坪）",
    historyCount: "交易筆數（筆）",
    chartNoHistory: "目前沒有有效歷史期別資料。",
    chartOnePeriod: "目前只有 1 個有效期別，暫無足夠資料形成趨勢。",
    priceChartSummary: "顯示 {{count}} 個有效期別的平均單價，未補齊缺失期別或推估中間值。",
    volumeChartSummary: "顯示 {{count}} 個有效期別的交易筆數，未將缺失資料補零。",
    initial: "請選擇縣市與行政區後查詢市場資料。",
    loading: "查詢中…",
    noData: "目前此區域尚無足夠的官方市場資料。",
    unavailable: "市場資料暫時無法使用，請稍後再試。",
    networkError: "目前無法連線至市場資料服務，請稍後重試。",
    supportReference: "參考代碼",
    distributions: "資料分布",
    priceDistribution: "價格分布",
    buildingDistribution: "建物類型分布",
    ageDistribution: "屋齡分布",
    methodology: "方法與限制",
    print: "列印目前摘要",
    reportTitle: "市場洞察摘要",
    boundary: "市場資料只供區域交易參考，不是估價、核貸或購買建議。",
    snapshot: "安全案件快照",
    generated: "產生時間",
    region: "區域",
    unitWanPerPing: "萬元／坪",
  },
  en: {
    summary: "Market summary",
    median: "Median unit price (NTD/sqm)",
    averageDirect: "Average unit price (NTD 10,000/ping)",
    averageNtdSqm: "Average unit price (NTD/sqm)",
    medianTotal: "Median total price (NTD)",
    count: "Transactions in period",
    countUnit: "records",
    period: "Data period",
    source: "Source",
    sourceUpdated: "Source updated",
    coverage: "Coverage",
    covered: "Data covered",
    coverageUnknown: "Coverage has not been confirmed",
    notCovered: "Data coverage is not currently confirmed",
    freshness: "Freshness",
    sample: "Sample status",
    included: "Included",
    excluded: "Excluded",
    periodComparison: "Versus previous period",
    recentAverageSix: "Six-period average unit price",
    recentAverageN: "{{count}}-period average unit price",
    highestAverage: "Highest average unit price",
    lowestAverage: "Lowest average unit price",
    recentTransactionsSix: "Transactions across six periods",
    recentTransactionsN: "Transactions across {{count}} periods",
    priceTrend: "Average unit price trend",
    volumeTrend: "Transaction count trend",
    history: "Recent-period market data",
    historyAverage: "Average unit price (NTD 10,000/ping)",
    historyCount: "Transactions (records)",
    chartNoHistory: "No valid historical periods are currently available.",
    chartOnePeriod: "Only one valid period is available, which is not enough to form a trend.",
    priceChartSummary: "Shows average unit prices for {{count}} valid periods without filling missing periods or estimating intermediate values.",
    volumeChartSummary: "Shows transaction counts for {{count}} valid periods without filling missing data with zero.",
    initial: "Select a county and district to query market data.",
    loading: "Searching…",
    noData: "This area does not currently have enough official market data.",
    unavailable: "Market data is temporarily unavailable. Please try again later.",
    networkError: "The market data service cannot be reached. Please try again later.",
    supportReference: "Reference code",
    distributions: "Distributions",
    priceDistribution: "Price distribution",
    buildingDistribution: "Building type distribution",
    ageDistribution: "Age-band distribution",
    methodology: "Methodology and limits",
    print: "Print current summary",
    reportTitle: "Market Insight Summary",
    boundary: "Market data is regional transaction reference only, not an appraisal, lending decision, or purchase recommendation.",
    snapshot: "Safe property-case snapshot",
    generated: "Generated",
    region: "Region",
    unitWanPerPing: "NTD 10,000/ping",
  },
  ja: {
    summary: "市場概要",
    median: "中央値単価（台湾ドル／㎡）",
    averageDirect: "平均単価（万元／坪）",
    averageNtdSqm: "平均単価（台湾ドル／㎡）",
    medianTotal: "中央値総額（台湾ドル）",
    count: "当期取引件数",
    countUnit: "件",
    period: "データ期間",
    source: "出典",
    sourceUpdated: "更新日",
    coverage: "カバレッジ",
    covered: "データあり",
    coverageUnknown: "カバレッジは未確認です",
    notCovered: "現在データのカバレッジを確認できません",
    freshness: "更新状態",
    sample: "標本状態",
    included: "採用件数",
    excluded: "除外件数",
    periodComparison: "前期比",
    recentAverageSix: "直近6期の平均単価",
    recentAverageN: "直近 {{count}} 期の平均単価",
    highestAverage: "最高平均単価",
    lowestAverage: "最低平均単価",
    recentTransactionsSix: "直近6期の取引件数",
    recentTransactionsN: "直近 {{count}} 期の取引件数",
    priceTrend: "平均単価の推移",
    volumeTrend: "取引件数の推移",
    history: "直近期間の市場データ",
    historyAverage: "平均単価（万元／坪）",
    historyCount: "取引件数（件）",
    chartNoHistory: "有効な過去期間データは現在ありません。",
    chartOnePeriod: "有効な期間は1件のみで、傾向を形成するには不十分です。",
    priceChartSummary: "欠損期間の補完や中間値の推定をせず、{{count}} 件の有効期間の平均単価を表示します。",
    volumeChartSummary: "欠損データをゼロで補完せず、{{count}} 件の有効期間の取引件数を表示します。",
    initial: "県市と行政区を選択して市場データを検索してください。",
    loading: "検索中…",
    noData: "この地域には現在、十分な公式市場データがありません。",
    unavailable: "市場データは一時的に利用できません。後でもう一度お試しください。",
    networkError: "市場データサービスに接続できません。後でもう一度お試しください。",
    supportReference: "参照コード",
    distributions: "分布",
    priceDistribution: "価格分布",
    buildingDistribution: "建物種類の分布",
    ageDistribution: "築年帯の分布",
    methodology: "方法と制限",
    print: "現在の概要を印刷",
    reportTitle: "市場洞察概要",
    boundary: "市場データは地域取引の参考であり、査定・融資判断・購入推奨ではありません。",
    snapshot: "安全な案件スナップショット",
    generated: "生成日時",
    region: "地域",
    unitWanPerPing: "万元／坪",
  },
  ko: {
    summary: "시장 요약",
    median: "중위 단가 (NTD/㎡)",
    averageDirect: "평균 단가 (만 NTD/평)",
    averageNtdSqm: "평균 단가 (NTD/㎡)",
    medianTotal: "중위 총액 (NTD)",
    count: "해당 기간 거래 건수",
    countUnit: "건",
    period: "데이터 기간",
    source: "출처",
    sourceUpdated: "업데이트",
    coverage: "데이터 범위",
    covered: "데이터 있음",
    coverageUnknown: "데이터 범위가 아직 확인되지 않았습니다",
    notCovered: "현재 데이터 범위를 확인할 수 없습니다",
    freshness: "최신성",
    sample: "표본 상태",
    included: "포함",
    excluded: "제외",
    periodComparison: "이전 기간 대비",
    recentAverageSix: "최근 6개 기간 평균 단가",
    recentAverageN: "최근 {{count}}개 기간 평균 단가",
    highestAverage: "최고 평균 단가",
    lowestAverage: "최저 평균 단가",
    recentTransactionsSix: "최근 6개 기간 거래 건수",
    recentTransactionsN: "최근 {{count}}개 기간 거래 건수",
    priceTrend: "평균 단가 추이",
    volumeTrend: "거래 건수 추이",
    history: "최근 기간 시장 데이터",
    historyAverage: "평균 단가 (만 NTD/평)",
    historyCount: "거래 건수 (건)",
    chartNoHistory: "현재 유효한 과거 기간 데이터가 없습니다.",
    chartOnePeriod: "유효한 기간이 1개뿐이어서 추이를 형성하기에 충분하지 않습니다.",
    priceChartSummary: "누락 기간을 채우거나 중간값을 추정하지 않고 유효한 {{count}}개 기간의 평균 단가를 표시합니다.",
    volumeChartSummary: "누락 데이터를 0으로 채우지 않고 유효한 {{count}}개 기간의 거래 건수를 표시합니다.",
    initial: "시·군과 행정구를 선택해 시장 데이터를 조회하세요.",
    loading: "조회 중…",
    noData: "현재 이 지역에는 충분한 공식 시장 데이터가 없습니다.",
    unavailable: "시장 데이터를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도하세요.",
    networkError: "시장 데이터 서비스에 연결할 수 없습니다. 잠시 후 다시 시도하세요.",
    supportReference: "참조 코드",
    distributions: "분포",
    priceDistribution: "가격 분포",
    buildingDistribution: "건물 유형 분포",
    ageDistribution: "연식 구간 분포",
    methodology: "방법과 제한",
    print: "현재 요약 인쇄",
    reportTitle: "시장 인사이트 요약",
    boundary: "시장 데이터는 지역 거래 참고용이며 감정, 대출 결정 또는 구매 권고가 아닙니다.",
    snapshot: "안전한 사건 스냅샷",
    generated: "생성 시각",
    region: "지역",
    unitWanPerPing: "만 NTD/평",
  },
};

export function getMarketInsightCopy(locale: string): MarketInsightCopy {
  return MARKET_INSIGHT_COPY[locale as MarketInsightLocale] ?? MARKET_INSIGHT_COPY["zh-TW"];
}

export function formatMarketCopy(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{{${key}}}`, String(value)),
    template,
  );
}
