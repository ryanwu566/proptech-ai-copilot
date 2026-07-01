export type DueDiligenceStatus = "not_started" | "reviewing" | "confirmed" | "blocked" | "not_applicable";
export type DueDiligenceReadiness = "completed" | "partial" | "not_provided";

export type DueDiligenceCategoryId =
  | "basic_property"
  | "building_condition"
  | "community_management"
  | "financing_tax"
  | "contract_negotiation"
  | "location_market_reference";

export type DueDiligenceTemplateItem = {
  item_id: string;
  category_id: DueDiligenceCategoryId;
  category_label: string;
  label: string;
  prompt: string;
};

export type DueDiligenceItem = DueDiligenceTemplateItem & {
  status: DueDiligenceStatus;
  note: string;
  reference_note: string;
  next_action: string;
  target_date: string;
};

export type DecisionReviewInput = {
  decision_review_summary?: string;
  decision_open_questions?: string;
  decision_next_step?: string;
};

export type DueDiligenceReadinessResult = {
  readiness: DueDiligenceReadiness;
  category_count: number;
  item_count: number;
  confirmed_count: number;
  reviewing_count: number;
  blocked_count: number;
  not_applicable_count: number;
  open_next_action_count: number;
  categories_with_confirmed_items: string[];
};

export const DUE_DILIGENCE_STATUS_LABELS: Record<DueDiligenceStatus, string> = {
  not_started: "尚未確認",
  reviewing: "檢查中",
  confirmed: "已由使用者確認",
  blocked: "暫時卡關",
  not_applicable: "不適用",
};

export const DUE_DILIGENCE_STATUS_OPTIONS: DueDiligenceStatus[] = [
  "not_started",
  "reviewing",
  "confirmed",
  "blocked",
  "not_applicable",
];

export const DUE_DILIGENCE_TEMPLATE: DueDiligenceTemplateItem[] = [
  item("basic_property", "基本物件", "basic_property_price_identity", "開價與物件識別", "確認開價、地址或明確物件識別已足以辨認案件。"),
  item("basic_property", "基本物件", "basic_property_area_age", "坪數與屋齡", "確認坪數、屋齡與建物型態是否仍需補資料。"),
  item("basic_property", "基本物件", "basic_property_parking_floor", "車位與樓層", "確認樓層、車位、公共設施或其他基本條件。"),
  item("building_condition", "屋況與建物", "building_condition_visible_issues", "可見屋況", "記錄滲漏、壁癌、結構疑慮或需專業確認的項目。"),
  item("building_condition", "屋況與建物", "building_condition_renovation_scope", "裝修範圍", "確認裝修需求、預備金與尚待估價的工程。"),
  item("building_condition", "屋況與建物", "building_condition_safety_documents", "安全文件", "確認使照、管線、消防或其他文件是否待補。"),
  item("community_management", "社區管理", "community_management_fee", "管理費與基金", "確認管理費、修繕基金與社區財務資料。"),
  item("community_management", "社區管理", "community_management_meeting_records", "會議與公告", "確認管委會紀錄、重大修繕或爭議事項。"),
  item("community_management", "社區管理", "community_management_rules", "規約與使用限制", "確認寵物、出租、停車或公共空間使用限制。"),
  item("financing_tax", "資金與稅費", "financing_tax_funding_plan", "資金計畫", "確認自備款、貸款、利率與月付承受度仍需補充的內容。"),
  item("financing_tax", "資金與稅費", "financing_tax_costs", "交易與持有成本", "確認買方成本、裝修預備金與每月持有預備金。"),
  item("financing_tax", "資金與稅費", "financing_tax_tax_review", "稅務確認", "確認契稅、房地合一稅、持有稅費或人工稅務確認事項。"),
  item("contract_negotiation", "合約與議價", "contract_negotiation_price_terms", "價格與付款條件", "確認議價空間、付款條件與保留條款。"),
  item("contract_negotiation", "合約與議價", "contract_negotiation_disclosure", "揭露與瑕疵", "確認賣方揭露、瑕疵擔保與需寫入契約的事項。"),
  item("contract_negotiation", "合約與議價", "contract_negotiation_timeline", "時程與交屋", "確認簽約、貸款、交屋與驗屋時程。"),
  item("contract_negotiation", "合約與議價", "contract_negotiation_advisor", "專業確認", "確認代書、律師、銀行或其他專業協助的待辦。"),
  item("location_market_reference", "位置與市場參考", "location_market_reference_livability", "生活機能參考", "記錄位置、通勤與生活機能仍需使用者確認的事項。"),
  item("location_market_reference", "位置與市場參考", "location_market_reference_terrain", "地勢與災害參考", "確認地勢與災害資料是否已檢視或有不可用限制。"),
  item("location_market_reference", "位置與市場參考", "location_market_reference_market", "市場行情參考", "確認市場查詢、成交參考與資料可用性。"),
  item("location_market_reference", "位置與市場參考", "location_market_reference_visit", "實地看屋重點", "整理現場看屋、鄰里觀察與後續追問事項。"),
];

export function buildDefaultDueDiligenceItems(): DueDiligenceItem[] {
  return DUE_DILIGENCE_TEMPLATE.map((template) => ({
    ...template,
    status: "not_started",
    note: "",
    reference_note: "",
    next_action: "",
    target_date: "",
  }));
}

export function normalizeDueDiligenceItems(items?: Partial<DueDiligenceItem>[] | null): DueDiligenceItem[] {
  const byId = new Map((items ?? []).map((item) => [item.item_id, item]));
  return DUE_DILIGENCE_TEMPLATE.map((template) => {
    const input = byId.get(template.item_id);
    return {
      ...template,
      status: normalizeStatus(input?.status),
      note: safeText(input?.note),
      reference_note: safeText(input?.reference_note),
      next_action: safeText(input?.next_action),
      target_date: normalizeTargetDate(input?.target_date),
    };
  });
}

export function buildDueDiligenceReadiness(
  items: DueDiligenceItem[],
  review: DecisionReviewInput,
): DueDiligenceReadinessResult {
  const normalized = normalizeDueDiligenceItems(items);
  const categories = Array.from(new Set(DUE_DILIGENCE_TEMPLATE.map((template) => template.category_id)));
  const confirmedCategories = categories.filter((category) => normalized.some((item) => item.category_id === category && item.status === "confirmed"));
  const confirmedCount = normalized.filter((item) => item.status === "confirmed").length;
  const reviewingCount = normalized.filter((item) => item.status === "reviewing").length;
  const blockedCount = normalized.filter((item) => item.status === "blocked").length;
  const notApplicableCount = normalized.filter((item) => item.status === "not_applicable").length;
  const openNextActionCount = normalized.filter((item) => item.next_action.trim()).length;
  const hasReview = Boolean(safeText(review.decision_review_summary) && safeText(review.decision_next_step));
  const hasAnyInput = normalized.some((item) =>
    item.status !== "not_started"
    || item.note
    || item.reference_note
    || item.next_action
    || item.target_date,
  ) || Boolean(safeText(review.decision_review_summary) || safeText(review.decision_open_questions) || safeText(review.decision_next_step));

  let readiness: DueDiligenceReadiness = "not_provided";
  if (confirmedCategories.length === categories.length && blockedCount === 0 && hasReview) readiness = "completed";
  else if (hasAnyInput || reviewingCount > 0 || blockedCount > 0) readiness = "partial";

  return {
    readiness,
    category_count: categories.length,
    item_count: normalized.length,
    confirmed_count: confirmedCount,
    reviewing_count: reviewingCount,
    blocked_count: blockedCount,
    not_applicable_count: notApplicableCount,
    open_next_action_count: openNextActionCount,
    categories_with_confirmed_items: confirmedCategories,
  };
}

export function groupDueDiligenceItems(items: DueDiligenceItem[]): Array<{ category_id: DueDiligenceCategoryId; category_label: string; items: DueDiligenceItem[] }> {
  const normalized = normalizeDueDiligenceItems(items);
  return Array.from(new Map(DUE_DILIGENCE_TEMPLATE.map((item) => [item.category_id, item.category_label])).entries()).map(([category_id, category_label]) => ({
    category_id,
    category_label,
    items: normalized.filter((item) => item.category_id === category_id),
  }));
}

function item(category_id: DueDiligenceCategoryId, category_label: string, item_id: string, label: string, prompt: string): DueDiligenceTemplateItem {
  return { category_id, category_label, item_id, label, prompt };
}

function normalizeStatus(status: unknown): DueDiligenceStatus {
  return DUE_DILIGENCE_STATUS_OPTIONS.includes(status as DueDiligenceStatus) ? status as DueDiligenceStatus : "not_started";
}

function normalizeTargetDate(value: unknown): string {
  const text = safeText(value);
  return /^\d{4}-\d{2}-\d{2}$/.test(text) ? text : "";
}

function safeText(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
