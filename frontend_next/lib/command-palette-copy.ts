import type { CopyCatalogue } from "./copy-catalogue";

const en = {
  trigger: "Quick actions", title: "Case commands", search: "Search actions…", close: "Close commands",
  empty: "No matching actions", results: "{{count}} matching actions", current: "Current page",
  global: "Navigation", savedContext: "Saved case", navigate: "Navigate", select: "Open", dismiss: "Close",
  new: "Create a new case", saved: "Open saved cases", compare: "Compare cases", account: "Open account", tour: "Start tour",
  overview: "Return to case overview", market: "View price and market", location: "View location and commute",
  risk: "View risk and environment", finance: "View money and holding costs", "decision-room": "Open Decision Room",
  report: "View case report", "confirm-location": "Confirm property location", "risk-review": "Review unresolved risk",
  "market-evidence": "View saved market evidence", outstanding: "Handle {{count}} outstanding items",
  riskCount: "{{count}} verification actions", evidence: "Saved evidence",
};
export type CommandCopyKey = keyof typeof en;
export const commandPaletteCopy: CopyCatalogue<CommandCopyKey> = {
  en,
  "zh-TW": {
    trigger: "快速操作", title: "案件快速操作", search: "搜尋操作…", close: "關閉快速操作",
    empty: "找不到符合的操作", results: "{{count}} 項符合的操作", current: "目前頁面",
    global: "導覽", savedContext: "已儲存案件", navigate: "移動", select: "開啟", dismiss: "關閉",
    new: "建立新案件", saved: "開啟已儲存案件", compare: "比較案件", account: "開啟帳戶", tour: "開始導覽",
    overview: "返回物件總覽", market: "查看價格與市場", location: "查看區位與通勤",
    risk: "查看風險與環境", finance: "查看資金與持有成本", "decision-room": "開啟購屋決策室",
    report: "查看案件報告", "confirm-location": "確認物件位置", "risk-review": "查看待查風險",
    "market-evidence": "查看已儲存的市場證據", outstanding: "處理 {{count}} 項待辦",
    riskCount: "{{count}} 項待查證", evidence: "已儲存證據",
  },
  ja: {
    trigger: "クイック操作", title: "案件コマンド", search: "操作を検索…", close: "コマンドを閉じる",
    empty: "一致する操作がありません", results: "{{count}} 件の操作が一致", current: "現在のページ",
    global: "ナビゲーション", savedContext: "保存済み案件", navigate: "移動", select: "開く", dismiss: "閉じる",
    new: "新しい案件を作成", saved: "保存済み案件を開く", compare: "案件を比較", account: "アカウントを開く", tour: "ガイドを開始",
    overview: "物件概要に戻る", market: "価格と市場を表示", location: "立地と通勤を表示",
    risk: "リスクと環境を表示", finance: "資金と保有コストを表示", "decision-room": "購入意思決定ルームを開く",
    report: "案件レポートを表示", "confirm-location": "物件の位置を確認", "risk-review": "未確認のリスクを表示",
    "market-evidence": "保存済み市場根拠を表示", outstanding: "未完了の {{count}} 件に対応",
    riskCount: "{{count}} 件の確認事項", evidence: "保存済み根拠",
  },
  ko: {
    trigger: "빠른 작업", title: "사례 명령", search: "작업 검색…", close: "명령 닫기",
    empty: "일치하는 작업이 없습니다", results: "일치하는 작업 {{count}}개", current: "현재 페이지",
    global: "탐색", savedContext: "저장된 사례", navigate: "이동", select: "열기", dismiss: "닫기",
    new: "새 사례 만들기", saved: "저장된 사례 열기", compare: "사례 비교", account: "계정 열기", tour: "가이드 시작",
    overview: "물건 개요로 돌아가기", market: "가격 및 시장 보기", location: "입지 및 통근 보기",
    risk: "위험 및 환경 보기", finance: "자금 및 보유 비용 보기", "decision-room": "부동산 의사결정 룸 열기",
    report: "사례 보고서 보기", "confirm-location": "물건 위치 확인", "risk-review": "미확인 위험 보기",
    "market-evidence": "저장된 시장 근거 보기", outstanding: "미완료 항목 {{count}}개 처리",
    riskCount: "확인할 항목 {{count}}개", evidence: "저장된 근거",
  },
};
