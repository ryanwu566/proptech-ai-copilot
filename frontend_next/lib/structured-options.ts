import type { ExperienceLocale } from "@/lib/experience-i18n";

type LocalizedLabels = Partial<Record<ExperienceLocale, string>> & { "zh-TW": string };

const COUNTY_LABELS: Record<string, LocalizedLabels> = {
  "臺北市": { "zh-TW": "臺北市", en: "Taipei City", ja: "台北市", ko: "타이베이시" },
  "新北市": { "zh-TW": "新北市", en: "New Taipei City", ja: "新北市", ko: "신베이시" },
  "桃園市": { "zh-TW": "桃園市", en: "Taoyuan City", ja: "桃園市", ko: "타오위안시" },
  "臺中市": { "zh-TW": "臺中市", en: "Taichung City", ja: "台中市", ko: "타이중시" },
  "臺南市": { "zh-TW": "臺南市", en: "Tainan City", ja: "台南市", ko: "타이난시" },
  "高雄市": { "zh-TW": "高雄市", en: "Kaohsiung City", ja: "高雄市", ko: "가오슝시" },
  "基隆市": { "zh-TW": "基隆市", en: "Keelung City", ja: "基隆市", ko: "지룽시" },
  "新竹市": { "zh-TW": "新竹市", en: "Hsinchu City", ja: "新竹市", ko: "신주시" },
  "嘉義市": { "zh-TW": "嘉義市", en: "Chiayi City", ja: "嘉義市", ko: "자이시" },
  "新竹縣": { "zh-TW": "新竹縣", en: "Hsinchu County", ja: "新竹県", ko: "신주현" },
  "苗栗縣": { "zh-TW": "苗栗縣", en: "Miaoli County", ja: "苗栗県", ko: "먀오리현" },
  "彰化縣": { "zh-TW": "彰化縣", en: "Changhua County", ja: "彰化県", ko: "장화현" },
  "南投縣": { "zh-TW": "南投縣", en: "Nantou County", ja: "南投県", ko: "난터우현" },
  "雲林縣": { "zh-TW": "雲林縣", en: "Yunlin County", ja: "雲林県", ko: "윈린현" },
  "嘉義縣": { "zh-TW": "嘉義縣", en: "Chiayi County", ja: "嘉義県", ko: "자이현" },
  "屏東縣": { "zh-TW": "屏東縣", en: "Pingtung County", ja: "屏東県", ko: "핑둥현" },
  "宜蘭縣": { "zh-TW": "宜蘭縣", en: "Yilan County", ja: "宜蘭県", ko: "이란현" },
  "花蓮縣": { "zh-TW": "花蓮縣", en: "Hualien County", ja: "花蓮県", ko: "화롄현" },
  "臺東縣": { "zh-TW": "臺東縣", en: "Taitung County", ja: "台東県", ko: "타이둥현" },
  "澎湖縣": { "zh-TW": "澎湖縣", en: "Penghu County", ja: "澎湖県", ko: "펑후현" },
  "金門縣": { "zh-TW": "金門縣", en: "Kinmen County", ja: "金門県", ko: "진먼현" },
  "連江縣": { "zh-TW": "連江縣", en: "Lienchiang County", ja: "連江県", ko: "롄장현" },
};

const DISTRICT_LABELS: Record<string, LocalizedLabels> = {
  "中正區": { "zh-TW": "中正區", en: "Zhongzheng District", ja: "中正区", ko: "중정구" },
  "大安區": { "zh-TW": "大安區", en: "Da'an District", ja: "大安区", ko: "다안구" },
  "信義區": { "zh-TW": "信義區", en: "Xinyi District", ja: "信義区", ko: "신이구" },
  "松山區": { "zh-TW": "松山區", en: "Songshan District", ja: "松山区", ko: "쑹산구" },
  "士林區": { "zh-TW": "士林區", en: "Shilin District", ja: "士林区", ko: "스린구" },
  "北投區": { "zh-TW": "北投區", en: "Beitou District", ja: "北投区", ko: "베이터우구" },
  "板橋區": { "zh-TW": "板橋區", en: "Banqiao District", ja: "板橋区", ko: "반차오구" },
  "三重區": { "zh-TW": "三重區", en: "Sanchong District", ja: "三重区", ko: "싼충구" },
  "中和區": { "zh-TW": "中和區", en: "Zhonghe District", ja: "中和区", ko: "중허구" },
  "新莊區": { "zh-TW": "新莊區", en: "Xinzhuang District", ja: "新荘区", ko: "신좡구" },
  "永和區": { "zh-TW": "永和區", en: "Yonghe District", ja: "永和区", ko: "융허구" },
  "桃園區": { "zh-TW": "桃園區", en: "Taoyuan District", ja: "桃園区", ko: "타오위안구" },
  "竹北市": { "zh-TW": "竹北市", en: "Zhubei City", ja: "竹北市", ko: "주베이시" },
};

const ROAD_LABELS: Record<string, LocalizedLabels> = {
  "和平東路二段": { "zh-TW": "和平東路二段", en: "Heping East Road, Section 2", ja: "和平東路2段", ko: "허핑동로 2단" },
  "市府路": { "zh-TW": "市府路", en: "City Hall Road", ja: "市府路", ko: "스푸로" },
};

export const BUILDING_TYPE_OPTIONS = [
  { value: "住宅大樓", labels: { "zh-TW": "住宅大樓", en: "Apartment building", ja: "集合住宅", ko: "아파트형 주택" } },
  { value: "華廈", labels: { "zh-TW": "華廈", en: "Mid-rise condominium", ja: "マンション", ko: "중층 공동주택" } },
  { value: "公寓", labels: { "zh-TW": "公寓", en: "Walk-up apartment", ja: "アパート", ko: "저층 아파트" } },
  { value: "套房", labels: { "zh-TW": "套房", en: "Studio", ja: "ワンルーム", ko: "원룸" } },
] as const;

const STRUCTURED_LABELS: Record<string, LocalizedLabels> = {
  loan_amount: { "zh-TW": "以貸款金額推算自備款", en: "Estimate down payment from loan amount", ja: "借入額から自己資金を推定", ko: "대출 금액으로 자기자금 추정" },
  down_payment: { "zh-TW": "以自備款推算貸款金額", en: "Estimate loan amount from down payment", ja: "自己資金から借入額を推定", ko: "자기자금으로 대출 금액 추정" },
  draft: { "zh-TW": "草稿", en: "Draft", ja: "下書き", ko: "초안" },
  reviewing: { "zh-TW": "檢視中", en: "Under review", ja: "確認中", ko: "검토 중" },
  shortlisted: { "zh-TW": "候選", en: "Shortlisted", ja: "候補", ko: "후보" },
  rejected: { "zh-TW": "暫不考慮", en: "Not considering now", ja: "保留", ko: "현재 보류" },
  purchased: { "zh-TW": "已購買", en: "Purchased", ja: "購入済み", ko: "구매 완료" },
  true: { "zh-TW": "是", en: "Yes", ja: "はい", ko: "예" },
  false: { "zh-TW": "否", en: "No", ja: "いいえ", ko: "아니요" },
  not_started: { "zh-TW": "尚未開始", en: "Not started", ja: "未開始", ko: "시작하지 않음" },
  in_progress: { "zh-TW": "進行中", en: "In progress", ja: "進行中", ko: "진행 중" },
  completed: { "zh-TW": "已完成", en: "Completed", ja: "完了", ko: "완료" },
  planned: { "zh-TW": "已規劃", en: "Planned", ja: "予定", ko: "예정" },
  cancelled: { "zh-TW": "已取消", en: "Cancelled", ja: "キャンセル", ko: "취소됨" },
  open: { "zh-TW": "待處理", en: "Open", ja: "未対応", ko: "미해결" },
  awaiting_response: { "zh-TW": "等待回覆", en: "Awaiting response", ja: "回答待ち", ko: "답변 대기" },
  user_recorded_response: { "zh-TW": "已記錄回覆", en: "Response recorded", ja: "回答記録済み", ko: "답변 기록됨" },
  resolved_by_user: { "zh-TW": "使用者已處理", en: "Resolved by user", ja: "ユーザー対応済み", ko: "사용자 해결" },
  no_longer_needed: { "zh-TW": "已不需要", en: "No longer needed", ja: "不要", ko: "더 이상 필요 없음" },
  property: { "zh-TW": "物件", en: "Property", ja: "物件", ko: "물건" },
  building: { "zh-TW": "建物", en: "Building", ja: "建物", ko: "건물" },
  community: { "zh-TW": "社區", en: "Community", ja: "コミュニティ", ko: "커뮤니티" },
  financing_tax: { "zh-TW": "資金／稅務", en: "Financing / tax", ja: "資金・税務", ko: "자금·세금" },
  contract_negotiation: { "zh-TW": "契約／議價", en: "Contract / negotiation", ja: "契約・交渉", ko: "계약·협상" },
  location_reference: { "zh-TW": "位置參考", en: "Location reference", ja: "位置参考", ko: "위치 참고" },
  other: { "zh-TW": "其他", en: "Other", ja: "その他", ko: "기타" },
  discussed: { "zh-TW": "已討論", en: "Discussed", ja: "相談済み", ko: "논의됨" },
  submitted_by_user: { "zh-TW": "使用者已送出", en: "Submitted by user", ja: "ユーザー提出済み", ko: "사용자 제출" },
  withdrawn: { "zh-TW": "已撤回", en: "Withdrawn", ja: "撤回", ko: "철회됨" },
  not_pursuing: { "zh-TW": "不再進行", en: "Not pursuing", ja: "進めない", ko: "진행하지 않음" },
  custom: { "zh-TW": "自訂", en: "Custom", ja: "カスタム", ko: "사용자 지정" },
  created: { "zh-TW": "建立案件", en: "Case created", ja: "案件作成", ko: "사건 생성" },
  viewing: { "zh-TW": "看屋", en: "Viewing", ja: "内見", ko: "방문" },
  question: { "zh-TW": "問題", en: "Question", ja: "質問", ko: "질문" },
  financial_review: { "zh-TW": "資金檢視", en: "Financial review", ja: "資金確認", ko: "자금 검토" },
  offer: { "zh-TW": "出價", en: "Offer", ja: "オファー", ko: "제안" },
  decision_review: { "zh-TW": "決策檢視", en: "Decision review", ja: "意思決定確認", ko: "의사결정 검토" },
  status_change: { "zh-TW": "狀態變更", en: "Status change", ja: "状態変更", ko: "상태 변경" },
  basic: { "zh-TW": "基本資料", en: "Basic information", ja: "基本情報", ko: "기본 정보" },
  market_reference: { "zh-TW": "市場參考", en: "Market reference", ja: "市場参考", ko: "시장 참고" },
  decision: { "zh-TW": "決策", en: "Decision", ja: "意思決定", ko: "의사결정" },
  confirmed: { "zh-TW": "已確認", en: "Confirmed", ja: "確認済み", ko: "확인됨" },
  blocked: { "zh-TW": "暫時卡關", en: "Blocked", ja: "保留", ko: "보류" },
  not_applicable: { "zh-TW": "不適用", en: "Not applicable", ja: "該当なし", ko: "해당 없음" },
  financial: { "zh-TW": "資金", en: "Financial", ja: "資金", ko: "자금" },
  value_tax: { "zh-TW": "估價稅費", en: "Valuation / tax", ja: "評価・税務", ko: "평가·세금" },
  location_market: { "zh-TW": "位置市場", en: "Location / market", ja: "位置・市場", ko: "위치·시장" },
  due_diligence: { "zh-TW": "盡職調查", en: "Due diligence", ja: "デューデリジェンス", ko: "실사" },
  viewing_offer: { "zh-TW": "看房出價", en: "Viewing / offer", ja: "内見・オファー", ko: "방문·제안" },
  executive_pack: { "zh-TW": "決策摘要", en: "Decision pack", ja: "意思決定パック", ko: "의사결정 자료" },
};

const SOURCE_LABELS: Record<string, LocalizedLabels> = {
  google_geocoding: { "zh-TW": "Google Geocoding", en: "Google Geocoding", ja: "Google Geocoding", ko: "Google Geocoding" },
  google_places: { "zh-TW": "Google Places", en: "Google Places", ja: "Google Places", ko: "Google Places" },
  tgos_geocoding: { "zh-TW": "TGOS", en: "TGOS", ja: "TGOS", ko: "TGOS" },
  official_plvr_opendata: { "zh-TW": "官方實價登錄匯入", en: "Official PLVR import", ja: "公式PLVR取込", ko: "공식 PLVR 가져오기" },
  postgres: { "zh-TW": "PostgreSQL 資料庫", en: "PostgreSQL database", ja: "PostgreSQLデータベース", ko: "PostgreSQL 데이터베이스" },
  mock: { "zh-TW": "展示資料（非即時）", en: "Demo data (not live)", ja: "デモデータ（最新ではありません）", ko: "데모 데이터(실시간 아님)" },
  demo: { "zh-TW": "展示資料（非即時）", en: "Demo data (not live)", ja: "デモデータ（最新ではありません）", ko: "데모 데이터(실시간 아님)" },
};

const STATE_LABELS: Record<string, LocalizedLabels> = {
  source_backed: { "zh-TW": "來源支援", en: "Source-backed", ja: "ソース確認済み", ko: "출처 기반" },
  calculated: { "zh-TW": "依輸入計算", en: "Calculated", ja: "入力から計算", ko: "입력값 계산" },
  heuristic: { "zh-TW": "啟發式參考", en: "Heuristic reference", ja: "ヒューリスティック参考", ko: "휴리스틱 참고" },
  demo: { "zh-TW": "展示資料", en: "Demo data", ja: "デモデータ", ko: "데모 데이터" },
  reference_only: { "zh-TW": "僅供參考", en: "Reference only", ja: "参考情報のみ", ko: "참고용" },
  unavailable: { "zh-TW": "暫時不可用", en: "Temporarily unavailable", ja: "一時利用不可", ko: "일시적으로 사용할 수 없음" },
  partial: { "zh-TW": "資料不完整", en: "Partial data", ja: "不完全なデータ", ko: "부분 데이터" },
  limited: { "zh-TW": "資料有限", en: "Limited data", ja: "限定的なデータ", ko: "제한된 데이터" },
  unknown: { "zh-TW": "狀態未知", en: "Unknown", ja: "不明", ko: "알 수 없음" },
  not_started: { "zh-TW": "尚未開始", en: "Not started", ja: "未開始", ko: "시작하지 않음" },
  error: { "zh-TW": "檢查失敗", en: "Check failed", ja: "確認失敗", ko: "확인 실패" },
};

function labelFor(labels: LocalizedLabels, locale: ExperienceLocale): string {
  return labels[locale] ?? labels.en ?? labels["zh-TW"];
}

function canonicalLookup(value: string): string {
  return value.trim().replace(/台/g, "臺");
}

export function getLocalizedCountyLabel(value: string, locale: ExperienceLocale): string {
  const canonical = canonicalLookup(value);
  return labelFor(COUNTY_LABELS[canonical] ?? { "zh-TW": value }, locale);
}

export function getLocalizedDistrictLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(DISTRICT_LABELS[canonicalLookup(value)] ?? { "zh-TW": value, en: `${value} District`, ja: `${value}区`, ko: `${value}구` }, locale);
}

export function getLocalizedRoadLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(ROAD_LABELS[canonicalLookup(value)] ?? { "zh-TW": value, en: value, ja: value, ko: value }, locale);
}

export function getLocalizedBuildingTypeLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(BUILDING_TYPE_OPTIONS.find((option) => option.value === value)?.labels ?? { "zh-TW": value, en: value, ja: value, ko: value }, locale);
}

export function getLocalizedStructuredLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(STRUCTURED_LABELS[value] ?? { "zh-TW": value, en: value, ja: value, ko: value }, locale);
}

export function getLocalizedSourceLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(SOURCE_LABELS[value] ?? { "zh-TW": value, en: value, ja: value, ko: value }, locale);
}

export function getLocalizedStateLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(STATE_LABELS[value] ?? { "zh-TW": value, en: value, ja: value, ko: value }, locale);
}

export function localizeStructuredSelects(root: ParentNode, locale: ExperienceLocale): void {
  root.querySelectorAll<HTMLSelectElement>("select").forEach((select) => {
    Array.from(select.options).forEach((option) => {
      const stableValue = option.dataset.stableValue ?? option.value;
      option.dataset.stableValue = stableValue;
      option.value = stableValue;
      if (!stableValue) return;
      const isSource = stableValue.startsWith("google_") || stableValue === "tgos_geocoding" || stableValue === "official_plvr_opendata" || stableValue === "postgres" || stableValue === "mock" || stableValue === "demo";
      const label = isSource
        ? getLocalizedSourceLabel(stableValue, locale)
        : COUNTY_LABELS[canonicalLookup(stableValue)]
          ? getLocalizedCountyLabel(stableValue, locale)
          : DISTRICT_LABELS[canonicalLookup(stableValue)]
            ? getLocalizedDistrictLabel(stableValue, locale)
            : ROAD_LABELS[canonicalLookup(stableValue)]
              ? getLocalizedRoadLabel(stableValue, locale)
              : BUILDING_TYPE_OPTIONS.some((item) => item.value === stableValue)
                ? getLocalizedBuildingTypeLabel(stableValue, locale)
                : STRUCTURED_LABELS[stableValue]
                  ? getLocalizedStructuredLabel(stableValue, locale)
                  : undefined;
      if (label && label !== option.textContent) option.textContent = label;
    });
  });
}
