/** Answer-first wording. Renders composed values only; it never derives, rounds before
 * comparison or adds a claim. Saved source text (destination, mode) keeps its language. */
import type { ExperienceLocale } from "../experience-i18n";
import type { FactOrigin, Headline, NextActionKind } from "./copilot-compose";
type Words = readonly [string, string, string, string];
const index = (locale: ExperienceLocale) => Math.max(0, ["zh-TW", "en", "ja", "ko"].indexOf(locale));
const fill = (template: string, values: Record<string, string>) => template.replace(/\{(\w+)\}/g, (_, name: string) => values[name] ?? "");

const words = {
  answer: ["回答", "Answer", "回答", "답변"],
  keyFacts: ["關鍵事實", "Key facts", "主要な事実", "핵심 사실"],
  missing: ["尚缺什麼", "What is missing", "不足している情報", "부족한 정보"],
  noMissing: ["此問題沒有列出缺少的證據。", "No missing evidence is listed for this question.", "この質問で不足している根拠はありません。", "이 질문에 부족한 근거가 없습니다."],
  moreMissing: ["另有 {count} 項未列於此。", "{count} more not shown here.", "ほか {count} 件はここに表示していません。", "여기에 표시되지 않은 항목 {count}개가 더 있습니다."],
  viewAllMissing: ["查看全部缺少的證據（{count}）", "View all missing evidence ({count})", "不足している根拠をすべて表示（{count}）", "부족한 근거 모두 보기 ({count})"],
  nextAction: ["建議下一步", "Next best action", "次に行うこと", "다음 권장 작업"],
  nextActionNote: ["只會開啟頁面，不會自動分析或更新資料。", "Opens the page only; nothing is analysed or refreshed automatically.", "画面を開くだけで、自動分析や更新は行いません。", "화면만 열며 자동 분석이나 갱신은 하지 않습니다."],
  fullEvidence: ["完整證據（{count}）", "Full evidence ({count})", "すべての根拠（{count}）", "전체 근거 ({count})"],
  provenance: ["來源與時間（{count}）", "Provenance ({count})", "出典と日時（{count}）", "출처 및 시점 ({count})"],
  citation: ["引用 {n}", "Citation {n}", "引用 {n}", "인용 {n}"],
  qualified: ["依部分證據回答；缺口列於下方。", "Based on partial evidence; gaps are listed below.", "一部の根拠に基づく回答です。不足は下に記載しています。", "일부 근거에 기반한 답변입니다. 누락은 아래에 있습니다."],
  bandNote: ["這是與已儲存市場區間的觀察比較，不是估價，也不判斷價格是否合理。", "Observed market-band comparison only — not a valuation or a fair-value judgement.", "保存済み市場レンジとの観察比較であり、査定や適正価格の判断ではありません。", "저장된 시장 범위와의 관찰 비교이며 감정이나 적정가 판단이 아닙니다."],
  commuteNote: ["這是已儲存路線，不代表目前路況。", "This is a saved route, not current traffic.", "保存済みの経路であり、現在の交通状況ではありません。", "저장된 경로이며 현재 교통 상황이 아닙니다."],
  incomeMissing: ["因缺少收入，仍無法判斷負擔能力。", "Affordability is still unknown because income is missing.", "収入が未入力のため、負担能力はまだ判断できません。", "소득이 없어 부담 능력은 아직 알 수 없습니다."],
  subtotalOnly: ["這是已知小計，不是負擔能力結論。", "This is a known subtotal, not an affordability conclusion.", "既知の小計であり、負担能力の結論ではありません。", "알려진 소계이며 부담 능력 결론이 아닙니다."],
  scenarioSubtotal: ["其他成本只有已知小計，未提供者仍未知。", "Other costs are a known subtotal; anything not entered remains unknown.", "その他の費用は既知の小計のみで、未入力分は不明です。", "기타 비용은 알려진 소계뿐이며 입력하지 않은 항목은 알 수 없습니다."],
  derivedFrom: ["＝開價 ÷ 面積", "= asking price ÷ area", "＝売出価格 ÷ 面積", "= 호가 ÷ 면적"],
  savedBand: ["已儲存市場單價 P25–P75", "Saved market unit price P25–P75", "保存済み市場単価 P25–P75", "저장된 시장 단가 P25–P75"],
  askingUnit: ["開價換算單價（推導值）", "Asking unit price (derived)", "売出単価（算出値）", "호가 단가 (산출값)"],
  savedRoute: ["已儲存通勤路線", "Saved commute route", "保存済みの通勤経路", "저장된 출퇴근 경로"],
} satisfies Record<string, Words>;
export function answerCopy(locale: ExperienceLocale) {
  return Object.fromEntries(Object.entries(words).map(([key, value]) => [key, value[index(locale)]])) as Record<keyof typeof words, string>;
}
export const answerText = (template: string, values: Record<string, string | number>) => fill(template, Object.fromEntries(Object.entries(values).map(([key, value]) => [key, String(value)])));

const origins: Record<FactOrigin, Words> = {
  user_entered: ["使用者輸入", "User-entered", "利用者入力", "사용자 입력"],
  saved_source: ["已儲存來源", "Saved source", "保存済み出典", "저장된 출처"],
  saved_assumption: ["已儲存假設", "Saved assumption", "保存済みの前提", "저장된 가정"],
  saved_calculation: ["已儲存試算", "Saved calculation", "保存済み試算", "저장된 계산"],
  scenario_assumption: ["情境假設", "Scenario assumption", "シナリオの前提", "시나리오 가정"],
  user_record: ["使用者紀錄", "User record", "利用者の記録", "사용자 기록"],
  derived: ["推導值", "Derived", "算出値", "산출값"],
};
export const originLabel = (origin: FactOrigin, locale: ExperienceLocale) => origins[origin][index(locale)];

const actions: Record<Exclude<NextActionKind, "none">, Words> = {
  review_price_conflict: ["到 Decision Room 檢視互相衝突的開價紀錄", "Review the conflicting asking-price records in Decision Room", "Decision Room で矛盾する売出価格の記録を確認", "Decision Room에서 상충하는 호가 기록 검토"],
  verify_identity: ["到總覽確認物件身分", "Verify the property identity in Overview", "概要で物件の識別を確認", "개요에서 부동산 식별 확인"],
  verify_legal: ["到總覽安排地籍、分區與權利的另行查證", "Open Overview to plan separate parcel, zoning and ownership checks", "概要で地番・用途地域・権利の別途確認を計画", "개요에서 필지·용도지역·소유권 별도 확인 계획"],
  inspect_saved_dates: ["到證據頁確認保存日期", "Open Evidence to check saved dates", "根拠画面で保存日を確認", "근거 화면에서 저장 날짜 확인"],
  enter_area: ["到總覽輸入或確認物件面積", "Enter or confirm the property area in Overview", "概要で物件面積を入力・確認", "개요에서 부동산 면적 입력 또는 확인"],
  refresh_market: ["到市場頁檢視或更新已儲存的市場證據", "Open Market to review or refresh saved market evidence", "市場画面で保存済みの市場根拠を確認・更新", "시장 화면에서 저장된 시장 근거 검토 또는 갱신"],
  review_market: ["到市場頁檢視已儲存的市場證據", "Open Market to review saved market evidence", "市場画面で保存済みの市場根拠を確認", "시장 화면에서 저장된 시장 근거 검토"],
  enter_income: ["到財務頁輸入月收入", "Enter monthly income in Finance", "資金画面で月収を入力", "재무 화면에서 월 소득 입력"],
  complete_finance: ["到財務頁補齊缺少的成本假設", "Complete missing cost assumptions in Finance", "資金画面で不足している費用の前提を入力", "재무 화면에서 누락된 비용 가정 입력"],
  review_finance: ["到財務頁檢視已儲存假設", "Review saved assumptions in Finance", "資金画面で保存済みの前提を確認", "재무 화면에서 저장된 가정 검토"],
  verify_commute: ["到區位頁核對通勤證據", "Open Location to verify commute evidence", "立地画面で通勤の根拠を確認", "입지 화면에서 출퇴근 근거 확인"],
  review_risk_sources: ["到風險頁檢視尚未確認的來源", "Open Risk to review unresolved sources", "リスク画面で未解決の出典を確認", "위험 화면에서 미해결 출처 검토"],
  review_risk: ["到風險頁檢視已儲存來源", "Open Risk to review saved sources", "リスク画面で保存済みの出典を確認", "위험 화면에서 저장된 출처 검토"],
  open_scenarios: ["到情境試算檢視假設", "Open Scenario Lab to review assumptions", "シナリオ試算で前提を確認", "시나리오 계산에서 가정 검토"],
  open_decision_room: ["到 Decision Room 檢視未完成事項", "Open Decision Room to review open items", "Decision Room で未完了事項を確認", "Decision Room에서 미완료 항목 검토"],
  open_location: ["到區位頁檢視已儲存設施", "Open Location to review saved amenities", "立地画面で保存済み施設を確認", "입지 화면에서 저장된 시설 검토"],
  open_overview: ["到總覽檢視物件身分", "Open Overview to review the property identity", "概要で物件の識別を確認", "개요에서 부동산 식별 검토"],
  inspect_missing: ["到證據頁檢視缺少的項目", "Open Evidence to inspect missing items", "根拠画面で不足項目を確認", "근거 화면에서 누락 항목 확인"],
  inspect_evidence: ["到證據頁檢視已儲存證據", "Open Evidence to inspect saved evidence", "根拠画面で保存済み根拠を確認", "근거 화면에서 저장된 근거 확인"],
};
export const nextActionLabel = (kind: NextActionKind, locale: ExperienceLocale) => kind === "none" ? null : actions[kind][index(locale)];

const modes: Record<string, Words> = { "開車": ["開車", "car", "車", "자동차"], "大眾運輸": ["大眾運輸", "public transport", "公共交通", "대중교통"], "步行": ["步行", "walking", "徒歩", "도보"] };
/** Enumerated saved travel modes are translated; any other saved text stays verbatim. */
export const travelMode = (mode: string, locale: ExperienceLocale) => modes[mode]?.[index(locale)] ?? mode;

const tag = (locale: ExperienceLocale) => (["zh-TW", "en", "ja", "ko"] as const)[index(locale)];
const number = (value: number, locale: ExperienceLocale, digits: number) => new Intl.NumberFormat(tag(locale), { maximumFractionDigits: digits }).format(value);
/** Human-readable quantities. Formatting is applied after any comparison; semantics are unchanged. */
export function formatQuantity(value: number, unit: string, locale: ExperienceLocale, extraDigits = 0): string {
  const i = index(locale);
  const wan = (amount: number, digits: number, suffix: Words) => i === 1
    ? `NT$${new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 + extraDigits }).format(amount * 10_000)}${suffix[1]}`
    : `${number(amount, locale, digits + extraDigits)}${suffix[i]}`;
  switch (unit) {
    case "萬元": return wan(value, 0, [" 萬", "", "万 TWD", "만 TWD"]);
    case "萬元／坪": return wan(value, 1, [" 萬／坪", " / ping", "万 TWD／坪", "만 TWD/평"]);
    case "萬元／月": return wan(value, 1, [" 萬／月", " / month", "万 TWD／月", "만 TWD/월"]);
    case "元／月": return `NT$${number(value, locale, 0)}${["／月", " / month", "／月", "/월"][i]}`;
    case "元／年": return `NT$${number(value, locale, 0)}${["／年", " / year", "／年", "/년"][i]}`;
    case "元／坪／月": return `NT$${number(value, locale, 0)}${["／坪／月", " / ping / month", "／坪／月", "/평/월"][i]}`;
    case "TWD": return `NT$${number(value, locale, 2)}`;
    case "分鐘": return `${number(value, locale, 0)}${[" 分鐘", " min", "分", "분"][i]}`;
    case "公尺": return value >= 1000 ? `${number(value / 1000, locale, 1)} km` : `${number(value, locale, 0)} m`;
    case "坪": return `${number(value, locale, 2)}${[" 坪", " ping", "坪", "평"][i]}`;
    case "%": return `${number(value, locale, 2)}%`;
    case "年": case "year": return `${number(value, locale, 0)}${[" 年", value === 1 ? " year" : " years", "年", "년"][i]}`;
    case "筆": return `${number(value, locale, 0)}${[" 筆", " records", "件", "건"][i]}`;
    case "處": return `${number(value, locale, 0)}${[" 處", " places", "か所", "곳"][i]}`;
    case "人": return `${number(value, locale, 0)}${[" 人", " people", "人", "명"][i]}`;
    default: return unit ? `${number(value, locale, 2)} ${unit}` : number(value, locale, 2);
  }
}
const range = (low: number, high: number, unit: string, locale: ExperienceLocale) => {
  // One unit suffix for the pair keeps the band compact.
  const lowText = formatQuantity(low, unit, locale); const highText = formatQuantity(high, unit, locale);
  const suffix = highText.replace(/^NT\$/, "").replace(/^[\d.,KMB]+/, "");
  return `${lowText.endsWith(suffix) && suffix ? lowText.slice(0, lowText.length - suffix.length) : lowText}–${highText}`;
};
export const formatRange = range;

const headlines = {
  market_band_above: ["以已儲存資料推導的開價單價 {unit}，高於已儲存市場單價 P25–P75 區間（{band}）。", "The derived asking unit price ({unit}) is above the saved market P25–P75 band ({band}).", "保存データから算出した売出単価（{unit}）は、保存済み市場単価の P25–P75 レンジ（{band}）を上回っています。", "저장 자료로 산출한 호가 단가({unit})는 저장된 시장 단가 P25–P75 범위({band})보다 높습니다."],
  market_band_within: ["以已儲存資料推導的開價單價 {unit}，落在已儲存市場單價 P25–P75 區間（{band}）內。", "The derived asking unit price ({unit}) is within the saved market P25–P75 band ({band}).", "保存データから算出した売出単価（{unit}）は、保存済み市場単価の P25–P75 レンジ（{band}）内です。", "저장 자료로 산출한 호가 단가({unit})는 저장된 시장 단가 P25–P75 범위({band}) 안에 있습니다."],
  market_band_below: ["以已儲存資料推導的開價單價 {unit}，低於已儲存市場單價 P25–P75 區間（{band}）。", "The derived asking unit price ({unit}) is below the saved market P25–P75 band ({band}).", "保存データから算出した売出単価（{unit}）は、保存済み市場単価の P25–P75 レンジ（{band}）を下回っています。", "저장 자료로 산출한 호가 단가({unit})는 저장된 시장 단가 P25–P75 범위({band})보다 낮습니다."],
  finance_housing: ["依已儲存假設，已知每月住宅支出為 {monthly}。", "Known monthly housing cost is {monthly} under the saved assumptions.", "保存済みの前提では、既知の月額住居費は {monthly} です。", "저장된 가정에서 알려진 월 주거비는 {monthly}입니다."],
  commute: ["已儲存路線：{mode}至{destination}需 {minutes}。", "The saved route to {destination} is {minutes} by {mode}.", "保存済みの経路：{destination}まで{mode}で {minutes}。", "저장된 경로: {destination}까지 {mode}로 {minutes}."],
  risk: ["已儲存風險來源：{recorded} 項有紀錄結果、{noMatch} 項未命中（不代表安全）、{unresolved} 項仍未確認。", "Saved risk sources: {recorded} with a recorded result, {noMatch} with no match (not proof of safety), {unresolved} still unresolved.", "保存済みのリスク出典：結果記録あり {recorded} 件、該当なし {noMatch} 件（安全の証明ではない）、未解決 {unresolved} 件。", "저장된 위험 출처: 결과 기록 {recorded}개, 일치 없음 {noMatch}개(안전의 증거 아님), 미해결 {unresolved}개."],
  scenario_payment: ["情境 {letter} 依使用者假設試算的房貸月付為 {monthly}。", "Scenario {letter} calculates a monthly mortgage of {monthly} from user assumptions.", "シナリオ {letter} の利用者前提による月額ローン試算は {monthly} です。", "시나리오 {letter}의 사용자 가정 기준 월 대출 상환액은 {monthly}입니다."],
  decision_records: ["Decision Room 使用者紀錄：{questions} 個待確認問題、{tasks} 項未完成任務。", "Decision Room user records: {questions} open questions and {tasks} open tasks.", "Decision Room の利用者記録：未解決の質問 {questions} 件、未完了タスク {tasks} 件。", "Decision Room 사용자 기록: 미해결 질문 {questions}개, 미완료 작업 {tasks}개."],
  supported: ["已儲存證據可回答此問題（{used} 項）。", "Saved evidence answers this question ({used} items).", "保存済みの根拠でこの質問に回答できます（{used} 件）。", "저장된 근거로 이 질문에 답할 수 있습니다({used}개)."],
  partial: ["已儲存證據只能部分回答：{used} 項可用、{missing} 項缺口。", "Saved evidence answers this only in part: {used} usable items, {missing} gaps.", "保存済みの根拠では一部のみ回答できます：利用可能 {used} 件、不足 {missing} 件。", "저장된 근거로 일부만 답할 수 있습니다: 사용 가능 {used}개, 누락 {missing}개."],
  insufficient: ["目前已儲存的證據不足以回答這個問題。", "There is not enough saved evidence to answer this yet.", "現在の保存済み根拠では、この質問にまだ回答できません。", "현재 저장된 근거로는 아직 이 질문에 답할 수 없습니다."],
  legal_unsupported: ["已儲存證據無法回答地籍、分區或權利問題，需另行查證。", "Parcel, zoning and ownership cannot be answered from saved evidence; they need separate verification.", "地番・用途地域・権利は保存済み根拠では回答できません。別途確認が必要です。", "필지·용도지역·소유권은 저장된 근거로 답할 수 없으며 별도 확인이 필요합니다."],
  live_not_requested: ["尚未要求即時資料；目前只有已儲存證據，保存不代表最新。", "Live data has not been requested; only saved evidence is available, and saved is not current.", "ライブデータは要求していません。保存済み根拠のみで、保存済みは最新を意味しません。", "실시간 데이터는 요청하지 않았습니다. 저장된 근거뿐이며 저장된 것은 최신이 아닙니다."],
  invalid_output: ["回覆無法通過驗證，因此不顯示任何結論。", "The response could not be validated, so no claim is shown.", "回答を検証できなかったため、結論は表示しません。", "응답을 검증할 수 없어 결론을 표시하지 않습니다."],
  conflict_price: ["已儲存的開價紀錄互相衝突，因此目前無法回答此問題。", "Saved asking-price records conflict, so this question cannot be resolved yet.", "保存済みの売出価格の記録が矛盾しているため、この質問にはまだ回答できません。", "저장된 호가 기록이 상충하여 아직 이 질문에 답할 수 없습니다."],
  conflict_identity: ["物件身分與已儲存證據衝突，因此目前無法回答此問題。", "The property identity conflicts with saved evidence, so this question cannot be resolved yet.", "物件の識別が保存済み根拠と矛盾しているため、この質問にはまだ回答できません。", "부동산 식별이 저장된 근거와 상충하여 아직 이 질문에 답할 수 없습니다."],
} satisfies Record<string, Words>;

const quote = (text: string, locale: ExperienceLocale) => (index(locale) === 0 || index(locale) === 2 ? `「${text}」` : `“${text}”`);

/** Headline sentence plus at most one bounded qualifier, both from composed values. */
export function headlineText(headline: Headline, locale: ExperienceLocale): { text: string; note: string | null } {
  const i = index(locale); const c = answerCopy(locale);
  const say = (key: keyof typeof headlines, values: Record<string, string | number> = {}) => answerText(headlines[key][i], values);
  const count = (value: number) => number(value, locale, 0);
  switch (headline.kind) {
    case "market_band": {
      // Position was decided on raw values; if rounding makes the value look equal to the
      // bound it is outside of, show more digits instead of an apparently contradictory pair.
      const bound = headline.position === "above" ? headline.high : headline.low;
      const tied = headline.position !== "within" && formatQuantity(headline.askingUnit, headline.unit, locale) === formatQuantity(bound, headline.unit, locale);
      return { text: say(`market_band_${headline.position}`, { unit: formatQuantity(headline.askingUnit, headline.unit, locale, tied ? 2 : 0), band: range(headline.low, headline.high, headline.unit, locale) }), note: c.bandNote };
    }
    case "finance_housing": return { text: say("finance_housing", { monthly: formatQuantity(headline.monthly, headline.unit, locale) }), note: headline.incomeMissing ? c.incomeMissing : c.subtotalOnly };
    case "commute": return { text: say("commute", { destination: quote(headline.destination, locale), mode: travelMode(headline.mode, locale), minutes: formatQuantity(headline.minutes, headline.unit, locale) }), note: c.commuteNote };
    case "risk": return { text: say("risk", { recorded: count(headline.recorded), noMatch: count(headline.noMatch), unresolved: count(headline.unresolved) }), note: null };
    case "scenario_payment": return { text: say("scenario_payment", { letter: headline.letter, monthly: formatQuantity(headline.monthly, headline.unit, locale) }), note: headline.complete ? null : c.scenarioSubtotal };
    case "decision_records": return { text: say("decision_records", { questions: count(headline.questions), tasks: count(headline.tasks) }), note: null };
    case "supported": case "partial": return { text: say(headline.kind, { used: count(headline.used), missing: count(headline.missing) }), note: null };
    default: return { text: say(headline.kind), note: null };
  }
}
