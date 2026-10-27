import type { CopyCatalogue } from "./copy-catalogue";

/**
 * Destination route card copy. Backend route `message`/`disclaimer` text is fixed product copy in one
 * language, so the card renders these localized equivalents instead. Provider names stay unchanged.
 */
export type CommuteRouteCopyKey =
  | "title" | "intro" | "destination" | "destinationPlaceholder" | "mode" | "estimate" | "estimating" | "looking"
  | "modeTransit" | "modeDriving" | "modeWalking"
  | "duration" | "distance" | "source" | "checked" | "simulatedSuffix" | "mockBanner" | "sourceMock" | "sourceNone"
  | "mockNote" | "disclaimer" | "needsLocation" | "livabilityNotice"
  | "destination_required" | "invalid_input" | "provider_timeout" | "configuration_error" | "provider_error" | "malformed_response" | "route_not_found";

export const commuteRouteCopy: CopyCatalogue<CommuteRouteCopyKey> = {
  "zh-TW": {
    livabilityNotice: "僅供通勤與生活機能參考，不影響地勢災害、貸款、法律或看房結論。",
    title: "目的地路線時間與距離", intro: "以目前物件位置為起點，查詢指定目的地；周邊大眾運輸資料即使暫時不可用，也不會清除有效路線。",
    destination: "目的地地址", destinationPlaceholder: "例如：台北車站", mode: "交通方式", estimate: "估算通勤", estimating: "查詢中…", looking: "正在查詢路線…",
    modeTransit: "大眾運輸", modeDriving: "開車", modeWalking: "步行",
    duration: "路線時間", distance: "路線距離", source: "資料來源", checked: "查詢時間", simulatedSuffix: "（模擬）",
    mockBanner: "測試／展示模擬路線 — 非 Google 實際結果", sourceMock: "測試／展示模擬路線（非 Google 實際結果）", sourceNone: "無",
    mockNote: "示範估算：非即時 Google 路線結果，僅供操作展示，不可作為真實通勤依據。",
    disclaimer: "通勤時間為外部路線估算，僅供生活機能與可及性參考，不代表實際交通、估價或看房結論。",
    needsLocation: "請先完成位置分析，才能使用目前房屋位置查詢 Google 路線。",
    destination_required: "請輸入通勤目的地。", invalid_input: "輸入資料無效，請檢查後重試。", provider_timeout: "路線服務逾時，請稍後重試。",
    configuration_error: "路線服務尚未完成設定。", provider_error: "路線服務目前無法使用，請稍後重試。", malformed_response: "路線服務回傳了無法讀取的資料。",
    route_not_found: "找不到符合條件的路線，請調整目的地或交通方式。",
  },
  en: {
    livabilityNotice: "For commute and daily-life context only. It does not affect terrain hazard, loan, legal or viewing conclusions.",
    title: "Destination route time and distance", intro: "Routes start from the current property location to the destination you enter. A valid route is kept even if nearby public transport data is temporarily unavailable.",
    destination: "Destination address", destinationPlaceholder: "e.g. Taipei Main Station", mode: "Transport mode", estimate: "Estimate commute", estimating: "Checking…", looking: "Checking route…",
    modeTransit: "Public transport", modeDriving: "Driving", modeWalking: "Walking",
    duration: "Route time", distance: "Route distance", source: "Source", checked: "Checked", simulatedSuffix: " (simulated)",
    mockBanner: "Test / demo simulated route — not an actual Google result", sourceMock: "Test / demo simulated route (not an actual Google result)", sourceNone: "None",
    mockNote: "Demo estimate: not a live Google route result. For demonstration only; do not rely on it as a real commute.",
    disclaimer: "Commute time is an external route estimate for daily-life and accessibility context only. It is not actual traffic, a valuation or a viewing conclusion.",
    needsLocation: "Complete the location check before checking Google routes from the current property location.",
    destination_required: "Enter a commute destination.", invalid_input: "The input is not valid. Check it and try again.", provider_timeout: "The route service timed out. Try again later.",
    configuration_error: "The route service is not configured yet.", provider_error: "The route service is currently unavailable. Try again later.", malformed_response: "The route service returned data that could not be read.",
    route_not_found: "No matching route was found. Adjust the destination or transport mode.",
  },
  ja: {
    livabilityNotice: "通勤と生活利便性の参考情報にすぎず、地形災害、ローン、法律、内見の結論には影響しません。",
    title: "目的地までのルート時間と距離", intro: "現在の物件位置を起点に、指定した目的地までを照会します。周辺の公共交通データが一時的に使えなくても、有効なルートは消えません。",
    destination: "目的地の住所", destinationPlaceholder: "例：台北駅", mode: "交通手段", estimate: "通勤を試算", estimating: "照会中…", looking: "ルートを照会中…",
    modeTransit: "公共交通", modeDriving: "車", modeWalking: "徒歩",
    duration: "ルート時間", distance: "ルート距離", source: "データ出典", checked: "照会日時", simulatedSuffix: "（模擬）",
    mockBanner: "テスト／デモ用の模擬ルート — Google の実際の結果ではありません", sourceMock: "テスト／デモ用の模擬ルート（Google の実際の結果ではありません）", sourceNone: "なし",
    mockNote: "デモ用の試算です。リアルタイムの Google ルート結果ではなく、操作の説明用です。実際の通勤の根拠にはできません。",
    disclaimer: "通勤時間は外部ルートによる試算で、生活利便性とアクセスの参考にすぎません。実際の交通状況、査定、内見の結論を示すものではありません。",
    needsLocation: "現在の物件位置から Google ルートを照会するには、先に位置の確認を完了してください。",
    destination_required: "通勤の目的地を入力してください。", invalid_input: "入力内容が無効です。確認してからやり直してください。", provider_timeout: "ルートサービスがタイムアウトしました。しばらくしてからやり直してください。",
    configuration_error: "ルートサービスはまだ設定されていません。", provider_error: "ルートサービスは現在利用できません。しばらくしてからやり直してください。", malformed_response: "ルートサービスから読み取れないデータが返されました。",
    route_not_found: "条件に合うルートが見つかりません。目的地または交通手段を変更してください。",
  },
  ko: {
    livabilityNotice: "통근과 생활 편의 참고용일 뿐이며 지형 재해, 대출, 법률 또는 집 보기 결론에 영향을 주지 않습니다.",
    title: "목적지 경로 시간과 거리", intro: "현재 부동산 위치를 출발지로 입력한 목적지까지 조회합니다. 주변 대중교통 데이터를 잠시 사용할 수 없어도 유효한 경로는 지워지지 않습니다.",
    destination: "목적지 주소", destinationPlaceholder: "예: 타이베이역", mode: "교통수단", estimate: "통근 추정", estimating: "조회 중…", looking: "경로를 조회하는 중…",
    modeTransit: "대중교통", modeDriving: "자동차", modeWalking: "도보",
    duration: "경로 시간", distance: "경로 거리", source: "데이터 출처", checked: "조회 시각", simulatedSuffix: " (모의)",
    mockBanner: "테스트/데모용 모의 경로 — 실제 Google 결과가 아닙니다", sourceMock: "테스트/데모용 모의 경로(실제 Google 결과가 아님)", sourceNone: "없음",
    mockNote: "데모 추정입니다. 실시간 Google 경로 결과가 아니며 시연용이므로 실제 통근 근거로 사용할 수 없습니다.",
    disclaimer: "통근 시간은 외부 경로 추정치로 생활 편의와 접근성 참고용일 뿐이며, 실제 교통 상황, 감정평가 또는 집 보기 결론을 뜻하지 않습니다.",
    needsLocation: "현재 부동산 위치에서 Google 경로를 조회하려면 먼저 위치 확인을 완료하세요.",
    destination_required: "통근 목적지를 입력하세요.", invalid_input: "입력 내용이 올바르지 않습니다. 확인 후 다시 시도하세요.", provider_timeout: "경로 서비스 응답 시간이 초과되었습니다. 잠시 후 다시 시도하세요.",
    configuration_error: "경로 서비스가 아직 설정되지 않았습니다.", provider_error: "경로 서비스를 현재 사용할 수 없습니다. 잠시 후 다시 시도하세요.", malformed_response: "경로 서비스가 읽을 수 없는 데이터를 반환했습니다.",
    route_not_found: "조건에 맞는 경로를 찾지 못했습니다. 목적지나 교통수단을 바꿔 보세요.",
  },
};
