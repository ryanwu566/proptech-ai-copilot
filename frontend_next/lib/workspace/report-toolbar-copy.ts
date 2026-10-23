import type { CopyCatalogue } from "../copy-catalogue";

type ReportToolbarKey = "title" | "loading" | "invalid" | "missing" | "backToCases" | "print" | "backToWorkspace" | "savedCases" | "printHint" | "newer" | "loadNewer";

/** On-screen Report chrome only. The printed document keeps its own wording and layout. */
export const reportToolbarCopy: CopyCatalogue<ReportToolbarKey> = {
  "zh-TW": {
    title: "案件證據報告", loading: "正在讀取案件快照",
    invalid: "案件儲存紀錄無效或識別衝突；正式報告與列印已停止。", missing: "找不到已儲存案件，或案件已被移除；正式列印已停止。",
    backToCases: "回到已儲存案件", print: "列印／另存 PDF", backToWorkspace: "返回案件工作區", savedCases: "已儲存案件",
    printHint: "開啟瀏覽器列印對話框，可選擇另存為 PDF。",
    newer: "案件已有較新快照；目前畫面與列印仍使用你正在檢視的保存快照。", loadNewer: "載入較新快照",
  },
  en: {
    title: "Case evidence report", loading: "Reading the case snapshot",
    invalid: "The saved case record is invalid or its identity conflicts; the formal report and printing are stopped.", missing: "The saved case was not found or has been removed; formal printing is stopped.",
    backToCases: "Back to saved cases", print: "Print / Save as PDF", backToWorkspace: "Back to the case", savedCases: "Saved cases",
    printHint: "Opens the browser print dialog, where you can save as PDF.",
    newer: "This case has a newer snapshot. The screen and print still use the saved snapshot you are viewing.", loadNewer: "Load newer snapshot",
  },
  ja: {
    title: "物件根拠レポート", loading: "案件のスナップショットを読み込んでいます",
    invalid: "保存された案件記録が無効、または識別が競合しています。正式レポートと印刷は停止しています。", missing: "保存済み案件が見つからないか削除されています。正式な印刷は停止しています。",
    backToCases: "保存済み案件に戻る", print: "印刷／PDF で保存", backToWorkspace: "案件に戻る", savedCases: "保存済み案件",
    printHint: "ブラウザーの印刷ダイアログを開きます。PDF として保存できます。",
    newer: "この案件にはより新しいスナップショットがあります。画面と印刷は、表示中の保存済みスナップショットを使い続けます。", loadNewer: "新しいスナップショットを読み込む",
  },
  ko: {
    title: "사례 근거 보고서", loading: "사례 스냅샷을 읽는 중",
    invalid: "저장된 사례 기록이 유효하지 않거나 식별이 충돌합니다. 정식 보고서와 인쇄가 중지되었습니다.", missing: "저장된 사례를 찾을 수 없거나 삭제되었습니다. 정식 인쇄가 중지되었습니다.",
    backToCases: "저장된 사례로 돌아가기", print: "인쇄 / PDF로 저장", backToWorkspace: "사례로 돌아가기", savedCases: "저장된 사례",
    printHint: "브라우저 인쇄 대화상자를 엽니다. PDF로 저장할 수 있습니다.",
    newer: "이 사례에 더 새로운 스냅샷이 있습니다. 화면과 인쇄는 지금 보고 있는 저장된 스냅샷을 계속 사용합니다.", loadNewer: "새 스냅샷 불러오기",
  },
};
