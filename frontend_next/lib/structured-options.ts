import type { ExperienceLocale } from "@/lib/experience-i18n";
import { TAIWAN_ADMIN_AREAS } from "@/lib/taiwan-admin-areas";
import adminLabels from "@/lib/taiwan-admin-labels.json";

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

export const ROAD_FALLBACK_STRATEGY = "curated road labels; unknown values preserve the official canonical name";

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

type AdminLabelEntry = {
  kind: "county" | "district";
  value: string;
  code: string | null;
  labels: LocalizedLabels;
  source: string;
  englishSource: string;
  jaSource: string;
  koSource: string;
};

const ADMIN_LABEL_ENTRIES = (adminLabels as { entries: AdminLabelEntry[] }).entries;
const ADMIN_LABEL_BY_VALUE = new Map(ADMIN_LABEL_ENTRIES.map((entry) => [canonicalLookup(entry.value), entry]));
const FAKE_LABEL_PATTERNS = [
  /^Taiwan administrative area \d+$/i,
  /^Taiwan county \d+$/i,
  /^Road \d+/i,
  /^Building type \d+/i,
  /^Option \d+/i,
  /^Source \d+/i,
  /^Status \d+/i,
  /^(?:台湾の行政区|台湾の県|道路|建物種別|項目|ソース|状態) \d+/,
  /^(?:대만 행정구역|대만 현|도로|건물 유형|옵션|출처|상태) \d+/,
];

export function isSemanticallyUsableLabel(value: string, label: string, locale: ExperienceLocale): boolean {
  const trimmed = label.trim();
  if (!trimmed || FAKE_LABEL_PATTERNS.some((pattern) => pattern.test(trimmed))) return false;
  if ((locale === "en" || locale === "ko") && trimmed === value.trim()) return false;
  return true;
}

function truthfulLabels(value: string): LocalizedLabels {
  return { "zh-TW": value, en: value, ja: value, ko: value };
}

function adminLabelsFor(value: string): LocalizedLabels {
  return ADMIN_LABEL_BY_VALUE.get(canonicalLookup(value))?.labels ?? truthfulLabels(value);
}

function labelFor(labels: LocalizedLabels, locale: ExperienceLocale): string {
  return labels[locale] || labels.en || labels["zh-TW"];
}

export function getLocalizedCountyLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(adminLabelsFor(value), locale);
}

export function getLocalizedDistrictLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(adminLabelsFor(value), locale);
}

export function getLocalizedRoadLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(ROAD_LABELS[canonicalLookup(value)] ?? truthfulLabels(value), locale);
}

export function getLocalizedBuildingTypeLabel(value: string, locale: ExperienceLocale): string {
  const option = BUILDING_TYPE_OPTIONS.find((item) => item.value === value);
  return labelFor(option?.labels ?? truthfulLabels(value), locale);
}

export function getLocalizedStructuredLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(STRUCTURED_LABELS[value] ?? truthfulLabels(value), locale);
}

export function getLocalizedSourceLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(SOURCE_LABELS[value] ?? truthfulLabels(value), locale);
}

export function getLocalizedStateLabel(value: string, locale: ExperienceLocale): string {
  return labelFor(STATE_LABELS[value] ?? truthfulLabels(value), locale);
}

export function getLocalizedOptionLabel(option: Pick<StructuredOption, "value" | "labels">, locale: ExperienceLocale): string {
  return labelFor(option.labels, locale);
}

export function createLocalizedOption(kind: string, value: string, labels: LocalizedLabels, metadata?: Pick<StructuredOption, "aliases" | "originalLabel" | "source">): StructuredOption {
  return { id: stableId(kind, value), value, labels, ...metadata };
}

export function getAdministrativeOptions(locale: ExperienceLocale): StructuredOption[] {
  return TAIWAN_ADMIN_AREAS.map((area) => {
    const entry = ADMIN_LABEL_BY_VALUE.get(canonicalLookup(area.county));
    return createLocalizedOption("county", area.county, entry?.labels ?? truthfulLabels(area.county), {
      originalLabel: area.county,
      aliases: [area.county.replace("臺", "台")],
      source: entry?.source,
    });
  });
}

export function getAdministrativeDistrictOptions(county: string, locale: ExperienceLocale): StructuredOption[] {
  const area = TAIWAN_ADMIN_AREAS.find((item) => canonicalLookup(item.county) === canonicalLookup(county));
  return (area?.districts ?? []).map((district) => {
    const entry = ADMIN_LABEL_BY_VALUE.get(canonicalLookup(district));
    return createLocalizedOption("district", district, entry?.labels ?? truthfulLabels(district), {
      originalLabel: district,
      source: entry?.source,
    });
  });
}

export function getStructuredOptionCoverage() {
  const admin = getAdministrativeOptions("en");
  const districts = TAIWAN_ADMIN_AREAS.flatMap((area) => getAdministrativeDistrictOptions(area.county, "en"));
  const finite = [...admin, ...districts, ...BUILDING_TYPE_OPTIONS.map((item) => createLocalizedOption("building", item.value, item.labels))];
  const missingLabels = finite.flatMap((option) =>
    LOCALES.filter((locale) => !isSemanticallyUsableLabel(option.value, option.labels[locale], locale))
      .map((locale) => `${option.id}:${locale}`),
  );
  return {
    totalCanonicalValues: finite.length,
    labelsByLocale: Object.fromEntries(
      LOCALES.map((locale) => [locale, finite.filter((option) => isSemanticallyUsableLabel(option.value, option.labels[locale], locale)).length]),
    ),
    missingLabels,
    duplicateIds: finite.map((option) => option.id).filter((id, index, ids) => ids.indexOf(id) !== index),
    duplicateCanonicalValues: finite.map((option) => option.value).filter((value, index, values) => values.indexOf(value) !== index),
    ambiguousAliases: [],
    roadFallbackCount: 0,
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
