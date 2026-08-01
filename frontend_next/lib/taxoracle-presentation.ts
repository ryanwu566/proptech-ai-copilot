import type { ExperienceLocale } from "@/lib/experience-i18n";
import type { TaxCase, TaxResult } from "@/lib/api";

export type TaxFieldKey = Exclude<keyof TaxCase, "case_id" | "client_name">;
type FieldCopy = { label: string; help: string; group: "property" | "occupancy" | "documents" | "review" };

const fieldKeys: TaxFieldKey[] = ["sold_self_occupied", "residency_condition_met", "purchase_within_reasonable_period", "purchased_self_occupied", "same_owner", "land_value_available", "required_docs_complete", "enters_five_year_monitoring", "exceptional_circumstances"];

const fieldCopies: Record<ExperienceLocale, Record<TaxFieldKey, FieldCopy>> = {
  "zh-TW": {
    sold_self_occupied: { label: "出售前是否為自住？", help: "確認出售物件的使用情形。", group: "occupancy" }, residency_condition_met: { label: "居住條件是否已確認？", help: "依目前提供的事實進行初步篩選。", group: "occupancy" }, purchase_within_reasonable_period: { label: "買入是否在規定期間內？", help: "日期與期間仍需依正式文件確認。", group: "property" }, purchased_self_occupied: { label: "買入物件是否預計自住？", help: "請依實際使用計畫回答。", group: "property" }, same_owner: { label: "前後物件是否為同一所有人？", help: "所有權文件可能需要專業複核。", group: "occupancy" }, land_value_available: { label: "公告土地現值資料是否可取得？", help: "缺少資料不會被自動視為符合。", group: "documents" }, required_docs_complete: { label: "必要文件是否已備齊？", help: "未備齊時會列為待補資料。", group: "documents" }, enters_five_year_monitoring: { label: "是否需要進入五年列管提醒？", help: "這是提醒用途，不是法律結論。", group: "review" }, exceptional_circumstances: { label: "是否有需要專業複核的特殊情形？", help: "若有特殊情形，請諮詢稅務專業人員。", group: "review" },
  },
  en: {
    sold_self_occupied: { label: "Was the property owner-occupied before sale?", help: "Describe the property's use before sale.", group: "occupancy" }, residency_condition_met: { label: "Are the residence conditions confirmed?", help: "This is an initial screening of the facts provided.", group: "occupancy" }, purchase_within_reasonable_period: { label: "Was the purchase within the applicable period?", help: "Dates and periods still require document review.", group: "property" }, purchased_self_occupied: { label: "Is the purchased property intended for self-use?", help: "Answer based on the intended use.", group: "property" }, same_owner: { label: "Is the owner the same before and after the transaction?", help: "Ownership documents may require professional review.", group: "occupancy" }, land_value_available: { label: "Is the announced land value information available?", help: "Missing information is not treated as confirmation.", group: "documents" }, required_docs_complete: { label: "Are the required documents available?", help: "Incomplete documents remain a follow-up item.", group: "documents" }, enters_five_year_monitoring: { label: "Should a five-year monitoring reminder be recorded?", help: "This is a reminder, not a legal conclusion.", group: "review" }, exceptional_circumstances: { label: "Are there exceptional circumstances requiring review?", help: "Ask a tax professional about exceptional circumstances.", group: "review" },
  },
  ja: {
    sold_self_occupied: { label: "売却前は自宅として使用していましたか？", help: "売却前の利用状況を確認します。", group: "occupancy" }, residency_condition_met: { label: "居住条件は確認済みですか？", help: "提供された事実による予備的な確認です。", group: "occupancy" }, purchase_within_reasonable_period: { label: "購入は適用期間内でしたか？", help: "日付と期間は書類で確認が必要です。", group: "property" }, purchased_self_occupied: { label: "購入物件は自宅として使用する予定ですか？", help: "予定している利用方法を選択してください。", group: "property" }, same_owner: { label: "取引前後の所有者は同じですか？", help: "所有権書類は専門家の確認が必要な場合があります。", group: "occupancy" }, land_value_available: { label: "公示土地価格の情報を取得できますか？", help: "情報がない場合、適合とは判断しません。", group: "documents" }, required_docs_complete: { label: "必要書類は揃っていますか？", help: "不足書類は確認事項として残ります。", group: "documents" }, enters_five_year_monitoring: { label: "5年間の確認リマインダーを記録しますか？", help: "リマインダーであり、法的判断ではありません。", group: "review" }, exceptional_circumstances: { label: "専門家の確認が必要な特別事情がありますか？", help: "特別事情は税務専門家に相談してください。", group: "review" },
  },
  ko: {
    sold_self_occupied: { label: "매도 전 해당 주택을 직접 거주했나요?", help: "매도 전 사용 상태를 확인합니다.", group: "occupancy" }, residency_condition_met: { label: "거주 요건을 확인했나요?", help: "제공된 사실에 대한 예비 확인입니다.", group: "occupancy" }, purchase_within_reasonable_period: { label: "매입이 적용 기간 안에 이루어졌나요?", help: "날짜와 기간은 서류 확인이 필요합니다.", group: "property" }, purchased_self_occupied: { label: "매입 주택을 직접 사용할 예정인가요?", help: "예정된 사용 목적을 기준으로 답하세요.", group: "property" }, same_owner: { label: "거래 전후 소유자가 동일한가요?", help: "소유권 서류는 전문가 확인이 필요할 수 있습니다.", group: "occupancy" }, land_value_available: { label: "공시지가 정보를 확인할 수 있나요?", help: "정보가 없으면 충족으로 처리하지 않습니다.", group: "documents" }, required_docs_complete: { label: "필요 서류가 준비되었나요?", help: "누락된 서류는 후속 확인 사항입니다.", group: "documents" }, enters_five_year_monitoring: { label: "5년 확인 알림을 기록할까요?", help: "알림이며 법적 판단이 아닙니다.", group: "review" }, exceptional_circumstances: { label: "전문가 검토가 필요한 특별 사정이 있나요?", help: "특별 사정은 세무 전문가에게 문의하세요.", group: "review" },
  },
};

const groups: Record<ExperienceLocale, Record<FieldCopy["group"], string>> = {
  "zh-TW": { property: "物件與交易", occupancy: "所有權與居住", documents: "文件與官方資料", review: "例外與複核" },
  en: { property: "Property and transaction", occupancy: "Ownership and occupancy", documents: "Documents and official information", review: "Exceptions and review" },
  ja: { property: "物件と取引", occupancy: "所有権と居住", documents: "書類と公式情報", review: "例外と確認" },
  ko: { property: "부동산과 거래", occupancy: "소유와 거주", documents: "서류와 공식 정보", review: "예외와 검토" },
};

const text: Record<ExperienceLocale, Record<string, string>> = {
  "zh-TW": { yes: "是", no: "否", unavailable: "無法判定", provided: "已提供", notProvided: "尚未提供", outcomeTitle: "初步稅務篩選", eligible: "依目前提供的資料，初步篩選條件目前符合。", not_eligible: "依目前提供的資料，有一項或多項必要條件目前未符合。", manual_review: "目前資料不完整或包含例外情形，建議交由專業人員複核。", boundary: "這是初步篩選結果，不是官方稅務核定。", facts: "已確認的必要事實", missing: "待補資料", reviewSignals: "需要複核的訊號", next: "下一步", nextText: "補充缺少的資料，並在交易前向稅務專業人員或主管機關確認。", source: "來源與規則狀態", sourceUnknown: "此示範尚未完成官方來源驗證。", calculation: "計算方式", calculationText: "使用既有 deterministic 規則進行初步篩選，結果只根據目前輸入。", technical: "技術詳細資料（預設收合）", internalVersion: "內部規則實作版本", caseId: "內部案件識別碼", price: "物件價格", currency: "新台幣", monthly: "每月", annual: "每年", holdingMonthly: "預估每月持有成本", holdingAnnual: "預估每年持有成本", holdingMeaning: "以目前輸入估算的持有成本；年額為月額乘以 12。不是帳單或核貸結果。", breakdown: "成本明細", notIncluded: "未納入或尚未提供的項目", noIncome: "未提供收入，因此不計算收入負擔比例。", exampleTitle: "競賽示範案件", exampleDisclosure: "示範資料／非真實客戶；可編輯，計算會依目前輸入重新執行。", reportTitle: "交易準備摘要", generated: "產生時間", print: "列印目前摘要", sourceConfigured: "官方來源狀態", professional: "建議專業複核" },
  en: { yes: "Yes", no: "No", unavailable: "Cannot determine", provided: "Provided", notProvided: "Not provided", outcomeTitle: "Preliminary tax screening", eligible: "Based on the information provided, the preliminary screening conditions are currently met.", not_eligible: "Based on the information provided, one or more required conditions are not currently met.", manual_review: "The available information is incomplete or includes an exception that requires professional review.", boundary: "This is a preliminary screening result, not an official tax assessment.", facts: "Confirmed required facts", missing: "Missing information", reviewSignals: "Review signals", next: "Next step", nextText: "Provide missing information and confirm with a tax professional or the relevant authority before a transaction.", source: "Source and rule status", sourceUnknown: "The official source has not been verified for this example.", calculation: "Calculation method", calculationText: "Existing deterministic rules provide a preliminary screening based only on the current inputs.", technical: "Technical details (collapsed by default)", internalVersion: "Internal rule implementation version", caseId: "Internal case identifier", price: "Property price", currency: "New Taiwan dollars", monthly: "per month", annual: "per year", holdingMonthly: "Estimated monthly holding cost", holdingAnnual: "Estimated annual holding cost", holdingMeaning: "A current-input ownership-cost estimate; the annual figure is monthly multiplied by 12. It is not a bill or loan approval.", breakdown: "Cost breakdown", notIncluded: "Not included or not provided", noIncome: "Income was not provided, so an income-burden ratio is not calculated.", exampleTitle: "Competition example case", exampleDisclosure: "Illustrative data / not a real customer; editable and recalculated from current inputs.", reportTitle: "Transaction preparation summary", generated: "Generated", print: "Print current summary", sourceConfigured: "Official source status", professional: "Professional review recommended" },
  ja: { yes: "はい", no: "いいえ", unavailable: "判定できません", provided: "提供済み", notProvided: "未提供", outcomeTitle: "税務の予備スクリーニング", eligible: "提供された情報では、予備スクリーニングの条件を現在満たしています。", not_eligible: "提供された情報では、必要条件の一つ以上を現在満たしていません。", manual_review: "情報が不足しているか例外があり、専門家の確認が必要です。", boundary: "これは予備スクリーニングであり、公式な税務判定ではありません。", facts: "確認済みの事実", missing: "不足情報", reviewSignals: "確認が必要な事項", next: "次のステップ", nextText: "不足情報を補い、取引前に税務専門家または関係機関へ確認してください。", source: "出典と規則の状態", sourceUnknown: "この例では公式出典の確認が完了していません。", calculation: "計算方法", calculationText: "既存の決定論的な規則で、現在の入力だけを使って予備判定します。", technical: "技術詳細（初期状態は折りたたみ）", internalVersion: "内部規則の実装バージョン", caseId: "内部案件識別子", price: "物件価格", currency: "ニュー台湾ドル", monthly: "月額", annual: "年額", holdingMonthly: "推定月間保有コスト", holdingAnnual: "推定年間保有コスト", holdingMeaning: "現在の入力による保有コストの参考値。年間額は月額×12で、請求書や融資承認ではありません。", breakdown: "コスト明細", notIncluded: "含まれない、または未提供", noIncome: "収入が未提供のため、負担率は計算していません。", exampleTitle: "競技用の例示案件", exampleDisclosure: "例示データ／実在顧客ではありません。入力を変更すると再計算します。", reportTitle: "取引準備サマリー", generated: "生成日時", print: "概要を印刷", sourceConfigured: "公式出典の状態", professional: "専門家の確認を推奨" },
  ko: { yes: "예", no: "아니요", unavailable: "판단할 수 없음", provided: "제공됨", notProvided: "제공되지 않음", outcomeTitle: "예비 세무 심사", eligible: "제공된 정보에 따르면 예비 심사 조건을 현재 충족합니다.", not_eligible: "제공된 정보에 따르면 하나 이상의 필수 조건을 현재 충족하지 않습니다.", manual_review: "정보가 불완전하거나 예외가 있어 전문가 검토가 필요합니다.", boundary: "이는 예비 심사 결과이며 공식 세무 판단이 아닙니다.", facts: "확인된 필수 사실", missing: "누락된 정보", reviewSignals: "검토 신호", next: "다음 단계", nextText: "누락 정보를 보완하고 거래 전에 세무 전문가 또는 관련 기관에 확인하세요.", source: "출처와 규칙 상태", sourceUnknown: "이 예시에서는 공식 출처 확인이 완료되지 않았습니다.", calculation: "계산 방법", calculationText: "기존 결정론적 규칙으로 현재 입력만 사용해 예비 심사합니다.", technical: "기술 세부사항 (기본 접힘)", internalVersion: "내부 규칙 구현 버전", caseId: "내부 케이스 식별자", price: "부동산 가격", currency: "신대만달러", monthly: "월", annual: "연", holdingMonthly: "예상 월 보유비용", holdingAnnual: "예상 연 보유비용", holdingMeaning: "현재 입력에 따른 보유비용 참고값이며 연간 금액은 월액×12입니다. 청구서나 대출 승인이 아닙니다.", breakdown: "비용 내역", notIncluded: "포함되지 않았거나 제공되지 않음", noIncome: "소득이 제공되지 않아 소득 부담률을 계산하지 않습니다.", exampleTitle: "대회 예시 케이스", exampleDisclosure: "예시 자료 / 실제 고객 아님; 입력을 바꾸면 다시 계산합니다.", reportTitle: "거래 준비 요약", generated: "생성 시각", print: "현재 요약 인쇄", sourceConfigured: "공식 출처 상태", professional: "전문가 검토 권장" },
};

export function getTaxFieldCopy(locale: ExperienceLocale, key: TaxFieldKey): FieldCopy { return fieldCopies[locale]?.[key] ?? fieldCopies.en[key]; }
export function getTaxGroupLabel(locale: ExperienceLocale, group: FieldCopy["group"]): string { return groups[locale]?.[group] ?? groups.en[group]; }
export function getTaxText(locale: ExperienceLocale, key: string): string { return text[locale]?.[key] ?? text.en[key] ?? key; }
export function getTaxFieldKeys(): TaxFieldKey[] { return fieldKeys; }
export function formatCurrency(value: number | null | undefined, locale: ExperienceLocale): string { if (value === null || value === undefined || !Number.isFinite(value)) return getTaxText(locale, "unavailable"); return `NT$${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value)}`; }
export function formatPropertyPrice(value: number, locale: ExperienceLocale): string { return formatCurrency(value * 10000, locale); }
export function formatBoolean(value: boolean | null | undefined, locale: ExperienceLocale): string { return value === true ? getTaxText(locale, "yes") : value === false ? getTaxText(locale, "no") : getTaxText(locale, "unavailable"); }
export function formatOutcome(value: TaxResult["eligibility_status"], locale: ExperienceLocale): string { return getTaxText(locale, value); }
export function humanSourceStatus(value: unknown, locale: ExperienceLocale): string { return value === "available" || value === "configured" ? getTaxText(locale, "provided") : getTaxText(locale, "sourceUnknown"); }

export function formatHoldingBreakdownKey(locale: ExperienceLocale, key: string): string {
  const labels: Record<ExperienceLocale, Record<string, string>> = {
    "zh-TW": { loan: "貸款支出", management: "管理費", repair_reserve: "修繕準備", tax_estimate: "房屋與土地稅估算", insurance: "保險" },
    en: { loan: "Financing payment", management: "Management cost", repair_reserve: "Maintenance reserve", tax_estimate: "Property and land tax estimate", insurance: "Insurance" },
    ja: { loan: "融資支出", management: "管理費", repair_reserve: "修繕準備", tax_estimate: "固定資産税等の推定", insurance: "保険" },
    ko: { loan: "금융 상환액", management: "관리비", repair_reserve: "수선 준비금", tax_estimate: "재산세 등 추정액", insurance: "보험" },
  };
  return labels[locale]?.[key] ?? labels.en[key] ?? getTaxText(locale, "notIncluded");
}

export function getTaxMetricLabel(locale: ExperienceLocale, metric: "failed" | "review" | "passed" | "missing"): string {
  const labels = {
    "zh-TW": { failed: "未通過規則", review: "需要複核", passed: "已通過規則", missing: "待補資料" },
    en: { failed: "Rules not met", review: "Review signals", passed: "Rules met", missing: "Missing information" },
    ja: { failed: "未達成の規則", review: "確認が必要な事項", passed: "確認済みの規則", missing: "不足情報" },
    ko: { failed: "충족되지 않은 규칙", review: "검토 신호", passed: "충족된 규칙", missing: "누락된 정보" },
  };
  return labels[locale][metric];
}

export function getTaxNoReviewMessage(locale: ExperienceLocale): string {
  return {
    "zh-TW": "目前沒有回傳需要複核的項目。",
    en: "No review items were returned for the current inputs.",
    ja: "現在の入力では確認事項は返されていません。",
    ko: "현재 입력에서는 검토 항목이 반환되지 않았습니다.",
  }[locale];
}

export function formatRuleVersion(value: unknown, locale: ExperienceLocale): string {
  if (typeof value !== "string" || !value) return getTaxText(locale, "unavailable");
  return {
    "zh-TW": "既有初步篩選規則版本",
    en: "Existing preliminary screening rule version",
    ja: "既存の予備スクリーニング規則バージョン",
    ko: "기존 예비 심사 규칙 버전",
  }[locale];
}
