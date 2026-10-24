import type { CopyCatalogue } from "../copy-catalogue";
import type { ExperienceLocale } from "../experience-i18n";
import type { OverviewItem } from "./overview-model";

/**
 * Overview presentation copy. The overview and checklist models keep producing their zh-TW wording and every
 * decision (what is known, unknown, blocked, ready); this layer only re-words those results for en, ja and ko.
 * zh-TW always renders the model text unchanged.
 */
type ViewKey =
  | "eyebrow" | "title" | "intro" | "decisionTitle" | "decisionDescription" | "attention" | "attentionEmpty" | "known" | "knownEmpty" | "unknown" | "unknownEmpty"
  | "statusLabel" | "readinessLabel" | "readinessNote"
  | "marketTitle" | "marketDescription" | "marketLink" | "asking" | "activePrice" | "marketMedian" | "estimateRange" | "estimateUnavailable" | "notYet" | "notProvided"
  | "locationTitle" | "locationDescription" | "locationLink" | "routeSaved" | "routeNone" | "transitUnavailable" | "otherMode"
  | "riskTitle" | "riskDescription" | "riskLink" | "riskNoMatch" | "riskUnknown" | "riskNone"
  | "financeTitle" | "financeDescription" | "financeLink" | "priceBasis" | "monthlyPayment" | "monthlyHousing" | "affordability" | "staleSnapshot" | "staleAssessment" | "assessed" | "unassessed" | "unassessedRatio" | "unassessedRecalc" | "unassessedOther" | "financeStale" | "financeUnassessed"
  | "saveTitle" | "saveDescription" | "saveNote" | "saveDisclosure" | "savedAt" | "marketDomain" | "locationDomain" | "riskDomain" | "financeDomain" | "identityBoundary" | "identityBoundaryText"
  | "nextTitle" | "next" | "nextEmpty" | "goTo"
  | "fresh_current" | "fresh_saved_snapshot" | "fresh_partial" | "fresh_stale" | "fresh_unavailable" | "fresh_not_started"
  | "mode_driving" | "mode_transit" | "mode_walking" | "mode_bicycling"
  | "section_overview" | "section_market" | "section_location" | "section_risk" | "section_finance"
  | "source_ASKING_PRICE" | "source_COMPARABLE_ESTIMATE" | "source_MANUAL_SCENARIO" | "source_none"
  | "basis_asking" | "basis_estimate" | "basis_manual";

export const overviewViewCopy: CopyCatalogue<ViewKey> = {
  "zh-TW": {
    eyebrow: "案件版本 {{revision}} · 瀏覽器本機快照", title: "物件總覽", intro: "先處理阻擋判讀的事項，再檢視已知證據與下一步查證。",
    decisionTitle: "決策摘要", decisionDescription: "只綜合目前案件版本中的有界證據；未查詢、無法取得與過期各自保留。",
    attention: "需要特別留意", attentionEmpty: "目前沒有額外需優先留意的狀態；仍應依證據限制查證。", known: "已掌握", knownEmpty: "目前沒有可在證據邊界內綜合的已知項目。", unknown: "尚未確認", unknownEmpty: "目前沒有額外尚未確認項目。",
    statusLabel: "目前案件狀態", readinessLabel: "看屋前準備", readinessNote: "{{count}} 項待確認或限制",
    marketTitle: "價格與市場", marketDescription: "開價、採用中的價格基準、市場證據與價格推估維持不同概念。", marketLink: "查看價格與市場", asking: "開價", activePrice: "目前採用價格（{{label}}）", marketMedian: "市場成交中位數", estimateRange: "價格推估區間", estimateUnavailable: "目前無法取得價格推估", notYet: "尚未取得", notProvided: "未提供",
    locationTitle: "區位與通勤", locationDescription: "保存的 Google 路線與次要大眾運輸證據各自呈現，互不覆蓋。", locationLink: "查看區位與通勤", routeSaved: "已保存前往{{destination}}的路線", routeNone: "尚未保存可用的目的地路線。", transitUnavailable: "次要大眾運輸證據目前無法取得；已保存的 Google 路線仍可使用。", otherMode: "其他方式",
    riskTitle: "風險與環境", riskDescription: "逐項保存符合、未命中與未知狀態；沒有任何整體安全分數。", riskLink: "查看風險與環境", riskNoMatch: "{{label}}：保存摘要未命中", riskUnknown: "{{label}}仍無法判定", riskNone: "尚未保存風險與環境證據。",
    financeTitle: "資金與持有成本", financeDescription: "計算狀態、已知成本與負擔能力分開呈現；缺少收入不會變成零。", financeLink: "查看資金與持有成本", priceBasis: "採用價格基準", monthlyPayment: "每月房貸試算", monthlyHousing: "已知每月住房成本", affordability: "負擔能力", staleSnapshot: "先前快照已過期", staleAssessment: "先前評估已過期", assessed: "已依收入評估", unassessed: "尚未評估（未提供月收入）", unassessedRatio: "尚未評估（已提供收入，但尚未取得可用負擔比例）", unassessedRecalc: "尚未評估（保存的評估資料不一致，需重新計算）", unassessedOther: "尚未評估（收入或可用負擔比例不足）",
    financeStale: "先前資金試算屬於不同物件狀態，不作為目前數值；重新確認物件後再檢視或計算。", financeUnassessed: "試算完成，但負擔能力尚未評估；兩者維持不同狀態。",
    saveTitle: "保存、鮮度與來源", saveDescription: "保存只代表保留目前已知狀態，不代表所有分析已完成。", saveNote: "已儲存的案件快照，不是即時重新查詢。各項結果與時間保留在下面的證據鮮度明細。", saveDisclosure: "查看快照與證據鮮度",
    savedAt: "案件保存時間", marketDomain: "市場／估價", locationDomain: "區位／通勤", riskDomain: "風險／環境", financeDomain: "資金／成本", identityBoundary: "身分邊界", identityBoundaryText: "瀏覽器案件關聯錨點只用於連結這次案件，不代表地號、建物、所有權、界址、權利或分區確認。",
    nextTitle: "下一步查證", next: "下一步", nextEmpty: "目前沒有系統指定的下一步。", goTo: "前往{{section}}",
    fresh_current: "本次工作階段證據", fresh_saved_snapshot: "已儲存的摘要快照", fresh_partial: "部分證據已保存，仍有項目待確認", fresh_stale: "資料可能已過期", fresh_unavailable: "目前無法取得證據", fresh_not_started: "尚未查詢",
    mode_driving: "開車", mode_transit: "大眾運輸", mode_walking: "步行", mode_bicycling: "自行車",
    section_overview: "物件確認", section_market: "價格與市場", section_location: "區位與通勤", section_risk: "風險與環境", section_finance: "資金與持有成本",
    source_ASKING_PRICE: "開價", source_COMPARABLE_ESTIMATE: "成交資料推估", source_MANUAL_SCENARIO: "手動試算情境", source_none: "價格來源未保存",
    basis_asking: "開價", basis_estimate: "成交資料推估中點", basis_manual: "比較基準價格",
  },
  en: {
    eyebrow: "Case version {{revision}} · Saved in this browser", title: "Case overview", intro: "Clear what blocks a judgement first, then review what is known and what to verify next.",
    decisionTitle: "Decision summary", decisionDescription: "Combines only the bounded evidence in this case version. Not queried, unavailable and outdated each stay as they are.",
    attention: "Needs attention", attentionEmpty: "Nothing else needs priority attention right now. Still verify within the evidence limits.", known: "Known", knownEmpty: "Nothing known can be combined within the evidence limits yet.", unknown: "Not yet confirmed", unknownEmpty: "Nothing else is waiting for confirmation.",
    statusLabel: "Current case status", readinessLabel: "Before viewing", readinessNote: "{{count}} items to confirm or limited",
    marketTitle: "Price and market", marketDescription: "Asking price, the price basis in use, market evidence and the price estimate stay separate ideas.", marketLink: "View price and market", asking: "Asking price", activePrice: "Price in use ({{label}})", marketMedian: "Market transaction median", estimateRange: "Estimated price range", estimateUnavailable: "Price estimate currently unavailable", notYet: "Not yet available", notProvided: "Not provided",
    locationTitle: "Location and commute", locationDescription: "The saved Google route and secondary transit evidence are shown separately; neither overrides the other.", locationLink: "View location and commute", routeSaved: "Saved route to {{destination}}", routeNone: "No usable destination route saved yet.", transitUnavailable: "Secondary transit evidence is currently unavailable; the saved Google route is still usable.", otherMode: "Other",
    riskTitle: "Risk and environment", riskDescription: "Matched, not matched and unknown are kept item by item. There is no overall safety score.", riskLink: "View risk and environment", riskNoMatch: "{{label}}: no match in the saved summary", riskUnknown: "{{label}} cannot be determined yet", riskNone: "No risk and environment evidence saved yet.",
    financeTitle: "Money and holding costs", financeDescription: "Calculation status, known costs and affordability are shown separately. Missing income never becomes zero.", financeLink: "View money and holding costs", priceBasis: "Price basis", monthlyPayment: "Monthly mortgage estimate", monthlyHousing: "Known monthly housing cost", affordability: "Affordability", staleSnapshot: "Earlier snapshot is outdated", staleAssessment: "Earlier assessment is outdated", assessed: "Assessed against income", unassessed: "Not assessed (no monthly income)", unassessedRatio: "Not assessed (income provided, but no usable burden ratio yet)", unassessedRecalc: "Not assessed (saved assessment is inconsistent; recalculate)", unassessedOther: "Not assessed (income or a usable burden ratio is missing)",
    financeStale: "The earlier money estimate belongs to a different property state and is not used as a current figure. Reconfirm the property before reviewing or recalculating.", financeUnassessed: "The estimate is complete, but affordability has not been assessed. They stay separate.",
    saveTitle: "Saving, freshness and sources", saveDescription: "Saving keeps what is currently known. It does not mean every analysis is complete.", saveNote: "This is a saved case snapshot, not a live re-query. Each result and its time are kept in the freshness details below.", saveDisclosure: "View snapshot and evidence freshness",
    savedAt: "Case saved", marketDomain: "Market / estimate", locationDomain: "Location / commute", riskDomain: "Risk / environment", financeDomain: "Money / costs", identityBoundary: "Identity boundary", identityBoundaryText: "The browser case link anchor only links this case. It does not confirm the parcel, building, ownership, boundaries, rights or zoning.",
    nextTitle: "What to verify next", next: "Next", nextEmpty: "No next step is set by the system right now.", goTo: "Go to {{section}}",
    fresh_current: "Evidence from this session", fresh_saved_snapshot: "Saved summary snapshot", fresh_partial: "Some evidence saved; items still to confirm", fresh_stale: "Evidence may be outdated", fresh_unavailable: "Evidence currently unavailable", fresh_not_started: "Not queried yet",
    mode_driving: "Driving", mode_transit: "Public transit", mode_walking: "Walking", mode_bicycling: "Cycling",
    section_overview: "property confirmation", section_market: "price and market", section_location: "location and commute", section_risk: "risk and environment", section_finance: "money and holding costs",
    source_ASKING_PRICE: "Asking price", source_COMPARABLE_ESTIMATE: "Transaction-based estimate", source_MANUAL_SCENARIO: "Manual scenario", source_none: "Price source not saved",
    basis_asking: "asking price", basis_estimate: "transaction-based estimate midpoint", basis_manual: "comparison base price",
  },
  ja: {
    eyebrow: "案件バージョン {{revision}} · このブラウザーに保存", title: "物件概要", intro: "判断を妨げる事項を先に解消し、分かっている根拠と次の確認事項を見ていきます。",
    decisionTitle: "判断のまとめ", decisionDescription: "この案件バージョンの範囲内の根拠だけをまとめます。未照会・取得不可・古い情報はそれぞれそのまま残します。",
    attention: "特に注意が必要", attentionEmpty: "現在、優先して注意すべき追加の状態はありません。根拠の制約に沿って確認してください。", known: "分かっていること", knownEmpty: "根拠の範囲内でまとめられる既知の項目はまだありません。", unknown: "未確認", unknownEmpty: "その他の未確認項目はありません。",
    statusLabel: "現在の案件の状態", readinessLabel: "内見前の準備", readinessNote: "確認待ち・制約あり {{count}} 件",
    marketTitle: "価格と市場", marketDescription: "売出価格、採用中の価格基準、市場の根拠、価格推計は別の概念として扱います。", marketLink: "価格と市場を見る", asking: "売出価格", activePrice: "採用中の価格（{{label}}）", marketMedian: "市場取引の中央値", estimateRange: "推計価格の範囲", estimateUnavailable: "価格推計は現在取得できません", notYet: "未取得", notProvided: "未提供",
    locationTitle: "立地と通勤", locationDescription: "保存した Google ルートと補助的な公共交通の根拠は別々に表示し、互いに上書きしません。", locationLink: "立地と通勤を見る", routeSaved: "{{destination}} へのルートを保存済み", routeNone: "利用できる目的地ルートはまだ保存されていません。", transitUnavailable: "補助的な公共交通の根拠は現在取得できません。保存済みの Google ルートは引き続き使えます。", otherMode: "その他",
    riskTitle: "リスクと環境", riskDescription: "該当・非該当・不明を項目ごとに保持します。全体の安全スコアはありません。", riskLink: "リスクと環境を見る", riskNoMatch: "{{label}}：保存済みサマリーでは非該当", riskUnknown: "{{label}}はまだ判定できません", riskNone: "リスクと環境の根拠はまだ保存されていません。",
    financeTitle: "資金と保有コスト", financeDescription: "計算の状態、判明しているコスト、返済負担は別々に表示します。収入がなくてもゼロにはなりません。", financeLink: "資金と保有コストを見る", priceBasis: "価格基準", monthlyPayment: "毎月のローン試算", monthlyHousing: "判明している毎月の住居費", affordability: "返済負担", staleSnapshot: "以前のスナップショットは古くなっています", staleAssessment: "以前の評価は古くなっています", assessed: "収入に基づき評価済み", unassessed: "未評価（月収未入力）", unassessedRatio: "未評価（収入は入力済みですが、有効な負担率はまだありません）", unassessedRecalc: "未評価（保存済みの評価が不整合のため再計算が必要）", unassessedOther: "未評価（収入または有効な負担率が不足）",
    financeStale: "以前の資金試算は別の物件状態のものであり、現在の数値としては使いません。物件を再確認してから確認または再計算してください。", financeUnassessed: "試算は完了しましたが、返済負担はまだ評価されていません。両者は別の状態のままです。",
    saveTitle: "保存・鮮度・出典", saveDescription: "保存は現在分かっている状態を残すだけで、すべての分析が完了したことを意味しません。", saveNote: "保存済みの案件スナップショットであり、リアルタイムの再照会ではありません。各結果と時刻は下の鮮度の詳細に残ります。", saveDisclosure: "スナップショットと根拠の鮮度を見る",
    savedAt: "案件の保存日時", marketDomain: "市場／推計", locationDomain: "立地／通勤", riskDomain: "リスク／環境", financeDomain: "資金／コスト", identityBoundary: "識別の境界", identityBoundaryText: "ブラウザー案件の関連付けアンカーはこの案件をつなぐためだけのもので、地番・建物・所有権・境界・権利・用途地域の確認を意味しません。",
    nextTitle: "次に確認すること", next: "次のステップ", nextEmpty: "現在、システムが指定する次のステップはありません。", goTo: "{{section}}へ",
    fresh_current: "今回のセッションの根拠", fresh_saved_snapshot: "保存済みのサマリー", fresh_partial: "一部の根拠を保存済み、未確認の項目あり", fresh_stale: "情報が古い可能性", fresh_unavailable: "根拠を現在取得できません", fresh_not_started: "未照会",
    mode_driving: "車", mode_transit: "公共交通", mode_walking: "徒歩", mode_bicycling: "自転車",
    section_overview: "物件の確認", section_market: "価格と市場", section_location: "立地と通勤", section_risk: "リスクと環境", section_finance: "資金と保有コスト",
    source_ASKING_PRICE: "売出価格", source_COMPARABLE_ESTIMATE: "取引データによる推計", source_MANUAL_SCENARIO: "手動の試算シナリオ", source_none: "価格の出典は未保存",
    basis_asking: "売出価格", basis_estimate: "取引データ推計の中央値", basis_manual: "比較基準価格",
  },
  ko: {
    eyebrow: "사례 버전 {{revision}} · 이 브라우저에 저장", title: "물건 개요", intro: "판단을 막는 사항을 먼저 해결한 뒤, 확인된 근거와 다음 확인 사항을 살펴보세요.",
    decisionTitle: "결정 요약", decisionDescription: "현재 사례 버전의 범위 안에 있는 근거만 종합합니다. 미조회, 가져올 수 없음, 오래됨은 각각 그대로 유지됩니다.",
    attention: "특히 주의할 사항", attentionEmpty: "지금 우선 주의할 추가 상태는 없습니다. 근거의 한계 안에서 확인하세요.", known: "확인된 내용", knownEmpty: "근거 범위 안에서 종합할 수 있는 확인된 항목이 아직 없습니다.", unknown: "아직 확인되지 않음", unknownEmpty: "추가로 확인을 기다리는 항목이 없습니다.",
    statusLabel: "현재 사례 상태", readinessLabel: "방문 전 준비", readinessNote: "확인 필요 또는 제한 {{count}}건",
    marketTitle: "가격과 시장", marketDescription: "호가, 사용 중인 가격 기준, 시장 근거, 가격 추정은 서로 다른 개념으로 유지됩니다.", marketLink: "가격과 시장 보기", asking: "호가", activePrice: "사용 중인 가격({{label}})", marketMedian: "시장 거래 중앙값", estimateRange: "추정 가격 범위", estimateUnavailable: "가격 추정을 현재 가져올 수 없음", notYet: "아직 없음", notProvided: "제공되지 않음",
    locationTitle: "입지와 통근", locationDescription: "저장된 Google 경로와 보조 대중교통 근거는 따로 표시되며 서로 덮어쓰지 않습니다.", locationLink: "입지와 통근 보기", routeSaved: "{{destination}}까지의 경로 저장됨", routeNone: "사용 가능한 목적지 경로가 아직 저장되지 않았습니다.", transitUnavailable: "보조 대중교통 근거를 현재 가져올 수 없습니다. 저장된 Google 경로는 계속 사용할 수 있습니다.", otherMode: "기타",
    riskTitle: "위험과 환경", riskDescription: "해당, 해당 없음, 알 수 없음을 항목별로 유지합니다. 전체 안전 점수는 없습니다.", riskLink: "위험과 환경 보기", riskNoMatch: "{{label}}: 저장된 요약에서 해당 없음", riskUnknown: "{{label}}: 아직 판단할 수 없음", riskNone: "위험 및 환경 근거가 아직 저장되지 않았습니다.",
    financeTitle: "자금과 보유 비용", financeDescription: "계산 상태, 알려진 비용, 부담 능력은 따로 표시됩니다. 소득이 없어도 0이 되지 않습니다.", financeLink: "자금과 보유 비용 보기", priceBasis: "가격 기준", monthlyPayment: "월 대출 상환 추정", monthlyHousing: "알려진 월 주거비", affordability: "부담 능력", staleSnapshot: "이전 스냅샷이 오래됨", staleAssessment: "이전 평가가 오래됨", assessed: "소득 기준으로 평가됨", unassessed: "평가되지 않음(월 소득 미입력)", unassessedRatio: "평가되지 않음(소득은 입력되었으나 유효한 부담 비율이 아직 없음)", unassessedRecalc: "평가되지 않음(저장된 평가가 일치하지 않아 재계산 필요)", unassessedOther: "평가되지 않음(소득 또는 유효한 부담 비율 부족)",
    financeStale: "이전 자금 추정은 다른 매물 상태에 속하므로 현재 수치로 사용하지 않습니다. 매물을 다시 확인한 후 검토하거나 다시 계산하세요.", financeUnassessed: "추정은 완료되었지만 부담 능력은 아직 평가되지 않았습니다. 두 상태는 별개로 유지됩니다.",
    saveTitle: "저장, 최신성 및 출처", saveDescription: "저장은 현재 알려진 상태를 남길 뿐이며 모든 분석이 끝났다는 뜻이 아닙니다.", saveNote: "저장된 사례 스냅샷이며 실시간 재조회가 아닙니다. 각 결과와 시각은 아래 최신성 세부 정보에 남아 있습니다.", saveDisclosure: "스냅샷과 근거 최신성 보기",
    savedAt: "사례 저장 시각", marketDomain: "시장 / 추정", locationDomain: "입지 / 통근", riskDomain: "위험 / 환경", financeDomain: "자금 / 비용", identityBoundary: "식별 경계", identityBoundaryText: "브라우저 사례 연결 앵커는 이 사례를 연결하는 데만 쓰이며 지번, 건물, 소유권, 경계, 권리 또는 용도지역을 확인하지 않습니다.",
    nextTitle: "다음 확인 사항", next: "다음 단계", nextEmpty: "현재 시스템이 지정한 다음 단계가 없습니다.", goTo: "{{section}}(으)로 이동",
    fresh_current: "이번 세션의 근거", fresh_saved_snapshot: "저장된 요약 스냅샷", fresh_partial: "일부 근거 저장됨, 확인할 항목 남음", fresh_stale: "자료가 오래되었을 수 있음", fresh_unavailable: "근거를 현재 가져올 수 없음", fresh_not_started: "아직 조회하지 않음",
    mode_driving: "자동차", mode_transit: "대중교통", mode_walking: "도보", mode_bicycling: "자전거",
    section_overview: "매물 확인", section_market: "가격과 시장", section_location: "입지와 통근", section_risk: "위험과 환경", section_finance: "자금과 보유 비용",
    source_ASKING_PRICE: "호가", source_COMPARABLE_ESTIMATE: "거래 자료 기반 추정", source_MANUAL_SCENARIO: "수동 추정 시나리오", source_none: "가격 출처가 저장되지 않음",
    basis_asking: "호가", basis_estimate: "거래 자료 추정 중간값", basis_manual: "비교 기준 가격",
  },
};

type Other = Exclude<ExperienceLocale, "zh-TW">;
type Four = Record<Other, string>;
const t3 = (en: string, ja: string, ko: string): Four => ({ en, ja, ko });
const fill = (text: string, values: Record<string, string>) => Object.entries(values).reduce((out, [key, value]) => out.replaceAll(`{{${key}}}`, value), text);

/** Evidence row names for Overview (market, valuation, location, commute, risk, finance). */
const evidenceRows: Record<string, Four> = {
  market: t3("Confirm market transaction evidence", "市場取引の根拠を確認", "시장 거래 근거 확인"),
  valuation: t3("Confirm the price estimate", "価格推計を確認", "가격 추정 확인"),
  location: t3("Confirm location data", "所在地データを確認", "위치 자료 확인"),
  commute: t3("Set a commute destination", "通勤先を設定", "통근 목적지 설정"),
  risk: t3("Confirm risk and environment evidence", "リスクと環境の根拠を確認", "위험 및 환경 근거 확인"),
  finance: t3("Build a money and holding-cost scenario", "資金と保有コストのシナリオを作成", "자금 및 보유 비용 시나리오 만들기"),
};

const hazards: Record<string, Four> = {
  terrain: t3("Terrain", "地形", "지형"),
  flood: t3("Flooding", "浸水", "침수"),
  landslide: t3("Landslide", "地すべり", "산사태"),
  debris_flow: t3("Debris flow", "土石流", "토석류"),
  liquefaction: t3("Soil liquefaction", "液状化", "토양 액상화"),
  geological_sensitivity: t3("Geologically sensitive area", "地質敏感区域", "지질 민감 지역"),
  active_fault: t3("Active fault", "活断層", "활성 단층"),
};

const items: Record<string, { label: Four; reason: Four }> = {
  "identity-revalidation": { label: t3("Reconfirm the current property", "現在の物件を再確認", "현재 매물 다시 확인"), reason: t3("The property data changed; previously affected evidence cannot be treated as current.", "物件データが変更されたため、影響を受けた以前の根拠は現在有効として扱えません。", "매물 자료가 변경되어 이전에 영향을 받은 근거를 현재 유효한 것으로 볼 수 없습니다.") },
  "identity-confirm-location": { label: t3("Confirm the property location", "物件の位置を確認", "매물 위치 확인"), reason: t3("The property location is not confirmed. Look up and confirm the address in Location and commute before requesting market, location and risk evidence.", "物件の位置が未確認です。「立地と通勤」で住所を照会・確定してから、市場・立地・リスクの根拠を照会できます。", "매물 위치가 확인되지 않았습니다. '입지와 통근'에서 주소를 조회하고 확정해야 시장, 입지, 위험 근거를 조회할 수 있습니다.") },
  "market-evidence": { label: t3("Saved market transaction summary", "保存済みの市場取引サマリー", "저장된 시장 거래 요약"), reason: t3("A bounded summary of market transactions is saved; see Price and market for its scope and limits.", "市場取引の範囲付きサマリーを保存済みです。範囲と制約は「価格と市場」で確認できます。", "시장 거래의 범위가 정해진 요약이 저장되어 있습니다. 범위와 한계는 '가격과 시장'에서 확인하세요.") },
  "secondary-transit-unavailable": { label: t3("Secondary transit evidence is currently unavailable", "補助的な公共交通の根拠は現在取得できません", "보조 대중교통 근거를 현재 가져올 수 없음"), reason: t3("The saved Google route is still usable; the two kinds of evidence stay independent.", "保存済みの Google ルートは引き続き使えます。2 つの根拠は独立しています。", "저장된 Google 경로는 계속 사용할 수 있으며 두 근거는 독립적으로 유지됩니다.") },
  "finance-calculation": { label: t3("Saved money estimate summary", "保存済みの資金試算サマリー", "저장된 자금 추정 요약"), reason: t3("Down payment, monthly payment and other bounded results are kept. A finished estimate does not mean affordability was assessed.", "頭金や毎月の返済などの範囲付き結果を保持しています。試算の完了は返済負担の評価を意味しません。", "계약금과 월 상환액 등 범위가 정해진 결과를 유지합니다. 추정 완료가 부담 능력 평가를 뜻하지는 않습니다.") },
  "finance-affordability-unassessed": { label: t3("Affordability not yet assessed", "返済負担は未評価", "부담 능력 미평가"), reason: t3("Affordability has not been assessed; a finished estimate and an affordability assessment stay separate.", "返済負担は未評価です。試算の完了と返済負担の評価は別の状態です。", "부담 능력이 평가되지 않았습니다. 추정 완료와 부담 능력 평가는 별개의 상태입니다.") },
  "verify-market-sources": { label: t3("Check price and market sources", "価格と市場の出典を確認", "가격 및 시장 출처 확인"), reason: t3("Review the scope, period and limits of the saved evidence.", "保存済み根拠の範囲・期間・制約を確認します。", "저장된 근거의 범위, 기간, 한계를 검토합니다.") },
  "verify-location-context": { label: t3("Check location and commute conditions", "立地と通勤の条件を確認", "입지 및 통근 조건 확인"), reason: t3("Confirm the destination, travel mode and secondary transit evidence fit this search.", "目的地・交通手段・補助的な公共交通の根拠が今回の条件に合うか確認します。", "목적지, 교통수단, 보조 대중교통 근거가 이번 조건에 맞는지 확인합니다.") },
  "verify-risk-sources": { label: t3("Check each risk source", "リスクの出典を項目ごとに確認", "위험 출처를 항목별로 확인"), reason: t3("Verify against each source's coverage and limits.", "各出典の対象範囲と制約に沿って確認します。", "각 출처의 적용 범위와 한계에 따라 확인합니다.") },
  "verify-finance-assumptions": { label: t3("Check money and cost assumptions", "資金とコストの前提を確認", "자금 및 비용 가정 확인"), reason: t3("Check income, the loan and holding costs not yet included.", "収入・ローン・まだ含まれていない保有コストを確認します。", "소득, 대출, 아직 포함되지 않은 보유 비용을 확인합니다.") },
};

const reasons = {
  notStarted: t3("Not queried yet; no data does not mean no problem.", "まだ照会していません。データがないことは問題がないことを意味しません。", "아직 조회하지 않았습니다. 자료가 없다고 문제가 없는 것은 아닙니다."),
  no_coverage: t3("Outside the current data coverage; confirm with another source.", "現在のデータの対象範囲外です。別の出典で確認してください。", "현재 자료 범위 밖입니다. 다른 출처로 확인하세요."),
  stale: t3("The existing summary needs reconfirming and is not treated as current evidence.", "既存のサマリーは再確認が必要で、現在の根拠として扱いません。", "기존 요약은 다시 확인해야 하며 현재 근거로 보지 않습니다."),
  unavailable: t3("This evidence is currently unavailable; unknown stays unknown.", "この根拠は現在取得できません。不明は不明のままです。", "이 근거를 현재 가져올 수 없습니다. 알 수 없음은 알 수 없음으로 유지됩니다."),
  riskMatched: t3("A saved source classification matched this location; see Risk and environment for the source and limits.", "保存済みの出典分類がこの位置に該当しました。出典と制約は「リスクと環境」で確認できます。", "저장된 출처 분류가 이 위치에 해당했습니다. 출처와 한계는 '위험과 환경'에서 확인하세요."),
  riskNoMatch: t3("No match in the saved summary is not proof of safety; still check the source coverage and the site.", "保存済みサマリーで非該当でも安全の証明ではありません。出典の範囲と現地を確認してください。", "저장된 요약에서 해당 없음은 안전의 증거가 아닙니다. 출처 범위와 현장을 계속 확인하세요."),
  riskUnknown: t3("The evidence is unavailable, outside coverage or outdated, so this cannot be determined.", "根拠が取得できない、範囲外、または古いため判定できません。", "근거를 가져올 수 없거나 범위 밖이거나 오래되어 판단할 수 없습니다."),
  commute: t3("The saved {{mode}} route distance and time summary is kept; Overview never re-queries it.", "保存済みの{{mode}}ルートの距離と時間のサマリーを保持しています。概要で自動的に再照会することはありません。", "저장된 {{mode}} 경로 거리와 시간 요약을 유지합니다. 개요에서 자동으로 다시 조회하지 않습니다."),
  affordability_unassessed: t3("No monthly income was provided; a finished estimate and an affordability assessment stay separate.", "月収が入力されていません。試算の完了と返済負担の評価は別の状態です。", "월 소득이 입력되지 않았습니다. 추정 완료와 부담 능력 평가는 별개의 상태입니다."),
  affordability_unassessedRatio: t3("Income was provided, but no usable burden ratio is available yet; a finished estimate and an affordability assessment stay separate.", "収入は入力済みですが、有効な負担率はまだありません。試算の完了と返済負担の評価は別の状態です。", "소득은 입력되었으나 유효한 부담 비율이 아직 없습니다. 추정 완료와 부담 능력 평가는 별개의 상태입니다."),
  affordability_unassessedRecalc: t3("The saved affordability data is inconsistent and needs recalculating; a finished estimate and an affordability assessment stay separate.", "保存済みの返済負担データが不整合のため再計算が必要です。試算の完了と返済負担の評価は別の状態です。", "저장된 부담 능력 자료가 일치하지 않아 재계산이 필요합니다. 추정 완료와 부담 능력 평가는 별개의 상태입니다."),
  needsReconfirm: t3("{{label}} (needs reconfirming)", "{{label}}（要再確認）", "{{label}} (다시 확인 필요)"),
};

/** Picks the unassessed wording from the money model's own reason; an unrecognized reason never claims income is missing. */
export function unassessedAffordabilityKey(reason: string | null | undefined): "unassessed" | "unassessedRatio" | "unassessedRecalc" | "unassessedOther" {
  if (!reason) return "unassessedOther";
  if (reason.startsWith("未提供月收入")) return "unassessed";
  if (reason.startsWith("尚未取得可用負擔比例")) return "unassessedRatio";
  if (reason.startsWith("保存的負擔評估資料不一致")) return "unassessedRecalc";
  return "unassessedOther";
}

type ItemCopy = { label: string; reason: string };
/** Re-words one overview item for en/ja/ko by its stable id; zh-TW and unknown ids keep the model text. */
export function presentOverviewItem(item: OverviewItem, locale: ExperienceLocale, mode?: string): ItemCopy {
  if (locale === "zh-TW") return { label: item.label, reason: item.reason };
  const direct = items[item.id];
  if (item.id === "finance-affordability-unassessed") {
    const key = unassessedAffordabilityKey(item.reason);
    return { label: direct.label[locale], reason: key === "unassessedOther" ? direct.reason[locale] : reasons[`affordability_${key}`][locale] };
  }
  if (item.id === "market-evidence") return { label: direct.label[locale], reason: marketFindings[item.reason]?.[locale] ?? item.reason };
  if (direct) return { label: direct.label[locale], reason: direct.reason[locale] };
  const evidence = /^(market|valuation|location|commute|risk|finance)-(not-started|stale|unavailable)$/.exec(item.id);
  if (evidence) {
    const [, key, kind] = evidence;
    const name = evidenceRows[key][locale];
    const reason = kind === "not-started" ? reasons.notStarted[locale] : item.reason.includes("涵蓋") ? reasons.no_coverage[locale] : kind === "stale" || item.reason.includes("重新確認") ? reasons.stale[locale] : reasons.unavailable[locale];
    if (kind === "stale") return { label: fill(reasons.needsReconfirm[locale], { label: name }), reason };
    return { label: kind === "unavailable" && key === "valuation" ? overviewViewCopy[locale].estimateUnavailable : name, reason };
  }
  const risk = /^risk-(material|no-match|unknown)-(.+)$/.exec(item.id);
  if (risk) {
    const name = hazards[risk[2]]?.[locale] ?? overviewViewCopy[locale].riskTitle;
    if (risk[1] === "material") return { label: name, reason: presentRiskResult(item.reason, locale) };
    if (risk[1] === "no-match") return { label: fill(overviewViewCopy[locale].riskNoMatch, { label: name }), reason: presentRiskResult(item.reason, locale) };
    return { label: fill(overviewViewCopy[locale].riskUnknown, { label: name }), reason: presentRiskResult(item.reason, locale) };
  }
  if (item.id === "commute-route") {
    const destination = /前往(.+)的路線/.exec(item.label)?.[1] ?? "";
    const rawMode = /已保存 (driving|transit|walking|bicycling) 路線/.exec(item.reason)?.[1];
    const modeLabel = rawMode ? overviewViewCopy[locale][`mode_${rawMode}` as ViewKey] : overviewViewCopy[locale].otherMode;
    return { label: fill(overviewViewCopy[locale].routeSaved, { destination }), reason: fill(reasons.commute[locale], { mode: mode ?? modeLabel }) };
  }
  return { label: item.label, reason: item.reason };
}

export const hazardName = (key: string, locale: ExperienceLocale, fallback: string) => locale === "zh-TW" ? fallback : hazards[key]?.[locale] ?? fallback;

const marketFindings: Record<string, Four> = {
  "物件身分尚未確認；保留開價與市場觀察，但不進行物件價格比較。": t3("Property identity is not confirmed. The asking price and market observations are kept, but no property price comparison is made.", "物件の識別は未確認です。売出価格と市場の観測は保持しますが、物件価格の比較は行いません。", "매물 식별이 확인되지 않았습니다. 호가와 시장 관측은 유지하지만 매물 가격 비교는 하지 않습니다."),
  "目前尚未提供開價，先以成交證據建立價格比較基準。": t3("No asking price has been provided. Establish a comparison basis from transaction evidence first.", "売出価格は未入力です。まず取引の根拠から価格比較の基準を作成してください。", "호가가 입력되지 않았습니다. 먼저 거래 근거로 가격 비교 기준을 마련하세요."),
  "已記錄開價，但區域成交總價中位數仍不足以進行比較。": t3("The asking price is recorded, but the area's median total transaction price is insufficient for comparison.", "売出価格は記録済みですが、地域の取引総額中央値は比較に十分ではありません。", "호가는 기록되었으나 지역 거래 총액 중앙값은 비교하기에 충분하지 않습니다."),
  "開價與目前觀察到的市場成交總價中位數接近。": t3("The asking price is close to the currently observed median total market transaction price.", "売出価格は現在観測される市場取引総額の中央値に近い水準です。", "호가는 현재 관측된 시장 거래 총액 중앙값에 가깝습니다."),
  "開價高於目前觀察到的市場成交總價中位數，仍需以物件條件與可比成交確認差異。": t3("The asking price is above the currently observed median total market transaction price. Confirm the difference against property conditions and comparable transactions.", "売出価格は現在観測される市場取引総額の中央値を上回ります。物件条件と比較可能な取引で差を確認してください。", "호가는 현재 관측된 시장 거래 총액 중앙값보다 높습니다. 매물 조건과 비교 거래로 차이를 확인하세요."),
  "開價低於目前觀察到的市場成交總價中位數，仍需確認物件條件與證據範圍。": t3("The asking price is below the currently observed median total market transaction price. Property conditions and evidence scope still need checking.", "売出価格は現在観測される市場取引総額の中央値を下回ります。物件条件と根拠の範囲を確認してください。", "호가는 현재 관측된 시장 거래 총액 중앙값보다 낮습니다. 매물 조건과 근거 범위를 확인해야 합니다."),
};

const riskResults: Record<string, Four> = {
  "未命中": t3("No match", "非該当", "해당 없음"),
  "目前無法取得": t3("Currently unavailable", "現在取得不可", "현재 가져올 수 없음"),
  "本次查詢範圍未比對到來源定義的符合資料；此結果僅限已確認的涵蓋與查詢範圍。": t3("No source-defined match was found within this query. This result is limited to the confirmed coverage and query scope.", "今回の照会範囲では出典定義の該当データがありません。確認済みの対象範囲と照会条件に限る結果です。", "이번 조회 범위에서 출처가 정의한 해당 자료를 찾지 못했습니다. 확인된 적용 범위와 조회 조건에 한정된 결과입니다."),
  "此位置不在目前資料涵蓋範圍，無法形成風險判讀。": t3("This location is outside current data coverage; no risk interpretation can be made.", "この位置は現在のデータの対象範囲外のため、リスクを判定できません。", "이 위치는 현재 자료 범위 밖이므로 위험을 판단할 수 없습니다."),
  "目前僅取得部分來源結果，無法形成完整判讀。": t3("Only partial source results are available; a complete interpretation cannot be made.", "出典結果の一部しか取得できず、完全な判定はできません。", "일부 출처 결과만 있어 완전한 판단을 할 수 없습니다."),
  "目前無法取得此項證據，風險仍無法判定。": t3("This evidence is currently unavailable; risk remains unknown.", "この根拠は現在取得できず、リスクは判定できません。", "이 근거를 현재 가져올 수 없으며 위험은 여전히 알 수 없습니다."),
  "目前資料不足，風險仍無法判定。": t3("Current data is insufficient; risk remains unknown.", "現在のデータは不足しており、リスクは判定できません。", "현재 자료가 부족하여 위험은 여전히 알 수 없습니다."),
  "目前自動查詢路徑尚未提供完成的活動斷層判讀結果。": t3("The automatic query has not provided a completed active-fault interpretation.", "自動照会では活断層の判定結果がまだ完成していません。", "자동 조회에서 활성 단층 판단 결과가 아직 완료되지 않았습니다."),
  "符合官方公告地質敏感區；目前來源未提供可辯護的風險分級。": t3("Matches an officially designated geologically sensitive area; the source provides no defensible risk grade.", "公告された地質敏感区域に該当します。出典から根拠あるリスク等級は示されていません。", "공식 공고 지질 민감 지역에 해당하며 출처에서 근거 있는 위험 등급을 제공하지 않습니다."),
  "本次位置符合此來源定義的圖層資料，需進一步查證。": t3("This location matches the source-defined layer; further verification is needed.", "この位置は出典定義のレイヤーに該当し、追加確認が必要です。", "이 위치는 출처가 정의한 레이어에 해당하며 추가 확인이 필요합니다."),
  "目前無法取得地形／坡度證據。": t3("Terrain / slope evidence is currently unavailable.", "地形・傾斜の根拠は現在取得できません。", "지형 및 경사 근거를 현재 가져올 수 없습니다."),
  "已取得地形／坡度參考資料。": t3("Terrain / slope reference data is available.", "地形・傾斜の参考データを取得済みです。", "지형 및 경사 참고 자료를 가져왔습니다."),
  "此摘要屬於先前物件狀態，不能作為目前證據。": t3("This summary belongs to an earlier property state and cannot be used as current evidence.", "以前の物件状態のサマリーであり、現在の根拠として使えません。", "이전 매물 상태의 요약으로 현재 근거로 사용할 수 없습니다."),
  "已儲存的查詢摘要為未命中；此結果不代表安全。": t3("The saved query summary had no match; this does not prove safety.", "保存済み照会サマリーでは非該当です。安全の証明ではありません。", "저장된 조회 요약은 해당 없음이며 안전의 증거가 아닙니다."),
  "目前無法取得此項已儲存證據，風險仍無法判定。": t3("This saved evidence is currently unavailable; the risk remains unknown.", "この保存済み根拠は現在取得できず、リスクは判定できません。", "이 저장된 근거를 현재 가져올 수 없으며 위험은 여전히 알 수 없습니다."),
  "已儲存摘要記錄此來源曾有符合資料；需重新查詢才能檢視完整結果。": t3("The saved summary records a source match; query again to see the full result.", "保存済みサマリーに出典の該当記録があります。全結果には再照会が必要です。", "저장된 요약에 출처 해당 기록이 있으며 전체 결과를 보려면 다시 조회해야 합니다."),
  "此為已儲存的摘要證據；需重新查詢才能檢視完整結果。": t3("This is saved summary evidence; query again to see the full result.", "保存済みの要約根拠です。全結果には再照会が必要です。", "저장된 요약 근거이며 전체 결과를 보려면 다시 조회해야 합니다."),
};
export function presentRiskResult(text: string, locale: ExperienceLocale): string {
  if (locale === "zh-TW") return text;
  if (riskResults[text]) return riskResults[text][locale];
  const followup = " 仍需核對來源範圍與現場。";
  if (text.endsWith(followup)) return `${presentRiskResult(text.slice(0, -followup.length), locale)} ${t3("Still check source coverage and the site.", "出典の対象範囲と現地の確認も必要です。", "출처 범위와 현장도 확인해야 합니다.")[locale]}`;
  const classification = /^本次位置符合來源分類「(.+)」。$/.exec(text);
  if (classification) return fill(t3("This location matches the source classification ‘{{name}}’.", "この位置は出典の分類「{{name}}」に該当します。", "이 위치는 출처 분류 '{{name}}'에 해당합니다.")[locale], { name: classification[1] });
  const categories = /^符合 (\d+) 項官方公告類別：(.+)。公告交集不代表高、中或低風險分級。$/.exec(text);
  if (categories) return fill(t3("Matches {{count}} officially designated categories: {{names}}. This intersection does not indicate a high, medium or low risk grade.", "公告された{{count}}分類に該当：{{names}}。公告範囲との交差は高・中・低のリスク等級を意味しません。", "공식 공고 분류 {{count}}개에 해당: {{names}}. 공고 범위 교차는 높음, 중간, 낮음 위험 등급을 뜻하지 않습니다.")[locale], { count: categories[1], names: categories[2] });
  const slope = /^來源提供坡度 (.+)。$/.exec(text);
  if (slope) return fill(t3("Source-reported slope: {{slope}}.", "出典の傾斜値：{{slope}}。", "출처의 경사 값: {{slope}}.")[locale], { slope: slope[1] });
  return text;
}

/** Re-expresses the model's preformatted 萬元 amounts as NT$ for en/ja/ko. Display only; values are unchanged. */
export function presentWanText(text: string, locale: ExperienceLocale): string {
  if (locale === "zh-TW") return text;
  if (text === "未提供") return overviewViewCopy[locale].notProvided;
  if (text === "尚未取得" || text === "尚未估算") return overviewViewCopy[locale].notYet;
  const perPing = { en: " / ping", ja: "／坪", ko: " / 평" }[locale];
  const nt = (raw: string) => `NT$${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(Number(raw.replaceAll(",", "")) * 10_000)}`;
  return text.replace(/([\d,]+(?:\.\d+)?)(?:\s*[–~-]\s*([\d,]+(?:\.\d+)?))?\s*萬元(／坪)?/g, (_match, low: string, high: string | undefined, ping: string | undefined) =>
    `${nt(low)}${high ? `–${nt(high)}` : ""}${ping ? perPing : ""}`);
}

/** Missing-cost lines from the money model, by their fixed wording. */
const missingCosts: Record<string, Four> = {
  "管理費（尚未提供）": t3("Management fee (not provided)", "管理費（未入力）", "관리비(미입력)"),
  "交易成本（未納入）": t3("Transaction costs (not included)", "取引コスト（未算入）", "거래 비용(미포함)"),
  "管理費（缺少坪數）": t3("Management fee (floor area missing)", "管理費（坪数未入力）", "관리비(면적 누락)"),
  "修繕準備（缺少坪數）": t3("Repair reserve (floor area missing)", "修繕積立金（坪数未入力）", "수선 충당금(면적 누락)"),
  "持有成本明細（尚未估算）": t3("Holding cost breakdown (not yet estimated)", "保有コストの内訳（未推計）", "보유 비용 내역(아직 추정 안 됨)"),
  "契稅、登記規費與仲介／代書等交易成本（未納入）": t3("Deed tax, registration fees, agent and scrivener costs (not included)", "契税・登記費用・仲介／司法書士などの取引コスト（未算入）", "취득세, 등기 수수료, 중개·법무사 등 거래 비용(미포함)"),
};
export const presentMissingCost = (text: string, locale: ExperienceLocale) => locale === "zh-TW" ? text : missingCosts[text]?.[locale] ?? text;

/** Checklist presentation: the visible list, controls and labels. Item evidence detail stays in its source wording. */
type ChecklistKey = "title" | "description" | "openFull" | "save" | "loadSaved" | "unsaved" | "saved" | "notSaved" | "notSavedStorage" | "identityStale" | "staleDraft"
  | "evidenceStatus" | "unsupportedAuto" | "gapReason" | "gapDefault" | "whyMatters" | "sources" | "noSources" | "viewSource" | "next" | "goTo" | "reviewedBy" | "reviewState"
  | "previousReview" | "recheck" | "userRecord" | "resolved" | "domainItems" | "nextGeneric";
export const checklistCopy: CopyCatalogue<ChecklistKey> = {
  "zh-TW": {
    title: "證據查證清單", description: "人工核對是使用者提供的紀錄，不代表官方查證；未知、未命中與無法取得仍保留原狀。", openFull: "開啟完整查證清單", save: "保存人工核對", loadSaved: "載入已保存核對狀態",
    unsaved: "尚未保存人工核對變更。", saved: "人工核對狀態已保存於此瀏覽器案件。", notSaved: "人工核對狀態未保存。", notSavedStorage: "人工核對狀態未保存。瀏覽器儲存失敗；請恢復儲存空間或存取後重試。",
    identityStale: "物件身分需重新確認；先前人工核對僅保留為歷史紀錄，目前不能新增核對。", staleDraft: "案件已有較新快照；草稿不能覆蓋新證據。請載入已保存核對狀態後再核對。",
    evidenceStatus: "來源證據狀態：", unsupportedAuto: "自動查證未支援", gapReason: "缺少或受限原因：", gapDefault: "保存摘要仍有來源與適用範圍限制", whyMatters: "為何重要：", sources: "來源：", noSources: "來源未保存", viewSource: "查看保存的來源：",
    next: "下一步：", goTo: "前往{{domain}}工作區", reviewedBy: "已由使用者核對：", reviewState: "人工核對狀態：", previousReview: "先前人工核對：", recheck: "；證據或物件已變更，需再次核對。", userRecord: "；僅為使用者紀錄。",
    resolved: "原缺口已由保存的來源證據補齊；人工核對紀錄仍保留。", domainItems: "{{domain}}查證項目", nextGeneric: "",
  },
  en: {
    title: "Evidence checklist", description: "Manual checks are your own records, not official verification. Unknown, no match and unavailable stay as they are.", openFull: "Open the full checklist", save: "Save manual checks", loadSaved: "Load saved checks",
    unsaved: "Manual check changes are not saved yet.", saved: "Manual checks saved to this browser case.", notSaved: "Manual checks were not saved. ", notSavedStorage: "Manual checks were not saved. Browser storage failed; free up storage or allow access and try again.",
    identityStale: "The property needs reconfirming. Earlier manual checks are kept as history only; new checks are not possible right now.", staleDraft: "This case has a newer snapshot; the draft cannot overwrite new evidence. Load the saved checks before checking again.",
    evidenceStatus: "Source evidence status: ", unsupportedAuto: "Automatic verification not supported", gapReason: "Missing or limited because: ", gapDefault: "The saved summary still has source and scope limits", whyMatters: "Why it matters: ", sources: "Sources: ", noSources: "Source not saved", viewSource: "View saved source: ",
    next: "Next: ", goTo: "Go to {{domain}}", reviewedBy: "Checked by you: ", reviewState: "Manual check status: ", previousReview: "Earlier manual check: ", recheck: "; the evidence or property changed, so check again.", userRecord: "; your record only.",
    resolved: "Saved source evidence now covers the original gap; your manual check record is kept.", domainItems: "{{domain}} checks", nextGeneric: "Review this in {{domain}}.",
  },
  ja: {
    title: "根拠の確認リスト", description: "手動確認はあなた自身の記録であり、公式の確認ではありません。不明・非該当・取得不可はそのまま残ります。", openFull: "確認リストをすべて開く", save: "手動確認を保存", loadSaved: "保存済みの確認状態を読み込む",
    unsaved: "手動確認の変更はまだ保存されていません。", saved: "手動確認の状態をこのブラウザーの案件に保存しました。", notSaved: "手動確認の状態は保存されていません。", notSavedStorage: "手動確認の状態は保存されていません。ブラウザーの保存に失敗しました。保存領域を空けるかアクセスを許可して再試行してください。",
    identityStale: "物件の再確認が必要です。以前の手動確認は履歴として残るだけで、現在は新しい確認を追加できません。", staleDraft: "この案件にはより新しいスナップショットがあります。下書きで新しい根拠を上書きできません。保存済みの確認状態を読み込んでから確認してください。",
    evidenceStatus: "出典の根拠の状態：", unsupportedAuto: "自動確認には未対応", gapReason: "不足・制約の理由：", gapDefault: "保存済みサマリーには出典と適用範囲の制約があります", whyMatters: "重要な理由：", sources: "出典：", noSources: "出典は未保存", viewSource: "保存済みの出典を見る：",
    next: "次のステップ：", goTo: "{{domain}}へ", reviewedBy: "あなたが確認済み：", reviewState: "手動確認の状態：", previousReview: "以前の手動確認：", recheck: "。根拠または物件が変わったため、再確認が必要です。", userRecord: "。あなたの記録のみです。",
    resolved: "保存済みの出典の根拠で元の不足が補われました。手動確認の記録は保持されます。", domainItems: "{{domain}}の確認項目", nextGeneric: "「{{domain}}」で確認してください。",
  },
  ko: {
    title: "근거 확인 목록", description: "수동 확인은 사용자가 남긴 기록이며 공식 확인이 아닙니다. 알 수 없음, 해당 없음, 가져올 수 없음은 그대로 유지됩니다.", openFull: "전체 확인 목록 열기", save: "수동 확인 저장", loadSaved: "저장된 확인 상태 불러오기",
    unsaved: "수동 확인 변경 사항이 아직 저장되지 않았습니다.", saved: "수동 확인 상태를 이 브라우저 사례에 저장했습니다.", notSaved: "수동 확인 상태를 저장하지 못했습니다. ", notSavedStorage: "수동 확인 상태를 저장하지 못했습니다. 브라우저 저장에 실패했습니다. 저장 공간을 확보하거나 접근을 허용한 후 다시 시도하세요.",
    identityStale: "매물을 다시 확인해야 합니다. 이전 수동 확인은 기록으로만 남으며 지금은 새로 확인할 수 없습니다.", staleDraft: "이 사례에 더 새로운 스냅샷이 있어 초안으로 새 근거를 덮어쓸 수 없습니다. 저장된 확인 상태를 불러온 후 다시 확인하세요.",
    evidenceStatus: "출처 근거 상태: ", unsupportedAuto: "자동 확인 미지원", gapReason: "누락 또는 제한 이유: ", gapDefault: "저장된 요약에는 여전히 출처 및 적용 범위 한계가 있습니다", whyMatters: "중요한 이유: ", sources: "출처: ", noSources: "출처가 저장되지 않음", viewSource: "저장된 출처 보기: ",
    next: "다음 단계: ", goTo: "{{domain}}(으)로 이동", reviewedBy: "사용자가 확인함: ", reviewState: "수동 확인 상태: ", previousReview: "이전 수동 확인: ", recheck: "; 근거나 매물이 바뀌어 다시 확인해야 합니다.", userRecord: "; 사용자 기록일 뿐입니다.",
    resolved: "저장된 출처 근거로 원래의 누락이 보완되었습니다. 수동 확인 기록은 유지됩니다.", domainItems: "{{domain}} 확인 항목", nextGeneric: "'{{domain}}'에서 확인하세요.",
  },
};

const checklistDomains: Record<string, Four> = {
  identity: t3("Property identity", "物件の識別", "매물 식별"), risk: t3("Risk and environment", "リスクと環境", "위험과 환경"), market: t3("Price and market", "価格と市場", "가격과 시장"),
  location: t3("Location and commute", "立地と通勤", "입지와 통근"), finance: t3("Money and costs", "資金とコスト", "자금과 비용"),
};
const checklistNames: Record<string, Four> = {
  "identity-legal": t3("Parcel, building and rights identity", "地番・建物・権利の識別", "지번, 건물 및 권리 식별"), "property-area": t3("Floor area", "物件の面積", "매물 면적"),
  "price-asking": t3("Asking price and chosen price basis", "売出価格と選択した価格基準", "호가와 선택한 가격 기준"), "market-summary": t3("Market transaction range and sample", "市場取引の範囲とサンプル", "시장 거래 범위와 표본"),
  "valuation-summary": t3("Price estimate and comparables", "価格推計と比較事例", "가격 추정과 비교 사례"), "location-summary": t3("Nearby facilities and source coverage", "周辺施設と出典の対象範囲", "주변 시설과 출처 범위"),
  "poi-risk": t3("Nearby facility risks", "周辺施設のリスク", "주변 시설 위험"), "commute-summary": t3("Destination route and commute", "目的地ルートと通勤条件", "목적지 경로와 통근 조건"),
  "finance-scenario": t3("Mortgage estimate and saved assumptions", "ローン試算と保存済みの前提", "대출 추정과 저장된 가정"), "finance-affordability": t3("Income and affordability", "収入と返済負担", "소득과 부담 능력"),
  "finance-costs": t3("Holding and transaction costs", "保有コストと取引コスト", "보유 및 거래 비용"), "finance-tax": t3("Supplementary tax check", "税務の補足確認", "세무 보충 확인"),
};
const reviewLabels: Record<string, Four> = {
  not_checked: t3("Not checked", "未確認", "확인 안 함"), pending: t3("Awaiting manual check", "手動確認待ち", "수동 확인 대기"),
  reviewed: t3("Checked by you", "あなたが確認済み", "사용자가 확인함"), recheck: t3("Check again", "再確認が必要", "다시 확인 필요"),
};
const evidenceStatuses: Record<string, Four> = {
  available: t3("Saved evidence", "保存済みの根拠", "저장된 근거"), limited: t3("Saved summary / limited", "保存済みサマリー／制約あり", "저장된 요약 / 제한"), not_run: t3("Not queried", "未照会", "조회 안 함"),
  unavailable: t3("Tried; currently unavailable", "照会済み、現在取得不可", "시도함, 현재 가져올 수 없음"), unsupported: t3("Not supported / manual check needed", "未対応／手動確認が必要", "지원 안 됨 / 수동 확인 필요"),
  no_coverage: t3("No data coverage", "データの対象範囲外", "자료 범위 없음"), no_match: t3("No match; not proof of safety", "非該当、安全の証明ではありません", "해당 없음, 안전의 증거 아님"),
  stale: t3("Outdated; reconfirm", "古い情報、再確認が必要", "오래됨, 다시 확인 필요"), insufficient: t3("Insufficient data", "データ不足", "자료 부족"),
};
const gapLabels: Record<string, Four> = {
  missing_input: t3("Missing input", "入力不足", "입력 누락"), not_run: t3("Not queried", "未照会", "조회 안 함"), unavailable: t3("Currently unavailable", "現在取得不可", "현재 가져올 수 없음"),
  unsupported: t3("Not supported", "未対応", "지원 안 됨"), no_coverage: t3("No data coverage", "データの対象範囲外", "자료 범위 없음"), stale: t3("Outdated", "古い情報", "오래됨"),
  insufficient: t3("Insufficient evidence", "根拠不足", "근거 부족"), not_preserved: t3("Not kept in the snapshot", "スナップショットに未保存", "스냅샷에 저장 안 됨"),
};
const pick = (table: Record<string, Four>, key: string, locale: ExperienceLocale, fallback: string) => locale === "zh-TW" ? fallback : table[key]?.[locale] ?? fallback;
export const checklistDomainLabel = (domain: string, locale: ExperienceLocale, fallback: string) => pick(checklistDomains, domain, locale, fallback);
export const checklistItemName = (id: string, locale: ExperienceLocale, fallback: string) => id.startsWith("risk-") ? hazardName(id.slice(5), locale, fallback) : pick(checklistNames, id, locale, fallback);
export const checklistReviewLabel = (state: string, locale: ExperienceLocale, fallback: string) => pick(reviewLabels, state, locale, fallback);
export const checklistEvidenceStatus = (status: string, locale: ExperienceLocale, fallback: string) => pick(evidenceStatuses, status, locale, fallback);
export const checklistGapLabel = (reason: string, locale: ExperienceLocale, fallback: string) => pick(gapLabels, reason, locale, fallback);

const checklistActions: Record<string, Four> = {
  "回到物件總覽確認案件條件": t3("Return to Overview to confirm the case conditions.", "概要に戻って案件の条件を確認してください。", "개요로 돌아가 사례 조건을 확인하세요."),
  "回到價格與市場，明確執行查詢確認證據": t3("Return to Price and market and explicitly query the evidence.", "価格と市場に戻り、明示的に照会して根拠を確認してください。", "가격과 시장으로 돌아가 직접 조회하여 근거를 확인하세요."),
  "回到區位與通勤，確認條件後明確查詢": t3("Return to Location and commute, confirm the conditions, then explicitly query.", "立地と通勤に戻り、条件を確認してから明示的に照会してください。", "입지와 통근으로 돌아가 조건을 확인한 후 직접 조회하세요."),
  "回到風險與環境，核對官方來源與現場條件": t3("Return to Risk and environment to check official sources and site conditions.", "リスクと環境に戻り、公式の出典と現地の条件を確認してください。", "위험과 환경으로 돌아가 공식 출처와 현장 조건을 확인하세요."),
  "回到資金與成本，補齊假設後明確計算": t3("Return to Money and costs, complete the assumptions, then explicitly calculate.", "資金とコストに戻り、前提を補ってから明示的に計算してください。", "자금과 비용으로 돌아가 가정을 입력한 후 직접 계산하세요."),
  "先確認本案件地址與定位；地籍、建物與權利文件需另行人工查證。": t3("Confirm this case's address and location first. Parcel, building and rights documents require separate manual verification.", "まず案件の住所と位置を確認してください。地籍・建物・権利の書類は別途手動で確認が必要です。", "먼저 사례의 주소와 위치를 확인하세요. 지적, 건물, 권리 서류는 별도의 수동 확인이 필요합니다."),
  "現場確認基地坡度、排水與擋土設施，必要時請專業人員判讀。": t3("Check the site's slope, drainage and retaining structures in person; seek a professional assessment if needed.", "現地で傾斜・排水・擁壁を確認し、必要に応じて専門家に相談してください。", "현장에서 경사, 배수 및 옹벽을 확인하고 필요하면 전문가의 평가를 받으세요."),
  "開啟水利署來源詳情，並查證現場排水與過往積淹水紀錄。": t3("Open the Water Resources Agency source details and check site drainage and past flooding records.", "水利署の出典詳細を開き、現地の排水と過去の浸水記録を確認してください。", "수리서 출처 세부 정보를 열고 현장 배수와 과거 침수 기록을 확인하세요."),
  "檢視農村水保署圖資，並確認基地周邊邊坡與擋土設施。": t3("Review the rural development and soil conservation maps, and check nearby slopes and retaining structures.", "農村水保署の地図と、敷地周辺の斜面・擁壁を確認してください。", "농촌수보서 지도와 부지 주변 경사면 및 옹벽을 확인하세요."),
  "檢視農村水保署土石流圖資與影響範圍，必要時請專業人員判讀。": t3("Review the agency's debris-flow maps and affected areas; seek a professional assessment if needed.", "農村水保署の土石流地図と影響範囲を確認し、必要に応じて専門家に相談してください。", "농촌수보서 토석류 지도와 영향 범위를 확인하고 필요하면 전문가의 평가를 받으세요."),
  "檢視地質雲的區域分類，個案仍應配合現地調查與工程評估。": t3("Review the geological map's area classification. Individual sites still require field investigation and engineering assessment.", "地質雲の地域分類を確認してください。個別案件では現地調査と工学的評価が必要です。", "지질운 지역 분류를 확인하세요. 개별 부지는 현장 조사와 공학적 평가가 필요합니다."),
  "核對地質調查及礦業管理中心的公告類別與資料版本。": t3("Check the Geological Survey and Mining Management Agency's published category and data version.", "地質調査及礦業管理中心の公告分類とデータ版を確認してください。", "지질조사 및 광업관리센터의 공고 분류와 자료 버전을 확인하세요."),
  "目前自動比對未完成；請改至官方地質圖台人工確認。": t3("Automatic matching is incomplete. Manually check the official geological map instead.", "自動照合は未完了です。公式の地質地図で手動確認してください。", "자동 대조가 완료되지 않았습니다. 공식 지질 지도에서 수동으로 확인하세요."),
};
export const presentChecklistAction = (text: string, locale: ExperienceLocale) => locale === "zh-TW" ? text : checklistActions[text]?.[locale] ?? text;

/** Localized detail for the readiness sentence; the readiness state itself comes from the model. */
const readinessDetail = {
  located: t3("the property location is not yet confirmed", "物件の位置が未確認", "매물 위치 미확인"),
  reconfirm: t3("the property identity needs reconfirming", "物件の識別に再確認が必要", "매물 식별 재확인 필요"),
  limitation: t3("items not yet confirmed", "未確認の事項", "확인되지 않은 사항"),
};
export function readinessDetailFor(locale: Other, neverLocated: boolean) {
  return { blocker: (neverLocated ? readinessDetail.located : readinessDetail.reconfirm)[locale], limitation: readinessDetail.limitation[locale] };
}

const perMonth = t3(" / month", "／月", " / 월");
/** Monthly NT$ amount for en/ja/ko; null stays "not yet available", never zero. */
export function presentMonthlyTwd(value: number | null | undefined, locale: Other): string {
  if (value == null || !Number.isFinite(value) || value < 0) return overviewViewCopy[locale].notYet;
  return `NT$${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value)}${perMonth[locale]}`;
}
export function presentDistance(metres: number | null | undefined, locale: Other): string {
  if (metres == null || !Number.isFinite(metres) || metres < 0) return overviewViewCopy[locale].notProvided;
  const format = new Intl.NumberFormat(locale, { maximumFractionDigits: metres < 10_000 ? 1 : 0 });
  return metres < 1_000 ? `${format.format(Math.round(metres))} m` : `${format.format(metres / 1_000)} km`;
}
const durationCopy = { minutes: t3("about {{m}} min", "約{{m}}分", "약 {{m}}분"), hours: t3("about {{h}} h {{m}} min", "約{{h}}時間{{m}}分", "약 {{h}}시간 {{m}}분") };
export function presentDuration(minutes: number | null | undefined, locale: Other): string {
  if (minutes == null || !Number.isFinite(minutes) || minutes < 0) return overviewViewCopy[locale].notProvided;
  const rounded = Math.round(minutes);
  return rounded < 60 ? fill(durationCopy.minutes[locale], { m: String(rounded) }) : fill(durationCopy.hours[locale], { h: String(Math.floor(rounded / 60)), m: String(rounded % 60) });
}
