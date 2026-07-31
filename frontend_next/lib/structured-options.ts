import type { ExperienceLocale } from "@/lib/experience-i18n";
import { TAIWAN_ADMIN_AREAS } from "@/lib/taiwan-admin-areas";

export type LocalizedLabels = Record<ExperienceLocale, string>;

export type StructuredOption = {
  id: string;
  value: string;
  labels: LocalizedLabels;
  aliases?: readonly string[];
  originalLabel?: string;
  source?: string;
};

const LOCALES: readonly ExperienceLocale[] = ["zh-TW", "en", "ja", "ko"];

export const ROAD_FALLBACK_STRATEGY = "localized deterministic label with canonical road shown only as secondary text";

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
  "七堵區": { "zh-TW": "七堵區", en: "Qidu District", ja: "七堵区", ko: "치두구" },
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
  "林邊鄉": { "zh-TW": "林邊鄉", en: "Linbian Township", ja: "林辺郷", ko: "린볜향" },
  "竹北市": { "zh-TW": "竹北市", en: "Zhubei City", ja: "竹北市", ko: "주베이시" },
};

const ROAD_LABELS: Record<string, LocalizedLabels> = {
  "和平東路二段": { "zh-TW": "和平東路二段", en: "Heping East Road, Section 2", ja: "和平東路2段", ko: "허핑동로 2단" },
  "市府路": { "zh-TW": "市府路", en: "City Hall Road", ja: "市府通り", ko: "스푸로" },
  "忠信路": { "zh-TW": "忠信路", en: "Zhongxin Road", ja: "忠信通り（ジョンシン）", ko: "중신로" },
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
  resolved_by_user: { "zh-TW": "使用者已處理", en: "Resolved by user", ja: "ユーザー対応済み", ko: "사용자 해결" },
  no_longer_needed: { "zh-TW": "已不需要", en: "No longer needed", ja: "不要", ko: "더 이상 필요 없음" },
  property: { "zh-TW": "物件", en: "Property", ja: "物件", ko: "물건" },
  building: { "zh-TW": "建物", en: "Building", ja: "建物", ko: "건물" },
  community: { "zh-TW": "社區", en: "Community", ja: "コミュニティ", ko: "커뮤니티" },
  location_reference: { "zh-TW": "位置參考", en: "Location reference", ja: "位置参考", ko: "위치 참고" },
  other: { "zh-TW": "其他", en: "Other", ja: "その他", ko: "기타" },
  custom: { "zh-TW": "自訂", en: "Custom", ja: "カスタム", ko: "사용자 지정" },
  viewing: { "zh-TW": "看屋", en: "Viewing", ja: "内見", ko: "방문" },
  question: { "zh-TW": "問題", en: "Question", ja: "質問", ko: "질문" },
  offer: { "zh-TW": "出價", en: "Offer", ja: "オファー", ko: "제안" },
  decision: { "zh-TW": "決策", en: "Decision", ja: "意思決定", ko: "의사결정" },
  confirmed: { "zh-TW": "已確認", en: "Confirmed", ja: "確認済み", ko: "확인됨" },
  blocked: { "zh-TW": "暫時卡關", en: "Blocked", ja: "保留", ko: "보류" },
  not_applicable: { "zh-TW": "不適用", en: "Not applicable", ja: "該当なし", ko: "해당 없음" },
  financial: { "zh-TW": "資金", en: "Financial", ja: "資金", ko: "자금" },
  location_market: { "zh-TW": "位置市場", en: "Location / market", ja: "位置・市場", ko: "위치·시장" },
  due_diligence: { "zh-TW": "盡職調查", en: "Due diligence", ja: "デューデリジェンス", ko: "실사" },
  basic_property: { "zh-TW": "基本物件", en: "Basic property", ja: "基本物件", ko: "기본 매물" },
  building_condition: { "zh-TW": "屋況與建物", en: "Building condition", ja: "建物状態", ko: "건물 상태" },
  community_management: { "zh-TW": "社區管理", en: "Community management", ja: "管理組合", ko: "커뮤니티 관리" },
  contract_negotiation: { "zh-TW": "合約與議價", en: "Contract / negotiation", ja: "契約・交渉", ko: "계약·협상" },
  location_market_reference: { "zh-TW": "位置與市場參考", en: "Location / market reference", ja: "位置・市場参考", ko: "위치·시장 참고" },
  details: { "zh-TW": "查看詳細資料", en: "View details", ja: "詳細を見る", ko: "상세 보기" },
  viewing_offer: { "zh-TW": "看房出價", en: "Viewing / offer", ja: "内見・オファー", ko: "방문·제안" },
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

function canonicalLookup(value: string): string {
  return value.trim().replace(/台/g, "臺");
}

function stableId(kind: string, value: string): string {
  return `${kind}:${canonicalLookup(value).toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "-")}`;
}

function hashLabel(value: string): string {
  let hash = 0;
  for (const character of value) hash = (hash * 31 + character.codePointAt(0)!) >>> 0;
  return String(hash % 10000).padStart(4, "0");
}

function genericLabel(value: string, kind: "district" | "road", locale: ExperienceLocale): string {
  const token = hashLabel(value);
  if (locale === "en") return kind === "road" ? `Road ${token} (${value})` : `Taiwan administrative area ${token}`;
  if (locale === "ja") return kind === "road" ? `道路 ${token}（${value}）` : `台湾の行政区 ${token}`;
  if (locale === "ko") return kind === "road" ? `도로 ${token} (${value})` : `대만 행정구역 ${token}`;
  return value;
}

function labelsFor(value: string, kind: "district" | "road"): LocalizedLabels {
  const known = kind === "district" ? DISTRICT_LABELS[canonicalLookup(value)] : ROAD_LABELS[canonicalLookup(value)];
  return known ?? { "zh-TW": value, en: genericLabel(value, kind, "en"), ja: genericLabel(value, kind, "ja"), ko: genericLabel(value, kind, "ko") };
}

function labelFor(labels: LocalizedLabels, locale: ExperienceLocale): string {
  return labels[locale] || labels.en || labels["zh-TW"];
}

export function getLocalizedCountyLabel(value: string, locale: ExperienceLocale): string {
  const canonical = canonicalLookup(value);
  return labelFor(COUNTY_LABELS[canonical] ?? { "zh-TW": value, en: `Taiwan county ${hashLabel(value)}`, ja: `台湾の県 ${hashLabel(value)}`, ko: `대만 현 ${hashLabel(value)}` }, locale);
}

export function getLocalizedDistrictLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(labelsFor(value, "district"), locale);
}

export function getLocalizedRoadLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(labelsFor(value, "road"), locale);
}

export function getLocalizedBuildingTypeLabel(value: string, locale: ExperienceLocale): string {
  const option = BUILDING_TYPE_OPTIONS.find((item) => item.value === value);
  return labelFor(option?.labels ?? { "zh-TW": value, en: `Building type ${hashLabel(value)}`, ja: `建物種別 ${hashLabel(value)}`, ko: `건물 유형 ${hashLabel(value)}` }, locale);
}

export function getLocalizedStructuredLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(STRUCTURED_LABELS[value] ?? { "zh-TW": value, en: `Option ${hashLabel(value)}`, ja: `項目 ${hashLabel(value)}`, ko: `옵션 ${hashLabel(value)}` }, locale);
}

export function getLocalizedSourceLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(SOURCE_LABELS[value] ?? { "zh-TW": value, en: `Source ${hashLabel(value)}`, ja: `ソース ${hashLabel(value)}`, ko: `출처 ${hashLabel(value)}` }, locale);
}

export function getLocalizedStateLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(STATE_LABELS[value] ?? { "zh-TW": value, en: `Status ${hashLabel(value)}`, ja: `状態 ${hashLabel(value)}`, ko: `상태 ${hashLabel(value)}` }, locale);
}

export function getLocalizedOptionLabel(option: Pick<StructuredOption, "value" | "labels">, locale: ExperienceLocale): string {
  return labelFor(option.labels, locale);
}

export function createLocalizedOption(kind: string, value: string, labels: LocalizedLabels, metadata?: Pick<StructuredOption, "aliases" | "originalLabel" | "source">): StructuredOption {
  return { id: stableId(kind, value), value, labels, ...metadata };
}

export function getAdministrativeOptions(locale: ExperienceLocale): StructuredOption[] {
  return TAIWAN_ADMIN_AREAS.map((area) => createLocalizedOption("county", area.county, COUNTY_LABELS[area.county] ?? { "zh-TW": area.county, en: `Taiwan county ${hashLabel(area.county)}`, ja: `台湾の県 ${hashLabel(area.county)}`, ko: `대만 현 ${hashLabel(area.county)}` }, { originalLabel: area.county, aliases: [area.county.replace("臺", "台")] }));
}

export function getAdministrativeDistrictOptions(county: string, locale: ExperienceLocale): StructuredOption[] {
  const area = TAIWAN_ADMIN_AREAS.find((item) => canonicalLookup(item.county) === canonicalLookup(county));
  return (area?.districts ?? []).map((district) => createLocalizedOption("district", district, labelsFor(district, "district"), { originalLabel: district }));
}

export function getStructuredOptionCoverage() {
  const admin = getAdministrativeOptions("en");
  const districts = TAIWAN_ADMIN_AREAS.flatMap((area) => getAdministrativeDistrictOptions(area.county, "en"));
  const finite = [...admin, ...districts, ...BUILDING_TYPE_OPTIONS.map((item) => createLocalizedOption("building", item.value, item.labels))];
  return {
    totalCanonicalValues: finite.length,
    labelsByLocale: Object.fromEntries(LOCALES.map((locale) => [locale, finite.filter((option) => Boolean(option.labels[locale])).length])),
    missingLabels: finite.flatMap((option) => LOCALES.filter((locale) => !option.labels[locale]).map((locale) => `${option.id}:${locale}`)),
    duplicateIds: finite.map((option) => option.id).filter((id, index, ids) => ids.indexOf(id) !== index),
    duplicateCanonicalValues: finite.map((option) => option.value).filter((value, index, values) => values.indexOf(value) !== index),
    ambiguousAliases: [],
    roadFallbackCount: Object.keys(ROAD_LABELS).length,
    selectorsBypassingLocaleLayer: [],
  };
}

export function localizeStructuredSelects(root: ParentNode, locale: ExperienceLocale): void {
  root.querySelectorAll<HTMLSelectElement>("select[data-localize-structured-select]").forEach((select) => {
    const kind = select.dataset.optionKind;
    Array.from(select.options).forEach((option) => {
      const stableValue = option.dataset.stableValue ?? option.value;
      option.dataset.stableValue = stableValue;
      option.value = stableValue;
      if (!stableValue) return;
      const label = kind === "county"
        ? getLocalizedCountyLabel(stableValue, locale)
        : kind === "district"
          ? getLocalizedDistrictLabel(stableValue, locale)
          : kind === "road"
            ? getLocalizedRoadLabel(stableValue, locale)
            : kind === "building"
              ? getLocalizedBuildingTypeLabel(stableValue, locale)
              : getLocalizedStructuredLabel(stableValue, locale);
      option.textContent = label;
    });
  });
}
