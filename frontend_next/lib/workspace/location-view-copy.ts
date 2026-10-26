import type { CopyCatalogue } from "../copy-catalogue";
import type { ExperienceLocale } from "../experience-i18n";
// @ts-expect-error Native TS runner extension.
import { translateCopyCatalogue } from "../copy-catalogue.ts";

/**
 * Product-owned copy for the Location workspace view, including legacy sections still rendered for
 * older saved cases. Saved addresses, village names, destinations and provider names are data and
 * are rendered as stored; never translate them here.
 */
export type LocationViewCopyKey =
  | "eyebrow" | "title" | "intro" | "mapLoading"
  | "statusStrip" | "metricProperty" | "metricNearby" | "metricNearbyNote" | "metricCommute"
  | "mapTitle" | "mapAttribution" | "mapChecked" | "notProvided"
  | "commuteTitle" | "commuteDescription" | "routeOnlyTransitUnavailable"
  | "legacyTitle" | "legacyDescription" | "poiSummaryLabel"
  | "poiTransit" | "poiConvenience" | "poiSchool" | "poiPark" | "poiMedical" | "poiRiskFacility"
  | "unknownNotRetrieved" | "poiSummaryMissingTitle" | "poiSummaryMissing" | "poiSummaryItem" | "listSeparator"
  | "riskTitle" | "riskAvailable" | "riskNoMatch" | "riskNoCoverage" | "riskUnavailable" | "riskUnknown" | "riskSourceMissing"
  | "riskReasonSourceUnavailable" | "riskReasonCoverageNotPreserved" | "riskReasonSuccess" | "riskReasonIdentityMismatch" | "riskReasonOther"
  | "riskLimitation" | "riskReasonLimitation"
  | "limitsTitle" | "currentLimits" | "noLimits" | "savedWarnings" | "nextTitle" | "next1" | "next2" | "next3"
  | "routeInvalidated" | "routeUnavailable" | "routeNotSet" | "routeCandidateOnly" | "transitUnavailable"
  | "sourcesTitle" | "sourcePropertyValue" | "sourceNone" | "sourceGoogle" | "sourceTgos" | "sourceNlsc" | "sourceUser" | "sourceSeparator"
  | "adminLocation" | "villageUnconfirmed" | "boundaryVintage"
  | "routeSource" | "routeNeedsReconfirm" | "routeSimulated" | "notRetrieved" | "sourceDated"
  | "transitSource" | "dateNotProvided" | "demographicsSource" | "selectedRoute"
  | "modeTransit" | "modeDriving" | "modeWalking"
  | "distanceMetres" | "distanceKilometres" | "durationMinutes" | "durationHours" | "durationHoursMinutes";

/** Unresolved items on the Location handoff, rendered through copy in the active locale. */
export type LocationUnresolvedKey = "routeInvalidated" | "routeUnavailable" | "routeNotSet" | "routeCandidateOnly" | "transitUnavailable";

export const locationViewCopy: CopyCatalogue<LocationViewCopyKey> = {
  "zh-TW": {
    eyebrow: "案件分析區段", title: "區位與通勤", intro: "這個物件位在什麼位置，周邊有哪些可核對的設施，前往重要目的地是否實際可行？", mapLoading: "正在載入地圖…",
    statusStrip: "區位與通勤狀態", metricProperty: "物件位置", metricNearby: "周邊證據", metricNearbyNote: "案件重開後的摘要會標示為有限證據", metricCommute: "目的地通勤",
    mapTitle: "目前物件位置與周邊證據", mapAttribution: "地圖底圖依畫面標示；點位不是地籍界線", mapChecked: "位置核對：{{date}}", notProvided: "未提供",
    commuteTitle: "目的地通勤證據", commuteDescription: "目的地路線與大眾運輸周邊資料是兩個獨立來源；其中一項不可用時，另一項仍可判讀。",
    routeOnlyTransitUnavailable: "目的地路線可用；大眾運輸周邊資料目前無法取得。",
    legacyTitle: "重要周邊證據", legacyDescription: "以實際設施筆數與距離為主；設施較多不代表物件較好。", poiSummaryLabel: "周邊設施摘要",
    poiTransit: "交通", poiConvenience: "日常便利", poiSchool: "學校", poiPark: "公園綠地", poiMedical: "醫療", poiRiskFacility: "需實地確認設施",
    unknownNotRetrieved: "未知／未取得", poiSummaryMissingTitle: "尚未取得周邊設施摘要", poiSummaryMissing: "此案件尚未保存可供判讀的周邊設施結果。",
    poiSummaryItem: "{{label}} {{value}}", listSeparator: "；",
    riskTitle: "需留意設施的來源與限制", riskAvailable: "已取得來源涵蓋", riskNoMatch: "來源查詢無符合設施，不代表安全", riskNoCoverage: "不在來源涵蓋範圍",
    riskUnavailable: "來源目前無法取得", riskUnknown: "涵蓋未知／未取得", riskSourceMissing: "來源未保存",
    riskReasonSourceUnavailable: "設施來源目前無法取得", riskReasonCoverageNotPreserved: "設施涵蓋未隨快照保存", riskReasonSuccess: "來源查詢成功",
    riskReasonIdentityMismatch: "設施證據與目前地址不一致", riskReasonOther: "依來源提供的查詢狀態；詳見保存限制",
    riskLimitation: "未知涵蓋不代表零處設施或安全。", riskReasonLimitation: "{{reason}}；{{limitation}}",
    limitsTitle: "未知事項與限制", currentLimits: "目前限制", noLimits: "目前沒有阻擋此區段判讀的主要限制。",
    savedWarnings: "先前保存的分析含 {{count}} 則資料品質提醒。",
    nextTitle: "下一步", next1: "加入工作地點、客戶據點或常用車站，逐一比較實際路線。", next2: "對重要設施核對營業狀態、出入口與現場步行條件。", next3: "將無法取得的資料列入看屋或客戶討論清單。",
    routeInvalidated: "先前目的地路線不屬於目前物件", routeUnavailable: "目的地路線目前無法取得", routeNotSet: "尚未設定通勤目的地",
    routeCandidateOnly: "路線僅為模擬、備援或部分結果，不能建立正式通勤就緒狀態。", transitUnavailable: "大眾運輸周邊資料目前無法取得",
    sourcesTitle: "來源與查詢細節", sourcePropertyValue: "{{sources}}；核對時間 {{date}}", sourceNone: "來源未提供",
    sourceGoogle: "Google 地址解析", sourceTgos: "TGOS 地址解析", sourceNlsc: "NLSC 村里界", sourceUser: "使用者確認", sourceSeparator: "、",
    adminLocation: "行政位置", villageUnconfirmed: "村里未確認", boundaryVintage: "；圖資版本 {{vintage}}",
    routeSource: "目的地路線", routeNeedsReconfirm: "物件位置需重新確認", routeSimulated: "模擬／備援路線", notRetrieved: "尚未取得", sourceDated: "{{source}}；{{date}}",
    transitSource: "大眾運輸周邊", dateNotProvided: "日期未提供", demographicsSource: "人口背景",
    selectedRoute: "已選路線：{{destination}} · {{mode}} · {{distance}} · {{duration}}",
    modeTransit: "大眾運輸", modeDriving: "開車", modeWalking: "步行",
    distanceMetres: "{{value}} 公尺", distanceKilometres: "{{value}} 公里", durationMinutes: "約 {{minutes}} 分鐘", durationHours: "{{hours}} 小時", durationHoursMinutes: "{{hours}} 小時 {{minutes}} 分鐘",
  },
  en: {
    eyebrow: "Case analysis section", title: "Location and commute", intro: "Where is this property, which nearby facilities can be verified, and are important destinations realistically reachable?", mapLoading: "Loading map…",
    statusStrip: "Location and commute status", metricProperty: "Property location", metricNearby: "Nearby evidence", metricNearbyNote: "Summaries shown after a case is reopened are marked as limited evidence", metricCommute: "Destination commute",
    mapTitle: "Current property location and nearby evidence", mapAttribution: "Basemap as labelled on the map. The pin is not a cadastral boundary.", mapChecked: "Location checked: {{date}}", notProvided: "Not provided",
    commuteTitle: "Destination commute evidence", commuteDescription: "Destination routes and nearby public transport data are independent sources. When one is unavailable, the other can still be read.",
    routeOnlyTransitUnavailable: "The destination route is available. Nearby public transport data is currently unavailable.",
    legacyTitle: "Key nearby evidence", legacyDescription: "Based on actual facility counts and distances. More facilities do not make a property better.", poiSummaryLabel: "Nearby facility summary",
    poiTransit: "Transport", poiConvenience: "Daily convenience", poiSchool: "Schools", poiPark: "Parks and green space", poiMedical: "Medical", poiRiskFacility: "Facilities to verify on site",
    unknownNotRetrieved: "Unknown / not retrieved", poiSummaryMissingTitle: "Nearby facility summary not retrieved", poiSummaryMissing: "This case has no saved nearby facility results that can be read yet.",
    poiSummaryItem: "{{label}} {{value}}", listSeparator: "; ",
    riskTitle: "Sources and limits for facilities to note", riskAvailable: "Source coverage retrieved", riskNoMatch: "The source query found no matching facilities. This does not mean it is safe.", riskNoCoverage: "Outside source coverage",
    riskUnavailable: "Source currently unavailable", riskUnknown: "Coverage unknown / not retrieved", riskSourceMissing: "Source not saved",
    riskReasonSourceUnavailable: "The facility source is currently unavailable", riskReasonCoverageNotPreserved: "Facility coverage was not saved with the snapshot", riskReasonSuccess: "Source query succeeded",
    riskReasonIdentityMismatch: "Facility evidence does not match the current address", riskReasonOther: "Query status as reported by the source; see saved limits",
    riskLimitation: "Unknown coverage does not mean zero facilities or safety.", riskReasonLimitation: "{{reason}}. {{limitation}}",
    limitsTitle: "Unknowns and limits", currentLimits: "Current limits", noLimits: "No major limit currently blocks reading this section.",
    savedWarnings: "The previously saved analysis includes {{count}} data-quality note(s), recorded in Traditional Chinese only.",
    nextTitle: "Next steps", next1: "Add workplaces, client sites or frequently used stations and compare actual routes one by one.", next2: "For important facilities, verify opening status, entrances and on-site walking conditions.", next3: "Add data that could not be retrieved to your viewing or client discussion list.",
    routeInvalidated: "The previous destination route does not belong to the current property", routeUnavailable: "The destination route is currently unavailable", routeNotSet: "No commute destination has been set",
    routeCandidateOnly: "The route is only simulated, fallback or partial, so commute readiness cannot be established.", transitUnavailable: "Nearby public transport data is currently unavailable",
    sourcesTitle: "Sources and query details", sourcePropertyValue: "{{sources}}; checked {{date}}", sourceNone: "Source not provided",
    sourceGoogle: "Google geocoding", sourceTgos: "TGOS geocoding", sourceNlsc: "NLSC village boundaries", sourceUser: "User confirmation", sourceSeparator: ", ",
    adminLocation: "Administrative location", villageUnconfirmed: "Village not confirmed", boundaryVintage: "; boundary data version {{vintage}}",
    routeSource: "Destination route", routeNeedsReconfirm: "Property location needs to be reconfirmed", routeSimulated: "Simulated / fallback route", notRetrieved: "Not yet retrieved", sourceDated: "{{source}}; {{date}}",
    transitSource: "Nearby public transport", dateNotProvided: "Date not provided", demographicsSource: "Population context",
    selectedRoute: "Selected route: {{destination}} · {{mode}} · {{distance}} · {{duration}}",
    modeTransit: "Public transport", modeDriving: "Driving", modeWalking: "Walking",
    distanceMetres: "{{value}} m", distanceKilometres: "{{value}} km", durationMinutes: "About {{minutes}} min", durationHours: "{{hours}} h", durationHoursMinutes: "{{hours}} h {{minutes}} min",
  },
  ja: {
    eyebrow: "案件分析セクション", title: "立地と通勤", intro: "この物件はどこにあり、周辺で確認できる施設は何か、重要な目的地へ実際に行きやすいかを確認します。", mapLoading: "地図を読み込み中…",
    statusStrip: "立地と通勤の状況", metricProperty: "物件の位置", metricNearby: "周辺の根拠", metricNearbyNote: "案件を開き直した後の概要は、限定的な根拠として表示されます", metricCommute: "目的地への通勤",
    mapTitle: "現在の物件位置と周辺の根拠", mapAttribution: "背景地図は画面の表示に従います。地点は地籍の境界ではありません。", mapChecked: "位置の確認：{{date}}", notProvided: "未提供",
    commuteTitle: "目的地への通勤の根拠", commuteDescription: "目的地ルートと周辺の公共交通データは別々の情報源です。一方が利用できなくても、もう一方は確認できます。",
    routeOnlyTransitUnavailable: "目的地ルートは利用できます。周辺の公共交通データは現在取得できません。",
    legacyTitle: "主な周辺の根拠", legacyDescription: "実際の施設件数と距離を基にしています。施設が多いほど物件が良いという意味ではありません。", poiSummaryLabel: "周辺施設の概要",
    poiTransit: "交通", poiConvenience: "日常の利便", poiSchool: "学校", poiPark: "公園・緑地", poiMedical: "医療", poiRiskFacility: "現地確認が必要な施設",
    unknownNotRetrieved: "不明／未取得", poiSummaryMissingTitle: "周辺施設の概要は未取得です", poiSummaryMissing: "この案件には、判断に使える周辺施設の結果がまだ保存されていません。",
    poiSummaryItem: "{{label}} {{value}}", listSeparator: "、",
    riskTitle: "注意が必要な施設の出典と制約", riskAvailable: "出典の対象範囲を取得済み", riskNoMatch: "出典の照会で該当施設はありませんでした。安全という意味ではありません", riskNoCoverage: "出典の対象範囲外",
    riskUnavailable: "出典を現在取得できません", riskUnknown: "対象範囲は不明／未取得", riskSourceMissing: "出典は保存されていません",
    riskReasonSourceUnavailable: "施設の出典を現在取得できません", riskReasonCoverageNotPreserved: "施設の対象範囲はスナップショットと一緒に保存されていません", riskReasonSuccess: "出典の照会に成功しました",
    riskReasonIdentityMismatch: "施設の根拠が現在の住所と一致しません", riskReasonOther: "出典が示す照会状況です。保存された制約をご確認ください",
    riskLimitation: "対象範囲が不明でも、施設がゼロ件である、または安全であるという意味ではありません。", riskReasonLimitation: "{{reason}}。{{limitation}}",
    limitsTitle: "不明点と制約", currentLimits: "現在の制約", noLimits: "現在、このセクションの判断を妨げる主な制約はありません。",
    savedWarnings: "以前に保存された分析には、繁体字中国語でのみ記録されたデータ品質の注記が {{count}} 件あります。",
    nextTitle: "次のステップ", next1: "職場、取引先、よく使う駅を追加し、実際のルートを一つずつ比較します。", next2: "重要な施設は、営業状況、出入口、現地の歩行条件を確認します。", next3: "取得できなかったデータを内見や顧客との相談リストに加えます。",
    routeInvalidated: "以前の目的地ルートは現在の物件のものではありません", routeUnavailable: "目的地ルートは現在取得できません", routeNotSet: "通勤の目的地がまだ設定されていません",
    routeCandidateOnly: "ルートは模擬・代替・部分的な結果のみのため、通勤の準備状況を確定できません。", transitUnavailable: "周辺の公共交通データは現在取得できません",
    sourcesTitle: "出典と照会の詳細", sourcePropertyValue: "{{sources}}；確認日時 {{date}}", sourceNone: "出典未提供",
    sourceGoogle: "Google ジオコーディング", sourceTgos: "TGOS ジオコーディング", sourceNlsc: "NLSC 村里境界", sourceUser: "利用者による確認", sourceSeparator: "、",
    adminLocation: "行政上の位置", villageUnconfirmed: "村里は未確認", boundaryVintage: "；境界データ版 {{vintage}}",
    routeSource: "目的地ルート", routeNeedsReconfirm: "物件の位置を再確認する必要があります", routeSimulated: "模擬／代替ルート", notRetrieved: "未取得", sourceDated: "{{source}}；{{date}}",
    transitSource: "周辺の公共交通", dateNotProvided: "日付未提供", demographicsSource: "人口の背景",
    selectedRoute: "選択したルート：{{destination}} · {{mode}} · {{distance}} · {{duration}}",
    modeTransit: "公共交通", modeDriving: "車", modeWalking: "徒歩",
    distanceMetres: "{{value}} m", distanceKilometres: "{{value}} km", durationMinutes: "約 {{minutes}} 分", durationHours: "{{hours}} 時間", durationHoursMinutes: "{{hours}} 時間 {{minutes}} 分",
  },
  ko: {
    eyebrow: "사례 분석 섹션", title: "입지와 통근", intro: "이 부동산은 어디에 있고, 주변에서 확인할 수 있는 시설은 무엇이며, 중요한 목적지까지 실제로 오갈 수 있는지 확인합니다.", mapLoading: "지도를 불러오는 중…",
    statusStrip: "입지와 통근 상태", metricProperty: "부동산 위치", metricNearby: "주변 근거", metricNearbyNote: "사례를 다시 연 뒤의 요약은 제한된 근거로 표시됩니다", metricCommute: "목적지 통근",
    mapTitle: "현재 부동산 위치와 주변 근거", mapAttribution: "배경 지도는 화면 표시를 따릅니다. 표시 지점은 지적 경계가 아닙니다.", mapChecked: "위치 확인: {{date}}", notProvided: "제공되지 않음",
    commuteTitle: "목적지 통근 근거", commuteDescription: "목적지 경로와 주변 대중교통 데이터는 서로 독립된 출처입니다. 하나를 사용할 수 없어도 다른 하나는 확인할 수 있습니다.",
    routeOnlyTransitUnavailable: "목적지 경로는 사용할 수 있습니다. 주변 대중교통 데이터는 현재 가져올 수 없습니다.",
    legacyTitle: "주요 주변 근거", legacyDescription: "실제 시설 수와 거리를 기준으로 합니다. 시설이 많다고 부동산이 더 좋은 것은 아닙니다.", poiSummaryLabel: "주변 시설 요약",
    poiTransit: "교통", poiConvenience: "생활 편의", poiSchool: "학교", poiPark: "공원·녹지", poiMedical: "의료", poiRiskFacility: "현장 확인이 필요한 시설",
    unknownNotRetrieved: "알 수 없음/가져오지 않음", poiSummaryMissingTitle: "주변 시설 요약을 가져오지 않았습니다", poiSummaryMissing: "이 사례에는 아직 판독할 수 있는 주변 시설 결과가 저장되어 있지 않습니다.",
    poiSummaryItem: "{{label}} {{value}}", listSeparator: "; ",
    riskTitle: "유의할 시설의 출처와 한계", riskAvailable: "출처 범위를 확인함", riskNoMatch: "출처 조회에서 해당 시설이 없었습니다. 안전하다는 뜻은 아닙니다", riskNoCoverage: "출처 범위 밖",
    riskUnavailable: "출처를 현재 가져올 수 없음", riskUnknown: "범위 알 수 없음/가져오지 않음", riskSourceMissing: "출처가 저장되지 않음",
    riskReasonSourceUnavailable: "시설 출처를 현재 가져올 수 없습니다", riskReasonCoverageNotPreserved: "시설 범위가 스냅숏과 함께 저장되지 않았습니다", riskReasonSuccess: "출처 조회에 성공했습니다",
    riskReasonIdentityMismatch: "시설 근거가 현재 주소와 일치하지 않습니다", riskReasonOther: "출처가 제공한 조회 상태입니다. 저장된 한계를 확인하세요",
    riskLimitation: "범위를 알 수 없다고 해서 시설이 없거나 안전하다는 뜻은 아닙니다.", riskReasonLimitation: "{{reason}}. {{limitation}}",
    limitsTitle: "알 수 없는 사항과 한계", currentLimits: "현재 한계", noLimits: "현재 이 섹션 판독을 막는 주요 한계는 없습니다.",
    savedWarnings: "이전에 저장된 분석에는 중국어 번체로만 기록된 데이터 품질 메모가 {{count}}건 있습니다.",
    nextTitle: "다음 단계", next1: "직장, 고객 거점, 자주 쓰는 역을 추가하고 실제 경로를 하나씩 비교하세요.", next2: "중요한 시설은 영업 상태, 출입구, 현장 보행 조건을 확인하세요.", next3: "가져오지 못한 데이터를 집 보기나 고객 상담 목록에 추가하세요.",
    routeInvalidated: "이전 목적지 경로는 현재 부동산의 경로가 아닙니다", routeUnavailable: "목적지 경로를 현재 가져올 수 없습니다", routeNotSet: "통근 목적지가 아직 설정되지 않았습니다",
    routeCandidateOnly: "경로가 모의, 대체 또는 부분 결과뿐이므로 통근 준비 상태를 확정할 수 없습니다.", transitUnavailable: "주변 대중교통 데이터를 현재 가져올 수 없습니다",
    sourcesTitle: "출처와 조회 세부 정보", sourcePropertyValue: "{{sources}}; 확인 시각 {{date}}", sourceNone: "출처가 제공되지 않음",
    sourceGoogle: "Google 지오코딩", sourceTgos: "TGOS 지오코딩", sourceNlsc: "NLSC 마을 경계", sourceUser: "사용자 확인", sourceSeparator: ", ",
    adminLocation: "행정 위치", villageUnconfirmed: "마을 미확인", boundaryVintage: "; 경계 데이터 버전 {{vintage}}",
    routeSource: "목적지 경로", routeNeedsReconfirm: "부동산 위치를 다시 확인해야 합니다", routeSimulated: "모의/대체 경로", notRetrieved: "아직 가져오지 않음", sourceDated: "{{source}}; {{date}}",
    transitSource: "주변 대중교통", dateNotProvided: "날짜가 제공되지 않음", demographicsSource: "인구 배경",
    selectedRoute: "선택한 경로: {{destination}} · {{mode}} · {{distance}} · {{duration}}",
    modeTransit: "대중교통", modeDriving: "자동차", modeWalking: "도보",
    distanceMetres: "{{value}} m", distanceKilometres: "{{value}} km", durationMinutes: "약 {{minutes}}분", durationHours: "{{hours}}시간", durationHoursMinutes: "{{hours}}시간 {{minutes}}분",
  },
};

function finiteNonNegative(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

/** Locale-aware route distance; the zh-TW output matches the shared commercial formatter. */
export function formatLocationDistance(metres: number | null | undefined, locale: ExperienceLocale): string {
  const copy = (key: LocationViewCopyKey, values?: Record<string, string>) => translateCopyCatalogue(locale, locationViewCopy, key, values);
  if (!finiteNonNegative(metres)) return copy("notProvided");
  if (metres < 1_000) return copy("distanceMetres", { value: new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(Math.round(metres)) });
  const kilometres = metres / 1_000;
  const value = kilometres < 10
    ? new Intl.NumberFormat(locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(kilometres)
    : new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(Math.round(kilometres));
  return copy("distanceKilometres", { value });
}

/** Locale-aware route duration; the zh-TW output matches the shared commercial formatter. */
export function formatLocationDuration(minutes: number | null | undefined, locale: ExperienceLocale): string {
  const copy = (key: LocationViewCopyKey, values?: Record<string, string | number>) => translateCopyCatalogue(locale, locationViewCopy, key, values);
  if (!finiteNonNegative(minutes)) return copy("notProvided");
  const rounded = Math.round(minutes);
  if (rounded < 60) return copy("durationMinutes", { minutes: rounded });
  const hours = Math.floor(rounded / 60);
  const remainder = rounded % 60;
  return remainder ? copy("durationHoursMinutes", { hours, minutes: remainder }) : copy("durationHours", { hours });
}
