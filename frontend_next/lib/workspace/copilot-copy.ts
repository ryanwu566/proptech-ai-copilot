import type { ExperienceLocale } from "../experience-i18n";
import type { CopilotTopic } from "./grounded-copilot";
import { translatedCopilotField } from "./copilot-field-copy";
type Words = readonly [string, string, string, string];
const index = (locale: ExperienceLocale) => ["zh-TW", "en", "ja", "ko"].indexOf(locale);
const words = {
  title: ["物件決策 Copilot", "Property decision Copilot", "物件判断 Copilot", "부동산 의사결정 Copilot"],
  intro: ["依本案件已儲存證據整理判斷與待查證事項。", "Reason from this case’s saved evidence and identify what to verify.", "この案件の保存済み根拠から判断材料と確認事項を整理します。", "이 사례의 저장된 근거로 판단 자료와 확인 사항을 정리합니다."],
  mode: ["本機確定性回覆 · 無模型連線", "Local deterministic responder · no model connection", "ローカルのルール応答 · モデル接続なし", "로컬 규칙 기반 응답 · 모델 연결 없음"],
  saved: ["已儲存證據", "Saved evidence", "保存済み根拠", "저장된 근거"],
  live: ["即時證據：未要求更新", "Live evidence: refresh not requested", "ライブ根拠：更新未要求", "실시간 근거: 갱신 요청 안 함"],
  context: ["目前案件／物件", "Current case / property", "現在の案件／物件", "현재 사례 / 부동산"],
  savedAt: ["案件保存時間", "Case saved", "案件の保存日時", "사례 저장 시간"],
  boundary: ["保存時間不代表資料仍為最新。地籍、分區與權利身分需另行查證；無法取得、未命中或未查詢都不代表安全。", "Saved dates do not establish current facts. Parcel, zoning and ownership require separate verification. Unavailable, no match and not queried never establish safety.", "保存日時は最新性を保証しません。地番・用途地域・権利は別途確認が必要です。取得不可・該当なし・未照会は安全を意味しません。", "저장 날짜는 최신 사실을 보장하지 않습니다. 필지·용도지역·소유권은 별도 확인이 필요합니다. 조회 불가·일치 없음·미조회는 안전을 뜻하지 않습니다."],
  question: ["詢問本案件的已儲存證據", "Ask about this case’s saved evidence", "この案件の保存済み根拠について質問", "이 사례의 저장된 근거에 질문"],
  send: ["詢問", "Ask", "質問する", "질문하기"],
  suggestions: ["建議問題", "Suggested questions", "質問の例", "추천 질문"],
  used: ["使用了哪些證據", "What evidence was used", "使用した根拠", "사용한 근거"],
  missing: ["缺少哪些證據", "What is missing", "不足している根拠", "부족한 근거"],
  followup: ["安全的後續問題", "Safe follow-up questions", "次に確認する質問", "안전한 후속 질문"],
  inspect: ["檢視案件證據", "Inspect case evidence", "案件の根拠を確認", "사례 근거 확인"],
  provenance: ["來源／查詢時間／來源更新日", "Source / checked / source updated", "出典／確認日時／出典更新日", "출처 / 확인 / 출처 갱신"],
  unknown: ["未保存／未知", "Not saved / unknown", "未保存／不明", "미저장 / 알 수 없음"],
  empty: ["沒有可用證據支持這個問題，請先補齊對應資料。", "No usable evidence supports this question. Add the relevant evidence first.", "この質問を裏付ける根拠がありません。関連資料を確認してください。", "이 질문을 뒷받침할 근거가 없습니다. 관련 자료를 먼저 확인하세요."],
  refresh: ["需要更新時，請先開啟對應證據頁，再明確選擇重新查詢；該操作會要求新資料。", "For fresh data, open the relevant evidence screen and explicitly choose refresh. That action will request new data.", "新しいデータが必要な場合は、該当する根拠画面で明示的に再照会してください。その操作で新しいデータを要求します。", "새 데이터가 필요하면 해당 근거 화면에서 갱신을 명시적으로 선택하세요. 이 작업은 새 데이터를 요청합니다."],
  scope: ["本次僅使用目前案件；比較其他案件需在 Compare 明確選取。Report 依保存快照製作。", "Only the active case is used. Select other cases explicitly in Compare. Reports use saved snapshots.", "現在の案件のみ使用します。他の案件は Compare で明示的に選択してください。レポートは保存済みスナップショットに基づきます。", "현재 사례만 사용합니다. 다른 사례는 Compare에서 명시적으로 선택하세요. 보고서는 저장된 스냅샷을 사용합니다."],
  summary: ["整理本案件的證據與缺口", "Summarize this case’s evidence and gaps", "この案件の根拠と不足を要約", "이 사례의 근거와 누락 요약"],
  nextMissing: ["還缺少哪些證據？", "What is missing?", "不足している根拠は？", "부족한 근거는?"],
  reset: ["清除對話", "Clear conversation", "会話を消去", "대화 지우기"],
  conflict: ["證據仍有衝突，請保留兩者並人工釐清；本回覆不選擇其中一方。", "Conflicting observations remain unresolved. Keep both and verify them manually.", "矛盾する記録は未解決です。両方を保持し、手動で確認してください。", "상충하는 기록이 해결되지 않았습니다. 둘 다 보존하고 수동으로 확인하세요."],
  numeric: ["數字與紀錄僅適用於所列保存假設；原始來源文字保留原語言。", "Figures and records apply only to the saved assumptions. Original source text retains its language.", "数値・記録は保存済み前提にのみ適用されます。出典の原文は元の言語で表示します。", "수치와 기록은 저장된 가정에만 적용됩니다. 출처 원문은 원래 언어로 표시합니다."],
  financeNote: ["已知每月住宅支出已含房貸，不可再加一次；缺少收入或成本時不能判定能否負擔。", "Known monthly housing costs already include the mortgage. Do not add it twice. Missing income or costs prevent an affordability conclusion.", "既知の月額住居費にはローンが含まれます。二重計上しないでください。収入・費用が不足する場合、負担能力は判断できません。", "알려진 월 주거비에는 대출 상환액이 포함됩니다. 중복 합산하지 마세요. 소득이나 비용이 없으면 부담 능력을 판단할 수 없습니다."],
  marketNote: ["開價、區域成交中位數與個案推估不同。區域分布不能證明本物件便宜或昂貴。", "Asking price, regional transaction median and property estimate are distinct. Regional figures do not establish whether this property is cheap or expensive.", "売出価格・地域の成約中央値・個別推定は異なります。地域データだけではこの物件の割安・割高は判断できません。", "호가·지역 거래 중앙값·개별 추정치는 다릅니다. 지역 수치만으로 이 부동산의 가격 적정성을 판단할 수 없습니다."],
  commuteNote: ["路線時間需連同目的地、交通方式與保存日期判讀，不保證現在路況。", "Read route time with destination, mode and saved date. It does not guarantee current traffic.", "経路時間は目的地・交通手段・保存日と併せて確認してください。現在の交通状況は保証しません。", "경로 시간은 목적지·교통수단·저장 날짜와 함께 확인하세요. 현재 교통 상황을 보장하지 않습니다."],
  scenarioNote: ["情境是使用者假設試算；未提供的費用仍未知，已知小計不是總成本。", "Scenarios are calculations from user assumptions. Missing costs remain unknown; known subtotals are not total costs.", "シナリオは利用者の前提による試算です。未入力費用は不明のままで、既知の小計は総費用ではありません。", "시나리오는 사용자 가정에 따른 계산입니다. 누락 비용은 알 수 없으며 알려진 소계는 총비용이 아닙니다."],
  decisionNote: ["Decision Room 的筆記、任務與人工核對是使用者紀錄，不代表官方認證。請在原頁查看內容與未完成事項。", "Decision Room notes, tasks and manual checks are user records, not official verification. Open the room for their contents and unresolved work.", "Decision Room のメモ・タスク・手動確認は利用者の記録であり、公的認証ではありません。内容と未完了事項は元の画面で確認してください。", "Decision Room의 메모·작업·수동 확인은 사용자 기록이며 공식 검증이 아닙니다. 원래 화면에서 내용과 미완료 사항을 확인하세요."],
  partial: ["已有部分判斷依據，限制與缺口如下。", "Some evidence is usable; limitations and gaps are listed below.", "一部の根拠を利用できます。制約と不足は以下の通りです。", "일부 근거를 사용할 수 있습니다. 제한과 누락은 아래와 같습니다."],
  limitation: ["限制", "Limitation", "制約", "제한"],
  difference: ["保存開價減去區域成交總價中位數（萬元）", "Saved asking price minus regional median total price (TWD × 10,000)", "保存売出価格と地域成約総額中央値の差（万 TWD）", "저장 호가에서 지역 총 거래가 중앙값을 뺀 금액 (만 TWD)"],
  housing: ["依保存假設，已知每月住宅支出（TWD）", "Known monthly housing costs under saved assumptions (TWD)", "保存済み前提による既知の月額住居費（TWD）", "저장된 가정에 따른 알려진 월 주거비 (TWD)"],
} satisfies Record<string, Words>;
export function copilotCopy(locale: ExperienceLocale) {
  return Object.fromEntries(Object.entries(words).map(([key, value]) => [key, value[index(locale)]])) as Record<keyof typeof words, string>;
}
const topics: Record<CopilotTopic, Words> = {
  identity: ["物件身分", "Property identity", "物件の識別", "부동산 식별"], market: ["市場證據", "Market evidence", "市場の根拠", "시장 근거"], valuation: ["成交資料推估", "Valuation evidence", "査定の根拠", "추정 근거"], finance: ["財務與負擔能力", "Finance and affordability", "資金と負担能力", "재무 및 부담 능력"], location: ["區位與設施", "Location and amenities", "立地と周辺施設", "입지 및 시설"], commute: ["通勤路線", "Commute routes", "通勤経路", "출퇴근 경로"], risk: ["地形與風險", "Terrain and risk", "地形とリスク", "지형 및 위험"], scenario: ["情境試算", "Scenario Lab", "シナリオ試算", "시나리오 계산"], decision: ["決策協作室", "Decision Room", "意思決定ルーム", "의사결정 룸"], compare: ["比較選取", "Compare selection", "比較対象の選択", "비교 대상 선택"], legal: ["地籍、分區與權利", "Parcel, zoning and ownership", "地番・用途地域・権利", "필지·용도지역·소유권"], current: ["即時資料", "Live data", "ライブデータ", "실시간 데이터"], unknown: ["不支援的問題", "Unsupported question", "対応外の質問", "지원하지 않는 질문"],
};
export const copilotTopicLabel = (topic: CopilotTopic, locale: ExperienceLocale) => topics[topic][index(locale)];
const statuses: Record<string, Words> = {
  supported: ["有證據支持", "Supported", "根拠あり", "근거 있음"], partially_supported: ["部分證據支持", "Partially supported", "一部根拠あり", "부분 근거 있음"], insufficient_evidence: ["證據不足", "Insufficient evidence", "根拠不足", "근거 부족"], conflicting_evidence: ["證據衝突", "Conflicting evidence", "根拠が矛盾", "근거 충돌"], available: ["可用", "Available", "利用可能", "사용 가능"], limited: ["有限證據", "Limited evidence", "制約あり", "제한된 근거"], not_run: ["尚未查詢", "Not queried", "未照会", "미조회"], unavailable: ["無法取得", "Unavailable", "取得不可", "조회 불가"], unsupported: ["不支援", "Unsupported", "対応外", "미지원"], no_coverage: ["未涵蓋", "No coverage", "対象範囲外", "범위 밖"], no_match: ["未命中（不代表安全）", "No match (not proof of safety)", "該当なし（安全の証明ではない）", "일치 없음 (안전의 증거 아님)"], stale: ["已過期／需重新確認", "Stale / requires revalidation", "古い／再確認が必要", "오래됨 / 재확인 필요"], insufficient: ["資料不足", "Insufficient", "資料不足", "자료 부족"],
};
export const copilotStatusLabel = (status: string, locale: ExperienceLocale) => statuses[status]?.[index(locale)] ?? copilotCopy(locale).unknown;

const labels: Record<string, Words> = {
  "identity-anchor": ["瀏覽器物件關聯（非地籍確認）", "Browser property link (not parcel verification)", "ブラウザーの物件関連付け（地番確認ではない）", "브라우저 부동산 연결 (필지 확인 아님)"],
  "room-asking": ["人工紀錄開價", "User-recorded asking price", "利用者記録の売出価格", "사용자 기록 호가"], "room-notes": ["看屋筆記數", "Viewing notes", "内見メモ数", "방문 메모 수"], "room-open-questions": ["待確認問題數", "Open questions", "未解決の質問数", "미해결 질문 수"], "room-open-tasks": ["未完成任務數", "Open tasks", "未完了タスク数", "미완료 작업 수"], "room-followup": ["需追蹤的人工查證數", "Manual checks needing follow-up", "追跡が必要な手動確認数", "후속 확인이 필요한 수동 확인 수"],
  "price-asking": ["開價", "Asking price", "売出価格", "호가"], "price-active": ["採用價格", "Active price", "採用価格", "적용 가격"], "market-total": ["區域成交總價中位數", "Regional median total price", "地域成約総額の中央値", "지역 총 거래가 중앙값"], "market-unit": ["區域單價中位數", "Regional median unit price", "地域単価の中央値", "지역 단가 중앙값"], "market-samples": ["有效樣本數", "Effective sample count", "有効サンプル数", "유효 표본 수"], "valuation-estimate": ["成交資料推估中點", "Transaction-based estimate", "成約データによる推定", "거래 자료 기반 추정"], "commute-duration": ["通勤時間", "Commute duration", "通勤時間", "출퇴근 시간"], "commute-destination": ["目的地", "Destination", "目的地", "목적지"], "commute-mode": ["交通方式", "Travel mode", "交通手段", "교통수단"], "finance-payment": ["房貸月付", "Monthly mortgage", "月額ローン返済", "월 대출 상환액"], "finance-housing": ["已知每月住宅支出（含房貸）", "Known monthly housing costs (including mortgage)", "既知の月額住居費（ローン含む）", "알려진 월 주거비 (대출 포함)"], "finance-income": ["月收入", "Monthly income", "月収", "월 소득"],
};
export function copilotEvidenceLabel(id: string, original: string, locale: ExperienceLocale): string {
  if (labels[id]) return labels[id][index(locale)];
  const special = ({ "identity-legal": "legal", "live-evidence": "current", "compare-selection": "compare", "scenario-saved": "scenario", "room-saved": "decision" } as Partial<Record<string, CopilotTopic>>)[id];
  if (special) return copilotTopicLabel(special, locale);
  return translatedCopilotField(id, locale) ?? original;
}
