import type { CopyCatalogue } from "../copy-catalogue";

type CaseFrameKey = "current" | "asking" | "estimate" | "manual" | "notProvided" | "snapshotSaved" | "lastSaved" | "saveSnapshot" | "saveFinance"
  | "saved" | "saveFailed" | "saveStorageFailed" | "revalidation" | "details" | "normalized" | "scope" | "scopeAnchor" | "scopePending"
  | "notYet" | "checkedAt" | "notChecked" | "boundary";

/** Case frame chrome shared by every case route. Identity and saved-state wording only; no status is inferred here. */
export const caseFrameCopy: CopyCatalogue<CaseFrameKey> = {
  "zh-TW": {
    current: "目前物件", asking: "開價", estimate: "成交資料推估中點", manual: "比較基準價格", notProvided: "未提供",
    snapshotSaved: "已儲存快照", lastSaved: "最後儲存", saveSnapshot: "保存目前案件快照", saveFinance: "儲存財務摘要",
    saved: "已保存目前已知狀態；未知、無法取得與尚未完成的項目仍保持原狀。", saveFailed: "儲存失敗：",
    saveStorageFailed: "儲存失敗：瀏覽器儲存空間無法寫入。請保留目前頁面，確認儲存設定後重試。",
    revalidation: "先前受影響的證據保留為過期狀態，重新確認前不會顯示為目前證據。",
    details: "物件與來源詳細資料", normalized: "正規化地址", scope: "關聯範圍", scopeAnchor: "瀏覽器案件關聯錨點", scopePending: "物件尚待確認",
    notYet: "尚未取得", checkedAt: "證據檢查時間", notChecked: "尚未檢查", boundary: "邊界",
  },
  en: {
    current: "Current property", asking: "Asking price", estimate: "Transaction-based estimate midpoint", manual: "Comparison base price", notProvided: "Not provided",
    snapshotSaved: "Saved snapshot", lastSaved: "Last saved", saveSnapshot: "Save case snapshot", saveFinance: "Save money summary",
    saved: "Saved what is currently known. Unknown, unavailable and unfinished items stay as they are.", saveFailed: "Save failed: ",
    saveStorageFailed: "Save failed: browser storage could not be written. Keep this page open, check your storage settings and try again.",
    revalidation: "Previously affected evidence is kept as outdated and is not shown as current until the property is reconfirmed.",
    details: "Property and source details", normalized: "Normalized address", scope: "Link scope", scopeAnchor: "Browser case link anchor", scopePending: "Property not yet confirmed",
    notYet: "Not yet available", checkedAt: "Evidence checked", notChecked: "Not checked yet", boundary: "Boundary",
  },
  ja: {
    current: "現在の物件", asking: "売出価格", estimate: "取引データ推計の中央値", manual: "比較基準価格", notProvided: "未提供",
    snapshotSaved: "保存済みスナップショット", lastSaved: "最終保存", saveSnapshot: "案件のスナップショットを保存", saveFinance: "資金サマリーを保存",
    saved: "現在わかっている状態を保存しました。不明・取得不可・未完了の項目はそのままです。", saveFailed: "保存できませんでした：",
    saveStorageFailed: "保存できませんでした：ブラウザーの保存領域に書き込めません。このページを開いたまま、保存設定を確認して再試行してください。",
    revalidation: "影響を受けた以前の根拠は古い状態として保持され、再確認するまで現在の根拠として表示されません。",
    details: "物件と出典の詳細", normalized: "正規化された住所", scope: "関連付けの範囲", scopeAnchor: "ブラウザー案件の関連付けアンカー", scopePending: "物件は未確認",
    notYet: "未取得", checkedAt: "根拠の確認日時", notChecked: "未確認", boundary: "境界",
  },
  ko: {
    current: "현재 매물", asking: "호가", estimate: "거래 자료 추정 중간값", manual: "비교 기준 가격", notProvided: "제공되지 않음",
    snapshotSaved: "저장된 스냅샷", lastSaved: "마지막 저장", saveSnapshot: "사례 스냅샷 저장", saveFinance: "자금 요약 저장",
    saved: "현재 알려진 상태를 저장했습니다. 알 수 없음, 가져올 수 없음, 미완료 항목은 그대로 유지됩니다.", saveFailed: "저장 실패: ",
    saveStorageFailed: "저장 실패: 브라우저 저장소에 쓸 수 없습니다. 이 페이지를 유지한 채 저장 설정을 확인한 후 다시 시도하세요.",
    revalidation: "이전에 영향을 받은 근거는 오래된 상태로 유지되며, 매물을 다시 확인하기 전에는 현재 근거로 표시되지 않습니다.",
    details: "매물 및 출처 세부 정보", normalized: "정규화된 주소", scope: "연결 범위", scopeAnchor: "브라우저 사례 연결 앵커", scopePending: "매물 확인 대기",
    notYet: "아직 없음", checkedAt: "근거 확인 시각", notChecked: "아직 확인 안 함", boundary: "경계",
  },
};
