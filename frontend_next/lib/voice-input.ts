import type { ExperienceLocale } from "@/lib/experience-i18n";
import type { JourneyStepId } from "@/lib/guided-journey";

export type VoiceInputState =
  | "unavailable"
  | "idle"
  | "requesting"
  | "listening"
  | "transcript_ready"
  | "confirmation_required"
  | "applying"
  | "stopped"
  | "cancelled"
  | "no_match"
  | "error";

export type VoiceAction =
  | { type: "navigate_step"; step: JourneyStepId }
  | { type: "open_help"; target: "help" | "evidence" }
  | { type: "focus_field"; field: "address" | "price" | "area" }
  | { type: "fill_field"; field: "address" | "price" | "area"; value: string }
  | { type: "select_option"; option: string }
  | { type: "stop_read_aloud" }
  | { type: "repeat_summary" };

export type VoiceCommandResult = {
  kind: "allowed" | "confirmation_required" | "blocked" | "no_match";
  action?: VoiceAction;
  transcript: string;
  reason?: string;
};

const NAVIGATION: Record<ExperienceLocale, readonly [RegExp, JourneyStepId][]> = {
  "zh-TW": [[/找物件|物件資料|property finder/i, "property"], [/位置|生活機能|地勢|通勤/i, "location"], [/價格|估價/i, "price"], [/貸款|資金|持有成本|稅務/i, "affordability"], [/決策摘要|看房摘要|案件/i, "decision"]],
  en: [[/property|find a home|finder/i, "property"], [/location|livability|terrain|commute/i, "location"], [/price|valuation/i, "price"], [/loan|funding|holding cost|tax/i, "affordability"], [/decision|viewing|case/i, "decision"]],
  ja: [[/物件|不動産/i, "property"], [/位置|生活|地形|通勤/i, "location"], [/価格|評価/i, "price"], [/ローン|資金|保有|税/i, "affordability"], [/判断|内見|案件/i, "decision"]],
  ko: [[/물건|부동산/i, "property"], [/위치|생활|지형|통근/i, "location"], [/가격|평가/i, "price"], [/대출|자금|보유|세금/i, "affordability"], [/판단|방문|사례/i, "decision"]],
};

const BLOCKED: Record<ExperienceLocale, readonly RegExp[]> = {
  "zh-TW": [/儲存|保存|刪除|刪掉|匯出|列印|比較|貸款|稅務|估價|市場|地勢|通勤|重新整理|刷新|購買|買房|出價|安全|保證|送出|提交/],
  en: [/save|delete|export|print|compare|loan|tax|valuation|market|terrain|commute|refresh|purchase|buy|offer|safe|guarantee|submit/i],
  ja: [/保存|削除|出力|印刷|比較|ローン|税|評価|市場|地形|通勤|更新|購入|入札|安全|保証|送信/],
  ko: [/저장|삭제|내보내기|인쇄|비교|대출|세금|평가|시장|지형|통근|새로고침|구매|제안|안전|보장|제출/],
};

const FIELD_PATTERNS: Record<ExperienceLocale, readonly [RegExp, "address" | "price" | "area"][]> = {
  "zh-TW": [[/(?:填入|輸入|設定)(?:地址|物件地址)\s+(.+)/, "address"], [/(?:填入|輸入|設定)(?:價格|總價)\s+(.+)/, "price"], [/(?:填入|輸入|設定)(?:坪數|面積)\s+(.+)/, "area"]],
  en: [[/(?:fill|enter|set)\s+(?:the\s+)?address\s+(.+)/i, "address"], [/(?:fill|enter|set)\s+(?:the\s+)?price\s+(.+)/i, "price"], [/(?:fill|enter|set)\s+(?:the\s+)?area\s+(.+)/i, "area"]],
  ja: [[/(?:住所|所在地)\s*(?:を|に)?\s*(?:入力|設定)\s+(.+)/, "address"], [/(?:価格)\s*(?:を|に)?\s*(?:入力|設定)\s+(.+)/, "price"], [/(?:面積)\s*(?:を|に)?\s*(?:入力|設定)\s+(.+)/, "area"]],
  ko: [[/(?:주소)\s*(?:를|에)?\s*(?:입력|설정)\s+(.+)/, "address"], [/(?:가격)\s*(?:을|에)?\s*(?:입력|설정)\s+(.+)/, "price"], [/(?:면적)\s*(?:을|에)?\s*(?:입력|설정)\s+(.+)/, "area"]],
};

function cleanTranscript(transcript: string): string {
  return transcript.trim().replace(/\s+/g, " ").slice(0, 240);
}

export function parseVoiceCommand(transcript: string, locale: ExperienceLocale): VoiceCommandResult {
  const clean = cleanTranscript(transcript);
  if (!clean) return { kind: "no_match", transcript: clean, reason: "empty" };
  if (BLOCKED[locale].some((pattern) => pattern.test(clean))) return { kind: "blocked", transcript: clean, reason: "restricted_action" };

  for (const [pattern, field] of FIELD_PATTERNS[locale]) {
    const match = clean.match(pattern);
    if (match?.[1]?.trim()) {
      return { kind: "confirmation_required", transcript: clean, action: { type: "fill_field", field, value: match[1].trim().slice(0, 160) } };
    }
  }

  if (/停止朗讀|停止閱讀|stop reading|stop read aloud|読み上げを停止|읽기 중지/i.test(clean)) return { kind: "confirmation_required", transcript: clean, action: { type: "stop_read_aloud" } };
  if (/重複摘要|再讀摘要|repeat summary|read summary again|要約を再生|요약 반복/i.test(clean)) return { kind: "confirmation_required", transcript: clean, action: { type: "repeat_summary" } };
  if (/說明|幫助|help|説明|도움말/i.test(clean)) return { kind: "confirmation_required", transcript: clean, action: { type: "open_help", target: "help" } };

  for (const [pattern, step] of NAVIGATION[locale]) {
    if (pattern.test(clean)) return { kind: "confirmation_required", transcript: clean, action: { type: "navigate_step", step } };
  }
  return { kind: "no_match", transcript: clean, reason: "not_allowlisted" };
}

export function isSafeVoiceAction(action: VoiceAction | undefined): action is VoiceAction {
  return Boolean(action && ["navigate_step", "open_help", "focus_field", "fill_field", "select_option", "stop_read_aloud", "repeat_summary"].includes(action.type));
}
