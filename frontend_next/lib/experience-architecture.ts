import type { TranslationKey } from "@/lib/experience-i18n";

export type ExperienceState =
  | "empty"
  | "loading"
  | "unavailable"
  | "no_official_data"
  | "partial"
  | "limited"
  | "no_match"
  | "unknown"
  | "not_assessed"
  | "error"
  | "ready";

export type ExperienceStatePresentation = {
  heading: string;
  explanation: string;
  nextAction?: string;
  sourceNote?: string;
};

export const EXPERIENCE_STATE_TRANSLATION_KEYS: Record<ExperienceState, { heading: TranslationKey; explanation: TranslationKey; nextAction: TranslationKey; sourceNote?: TranslationKey }> = {
  empty: { heading: "state.empty.heading", explanation: "state.empty.explanation", nextAction: "state.empty.next" },
  loading: { heading: "state.loading.heading", explanation: "state.loading.explanation", nextAction: "state.loading.explanation" },
  unavailable: { heading: "state.unavailable.heading", explanation: "state.unavailable.explanation", nextAction: "state.unavailable.next" },
  no_official_data: { heading: "state.no_official_data.heading", explanation: "state.no_official_data.explanation", nextAction: "state.no_official_data.next", sourceNote: "state.no_official_data.source" },
  partial: { heading: "state.partial.heading", explanation: "state.partial.explanation", nextAction: "state.partial.next" },
  limited: { heading: "state.limited.heading", explanation: "state.limited.explanation", nextAction: "state.limited.next" },
  no_match: { heading: "state.no_match.heading", explanation: "state.no_match.explanation", nextAction: "state.no_match.next" },
  unknown: { heading: "state.unknown.heading", explanation: "state.unknown.explanation", nextAction: "state.unknown.next" },
  not_assessed: { heading: "state.not_assessed.heading", explanation: "state.not_assessed.explanation", nextAction: "state.not_assessed.next" },
  error: { heading: "state.error.heading", explanation: "state.error.explanation", nextAction: "state.error.next" },
  ready: { heading: "state.ready.heading", explanation: "state.ready.explanation", nextAction: "state.ready.explanation" },
};

export const EXPERIENCE_STATE_PRESENTATIONS: Record<ExperienceState, ExperienceStatePresentation> = {
  empty: { heading: "尚未開始", explanation: "目前還沒有可供顯示的分析結果。", nextAction: "先補上物件資料，再開始需要的分析。" },
  loading: { heading: "正在處理", explanation: "正在整理目前可用的資料，請稍候。" },
  unavailable: { heading: "資料暫時不可用", explanation: "目前無法取得這項資料；這不代表低風險或沒有結果。", nextAction: "稍後再試，或先查看其他已可用資訊。" },
  no_official_data: { heading: "沒有官方資料", explanation: "目前沒有足夠的官方資料可供這項判讀。", nextAction: "先查看資料限制，再決定是否補充條件。", sourceNote: "沒有官方資料不等於沒有事件、交易或風險。" },
  partial: { heading: "資料尚不完整", explanation: "目前只能整理部分已取得資訊，不能視為完整分析。", nextAction: "補齊標示的資料後再重新檢查。" },
  limited: { heading: "資料範圍有限", explanation: "目前資料的涵蓋範圍或期間有限，解讀需要保留。", nextAction: "查看來源與涵蓋限制，再決定下一步。" },
  no_match: { heading: "沒有符合的資料", explanation: "目前找不到符合條件的資料，不代表該項目不存在。", nextAction: "調整查詢條件或查看其他資料面向。" },
  unknown: { heading: "狀態未知", explanation: "目前無法可靠判定資料狀態，不會將它視為低風險。", nextAction: "查看資料來源與限制，必要時稍後再試。" },
  not_assessed: { heading: "尚未評估", explanation: "這個面向尚未執行分析，不能視為已通過檢查。", nextAction: "由使用者主動開始這項分析。" },
  error: { heading: "處理失敗", explanation: "這次處理沒有完成，未產生可用結論。", nextAction: "稍後再試；也可以先查看已完成的分析。" },
  ready: { heading: "資料可用", explanation: "目前結果已整理完成，請同時查看來源與限制。" },
};

export type ActionKind = "primary" | "secondary" | "navigation";

export type PrimaryActionContract = {
  viewId: string;
  primaryActionId: string;
  secondaryActionIds: readonly string[];
  automaticEffects: false;
};

export const HOMEPAGE_PRIMARY_ACTION_CONTRACT: PrimaryActionContract = {
  viewId: "homepage",
  primaryActionId: "property-finder",
  secondaryActionIds: ["workspace", "saved-case", "report", "expert-tools", "direct-tool"],
  automaticEffects: false,
};

export const JOURNEY_PRIMARY_ACTION_CONTRACTS: Readonly<Record<string, PrimaryActionContract>> = {
  property: { viewId: "journey-property", primaryActionId: "property-finder", secondaryActionIds: ["property-search"], automaticEffects: false },
  location: { viewId: "journey-location", primaryActionId: "location-insight", secondaryActionIds: ["terrain-risk", "commute", "market-insight", "map"], automaticEffects: false },
  price: { viewId: "journey-price", primaryActionId: "valuation", secondaryActionIds: ["property-search"], automaticEffects: false },
  affordability: { viewId: "journey-affordability", primaryActionId: "loan", secondaryActionIds: ["holding-cost", "taxoracle"], automaticEffects: false },
  decision: { viewId: "journey-decision", primaryActionId: "viewing-decision", secondaryActionIds: ["property-case", "comparison", "print-export"], automaticEffects: false },
};

export function getExperienceStatePresentation(state: ExperienceState, translate?: (key: TranslationKey) => string): ExperienceStatePresentation {
  const presentation = EXPERIENCE_STATE_PRESENTATIONS[state];
  if (!translate) return presentation;
  const keys = EXPERIENCE_STATE_TRANSLATION_KEYS[state];
  return {
    heading: translate(keys.heading),
    explanation: translate(keys.explanation),
    nextAction: translate(keys.nextAction),
    sourceNote: keys.sourceNote ? translate(keys.sourceNote) : presentation.sourceNote,
  };
}
