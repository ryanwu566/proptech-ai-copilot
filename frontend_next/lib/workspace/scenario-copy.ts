import "server-only";
import type { CopyCatalogue } from "../copy-catalogue";

const en = {
  title: "Property Scenario Lab", nav: "Scenario Lab", intro: "Change your offer and assumptions. Compare three scenarios immediately; saved property evidence stays frozen.",
  assumptions: "Your assumptions", scenario: "Scenario", offerTwd: "Offer price (TWD)", downValue: "Down payment", downMode: "Down payment input", amount: "Amount (TWD)", ratio: "Ratio (%)",
  ratePercent: "Annual interest rate (%)", loanYears: "Loan term (years)", acquisitionTwd: "Acquisition costs (TWD)", recurringTwd: "Recurring holding costs (TWD/month)", renovationTwd: "Renovation allowance (TWD)", holdingYears: "Holding period (years)", commuteMinutes: "Manual one-way commute (minutes)",
  inputNote: "Blank means unknown. Enter 0 only when you assume no cost. Acquisition costs include only the taxes and fees you enter; recurring costs exclude the mortgage.",
  unknown: "Unknown", unknownItems: "Unknown items", none: "No missing inputs", subtotal: "Known subtotal", complete: "Entered costs included", comparison: "Compare A / B / C", scroll: "Scroll horizontally to compare all three scenarios.",
  purchaseCashTwd: "Cash required at purchase", principalTwd: "Mortgage principal", paymentTwd: "Monthly mortgage payment", monthlyOwnershipTwd: "Monthly recurring ownership cost", firstYearTwd: "First-year cash burden", acquisitionTotalTwd: "Total acquisition cost", holdingCashTwd: "Cash over holding period",
  asking: "Asking price (read-only)", saved: "Saved finance price (read-only)", askingDelta: "Offer delta vs asking", savedDelta: "Offer delta vs saved finance", baselineDelta: "Offer delta vs frozen baseline", paymentDelta: "Mortgage delta vs baseline", cashDelta: "Purchase cash delta vs baseline", ownershipDelta: "Monthly ownership delta vs baseline", yearDelta: "First-year cash delta vs baseline",
  freeze: "Freeze as baseline", baseline: "Frozen scenario baseline", clear: "Clear baseline", noBaseline: "Freeze a scenario to compare changes against a fixed baseline.", save: "Save drafts and baseline", savedStatus: "Scenario drafts saved separately in this browser.", failed: "Browser storage unavailable. Current drafts remain on screen.", damaged: "Saved scenarios could not be restored. Fresh drafts are shown.",
  method: "Calculation method", methodNote: "Fixed-rate principal-and-interest amortization using the existing mortgage equation; no grace period. Purchase cash = down payment + entered acquisition costs + renovation. Total acquisition = offer + acquisition costs + renovation. First-year cash adds 12 months of mortgage and holding costs. Holding-period cash caps mortgage payments at loan maturity. Totals are cash outflows; no resale, appreciation, return forecast or sale costs. Amounts round only for display.",
  boundary: "Your offer is an assumption, not a prediction of an accepted offer. No provider requests run here. Unknown taxes and fees are not estimated. Production valuation and saved evidence are unchanged.", commute: "Commute reference", accepted: "Accepted saved route", noCommute: "No accepted commute evidence. You may enter a manual duration for each scenario.", manual: "Manual assumption", minutes: "minutes one way", checked: "Checked", source: "Source", commuteNote: "Commute is a time comparison only; it is not included in ownership costs.", range: "Enter a non-negative value within the allowed range; down payment cannot exceed the offer (or 100%).", positive: "Enter a value greater than zero.", integer: "Enter a whole number of years (1–100).", readonly: "Frozen saved evidence", stale: "Saved finance assumptions are stale or unsupported; no loan defaults were reused.",
};
export type ScenarioCopyKey = keyof typeof en;
export const scenarioCopy: CopyCatalogue<ScenarioCopyKey> = {
  en,
  "zh-TW": {
    title: "物件情境實驗室", nav: "情境實驗室", intro: "調整出價與假設，立即比較三種情境；已保存的物件證據維持凍結。",
    assumptions: "您的假設", scenario: "情境", offerTwd: "出價（新臺幣）", downValue: "自備款", downMode: "自備款輸入方式", amount: "金額（新臺幣）", ratio: "比例（%）",
    ratePercent: "年利率（%）", loanYears: "貸款年期（年）", acquisitionTwd: "取得費用（新臺幣）", recurringTwd: "經常持有費用（新臺幣／月）", renovationTwd: "裝修預算（新臺幣）", holdingYears: "持有期間（年）", commuteMinutes: "手動單程通勤（分鐘）",
    inputNote: "留白代表未知；只有假設無費用時才填 0。取得費用只包含您輸入的稅費；經常持有費用不含房貸。",
    unknown: "未知", unknownItems: "未知項目", none: "輸入項目齊全", subtotal: "已知金額小計", complete: "已納入填寫的費用", comparison: "比較 A／B／C", scroll: "可水平捲動以比較三種情境。",
    purchaseCashTwd: "購買時所需現金", principalTwd: "房貸本金", paymentTwd: "每月房貸月付", monthlyOwnershipTwd: "每月經常持有支出", firstYearTwd: "首年現金負擔", acquisitionTotalTwd: "總取得成本", holdingCashTwd: "持有期間現金支出",
    asking: "開價（唯讀）", saved: "保存的財務價格（唯讀）", askingDelta: "出價相較開價差額", savedDelta: "出價相較保存財務價格差額", baselineDelta: "出價相較凍結基準差額", paymentDelta: "月付相較基準差額", cashDelta: "購買現金相較基準差額", ownershipDelta: "每月持有支出相較基準差額", yearDelta: "首年現金相較基準差額",
    freeze: "凍結為基準", baseline: "凍結情境基準", clear: "清除基準", noBaseline: "凍結一種情境，即可與固定基準比較變化。", save: "保存草稿與基準", savedStatus: "情境草稿已獨立保存在此瀏覽器。", failed: "瀏覽器儲存無法使用；目前草稿仍保留在畫面。", damaged: "無法還原保存情境，已顯示新草稿。",
    method: "計算方式", methodNote: "沿用既有房貸本息攤還公式，假設固定利率且無寬限期。購買現金＝自備款＋填寫的取得費用＋裝修。總取得成本＝出價＋取得費用＋裝修。首年現金再加 12 個月房貸及持有費用。持有期間房貸支出以貸款到期為上限。總額為現金流出，不含轉售、增值、報酬預測或出售費用；僅在顯示時四捨五入。",
    boundary: "出價是您的假設，不是可接受出價預測。此頁不呼叫資料供應者，不估算未知稅費，不改動正式估價或已保存證據。", commute: "通勤參考", accepted: "已接受的保存路線", noCommute: "沒有已接受的通勤證據，可為各情境輸入手動時間。", manual: "手動假設", minutes: "分鐘／單程", checked: "查詢時間", source: "來源", commuteNote: "通勤只比較時間，不納入持有成本。", range: "請填允許範圍內的非負數；自備款不可超過出價或 100%。", positive: "請填大於零的數值。", integer: "請填整數年期（1–100 年）。", readonly: "已保存證據維持凍結", stale: "保存的財務假設已過期或不支援，未沿用貸款預設值。",
  },
  ja: {
    title: "物件シナリオラボ", nav: "シナリオラボ", intro: "購入希望価格と条件を変更し、3つのシナリオをすぐに比較できます。保存済みの物件エビデンスは固定されます。",
    assumptions: "入力条件", scenario: "シナリオ", offerTwd: "購入希望価格（TWD）", downValue: "頭金", downMode: "頭金の入力方法", amount: "金額（TWD）", ratio: "割合（%）",
    ratePercent: "年利率（%）", loanYears: "借入期間（年）", acquisitionTwd: "取得諸費用（TWD）", recurringTwd: "維持費（TWD／月）", renovationTwd: "改修予算（TWD）", holdingYears: "保有期間（年）", commuteMinutes: "手動入力の片道通勤時間（分）",
    inputNote: "空欄は不明です。費用なしと仮定する場合のみ0を入力してください。取得諸費用は入力した税金・手数料のみ、維持費はローン返済を除きます。",
    unknown: "不明", unknownItems: "不明な項目", none: "入力済み", subtotal: "既知額の小計", complete: "入力した費用を含む", comparison: "A／B／Cを比較", scroll: "横にスクロールして3つのシナリオを比較できます。",
    purchaseCashTwd: "購入時に必要な現金", principalTwd: "借入元金", paymentTwd: "毎月のローン返済額", monthlyOwnershipTwd: "毎月の所有費用", firstYearTwd: "初年度の現金負担", acquisitionTotalTwd: "総取得費用", holdingCashTwd: "保有期間の現金支出",
    asking: "売出価格（参照のみ）", saved: "保存済み資金計算の価格（参照のみ）", askingDelta: "売出価格との差額", savedDelta: "保存済み資金価格との差額", baselineDelta: "固定基準との価格差額", paymentDelta: "基準との月返済差額", cashDelta: "基準との購入現金差額", ownershipDelta: "基準との月所有費用差額", yearDelta: "基準との初年度現金差額",
    freeze: "基準として固定", baseline: "固定シナリオ基準", clear: "基準を解除", noBaseline: "シナリオを固定すると、一定の基準と変更内容を比較できます。", save: "下書きと基準を保存", savedStatus: "シナリオをこのブラウザに別途保存しました。", failed: "ブラウザに保存できません。現在の下書きは画面に残ります。", damaged: "保存済みシナリオを復元できません。新しい下書きを表示します。",
    method: "計算方法", methodNote: "既存の元利均等返済式を使用。固定金利・据置期間なし。購入現金＝頭金＋入力諸費用＋改修。総取得費用＝希望価格＋諸費用＋改修。初年度は12か月分の返済・維持費を加算。保有期間の返済は借入満期まで。合計は現金支出であり、転売・値上がり・収益予測・売却費用は含みません。丸めは表示時のみ。",
    boundary: "希望価格は入力条件であり、売主の承諾価格の予測ではありません。外部データ取得、不明な税金・手数料の推定は行わず、本番評価と保存エビデンスは変更しません。", commute: "通勤参考", accepted: "承認済みの保存ルート", noCommute: "承認済み通勤エビデンスがありません。各シナリオに手動で時間を入力できます。", manual: "手動入力条件", minutes: "分／片道", checked: "確認日時", source: "情報源", commuteNote: "通勤は時間のみの比較です。所有費用には含みません。", range: "許容範囲内の非負数を入力してください。頭金は希望価格または100%以下です。", positive: "0より大きい値を入力してください。", integer: "整数の年数（1～100）を入力してください。", readonly: "保存エビデンスは固定", stale: "保存済み資金条件は古いか非対応のため、借入初期値には使用していません。",
  },
  ko: {
    title: "부동산 시나리오 랩", nav: "시나리오 랩", intro: "제안 가격과 가정을 바꾸고 세 시나리오를 즉시 비교하세요. 저장된 부동산 근거는 그대로 유지됩니다.",
    assumptions: "입력 가정", scenario: "시나리오", offerTwd: "제안 가격 (TWD)", downValue: "계약금 및 자기자금", downMode: "자기자금 입력 방식", amount: "금액 (TWD)", ratio: "비율 (%)",
    ratePercent: "연이율 (%)", loanYears: "대출 기간 (년)", acquisitionTwd: "취득 부대비용 (TWD)", recurringTwd: "보유 비용 (TWD/월)", renovationTwd: "수리 예산 (TWD)", holdingYears: "보유 기간 (년)", commuteMinutes: "수동 편도 통근 시간 (분)",
    inputNote: "빈칸은 알 수 없음입니다. 비용이 없다고 가정할 때만 0을 입력하세요. 취득 비용은 입력한 세금과 수수료만 포함하며, 보유 비용은 대출 상환을 제외합니다.",
    unknown: "알 수 없음", unknownItems: "알 수 없는 항목", none: "입력 완료", subtotal: "알려진 금액 소계", complete: "입력한 비용 포함", comparison: "A / B / C 비교", scroll: "가로로 스크롤하여 세 시나리오를 비교하세요.",
    purchaseCashTwd: "매입 시 필요한 현금", principalTwd: "대출 원금", paymentTwd: "월 대출 상환액", monthlyOwnershipTwd: "월 소유 비용", firstYearTwd: "첫해 현금 부담", acquisitionTotalTwd: "총 취득 비용", holdingCashTwd: "보유 기간 현금 지출",
    asking: "매도 호가 (읽기 전용)", saved: "저장된 금융 가격 (읽기 전용)", askingDelta: "호가 대비 제안 차액", savedDelta: "저장 금융 가격 대비 차액", baselineDelta: "고정 기준 대비 제안 차액", paymentDelta: "기준 대비 월 상환 차액", cashDelta: "기준 대비 매입 현금 차액", ownershipDelta: "기준 대비 월 소유 비용 차액", yearDelta: "기준 대비 첫해 현금 차액",
    freeze: "기준으로 고정", baseline: "고정 시나리오 기준", clear: "기준 해제", noBaseline: "시나리오를 고정하면 일정한 기준과 변경 사항을 비교할 수 있습니다.", save: "초안 및 기준 저장", savedStatus: "시나리오 초안이 이 브라우저에 별도로 저장되었습니다.", failed: "브라우저에 저장할 수 없습니다. 현재 초안은 화면에 유지됩니다.", damaged: "저장 시나리오를 복원할 수 없어 새 초안을 표시합니다.",
    method: "계산 방식", methodNote: "기존 원리금 균등 상환 공식을 사용하며 고정 금리, 거치 기간 없음으로 가정합니다. 매입 현금 = 자기자금 + 입력 취득 비용 + 수리. 총 취득 비용 = 제안 가격 + 취득 비용 + 수리. 첫해에는 12개월 상환 및 보유 비용을 더합니다. 보유 기간의 상환은 대출 만기까지만 계산합니다. 합계는 현금 지출이며 재판매, 가격 상승, 수익 예측, 매각 비용은 제외합니다. 표시에만 반올림합니다.",
    boundary: "제안 가격은 가정이며 수락 가격 예측이 아닙니다. 외부 데이터 요청이나 알 수 없는 세금 및 수수료 추정 없이 운영 평가와 저장 근거를 유지합니다.", commute: "통근 참고", accepted: "승인된 저장 경로", noCommute: "승인된 통근 근거가 없습니다. 시나리오별로 시간을 직접 입력할 수 있습니다.", manual: "수동 가정", minutes: "분 / 편도", checked: "확인 시각", source: "출처", commuteNote: "통근은 시간만 비교하며 소유 비용에 포함하지 않습니다.", range: "허용 범위 내 0 이상의 수를 입력하세요. 자기자금은 제안 가격 또는 100%를 초과할 수 없습니다.", positive: "0보다 큰 값을 입력하세요.", integer: "정수 기간을 입력하세요 (1–100년).", readonly: "저장 근거 고정", stale: "저장된 금융 가정이 오래되었거나 지원되지 않아 대출 기본값으로 사용하지 않았습니다.",
  },
};
