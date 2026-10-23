import type { CopyCatalogue } from "../copy-catalogue";

export type DemoCaseCopyKey = "title" | "body" | "boundary" | "compare" | "restore" | "restoring" | "restored" | "restoreFailed";

/** Disclosure shown wherever a demo snapshot is open. Never implies live, official or ranked evidence. */
export const demoCaseCopy: CopyCatalogue<DemoCaseCopyKey> = {
  "zh-TW": {
    title: "示範案件",
    body: "這是 {{date}} 的示範快照，用來展示完整流程。地址為路段層級，數值與來源脈絡均為範例資料，不是即時查詢，也不是正式官方證據。",
    boundary: "未知仍為未知，未命中不代表安全；本系統不排名、不選出勝出案件，也不提供購買建議。",
    compare: "比較示範案件 A 與 B",
    restore: "還原示範內容",
    restoring: "正在還原…",
    restored: "已還原示範案件 A／B 與其決策室；其他案件未變更。",
    restoreFailed: "未能還原示範內容；其他案件未變更。請到案件管理檢查儲存空間後再試。",
  },
  en: {
    title: "Demo case",
    body: "This is a demonstration snapshot dated {{date}}, shown to walk through the full workflow. The address is road-level and all values and source context are example data — not a live query and not official evidence.",
    boundary: "Unknown stays unknown and no match does not mean safe. Nothing is ranked, no case is picked as a winner, and no purchase advice is given.",
    compare: "Compare demo cases A and B",
    restore: "Restore demo content",
    restoring: "Restoring…",
    restored: "Demo cases A and B and their Decision Rooms were restored; your other cases are unchanged.",
    restoreFailed: "The demo content could not be restored; your other cases are unchanged. Check storage in case management and try again.",
  },
  ja: {
    title: "デモ案件",
    body: "これは {{date}} 時点のデモ用スナップショットで、一連の流れを紹介するためのものです。住所は路線単位で、数値と出典情報はすべてサンプルデータです。リアルタイムの照会でも正式な公的根拠でもありません。",
    boundary: "不明は不明のまま、該当なしは安全を意味しません。順位付けや優劣の判定、購入の推奨は行いません。",
    compare: "デモ案件 A と B を比較",
    restore: "デモ内容を元に戻す",
    restoring: "元に戻しています…",
    restored: "デモ案件 A／B と意思決定ルームを元に戻しました。他の案件は変更されていません。",
    restoreFailed: "デモ内容を元に戻せませんでした。他の案件は変更されていません。案件管理で保存容量を確認して再度お試しください。",
  },
  ko: {
    title: "예시 사례",
    body: "{{date}} 기준 예시 스냅샷으로, 전체 흐름을 보여 주기 위한 것입니다. 주소는 도로 단위이며 수치와 출처 정보는 모두 예시 데이터입니다. 실시간 조회나 공식 근거가 아닙니다.",
    boundary: "미확인은 미확인 그대로이며, 미해당은 안전을 의미하지 않습니다. 순위나 우열 판정, 구매 권고를 제공하지 않습니다.",
    compare: "예시 사례 A와 B 비교",
    restore: "예시 내용 복원",
    restoring: "복원 중…",
    restored: "예시 사례 A·B와 의사결정 룸을 복원했습니다. 다른 사례는 변경되지 않았습니다.",
    restoreFailed: "예시 내용을 복원하지 못했습니다. 다른 사례는 변경되지 않았습니다. 사례 관리에서 저장 공간을 확인한 뒤 다시 시도하세요.",
  },
};
