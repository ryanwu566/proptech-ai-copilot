import type { ExperienceLocale } from "@/lib/experience-i18n";

export type CompetitionCapability = {
  id: string;
  name: string;
  role: "primary" | "supporting";
  implementation: string;
  browser: string;
  source: string;
  validation: string;
  production: string;
  limitation: string;
};

export const COMPETITION_NOTICE =
  "This is a preliminary reference, not an official tax assessment, loan approval, appraisal, legal opinion, safety guarantee, or purchase recommendation.";

export const capabilities: CompetitionCapability[] = [
  { id: "taxoracle", name: "TaxOracle preliminary screening", role: "primary", implementation: "implemented", browser: "tested", source: "official rule metadata", validation: "professional review pending", production: "reference-only", limitation: "TX001-TX009 compatibility screening; confirm with a tax professional." },
  { id: "holding-cost", name: "Holding Cost", role: "primary", implementation: "implemented", browser: "tested", source: "deterministic current-input model", validation: "illustrative", production: "reference-only", limitation: "Not an actual bill, quote, or lending decision." },
  { id: "case", name: "Reusable Property Case", role: "primary", implementation: "implemented", browser: "tested", source: "user-provided facts", validation: "product validation pending", production: "available", limitation: "Missing facts remain visible and require review." },
  { id: "valuation", name: "Valuation", role: "supporting", implementation: "implemented", browser: "tested", source: "source-status dependent", validation: "professional review pending", production: "reference-only", limitation: "Does not replace appraisal." },
  { id: "location", name: "Location and Map Insight", role: "supporting", implementation: "implemented", browser: "tested", source: "configured provider dependent", validation: "reference-only", production: "reference-only", limitation: "Availability and coverage vary by source." },
  { id: "terrain", name: "Terrain Risk", role: "supporting", implementation: "implemented", browser: "tested", source: "official layer metadata", validation: "reference-only", production: "reference-only", limitation: "Missing data does not mean no risk." },
  { id: "market", name: "Market Insight", role: "supporting", implementation: "implemented", browser: "tested", source: "read-model status dependent", validation: "validation pending", production: "reference-only", limitation: "Unavailable or incomplete data remains unavailable." },
  { id: "customer-validation", name: "Paid customer validation", role: "supporting", implementation: "planned", browser: "not applicable", source: "not configured", validation: "market validation pending", production: "planned", limitation: "No customer, revenue, accuracy, or time-saving claim is made." },
];

export const competitionCopy: Record<ExperienceLocale, {
  eyebrow: string; title: string; description: string; primary: string; secondary: string; boundary: string;
  demoTitle: string; demoDescription: string; illustrative: string; steps: string[]; calculate: string; calculating: string; reset: string;
  evidence: string; privacy: string; terms: string; source: string; missing: string; inputs: string; output: string; changed: string;
  offline: string; switchOffline: string; live: string; incomplete: string; print: string;
}> = {
  "zh-TW": { eyebrow: "給房產專業人員的交易準備工具", title: "在客戶會議前，先釐清稅務、持有成本與交易條件", description: "用 deterministic 初步計算、官方來源追蹤與可重用案件，整理已知事實與待確認事項。", primary: "開始三分鐘 TaxOracle 示範", secondary: "開始建立物件案件", boundary: "結果是初步參考，不是官方核定；必要時請交由專業人員複核。", demoTitle: "三分鐘交易準備示範", demoDescription: "先看案件事實，再執行既有 TaxOracle 與 Holding Cost 計算。可編輯輸入，結果會隨輸入重新計算。", illustrative: "示範案件／非真實客戶", steps: ["物件事實", "稅務與成本", "證據", "摘要"], calculate: "重新計算", calculating: "計算中…", reset: "重設示範", evidence: "證據與方法", privacy: "隱私政策", terms: "條款與限制", source: "規則與來源", missing: "待補事實", inputs: "本次使用的輸入", output: "計算摘要", changed: "本次變更會影響對應的持有成本或資格規則。", offline: "離線示範：僅展示本機可重現的參考模型，不代表已連線取得最新官方資料。", switchOffline: "切換到明確標示的離線示範", live: "連線計算", incomplete: "資料尚未完整，請在交易討論前補件或人工確認。", print: "列印目前摘要" },
  en: { eyebrow: "Transaction preparation for real-estate professionals", title: "Clarify taxes, holding costs and transaction conditions before the client meeting", description: "Combine deterministic preliminary calculations, official-source traceability and a reusable property case.", primary: "Start the three-minute TaxOracle demo", secondary: "Start a property case", boundary: "Preliminary reference only, not an official assessment; professional review may be required.", demoTitle: "Three-minute transaction preparation demo", demoDescription: "Review the case facts, then run the existing TaxOracle and Holding Cost calculations. Edit inputs and recalculate to see causal changes.", illustrative: "Illustrative example / not a real customer", steps: ["Property facts", "Tax and costs", "Evidence", "Summary"], calculate: "Recalculate", calculating: "Calculating…", reset: "Reset example", evidence: "Evidence and methodology", privacy: "Privacy policy", terms: "Terms and limitations", source: "Rules and sources", missing: "Missing facts", inputs: "Inputs used", output: "Calculation summary", changed: "This change affects the related holding-cost or qualification rule.", offline: "Offline demo: a locally reproducible reference model only; it does not claim current official data.", switchOffline: "Switch to the explicitly labelled offline demo", live: "Live calculation", incomplete: "Facts are incomplete; complete or professionally review them before a transaction discussion.", print: "Print current summary" },
  ja: { eyebrow: "不動産専門家向けの取引準備", title: "顧客との面談前に税務・保有コスト・取引条件を整理", description: "決定論的な予備計算、公式情報の追跡、再利用できる案件を組み合わせます。", primary: "3分TaxOracleデモを開始", secondary: "物件案件を開始", boundary: "予備的な参考情報であり、公式判断ではありません。必要に応じて専門家が確認します。", demoTitle: "3分間の取引準備デモ", demoDescription: "案件事実を確認し、既存のTaxOracleと保有コスト計算を実行します。入力変更後に再計算します。", illustrative: "例示案件／実在顧客ではありません", steps: ["物件事実", "税務とコスト", "証拠", "概要"], calculate: "再計算", calculating: "計算中…", reset: "例をリセット", evidence: "証拠と方法", privacy: "プライバシー", terms: "規約と制限", source: "規則と出典", missing: "不足事実", inputs: "使用した入力", output: "計算概要", changed: "この変更は関連する保有コストまたは資格ルールに反映されます。", offline: "オフラインデモ：ローカル再現可能な参考モデルであり、最新の公式データを示しません。", switchOffline: "明示されたオフラインデモへ", live: "接続計算", incomplete: "事実が不足しています。取引前に補足または専門家確認をしてください。", print: "概要を印刷" },
  ko: { eyebrow: "부동산 전문가를 위한 거래 준비", title: "고객 미팅 전에 세금·보유비용·거래 조건을 정리하세요", description: "결정론적 예비 계산, 공식 출처 추적, 재사용 가능한 부동산 케이스를 결합합니다.", primary: "3분 TaxOracle 데모 시작", secondary: "부동산 케이스 시작", boundary: "예비 참고용이며 공식 세무 판단이 아닙니다. 필요하면 전문가 검토가 필요합니다.", demoTitle: "3분 거래 준비 데모", demoDescription: "케이스 사실을 확인하고 기존 TaxOracle 및 보유비용 계산을 실행합니다. 입력을 바꾸면 다시 계산됩니다.", illustrative: "예시 케이스 / 실제 고객 아님", steps: ["부동산 사실", "세금과 비용", "근거", "요약"], calculate: "다시 계산", calculating: "계산 중…", reset: "예시 초기화", evidence: "근거와 방법", privacy: "개인정보 보호", terms: "약관과 제한", source: "규칙과 출처", missing: "누락된 사실", inputs: "사용한 입력", output: "계산 요약", changed: "이 변경은 관련 보유비용 또는 자격 규칙에 반영됩니다.", offline: "오프라인 데모: 로컬에서 재현 가능한 참고 모델이며 최신 공식 데이터를 의미하지 않습니다.", switchOffline: "명시된 오프라인 데모로 전환", live: "연결 계산", incomplete: "사실이 완전하지 않습니다. 거래 전 보완하거나 전문가에게 확인하세요.", print: "현재 요약 인쇄" },
};

export function getCompetitionCopy(locale: ExperienceLocale) { return competitionCopy[locale] ?? competitionCopy["zh-TW"]; }
