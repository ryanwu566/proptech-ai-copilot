import type { ExperienceLocale } from "../experience-i18n";
import type { BuyerHazard, BuyerState } from "./risk-buyer-model";

type Four = readonly [string, string, string, string];
const index = (locale: ExperienceLocale) => (["zh-TW", "en", "ja", "ko"] as const).indexOf(locale);
const labels = {
  title: ["風險與環境", "Risk & environment", "リスクと環境", "위험 및 환경"],
  intro: ["出價前，先釐清證據，再逐項查證。", "Understand the evidence and verify each topic before making an offer.", "購入の申込み前に、証拠を整理し、一つずつ確認しましょう。", "매수 제안 전에 근거를 파악하고 항목별로 확인하세요."],
  principle: ["未知不代表安全", "Unknown does not mean safe", "不明は安全を意味しません", "미확인은 안전을 뜻하지 않습니다"],
  caution: ["未命中、資料不足與無法取得，都不能作為安全證明。", "No match, insufficient data and unavailable evidence cannot establish safety.", "該当なし、資料不足、取得不可は、いずれも安全の証明にはなりません。", "일치 없음, 자료 부족, 근거를 가져올 수 없음은 모두 안전의 증거가 아닙니다."],
  preQuery: ["尚未查詢風險證據；出價前仍需逐項查證。", "Risk evidence has not been queried; verify each topic before making an offer.", "リスクの証拠は未照会です。購入の申込み前に各項目の確認が必要です。", "위험 근거를 아직 조회하지 않았습니다. 매수 제안 전에 항목별 확인이 필요합니다."],
  count: ["出價前仍有 {count} 項需要查證", "{count} topics still need verification before an offer", "購入の申込み前に、まだ {count} 項目の確認が必要です", "매수 제안 전 아직 {count}개 항목을 확인해야 합니다"],
  countNote: ["計算不同災害主題，包含未命中的例行查證；不含地形參考與建物提醒。閱讀卡片不代表已完成查證。", "Counts distinct hazard topics, including routine checks after no match. Terrain reference and building advice are excluded. Reading a card does not complete verification.", "該当なしの通常確認も含め、災害の種類を数えています。地形参考と建物の助言は対象外です。カードの閲覧は確認完了を意味しません。", "일치 없음의 정기 확인을 포함한 개별 재해 항목 수입니다. 지형 참고와 건물 조언은 제외됩니다. 카드를 읽어도 확인이 완료되지는 않습니다."],
  known: ["已知", "What we know", "分かっていること", "확인된 내용"],
  limits: ["不能證明", "What this does not prove", "この結果だけでは分からないこと", "이 결과로 입증되지 않는 내용"],
  next: ["下一步查證", "Verify next", "次に確認すること", "다음 확인 사항"],
  guidance: ["以下為應用程式整理的查證指引，並非官方來源引文。", "Verification guidance prepared by the application, not an official-source quotation.", "以下はアプリが整理した確認の指針です。公式資料からの引用ではありません。", "아래는 앱이 작성한 확인 안내이며 공식 출처의 인용문이 아닙니다."],
  current_query: ["本次查詢", "Current query", "今回の照会", "이번 조회"],
  saved_summary: ["已儲存摘要", "Saved summary", "保存済み要約", "저장된 요약"],
  stale: ["已過期", "Stale", "更新が必要", "오래된 근거"],
  not_queried: ["尚未查詢", "Not queried", "未照会", "조회 전"],
  savedTitle: ["已儲存的摘要證據", "Saved summary evidence", "保存済みの要約証拠", "저장된 요약 근거"],
  savedNotice: ["需重新查詢才能檢視完整結果；摘要不會被重建成即時證據。", "Query again to view full results. Saved summaries do not reconstruct current provider evidence.", "完全な結果を見るには再照会が必要です。保存済み要約から現在の提供元の証拠は再構築しません。", "전체 결과를 보려면 다시 조회하세요. 저장된 요약으로 현재 제공기관의 근거를 재구성하지 않습니다."],
  savedMatched: ["保存摘要記錄到需要查證的訊號。", "The saved summary records a matched signal requiring verification.", "保存済み要約には確認が必要な該当情報が記録されています。", "저장된 요약에 확인이 필요한 일치 신호가 기록되어 있습니다."],
  savedNoMatch: ["保存摘要記錄為未命中；並非本次查詢。", "The saved summary records no match; this is not a current query.", "保存済み要約は該当なしと記録されています。今回の照会結果ではありません。", "저장된 요약에 일치 없음으로 기록되어 있습니다. 이번 조회 결과가 아닙니다."],
  staleNotice: ["此摘要屬於先前物件狀態，不能作為目前證據。", "This summary belongs to a previous property identity and cannot serve as current evidence.", "この要約は以前の物件情報に対応しており、現在の証拠としては使えません。", "이 요약은 이전 매물 정보에 해당하며 현재 근거로 사용할 수 없습니다."],
  query: ["查詢目前物件風險證據", "Query risk evidence for this property", "この物件のリスク証拠を照会", "현재 매물의 위험 근거 조회"],
  loading: ["查詢中", "Querying", "照会中", "조회 중"],
  identity: ["物件資料已變更，需重新確認後再查詢。", "Property details need confirmation before querying.", "照会前に物件情報の再確認が必要です。", "조회 전에 매물 정보를 다시 확인해야 합니다."],
  errorTitle: ["查詢未完成", "Query incomplete", "照会未完了", "조회 미완료"],
  saveError: ["風險證據未保存；請確認瀏覽器儲存後重試。", "Risk evidence was not saved. Check browser storage and try again.", "リスク証拠を保存できませんでした。ブラウザーの保存設定を確認して再試行してください。", "위험 근거가 저장되지 않았습니다. 브라우저 저장 설정을 확인하고 다시 시도하세요."],
  queryError: ["目前無法完成風險證據查詢；已保留其他可用內容，請稍後重試並持續人工查證。", "Risk evidence could not be retrieved. Other content is retained; try again later and continue manual verification.", "リスク証拠を取得できません。他の内容は保持されています。後で再試行し、手動での確認を続けてください。", "위험 근거를 가져오지 못했습니다. 다른 내용은 유지됩니다. 나중에 다시 시도하고 수동 확인을 계속하세요."],
  retry: ["重試此項查詢", "Retry query", "照会を再試行", "조회 다시 시도"],
  cards: ["出價前查證事項", "Due diligence before an offer", "購入の申込み前の確認事項", "매수 제안 전 확인 사항"],
  sourceDetails: ["來源／證據詳情", "Source / evidence details", "出典・証拠の詳細", "출처 / 근거 상세"],
  openCard: ["展開查證指引", "Open verification guidance", "確認の指針を開く", "확인 안내 펼치기"],
  evidenceType: ["證據類型", "Evidence type", "証拠の種類", "근거 유형"],
  topicIdentity: ["主題代碼", "Topic identifier", "項目コード", "항목 코드"],
  details: ["詳細證據", "Detailed evidence", "証拠の詳細", "상세 근거"],
  table: ["風險證據表", "Risk evidence table", "リスク証拠一覧", "위험 근거 표"],
  tableNote: ["保留來源原文與技術欄位；查詢完成不等於風險較低。", "Original evidence text and technical fields are retained. A completed query does not establish lower risk.", "元の証拠文と技術項目を保持します。照会の完了はリスクが低いことを意味しません。", "원문과 기술 필드를 유지합니다. 조회 완료가 위험이 낮다는 뜻은 아닙니다."],
  source: ["來源", "Source", "出典", "출처"],
  agency: ["機關", "Agency", "機関", "기관"],
  dataset: ["資料集", "Dataset", "データセット", "데이터셋"],
  classification: ["來源分類／公告類別", "Source classification / announced category", "出典の分類・公表区分", "출처 분류 / 공고 범주"],
  coverage: ["涵蓋範圍", "Coverage", "対象範囲", "제공 범위"],
  covered: ["本次範圍已涵蓋", "Query area covered", "照会範囲を網羅", "조회 범위 포함"],
  not_covered: ["不在涵蓋範圍", "Outside coverage", "対象範囲外", "제공 범위 밖"],
  partial: ["部分涵蓋", "Partial coverage", "一部のみ対象", "일부 범위만 포함"],
  unknown: ["未知／未提供", "Unknown / not provided", "不明・未提供", "알 수 없음 / 미제공"],
  version: ["有效期間／版本", "Effective period / version", "有効期間・版", "유효 기간 / 버전"],
  period: ["來源資料期間", "Source data period", "出典データの期間", "출처 자료 기간"],
  checked: ["查詢／保存時間", "Query / saved time", "照会・保存日時", "조회 / 저장 시간"],
  timeNote: ["查詢時間不等於資料發布時間。", "Query time is not the dataset publication time.", "照会日時はデータの公開日時ではありません。", "조회 시간은 자료 발행 시간이 아닙니다."],
  condition: ["查詢條件", "Query condition", "照会条件", "조회 조건"],
  limitations: ["來源限制", "Source limitations", "出典の制約", "출처 제한"],
  reference: ["引用／參考識別", "Citation / reference identity", "引用・参照識別子", "인용 / 참조 식별자"],
  official: ["查看來源", "Open source", "出典を見る", "출처 보기"],
  result: ["證據結果原文", "Original evidence result", "元の証拠結果", "근거 결과 원문"],
  status: ["技術狀態", "Technical state", "技術状態", "기술 상태"],
  terrain: ["地形／坡度參考", "Terrain / slope reference", "地形・傾斜の参考", "지형 / 경사 참고"],
  mapTitle: ["風險／環境地圖", "Supporting risk / environment map", "リスク・環境の参考地図", "위험 / 환경 참고 지도"],
  mapRegion: ["風險與環境圖", "Risk and environment map", "リスクと環境の地図", "위험 및 환경 지도"],
  mapNote: ["位置與 500 公尺查詢範圍僅供脈絡；不等於地籍或工程界線。僅顯示本次查詢實際提供的幾何。", "Location and the 500 m query radius provide context, not cadastral or engineering boundaries. Only geometry returned by the current query is shown.", "位置と半径500mの照会範囲は参考であり、地籍や工事の境界ではありません。今回の照会で提供された形状のみ表示します。", "위치와 500m 조회 반경은 참고 정보이며 지적 또는 공학적 경계가 아닙니다. 이번 조회에서 제공한 도형만 표시합니다."],
  mapAttribution: ["OpenStreetMap；其他圖層依各證據來源", "OpenStreetMap; other layers attributed to their evidence sources", "OpenStreetMap、その他のレイヤーは各出典による", "OpenStreetMap, 기타 레이어는 각 근거 출처에 따름"],
  mapLoading: ["載入地圖中", "Loading map", "地図を読み込み中", "지도 로딩 중"],
  location: ["目前物件位置", "Current property location", "現在の物件位置", "현재 매물 위치"],
  methods: ["來源與方法詳情", "Source and method details", "出典と方法の詳細", "출처 및 방법 상세"],
  sourceOriginal: ["來源與查詢資訊原文（僅保留實際提供內容）", "Original source and query records (only supplied content)", "元の出典・照会情報（実際に提供された内容のみ）", "출처 및 조회 정보 원문 (제공된 내용만)"],
  satellite: ["衛星影像參考（輔助證據）", "Satellite reference (supporting evidence)", "衛星画像の参考（補助証拠）", "위성 영상 참고 (보조 근거)"],
  buildingTitle: ["建物狀況：獨立查證提醒", "Building condition: separate advisory", "建物の状態：別途確認の助言", "건물 상태: 별도 확인 안내"],
  buildingNote: ["請取得賣方書面揭露、確認漏水歷史，並視需要安排適當的建物檢查。這不是本頁災害證據結果，不計入查證項目數。", "Request written seller disclosure, check leakage history and arrange an appropriate building inspection when needed. This is advice, not a hazard evidence result, and is excluded from the count.", "売主の書面告知、漏水履歴を確認し、必要に応じて適切な建物検査を依頼してください。これは災害の証拠結果ではなく、項目数には含めません。", "매도인의 서면 고지와 누수 이력을 확인하고 필요시 적절한 건물 점검을 의뢰하세요. 이는 재해 근거 결과가 아닌 조언이며 항목 수에 포함되지 않습니다."],
} as const satisfies Record<string, Four>;

export function riskBuyerCopy(locale: ExperienceLocale): { [K in keyof typeof labels]: string } {
  return Object.fromEntries(Object.entries(labels).map(([key, values]) => [key, values[index(locale)]])) as { [K in keyof typeof labels]: string };
}

// These explanations are application guidance, never attributed as official quotations.
const states: Record<BuyerState, { meaning: Four; limits: Four; next: Four }> = {
  MATCHED: {
    meaning: ["本次資料比對到需要查證的訊號。", "The queried data matched a signal that needs verification.", "照会データに確認が必要な情報が該当しました。", "조회 자료에서 확인이 필요한 신호가 일치했습니다."],
    limits: ["不能證明實際受損、整筆土地狀況、結構失效或必然發生的未來損失。", "This does not establish actual damage, parcel-wide conditions, structural failure or inevitable future loss.", "実際の被害、土地全体の状態、構造の破損、将来の必然的な損失は証明できません。", "실제 피해, 필지 전체 상태, 구조적 결함 또는 불가피한 미래 손실을 입증하지 않습니다."],
    next: ["優先完成以下災害專屬查證。", "Prioritize the hazard-specific checks below.", "以下の災害別の確認を優先してください。", "아래 재해별 확인을 우선 진행하세요."],
  },
  "NO MATCH": {
    meaning: ["本次資料與查詢範圍內未找到符合紀錄。", "No matching record was found in the queried data and area.", "今回のデータと照会範囲では該当する記録が見つかりませんでした。", "이번 자료와 조회 범위에서 일치하는 기록을 찾지 못했습니다."],
    limits: ["不能證明安全、沒有歷史事件或資料完整涵蓋。", "This does not prove safety, absence of past incidents or complete coverage.", "安全、過去の被害がないこと、資料の完全な網羅性は証明できません。", "안전, 과거 사고의 부재 또는 완전한 자료 제공 범위를 입증하지 않습니다."],
    next: ["仍需完成以下例行買方查證。", "Keep the routine buyer checks below.", "以下の通常の購入前確認は引き続き必要です。", "아래의 기본 매수자 확인을 계속 진행하세요."],
  },
  "NO COVERAGE": {
    meaning: ["此來源未涵蓋該位置或條件。", "This source does not cover this location or condition.", "この出典は対象の位置または条件を網羅していません。", "이 출처는 해당 위치 또는 조건을 포함하지 않습니다."],
    limits: ["未涵蓋不是未命中，也不能證明危害不存在。", "Missing coverage is not a negative result and does not establish absence of the hazard.", "対象範囲外は該当なしではなく、災害要因がないことも証明しません。", "범위 미포함은 일치 없음이 아니며 재해 부재를 입증하지 않습니다."],
    next: ["改以官方系統與物件專屬資料人工查證；重複相同查詢不會補足涵蓋。", "Verify manually through official systems and property-specific records; repeating the same query does not add coverage.", "公式システムと物件固有の資料で手動確認してください。同じ照会を繰り返しても対象範囲は広がりません。", "공식 시스템과 매물별 기록으로 수동 확인하세요. 같은 조회를 반복해도 범위가 늘어나지 않습니다."],
  },
  UNKNOWN: {
    meaning: ["現有證據不足以判定。", "Available evidence is insufficient to determine the finding.", "現在の証拠では判断できません。", "현재 근거만으로 판단할 수 없습니다."],
    limits: ["不能視為低風險或沒有風險；仍缺少可判讀的涵蓋、結果或物件專屬證據。", "This does not mean low or no risk. Interpretable coverage, results or property-specific evidence are still missing.", "低リスクやリスクなしではありません。判断可能な対象範囲、結果、または物件固有の証拠が不足しています。", "위험이 낮거나 없다는 뜻이 아닙니다. 해석 가능한 범위, 결과 또는 매물별 근거가 부족합니다."],
    next: ["查看來源限制以確認缺少的證據，再依以下官方與現場管道補查。", "Check source limitations for the missing evidence, then use the official and on-site checks below.", "出典の制約から不足する証拠を確認し、以下の公式・現地確認で補ってください。", "출처 제한에서 부족한 근거를 확인한 뒤 아래 공식 및 현장 확인으로 보완하세요."],
  },
  UNAVAILABLE: {
    meaning: ["此次未能取得證據。", "Evidence could not be retrieved on this attempt.", "今回は証拠を取得できませんでした。", "이번 시도에서 근거를 가져오지 못했습니다."],
    limits: ["不能視為未命中或未涵蓋，也不能作為安全證明。", "This is neither no match nor no coverage and cannot establish safety.", "該当なしや対象範囲外とは異なり、安全の証明にはなりません。", "일치 없음이나 범위 미포함이 아니며 안전의 증거가 아닙니다."],
    next: ["持續人工官方／物件查證；如屬暫時取得失敗，可稍後重新查詢。", "Continue manual official and property checks. If retrieval failed temporarily, query again later.", "公式・物件資料の手動確認を続けてください。一時的な取得失敗なら後で再照会できます。", "공식 및 매물 자료를 수동 확인하세요. 일시적인 조회 실패라면 나중에 다시 조회할 수 있습니다."],
  },
  UNSUPPORTED: {
    meaning: ["產品目前無法自動完成這項判讀。", "The product cannot currently complete this assessment automatically.", "現在この判読を製品が自動で完了することはできません。", "현재 제품은 이 판독을 자동으로 완료할 수 없습니다."],
    limits: ["自動支援限制不代表此危害不存在。", "The automation limitation does not mean the hazard is absent.", "自動対応の制限は、災害要因がないことを意味しません。", "자동 지원 제한이 재해 부재를 의미하지 않습니다."],
    next: ["透過官方圖資人工確認；需要時請合適專業人員判讀。", "Verify official maps manually and seek qualified interpretation when needed.", "公式地図で手動確認し、必要に応じて適切な専門家に解釈を依頼してください。", "공식 지도를 수동 확인하고 필요시 적격 전문가에게 해석을 의뢰하세요."],
  },
  LIMITED: {
    meaning: ["僅有部分或受限證據，無法完成完整判讀。", "Only partial or limited evidence is available for assessment.", "部分的または制限のある証拠しかなく、完全な判断はできません。", "일부 또는 제한된 근거만 있어 완전한 판독이 불가능합니다."],
    limits: ["不能把部分資料或訊號當成完整涵蓋、實際損害或安全結論。", "Partial evidence or signals do not establish complete coverage, actual damage or safety.", "部分的な資料や情報は、完全な網羅、実際の被害、安全の結論を証明しません。", "일부 자료나 신호로 완전한 범위, 실제 피해 또는 안전을 입증할 수 없습니다."],
    next: ["先確認來源限制與缺少的範圍，再補足官方／物件查證。", "Review limitations and missing scope, then obtain official and property-specific checks.", "出典の制約と不足範囲を確認し、公式・物件資料で補ってください。", "출처 제한과 누락 범위를 검토하고 공식 및 매물별 확인으로 보완하세요."],
  },
  STALE: {
    meaning: ["證據屬於先前物件狀態，已不適用於目前判讀。", "Evidence belongs to a previous property state and is stale for the current assessment.", "証拠は以前の物件状態に対応しており、現在の判断には使えません。", "근거가 이전 매물 상태에 해당하여 현재 판단에 사용할 수 없습니다."],
    limits: ["不能將舊摘要視為目前位置或條件的證據。", "An old summary does not establish findings for the current location or conditions.", "古い要約は現在の位置や条件の証拠にはなりません。", "오래된 요약은 현재 위치나 조건의 근거가 아닙니다."],
    next: ["重新確認物件身分後查詢，並保留以下人工查證。", "Confirm property identity before querying again; keep the manual checks below.", "物件情報を再確認して照会し、以下の手動確認も続けてください。", "매물 정보를 다시 확인한 뒤 조회하고 아래 수동 확인도 유지하세요."],
  },
  "NOT QUERIED": {
    meaning: ["目前沒有此主題的查詢證據。", "There is no query evidence for this topic here.", "この項目の照会証拠はまだありません。", "이 항목의 조회 근거가 아직 없습니다."],
    limits: ["未查詢或摘要未保存此項，不代表危害不存在。", "An unqueried topic or missing saved item does not establish absence of the hazard.", "未照会や要約に未保存であることは、災害要因がないことを意味しません。", "조회 전이거나 요약에 없는 항목이 재해 부재를 입증하지 않습니다."],
    next: ["確認物件後查詢官方證據，並完成以下人工查證。", "Confirm the property, query evidence and complete the manual checks below.", "物件を確認して公式証拠を照会し、以下の手動確認を行ってください。", "매물을 확인한 뒤 공식 근거를 조회하고 아래 수동 확인을 완료하세요."],
  },
};

export function buyerStateCopy(state: BuyerState, locale: ExperienceLocale) {
  const copy = states[state]; const i = index(locale);
  return { meaning: copy.meaning[i], limits: copy.limits[i], next: copy.next[i] };
}

const hazards: Record<BuyerHazard, { name: Four; actions: readonly Four[] }> = {
  flood: { name: ["淹水潛勢", "Flooding", "浸水", "침수"], actions: [
    ["確認地下室／停車場淹水歷史。", "Check basement and parking flooding history.", "地下室・駐車場の浸水履歴を確認。", "지하실 및 주차장 침수 이력을 확인하세요."],
    ["索取管委會相關紀錄。", "Request management committee records.", "管理組合の関連記録を請求。", "관리위원회 관련 기록을 요청하세요."],
    ["取得賣方書面揭露。", "Obtain written seller disclosure.", "売主の書面告知を取得。", "매도인의 서면 고지를 받으세요."],
  ] },
  liquefaction: { name: ["土壤液化潛勢", "Soil liquefaction", "液状化", "토양 액상화"], actions: [
    ["透過官方系統確認位置。", "Confirm the location in the official system.", "公式システムで位置を確認。", "공식 시스템에서 위치를 확인하세요."],
    ["詢問是否有地質鑽探／地工調查報告。", "Ask whether a geotechnical investigation exists.", "地盤調査報告の有無を確認。", "지반 조사 보고서가 있는지 문의하세요."],
  ] },
  landslide: { name: ["崩塌與邊坡", "Landslides and slopes", "崩壊と斜面", "산사태 및 사면"], actions: [
    ["現場檢視鄰近邊坡。", "Inspect nearby slopes on site.", "周辺の斜面を現地確認。", "인근 사면을 현장에서 확인하세요."],
    ["檢視擋土牆狀況。", "Inspect retaining walls.", "擁壁の状態を確認。", "옹벽 상태를 확인하세요."],
    ["索取維護紀錄。", "Request maintenance records.", "維持管理記録を請求。", "유지보수 기록을 요청하세요."],
  ] },
  debris_flow: { name: ["土石流", "Debris flow", "土石流", "토석류"], actions: [
    ["確認官方公告圖資範圍。", "Verify the official mapped scope.", "公式地図の対象範囲を確認。", "공식 지도 범위를 확인하세요."],
    ["確認該範圍與物件的關係。", "Confirm how the mapped scope relates to the property.", "範囲と物件の関係を確認。", "해당 범위와 매물의 관계를 확인하세요."],
    ["需要時請合適專業人員判讀。", "Seek qualified interpretation when required.", "必要に応じて適切な専門家に解釈を依頼。", "필요시 적격 전문가에게 해석을 의뢰하세요."],
  ] },
  geological_sensitivity: { name: ["地質敏感區", "Geological sensitivity", "地質敏感区域", "지질 민감 구역"], actions: [
    ["確認官方公告類別與版本；公告類別並非嚴重度分級。", "Confirm the announced category and version; categories are not severity ratings.", "公表区分と版を確認。区分は深刻度の評価ではありません。", "공고 범주와 버전을 확인하세요. 범주는 심각도 등급이 아닙니다."],
    ["確認公告範圍與物件的關係。", "Confirm the announced scope's relationship to the property.", "公表範囲と物件の関係を確認。", "공고 범위와 매물의 관계를 확인하세요."],
  ] },
  active_fault: { name: ["活動斷層", "Active faults", "活断層", "활성 단층"], actions: [
    ["本產品自動判讀支援有限；請透過官方圖資人工確認位置與斷層關係。", "Automated interpretation is limited; manually verify the property's relationship to faults using official maps.", "自動判読の対応には制限があります。公式地図で物件と断層の関係を手動確認してください。", "자동 판독 지원이 제한됩니다. 공식 지도로 매물과 단층의 관계를 수동 확인하세요."],
  ] },
};

export function hazardBuyerCopy(key: BuyerHazard, locale: ExperienceLocale) {
  const copy = hazards[key]; const i = index(locale);
  return { name: copy.name[i], actions: copy.actions.map((action) => action[i]) };
}

export function riskBuyerSummary(count: number | null, locale: ExperienceLocale) {
  const c = riskBuyerCopy(locale);
  return count === null ? c.preQuery : c.count.replace("{count}", new Intl.NumberFormat(locale).format(count));
}
