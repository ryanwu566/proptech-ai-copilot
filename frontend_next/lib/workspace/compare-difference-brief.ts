import type { CaseEvidenceModel, EvidenceField } from "./case-evidence";
// @ts-expect-error Native TS runner extension.
import { buildEvidenceChecklist } from "./evidence-checklist.ts";
// @ts-expect-error Native TS runner extension.
import { classifyCells } from "./compare-diff.ts";

type Field = EvidenceField<string | number>;
export type BriefCategoryId = "price" | "location" | "risk" | "money" | "verification";
export type BriefStatement = {
  caseId: string; text: string; fieldIds: string[]; gapIds: string[];
  actionIds: string[]; counts?: Record<string, number>;
};
export type BriefCategory = {
  id: BriefCategoryId; title: string; statements: BriefStatement[]; difference: string; caution?: string;
};
export type DifferenceBrief = {
  cases: Array<{ caseId: string; title: string; savedAt: string }>;
  categories: BriefCategory[];
};
export type BriefLocale = "zh-TW" | "en" | "ja" | "ko";

/** No clock, storage, providers, calculators or model calls. All claims retain their saved input IDs. */
export function buildDifferenceBrief(cases: CaseEvidenceModel[], locale: BriefLocale = "zh-TW"): DifferenceBrief {
  const language = ["zh-TW", "en", "ja", "ko"].indexOf(locale);
  const t = (zh: string, en: string, ja: string, ko: string) => [zh, en, ja, ko][language] ?? en;
  const numberFormat = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });
  const n = (value: number) => numberFormat.format(value);
  const sep = t("；", "; ", "；", "; ");
  const model: DifferenceBrief = { cases: cases.map(({ caseId, title, savedAt }) => ({ caseId, title, savedAt })), categories: [] };
  if (cases.length < 2 || cases.length > 4 || cases.some((item) => item.identity.state !== "confirmed") || new Set(cases.map((item) => item.caseId)).size !== cases.length) return model;
  const stale = (f: Field) => f.status === "stale" || f.freshness.inputRelation === "stale" || f.freshness.timeRelation === "stale";
  const usable = (f: Field) => !stale(f) && ["available", "limited", "no_match"].includes(f.status) && f.value !== null && (typeof f.value !== "number" || Number.isFinite(f.value) && f.value >= 0);
  const num = (f: Field): number | null => usable(f) && typeof f.value === "number" ? f.value : null;
  const state = (f: Field) => stale(f) ? t("已過期", "stale", "期限切れ", "오래됨") : f.status === "not_run" ? t("尚未查詢／計算", "not queried / calculated", "未照会・未計算", "조회·계산 전") : f.status === "unavailable" ? t("目前無法取得", "unavailable", "取得不可", "이용 불가") : f.status === "unsupported" ? t("不支援，需人工查證", "unsupported; verify manually", "非対応・要手動確認", "미지원·수동 확인 필요") : f.status === "no_coverage" ? t("無資料覆蓋", "no coverage", "対象データなし", "자료 범위 밖") : t("未知／未保存", "unknown / not preserved", "不明・未保存", "미확인·미저장");
  const value = (f: Field) => usable(f) ? `${typeof f.value === "number" ? n(f.value) : f.value}${f.unit ? ` ${f.unit}` : ""}` : state(f);
  const statement = (item: CaseEvidenceModel, text: string, fields: Field[], extra: Partial<BriefStatement> = {}): BriefStatement => ({ caseId: item.caseId, text, fieldIds: [...new Set(fields.map((f) => f.id))], gapIds: [], actionIds: [], ...extra });
  const changed = (fields: Field[][]) => fields[0].some((_, i) => classifyCells(fields.map((row) => row[i])).relation === "differs");
  const spread = (fields: Field[]): number | null => {
    const numbers = fields.map(num);
    return numbers.every((v) => v !== null) && new Set(fields.map((f) => f.unit)).size === 1 ? Math.max(...numbers as number[]) - Math.min(...numbers as number[]) : null;
  };
  const same = t("保存摘要未呈現此類差異；缺漏與未知仍需查證。", "No difference is shown in this saved summary; missing and unknown evidence still needs verification.", "保存要約では差は確認できません。不明点は引き続き要確認です。", "저장 요약에 차이가 나타나지 않습니다. 누락·미확인 근거는 추가 확인이 필요합니다.");

  const priceFields = cases.map((item) => [item.price.asking, item.price.area, item.price.marketMedianUnit, item.price.marketP25, item.price.marketP75, item.price.sampleSize, item.price.scope, item.price.period]);
  const priceStatements = cases.map((item, i) => {
    const p = item.price; const asking = num(p.asking); const area = num(p.area);
    const parts = [`${t("開價", "asking", "提示価格", "호가")} ${value(p.asking)}`];
    if (asking !== null && area !== null && area > 0) parts.push(`${t("換算單價", "derived unit price", "換算単価", "환산 단가")} ${n(asking / area)} ${p.asking.unit}／${p.area.unit}`);
    parts.push(`${t("市場單價中位數", "market unit median", "市場単価中央値", "시장 단가 중앙값")} ${value(p.marketMedianUnit)}`);
    if (num(p.marketP25) !== null && num(p.marketP75) !== null && p.marketP25.unit === p.marketP75.unit && p.marketP25.value! <= p.marketP75.value!) parts.push(`P25–P75 ${n(p.marketP25.value!)}–${n(p.marketP75.value!)} ${p.marketP25.unit}`);
    return statement(item, parts.join(sep), priceFields[i]);
  });
  const priceDelta = spread(cases.map((item) => item.price.asking));
  const unitPrices = cases.map((item) => {
    const asking = num(item.price.asking); const area = num(item.price.area);
    return asking !== null && area !== null && area > 0 ? asking / area : null;
  });
  const unitDelta = unitPrices.every((v) => v !== null) && new Set(cases.map((item) => `${item.price.asking.unit}/${item.price.area.unit}`)).size === 1 ? Math.max(...unitPrices as number[]) - Math.min(...unitPrices as number[]) : null;
  const marketChanged = changed(priceFields.map((fields) => fields.slice(2)));
  const priceContrast = priceDelta !== null && priceDelta > 0 ? t(`開價${cases.length === 2 ? "相差" : "範圍差距"} ${n(priceDelta)} ${cases[0].price.asking.unit}。`, `The saved asking prices span ${n(priceDelta)} ${cases[0].price.asking.unit}.`, `提示価格の差幅は ${n(priceDelta)} ${cases[0].price.asking.unit}です。`, `저장 호가의 차이 폭은 ${n(priceDelta)} ${cases[0].price.asking.unit}입니다.`) : "";
  const unitContrast = !priceContrast && unitDelta !== null && unitDelta > 0 ? t(`換算單價相差 ${n(unitDelta)} ${cases[0].price.asking.unit}／${cases[0].price.area.unit}。`, `Derived unit prices span ${n(unitDelta)} ${cases[0].price.asking.unit}/${cases[0].price.area.unit}.`, `換算単価の差幅は ${n(unitDelta)} ${cases[0].price.asking.unit}／${cases[0].price.area.unit}です。`, `환산 단가의 차이 폭은 ${n(unitDelta)} ${cases[0].price.asking.unit}/${cases[0].price.area.unit}입니다.`) : "";
  model.categories.push({ id: "price", title: t("價格與市場", "Price / market", "価格・市場", "가격·시장"), statements: priceStatements,
    difference: [priceContrast || unitContrast, marketChanged ? t("市場證據的數值、範圍、期間或保存狀態不同，需按各案來源解讀。", "Market values, scope, period or saved evidence states differ; read each case's sources.", "市場数値・範囲・期間または保存状態が異なります。各案件の出典を確認してください。", "시장 수치·범위·기간 또는 저장 상태가 다릅니다. 각 사례의 출처를 확인하세요.") : ""].filter(Boolean).join(" ") || (changed(priceFields) ? t("保存開價或面積的證據狀態不同，無法將缺值視為相同。", "Saved asking price or area evidence states differ; missing values cannot be treated as equal.", "保存価格または面積の証拠状態が異なり、欠損値を同じとは扱えません。", "저장 호가 또는 면적의 근거 상태가 달라 누락값을 같다고 볼 수 없습니다.") : same),
    caution: t("區域成交分布不代表個案價值；換算單價以保存開價除以保存面積。", "Regional transactions do not establish this property's value. Unit price is saved asking price divided by saved area.", "地域の取引分布は個別物件の価値を示しません。単価は保存価格÷保存面積です。", "지역 거래 분포는 개별 물건의 가치를 나타내지 않습니다. 단가는 저장 호가÷저장 면적입니다。") });

  const locationFields = cases.map((item) => [item.commute.destination, item.commute.mode, item.commute.duration, item.commute.distance, item.location.radius, item.location.coverage]);
  const routeReady = cases.every((item) => [item.commute.destination, item.commute.mode, item.commute.duration].every(usable));
  const sameRoute = routeReady && new Set(cases.map((item) => item.commute.destination.value)).size === 1 && new Set(cases.map((item) => item.commute.mode.value)).size === 1;
  const durationDelta = sameRoute ? spread(cases.map((item) => item.commute.duration)) : null;
  model.categories.push({ id: "location", title: t("區位與通勤", "Location / commute", "立地・通勤", "입지·통근"), statements: cases.map((item, i) => {
    const route = [item.commute.destination, item.commute.mode, item.commute.duration].every(usable);
    const savedNearby = item.comparisonContext?.nearby;
    const nearby = savedNearby ? `${t("已保存", "saved", "保存済み", "저장됨")} · Google Places · ${savedNearby.radiusM} m${savedNearby.partial ? ` · ${t("部分來源", "partial sources", "一部の出典のみ", "일부 출처")}` : ""}` : usable(item.location.radius) ? t("已保存摘要", "saved summary", "要約保存済み", "요약 저장됨") : state(item.location.radius);
    const context = item.comparisonContext;
    const parts = [t("定位關聯已確認", "location association confirmed", "位置の関連確認済み", "위치 연결 확인됨")];
    if (context) parts.push(context.administration || t("行政資訊未完整保存", "administrative information incomplete", "行政情報の保存が不完全", "행정 정보 일부 미저장"));
    parts.push(`${t("周邊證據", "nearby evidence", "周辺エビデンス", "주변 근거")} ${nearby}`);
    parts.push(route ? `${value(item.commute.destination)} · ${value(item.commute.mode)} ${value(item.commute.duration)}${usable(item.commute.distance) ? ` / ${value(item.commute.distance)}` : ""}` : `${t("通勤", "commute", "通勤", "통근")} ${state(item.commute.duration)}`);
    return statement(item, parts.join(sep), locationFields[i]);
  }), difference: !routeReady ? t("至少一案缺少可採用的保存路線，無法比較通勤時間。", "At least one case lacks a usable saved route, so commute times cannot be compared.", "少なくとも一件に有効な保存ルートがなく、通勤時間を比較できません。", "적어도 한 사례에 유효한 저장 경로가 없어 통근 시간을 비교할 수 없습니다.") : !sameRoute ? t("目的地或交通方式不同，保存的通勤時間不宜直接對比。", "Destinations or travel modes differ; saved commute times are not directly comparable.", "目的地または交通手段が異なるため、通勤時間は直接比較できません。", "목적지 또는 교통수단이 달라 저장 통근 시간을 직접 비교할 수 없습니다.") : durationDelta !== null && durationDelta > 0 ? t(`相同目的地與交通方式下，保存時間相差 ${n(durationDelta)} 分鐘。`, `For the same destination and mode, saved times span ${n(durationDelta)} minutes.`, `同じ目的地・交通手段で保存時間の差幅は ${n(durationDelta)} 分です。`, `같은 목적지·교통수단에서 저장 시간의 차이 폭은 ${n(durationDelta)}분입니다.`) : changed(locationFields) || new Set(cases.map((item) => JSON.stringify(item.comparisonContext))).size > 1 ? t("通勤時間未呈現差異，但路線距離或周邊證據不同。", "Saved times show no difference, but route conditions, administrative information or nearby evidence differs.", "保存時間に差はありませんが、距離または周辺情報が異なります。", "저장 시간에는 차이가 없으나 거리 또는 주변 근거가 다릅니다.") : same,
    caution: t("僅為瀏覽器案件定位關聯；出發時間與交通時段未保存，路線估算不代表目前路況。", "Browser case location association only. Departure time and traffic period were not saved; estimates do not describe current traffic.", "ブラウザー内の位置関連のみ。出発時刻・交通時間帯は未保存で、推定は現在の交通状況を示しません。", "브라우저 위치 연결만 확인합니다. 출발 시간·교통 시간대는 미저장이며 추정값은 현재 교통 상황을 나타내지 않습니다.") });

  const riskKeys = ["matched", "unknown", "unavailable", "notQueried", "noMatch", "unsupported", "stale"] as const;
  const riskLabels = [t("命中", "matched", "該当", "해당"), t("未知", "unknown", "不明", "미확인"), t("無法取得", "unavailable", "取得不可", "이용 불가"), t("未查詢", "not queried", "未照会", "미조회"), t("未命中", "no match", "非該当", "미해당"), t("不支援／無覆蓋", "unsupported / no coverage", "非対応・対象外", "미지원·범위 밖"), t("過期", "stale", "期限切れ", "오래됨")];
  const riskStatements = cases.map((item) => {
    const counts: Record<string, number> = Object.fromEntries(riskKeys.map((key) => [key, 0]));
    for (const row of item.risk) {
      const f = row.evidence;
      const key = stale(f) ? "stale" : f.status === "not_run" ? "notQueried" : f.status === "unavailable" ? "unavailable" : ["unsupported", "no_coverage"].includes(f.status) ? "unsupported" : !usable(f) ? "unknown" : row.matched === true ? "matched" : f.status === "no_match" ? "noMatch" : "unknown";
      counts[key]++;
    }
    return statement(item, riskKeys.flatMap((key, i) => counts[key] > 0 || key === "matched" ? [`${riskLabels[i]} ${counts[key]}`] : []).join(sep), item.risk.map((row) => row.evidence), { counts });
  });
  model.categories.push({ id: "risk", title: t("風險與環境", "Risk / environment", "リスク・環境", "위험·환경"), statements: riskStatements,
    difference: new Set(riskStatements.map((s) => JSON.stringify(s.counts))).size > 1 ? t("命中、未知與查詢狀態的分布不同；各項來源仍需分別查證。", "The counts of matched, unknown and query states differ; verify each source separately.", "該当・不明・照会状態の件数分布が異なります。出典ごとに要確認です。", "해당·미확인·조회 상태별 건수가 다릅니다. 출처별 확인이 필요합니다.") : t("各狀態項數相同，並不表示各案命中內容或實際風險相同。", "State counts are equal; findings and actual risks may still differ.", "状態別件数は同じでも、結果や実際のリスクが同じとは限りません。", "상태별 건수가 같아도 결과나 실제 위험이 같다는 뜻은 아닙니다."),
    caution: t("未知不等於安全；未命中不代表零風險。", "Unknown does not mean safe; no match does not mean zero risk.", "不明は安全を意味しません。非該当はリスクゼロを意味しません。", "미확인은 안전을 뜻하지 않으며 미해당은 위험이 없다는 뜻이 아닙니다.") });

  const moneyFields = cases.map((item) => [item.finance.downPayment, item.finance.principal, item.finance.monthlyPayment, item.finance.knownMonthlyHousing, item.finance.price, item.finance.basis, item.finance.interestRate, item.finance.term, item.finance.downPaymentRatio, item.finance.missingCosts]);
  const paymentDelta = spread(cases.map((item) => item.finance.monthlyPayment));
  const assumptionsChanged = changed(moneyFields.map((fields) => fields.slice(4, 9)));
  const housingDelta = spread(cases.map((item) => item.finance.knownMonthlyHousing));
  const downDelta = spread(cases.map((item) => item.finance.downPayment));
  const loanDelta = spread(cases.map((item) => item.finance.principal));
  const costContrast = housingDelta !== null && housingDelta > 0 ? t(`保存已知住宅支出相差 ${n(housingDelta)} 元／月（含房貸）。`, `Saved known housing costs span ${n(housingDelta)} TWD/month (including mortgage).`, `既知住宅費の差幅は ${n(housingDelta)} 元／月（返済含む）です。`, `저장된 주거비의 차이 폭은 ${n(housingDelta)} TWD/월(상환 포함)입니다.`) : downDelta !== null && downDelta > 0 ? t(`保存自備款相差 ${n(downDelta)} ${cases[0].finance.downPayment.unit}。`, `Saved down payments span ${n(downDelta)} ${cases[0].finance.downPayment.unit}.`, `保存頭金の差幅は ${n(downDelta)} ${cases[0].finance.downPayment.unit}です。`, `저장 계약자금의 차이 폭은 ${n(downDelta)} ${cases[0].finance.downPayment.unit}입니다.`) : loanDelta !== null && loanDelta > 0 ? t(`保存貸款本金相差 ${n(loanDelta)} ${cases[0].finance.principal.unit}。`, `Saved loan principals span ${n(loanDelta)} ${cases[0].finance.principal.unit}.`, `保存借入元本の差幅は ${n(loanDelta)} ${cases[0].finance.principal.unit}です。`, `저장 대출 원금의 차이 폭은 ${n(loanDelta)} ${cases[0].finance.principal.unit}입니다.`) : changed(moneyFields) ? t("保存金額、成本缺漏或證據狀態不同，需連同保存條件核對。", "Saved amounts, missing costs or evidence states differ; review them with their saved conditions.", "保存金額・未算入費用または証拠状態が異なります。保存条件と併せて要確認です。", "저장 금액·누락 비용 또는 근거 상태가 다릅니다. 저장 조건과 함께 확인하세요.") : "";
  model.categories.push({ id: "money", title: t("資金與成本", "Money", "資金・費用", "자금·비용"), statements: cases.map((item, i) => statement(item, [
    `${t("自備款", "down payment", "頭金", "계약자금")} ${value(item.finance.downPayment)}`,
    `${t("貸款", "loan", "借入額", "대출액")} ${value(item.finance.principal)}`,
    `${t("房貸月付", "monthly mortgage", "月額返済", "월 상환액")} ${value(item.finance.monthlyPayment)}`,
    `${t("已知住宅支出（含房貸）", "known housing costs (including mortgage)", "既知住宅費（返済含む）", "알려진 주거비(상환 포함)")} ${value(item.finance.knownMonthlyHousing)}`,
  ].join(sep), moneyFields[i])), difference: paymentDelta === null ? t("至少一案缺少可採用的保存月付，無法直接比較；請先核對缺漏假設。", "At least one case lacks a usable saved payment; direct comparison requires the missing assumptions.", "少なくとも一件に有効な保存返済額がなく、比較には不足する前提の確認が必要です。", "적어도 한 사례에 유효한 저장 상환액이 없어 누락된 가정을 먼저 확인해야 합니다.") : [paymentDelta > 0 ? t(`保存房貸月付相差 ${n(paymentDelta)} 元／月。`, `Saved mortgage payments span ${n(paymentDelta)} TWD/month.`, `保存月額返済の差幅は ${n(paymentDelta)} 元／月です。`, `저장 월 상환액의 차이 폭은 ${n(paymentDelta)} TWD/월입니다.`) : "", assumptionsChanged ? t("採用價格或貸款假設不同，差額需連同假設解讀。", "Prices or loan assumptions differ; interpret the amounts with those assumptions.", "採用価格または借入前提が異なるため、金額は前提と併せて確認してください。", "적용 가격 또는 대출 가정이 다르므로 금액을 가정과 함께 해석하세요.") : ""].filter(Boolean).join(" ") || costContrast || same,
    caution: t("自備款不是完整所需現金；已知支出可能未含全部成本。缺漏假設見保存證據。", "Down payment is not total cash needed; known costs may omit expenses. See saved evidence for missing assumptions.", "頭金は必要現金の総額ではありません。既知費用に未算入費用があり得ます。不足前提は保存情報を確認。", "계약자금은 필요 현금 총액이 아닙니다. 알려진 비용에 미포함 지출이 있을 수 있습니다. 누락 가정은 저장 근거를 확인하세요.") });

  const verificationStatements = cases.map((item) => {
    const gaps = [...new Set(item.gaps.filter((gap) => gap.caseId === item.caseId).map((gap) => gap.id))];
    const actions = buildEvidenceChecklist(item).filter((action) => action.reviewState !== "reviewed");
    const savedActions = item.savedFinanceActions ?? [];
    return statement(item, t(`${gaps.length} 項證據缺口；${actions.length} 項待核對行動${savedActions.length ? `；另有 ${savedActions.length} 項保存的資金待辦` : ""}。`, `${gaps.length} evidence gaps; ${actions.length} open verification actions${savedActions.length ? `; ${savedActions.length} saved Money tasks listed separately` : ""}.`, `証拠の欠落 ${gaps.length} 件・未確認アクション ${actions.length} 件${savedActions.length ? `・保存された資金タスク ${savedActions.length} 件（別掲）` : ""}。`, `근거 공백 ${gaps.length}개·미확인 작업 ${actions.length}개${savedActions.length ? `·저장된 자금 작업 ${savedActions.length}개(별도)` : ""}.`), [], { gapIds: gaps, actionIds: actions.map((a) => a.id), counts: { gaps: gaps.length, actions: actions.length, savedTasks: savedActions.length } });
  });
  const gapCounts = verificationStatements.map((s) => s.counts!.gaps);
  const delta = Math.max(...gapCounts) - Math.min(...gapCounts);
  model.categories.push({ id: "verification", title: t("查證與待辦", "Verification / open items", "確認・未解決項目", "검증·미해결 항목"), statements: verificationStatements,
    difference: delta > 0 ? t(`列出的證據缺口相差 ${delta} 項；項數反映保存缺漏，不代表購買就緒程度。`, `Listed evidence gaps span ${delta} items; counts describe saved omissions, not readiness to buy.`, `証拠の欠落件数の差幅は ${delta} 件です。件数は購入準備の度合いを示しません。`, `근거 공백 건수의 차이 폭은 ${delta}개입니다. 건수는 구매 준비도를 나타내지 않습니다.`) : new Set(verificationStatements.map((s) => s.counts!.actions)).size > 1 ? t("證據缺口項數相同，但尚待人工核對的行動項數不同。", "Evidence gap counts match, but open manual verification action counts differ.", "欠落件数は同じですが、未確認アクションの件数が異なります。", "근거 공백 건수는 같으나 미확인 수동 작업 건수가 다릅니다.") : t("列出的缺口與行動項數相同；內容仍須逐項核對。", "Listed gap and action counts match; their contents still need individual verification.", "欠落・アクション件数は同じですが、内容は個別に要確認です。", "공백·작업 건수는 같으나 내용별 확인이 필요합니다.") });
  return model;
}
