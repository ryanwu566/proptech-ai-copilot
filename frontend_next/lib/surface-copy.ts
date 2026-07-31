import type { ExperienceLocale } from "@/lib/experience-i18n";

export type TerrainSurfaceCopy = {
  title: string; description: string; warning: string; locationFrom: string;
  address: string; addressPlaceholder: string; city: string; district: string; road: string;
  latitude: string; longitude: string; radius: string; useLocation: string; analyze: string;
  compactAnalyze: string; analyzing: string; empty: string; emptyDetail: string; compactMissing: string;
  standaloneMissing: string; helpTitle: string; helpBody: string; layers: Record<string, string>;
  resultKicker: string; summaryTitle: string; summaryMeta: string; referenceTitle: string;
  attach: string; attachDisabled: string; referenceState: string; slope: string; riskFactors: string;
  noRiskFactors: string; recommended: string; layersDisclosure: string; layer: string; status: string;
  vintage: string; limitation: string; external: string; externalLink: string; noDate: string;
  noLimit: string; noExternal: string; missingSources: string; sourceTransparency: string;
  sourceFallbackNotice: string; noSourceLayers: string; source: string; coverage: string;
  updated: string; unknown: string; sourceUnavailable: string; states: Record<string, string>;
  assessment: Record<string, string>; coverageStates: Record<string, string>; risk: Record<string, string>;
};

export type HoldingSurfaceCopy = {
  title: string; description: string; propertyPrice: string; loanPayment: string; monthlyIncome: string;
  area: string; managementFee: string; repairReserve: string; homeTaxRate: string; landTaxRate: string;
  insurance: string; calculate: string; loading: string; invalid: string; empty: string; emptyDetail: string;
  error: string; resultTitle: string; monthlyTotal: string; annualTotal: string; incomeBurden: string;
  annualTax: string; breakdownTitle: string; detailsTitle: string; item: string; monthly: string;
  percentage: string; noBreakdown: string; omitted: string; limitation: string; currency: string;
  unavailable: string;
};

export type ShellSurfaceCopy = {
  beginner: string; expert: string; tour: string; readSummary: string; startListening: string;
  stopListening: string; serviceReady: string; serviceUnavailable: string;
};

export type SurfaceCopy = { terrain: TerrainSurfaceCopy; holding: HoldingSurfaceCopy; shell: ShellSurfaceCopy };

const terrainZh: TerrainSurfaceCopy = {
  title: "地勢／災害風險", description: "檢查既有地勢與災害資料層，僅作看房風險參考。",
  warning: "地勢與災害資料僅供看房風險參考，資料不足或暫時不可用不代表沒有風險。",
  locationFrom: "已沿用目前位置分析的定位資料，請確認來源與限制後再檢查。", address: "物件地址",
  addressPlaceholder: "輸入完整物件地址", city: "縣市", district: "行政區", road: "路段或地點",
  latitude: "緯度", longitude: "經度", radius: "分析半徑（公尺）", useLocation: "沿用目前位置座標",
  analyze: "開始地勢／災害檢查", compactAnalyze: "檢查目前位置風險", analyzing: "檢查中…",
  empty: "尚未完成地勢／災害檢查。", emptyDetail: "輸入地址、路段或座標後開始檢查。",
  compactMissing: "請先完成可信位置分析，再檢查地勢／災害資料。", standaloneMissing: "請先輸入地址、路段或完整座標。",
  helpTitle: "地勢與災害資料限制", helpBody: "各資料層獨立檢查；未涵蓋或不可用不代表沒有風險。",
  layers: { terrain: "地勢", landslide: "山崩", debris_flow: "土石流", flood: "淹水", geological_sensitivity: "地質敏感區", liquefaction: "土壤液化", active_fault: "活動斷層" },
  resultKicker: "地勢／災害檢查", summaryTitle: "資料檢查摘要", summaryMeta: "資料狀態與限制會隨來源回應更新。",
  referenceTitle: "看房風險參考", attach: "加入案件參考", attachDisabled: "目前無法加入案件參考", referenceState: "目前狀態",
  slope: "地勢狀態", riskFactors: "風險因素", noRiskFactors: "目前沒有可用的風險因素摘要；這不代表沒有風險。",
  recommended: "建議確認項目", layersDisclosure: "查看風險資料層", layer: "圖層", status: "檢查狀態",
  vintage: "資料日期", limitation: "來源與限制", external: "外部資料", externalLink: "查看官方資料",
  noDate: "未提供日期", noLimit: "未提供限制說明", noExternal: "無外部連結", missingSources: "尚未取得的資料來源",
  sourceTransparency: "風險資料來源與限制", sourceFallbackNotice: "地勢與災害資料僅供看房風險參考，資料不足或暫時不可用不代表沒有風險。",
  noSourceLayers: "目前沒有可安全呈現的來源圖層；資料不足不代表沒有風險。", source: "來源", coverage: "涵蓋範圍",
  updated: "資料更新", unknown: "未知", sourceUnavailable: "暫時不可用",
  states: { available: "已檢查", limited: "資料有限", unavailable: "暫時不可用", error: "檢查失敗", skipped: "未檢查" },
  assessment: { matched: "符合", not_matched: "未符合", unavailable: "暫時不可用", not_assessed: "未評估" },
  coverageStates: { covered: "已涵蓋", not_covered: "未涵蓋", unknown: "未知" },
  risk: { high: "較高風險訊號", medium: "中度風險訊號", low: "較低風險訊號", unknown: "風險未知" },
};

const terrainEn: TerrainSurfaceCopy = {
  title: "Terrain Risk", description: "Check existing terrain and hazard layers for viewing risk reference only.",
  warning: "Terrain and hazard data is for viewing risk reference only. Missing or temporarily unavailable data does not mean no risk.",
  locationFrom: "The current location analysis is being reused. Review its source and limitations before checking.", address: "Property address",
  addressPlaceholder: "Enter the full property address", city: "City", district: "District", road: "Road or place",
  latitude: "Latitude", longitude: "Longitude", radius: "Analysis radius (metres)", useLocation: "Use current location coordinates",
  analyze: "Start terrain and hazard check", compactAnalyze: "Check current location risk", analyzing: "Checking…",
  empty: "Terrain and hazard check has not started.", emptyDetail: "Enter an address, road, or coordinates to begin.",
  compactMissing: "Complete a trusted location analysis before checking terrain and hazard data.", standaloneMissing: "Enter an address, road, or complete coordinates first.",
  helpTitle: "Terrain and hazard data limits", helpBody: "Layers are checked independently; uncovered or unavailable data does not mean no risk.",
  layers: { terrain: "Terrain", landslide: "Landslide", debris_flow: "Debris flow", flood: "Flood", geological_sensitivity: "Geological sensitivity", liquefaction: "Liquefaction", active_fault: "Active fault" },
  resultKicker: "Terrain and hazard check", summaryTitle: "Data check summary", summaryMeta: "Data status and limitations follow each source response.",
  referenceTitle: "Viewing risk reference", attach: "Add case reference", attachDisabled: "Case reference is unavailable", referenceState: "Current state",
  slope: "Terrain state", riskFactors: "Risk factors", noRiskFactors: "No risk-factor summary is available; this does not mean no risk.",
  recommended: "Checks to consider", layersDisclosure: "View risk data layers", layer: "Layer", status: "Check status",
  vintage: "Data date", limitation: "Source and limitation", external: "External data", externalLink: "View official data",
  noDate: "Date not provided", noLimit: "Limitation not provided", noExternal: "No external link", missingSources: "Sources not available",
  sourceTransparency: "Risk data sources and limitations", sourceFallbackNotice: "Terrain and hazard data is for viewing risk reference only. Missing or temporarily unavailable data does not mean no risk.",
  noSourceLayers: "No source layers can be safely shown; missing data does not mean no risk.", source: "Source", coverage: "Coverage",
  updated: "Data updated", unknown: "Unknown", sourceUnavailable: "Temporarily unavailable",
  states: { available: "Checked", limited: "Limited data", unavailable: "Temporarily unavailable", error: "Check failed", skipped: "Not checked" },
  assessment: { matched: "Matched", not_matched: "Not matched", unavailable: "Temporarily unavailable", not_assessed: "Not assessed" },
  coverageStates: { covered: "Covered", not_covered: "Not covered", unknown: "Unknown" },
  risk: { high: "Higher risk signal", medium: "Moderate risk signal", low: "Lower risk signal", unknown: "Risk unknown" },
};

const terrainJa: TerrainSurfaceCopy = { ...terrainEn, title: "地形・災害リスク", description: "既存の地形・災害データ層を確認します。内見時のリスク参考情報です。", warning: "地形・災害データは内見時のリスク参考情報です。データ不足や一時利用不可は、リスクがないことを意味しません。", address: "物件住所", addressPlaceholder: "物件の住所を入力", city: "市・県", district: "区・郡", road: "道路または場所", latitude: "緯度", longitude: "経度", radius: "分析半径（メートル）", useLocation: "現在の位置座標を使用", analyze: "地形・災害を確認", compactAnalyze: "現在地のリスクを確認", analyzing: "確認中…", empty: "地形・災害の確認はまだ実行されていません。", emptyDetail: "住所、道路、または座標を入力してください。", compactMissing: "信頼できる位置分析を先に完了してください。", standaloneMissing: "住所、道路、または完全な座標を入力してください。", helpTitle: "地形・災害データの制限", helpBody: "各層は個別に確認されます。対象外や利用不可は、リスクがないことを意味しません。", resultKicker: "地形・災害の確認", summaryTitle: "データ確認の概要", summaryMeta: "データの状態と制限は各ソースの応答に従います。", referenceTitle: "内見時のリスク参考", attach: "案件の参考情報に追加", attachDisabled: "案件の参考情報に追加できません", referenceState: "現在の状態", slope: "地形の状態", riskFactors: "リスク要因", noRiskFactors: "利用できるリスク要因の概要がありません。リスクがないことを意味しません。", recommended: "確認を検討する項目", layersDisclosure: "リスクデータ層を見る", layer: "データ層", status: "確認状態", vintage: "データ日付", limitation: "ソースと制限", external: "外部データ", externalLink: "公式データを見る", noDate: "日付なし", noLimit: "制限の記載なし", noExternal: "外部リンクなし", missingSources: "取得できないソース", sourceTransparency: "リスクデータのソースと制限", sourceFallbackNotice: "地形・災害データは内見時のリスク参考情報です。データ不足や一時利用不可は、リスクがないことを意味しません。", noSourceLayers: "安全に表示できるソース層がありません。データ不足はリスクがないことを意味しません。", source: "ソース", coverage: "対象範囲", updated: "データ更新", unknown: "不明", sourceUnavailable: "一時利用不可", layers: { terrain: "地形", landslide: "山崩れ", debris_flow: "土石流", flood: "洪水", geological_sensitivity: "地質敏感区域", liquefaction: "液状化", active_fault: "活断層" }, states: { available: "確認済み", limited: "限定的", unavailable: "一時利用不可", error: "確認失敗", skipped: "未確認" }, assessment: { matched: "該当", not_matched: "非該当", unavailable: "一時利用不可", not_assessed: "未評価" }, coverageStates: { covered: "対象", not_covered: "対象外", unknown: "不明" }, risk: { high: "高いリスク信号", medium: "中程度のリスク信号", low: "低いリスク信号", unknown: "リスク不明" } };

const terrainKo: TerrainSurfaceCopy = { ...terrainEn, title: "지형·재해 위험", description: "기존 지형·재해 데이터 레이어를 확인합니다. 집 보기 위험 참고용입니다.", warning: "지형·재해 데이터는 집 보기 위험 참고용입니다. 데이터 부족이나 일시적 사용 불가는 위험이 없다는 뜻이 아닙니다.", address: "물건 주소", addressPlaceholder: "물건의 전체 주소 입력", city: "시·현", district: "구·군", road: "도로 또는 장소", latitude: "위도", longitude: "경도", radius: "분석 반경(미터)", useLocation: "현재 위치 좌표 사용", analyze: "지형·재해 확인 시작", compactAnalyze: "현재 위치 위험 확인", analyzing: "확인 중…", empty: "지형·재해 확인을 아직 시작하지 않았습니다.", emptyDetail: "주소, 도로 또는 좌표를 입력하세요.", compactMissing: "신뢰할 수 있는 위치 분석을 먼저 완료하세요.", standaloneMissing: "주소, 도로 또는 완전한 좌표를 먼저 입력하세요.", helpTitle: "지형·재해 데이터 제한", helpBody: "각 레이어는 독립적으로 확인됩니다. 미포함 또는 사용 불가는 위험이 없다는 뜻이 아닙니다.", resultKicker: "지형·재해 확인", summaryTitle: "데이터 확인 요약", summaryMeta: "데이터 상태와 제한은 각 출처 응답을 따릅니다.", referenceTitle: "집 보기 위험 참고", attach: "사건 참고 정보에 추가", attachDisabled: "사건 참고 정보에 추가할 수 없음", referenceState: "현재 상태", slope: "지형 상태", riskFactors: "위험 요인", noRiskFactors: "사용 가능한 위험 요인 요약이 없습니다. 위험이 없다는 뜻이 아닙니다.", recommended: "확인할 항목", layersDisclosure: "위험 데이터 레이어 보기", layer: "레이어", status: "확인 상태", vintage: "데이터 날짜", limitation: "출처와 제한", external: "외부 데이터", externalLink: "공식 데이터 보기", noDate: "날짜 없음", noLimit: "제한 정보 없음", noExternal: "외부 링크 없음", missingSources: "사용할 수 없는 출처", sourceTransparency: "위험 데이터 출처와 제한", sourceFallbackNotice: "지형·재해 데이터는 집 보기 위험 참고용입니다. 데이터 부족이나 일시적 사용 불가는 위험이 없다는 뜻이 아닙니다.", noSourceLayers: "안전하게 표시할 출처 레이어가 없습니다. 데이터 부족은 위험이 없다는 뜻이 아닙니다.", source: "출처", coverage: "범위", updated: "데이터 갱신", unknown: "알 수 없음", sourceUnavailable: "일시적으로 사용할 수 없음", layers: { terrain: "지형", landslide: "산사태", debris_flow: "토석류", flood: "침수", geological_sensitivity: "지질 민감 지역", liquefaction: "액상화", active_fault: "활성 단층" }, states: { available: "확인됨", limited: "제한적 데이터", unavailable: "일시적 사용 불가", error: "확인 실패", skipped: "확인하지 않음" }, assessment: { matched: "해당", not_matched: "해당 없음", unavailable: "일시적 사용 불가", not_assessed: "평가하지 않음" }, coverageStates: { covered: "포함", not_covered: "미포함", unknown: "알 수 없음" }, risk: { high: "높은 위험 신호", medium: "중간 위험 신호", low: "낮은 위험 신호", unknown: "위험 알 수 없음" } };

const holdingZh: HoldingSurfaceCopy = { title: "持有成本", description: "估算每月與每年的持有成本，僅作資金規劃參考，不是核貸或購買建議。", propertyPrice: "房屋價格（萬元）", loanPayment: "每月貸款支出（萬元）", monthlyIncome: "每月收入（萬元，可選）", area: "面積（坪，可選）", managementFee: "管理費（每坪／月）", repairReserve: "修繕準備金（每坪／月）", homeTaxRate: "房屋稅年率", landTaxRate: "地價稅年率", insurance: "年保險費", calculate: "計算持有成本", loading: "計算中…", invalid: "請先輸入有效房屋價格。", empty: "尚未計算持有成本。", emptyDetail: "輸入房屋價格後開始計算。", error: "持有成本目前無法計算，請稍後再試。", resultTitle: "持有成本摘要", monthlyTotal: "每月持有成本", annualTotal: "每年持有成本", incomeBurden: "收入負擔比例", annualTax: "年度稅費估算", breakdownTitle: "每月成本分布", detailsTitle: "查看持有成本明細", item: "項目", monthly: "每月金額", percentage: "占比", noBreakdown: "目前沒有可用的成本分布資料。", omitted: "另有 {count} 項成本未在圖表中顯示。", limitation: "計算結果來自目前輸入與既有規則；不代表實際帳單或貸款核准。", currency: "萬元", unavailable: "目前無可用資料" };
const holdingEn: HoldingSurfaceCopy = { title: "Holding Cost", description: "Estimate monthly and annual ownership costs for financial planning reference only; this is not a lending or purchase recommendation.", propertyPrice: "Property price (ten-thousand NTD)", loanPayment: "Monthly loan payment (ten-thousand NTD)", monthlyIncome: "Monthly income (ten-thousand NTD, optional)", area: "Area (ping, optional)", managementFee: "Management fee (per ping/month)", repairReserve: "Repair reserve (per ping/month)", homeTaxRate: "Annual home tax rate", landTaxRate: "Annual land tax rate", insurance: "Annual insurance", calculate: "Calculate holding cost", loading: "Calculating…", invalid: "Enter a valid property price first.", empty: "Holding cost has not been calculated.", emptyDetail: "Enter the property price to begin.", error: "Holding cost is temporarily unavailable. Please try again later.", resultTitle: "Holding cost summary", monthlyTotal: "Monthly holding cost", annualTotal: "Annual holding cost", incomeBurden: "Income burden", annualTax: "Annual tax estimate", breakdownTitle: "Monthly cost breakdown", detailsTitle: "View holding cost details", item: "Item", monthly: "Monthly amount", percentage: "Share", noBreakdown: "No cost breakdown is available.", omitted: "{count} additional cost items are omitted from the chart.", limitation: "This result uses current inputs and existing rules; it is not an actual bill or loan approval.", currency: "ten-thousand NTD", unavailable: "No data available" };
const holdingJa: HoldingSurfaceCopy = { ...holdingEn, title: "保有コスト", description: "月次・年次の保有コストを資金計画の参考として計算します。融資や購入の推奨ではありません。", propertyPrice: "物件価格（万NTD）", loanPayment: "月々のローン支出（万NTD）", monthlyIncome: "月収（万NTD、任意）", area: "面積（坪、任意）", managementFee: "管理費（坪／月）", repairReserve: "修繕準備金（坪／月）", insurance: "年間保険料", calculate: "保有コストを計算", loading: "計算中…", invalid: "有効な物件価格を入力してください。", empty: "保有コストはまだ計算されていません。", emptyDetail: "物件価格を入力して開始してください。", error: "保有コストを利用できません。後でもう一度お試しください。", resultTitle: "保有コストの概要", monthlyTotal: "月間保有コスト", annualTotal: "年間保有コスト", incomeBurden: "収入負担率", annualTax: "年間税額の推定", breakdownTitle: "月間コストの内訳", detailsTitle: "保有コストの詳細を見る", item: "項目", monthly: "月額", percentage: "割合", noBreakdown: "利用できるコスト内訳がありません。", omitted: "グラフに表示していないコストが {count} 件あります。", limitation: "現在の入力と既存ルールによる結果であり、実際の請求額や融資承認を示しません。", currency: "万NTD", unavailable: "利用できるデータがありません" };
const holdingKo: HoldingSurfaceCopy = { ...holdingEn, title: "보유 비용", description: "월·연간 보유 비용을 자금 계획 참고용으로 계산합니다. 대출이나 구매 추천이 아닙니다.", propertyPrice: "매물 가격(만 NTD)", loanPayment: "월 대출 지출(만 NTD)", monthlyIncome: "월 소득(만 NTD, 선택)", area: "면적(평, 선택)", managementFee: "관리비(평/월)", repairReserve: "수선 준비금(평/월)", insurance: "연간 보험료", calculate: "보유 비용 계산", loading: "계산 중…", invalid: "유효한 매물 가격을 먼저 입력하세요.", empty: "보유 비용을 아직 계산하지 않았습니다.", emptyDetail: "매물 가격을 입력해 시작하세요.", error: "보유 비용을 사용할 수 없습니다. 잠시 후 다시 시도하세요.", resultTitle: "보유 비용 요약", monthlyTotal: "월 보유 비용", annualTotal: "연 보유 비용", incomeBurden: "소득 부담률", annualTax: "연간 세금 추정", breakdownTitle: "월 비용 내역", detailsTitle: "보유 비용 상세 보기", item: "항목", monthly: "월 금액", percentage: "비중", noBreakdown: "사용 가능한 비용 내역이 없습니다.", omitted: "차트에 표시하지 않은 비용 {count}개가 있습니다.", limitation: "현재 입력과 기존 규칙에 따른 결과이며 실제 청구액이나 대출 승인을 뜻하지 않습니다.", currency: "만 NTD", unavailable: "사용 가능한 데이터 없음" };

const shell: ShellSurfaceCopy = { beginner: "新手模式", expert: "專家模式", tour: "產品導覽", readSummary: "朗讀目前摘要", startListening: "開始聆聽", stopListening: "停止聆聽", serviceReady: "服務可用", serviceUnavailable: "服務暫時不可用" };
const byLocale: Record<ExperienceLocale, SurfaceCopy> = {
  "zh-TW": { terrain: terrainZh, holding: holdingZh, shell },
  en: { terrain: terrainEn, holding: holdingEn, shell: { ...shell, beginner: "Beginner mode", expert: "Expert mode", tour: "Product tour", readSummary: "Read current summary aloud", startListening: "Start listening", stopListening: "Stop listening", serviceReady: "Service available", serviceUnavailable: "Service temporarily unavailable" } },
  ja: { terrain: terrainJa, holding: holdingJa, shell: { ...shell, beginner: "初心者モード", expert: "専門モード", tour: "製品ツアー", readSummary: "概要を読み上げる", startListening: "音声入力を開始", stopListening: "音声入力を停止", serviceReady: "サービス利用可能", serviceUnavailable: "サービス一時停止" } },
  ko: { terrain: terrainKo, holding: holdingKo, shell: { ...shell, beginner: "초보자 모드", expert: "전문가 모드", tour: "제품 둘러보기", readSummary: "현재 요약 읽기", startListening: "듣기 시작", stopListening: "듣기 중지", serviceReady: "서비스 사용 가능", serviceUnavailable: "서비스 일시 불가" } },
};

export function getSurfaceCopy(locale: ExperienceLocale): SurfaceCopy {
  return byLocale[locale] ?? byLocale["zh-TW"];
}
