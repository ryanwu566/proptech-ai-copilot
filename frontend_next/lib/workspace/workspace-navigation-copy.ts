import type { CopyCatalogue } from "../copy-catalogue";
import type { WorkspaceSection } from "./workspace-model";
import { moneyEntryCopy } from "./money-entry-copy";

type NavigationLabel = WorkspaceSection | "label" | "outputs" | "compare" | "report" | "planning" | "decisionRoom" | "primary" | "secondary" | "groupCase" | "groupDecide" | "groupTools";
// Shared entry labels only: keep the full operational room catalogue in its route.
export const workspaceNavigationCopy: CopyCatalogue<NavigationLabel> = {
  "zh-TW": {
    label: "案件工作區", overview: "物件總覽", market: "價格與市場", location: "區位與通勤", risk: "風險與環境", finance: moneyEntryCopy["zh-TW"].title,
    outputs: "輸出與方法", compare: "比較案件", report: "案件報告", planning: "進階案件規劃", decisionRoom: "購屋決策室", primary: "案件流程", secondary: "輔助頁面", groupCase: "看屋前證據", groupDecide: "決策輸出", groupTools: "工具",
  },
  en: {
    label: "Case workspace", overview: "Case overview", market: "Price and market", location: "Location and commute", risk: "Risk and environment", finance: moneyEntryCopy.en.title,
    outputs: "Outputs and methods", compare: "Compare cases", report: "Case report", planning: "Advanced case planning", decisionRoom: "Property Decision Room", primary: "Case workflow", secondary: "Supporting pages", groupCase: "Pre-viewing evidence", groupDecide: "Decision outputs", groupTools: "Tools",
  },
  ja: {
    label: "物件ワークスペース", overview: "物件概要", market: "価格と市場", location: "立地と通勤", risk: "リスクと環境", finance: moneyEntryCopy.ja.title,
    outputs: "出力と方法", compare: "物件を比較", report: "物件レポート", planning: "詳細な物件計画", decisionRoom: "購入意思決定ルーム", primary: "案件の流れ", secondary: "補助ページ", groupCase: "内見前の根拠", groupDecide: "判断の出力", groupTools: "ツール",
  },
  ko: {
    label: "사례 작업 공간", overview: "물건 개요", market: "가격과 시장", location: "입지와 통근", risk: "위험과 환경", finance: moneyEntryCopy.ko.title,
    outputs: "출력과 방법", compare: "사례 비교", report: "사례 보고서", planning: "상세 사례 계획", decisionRoom: "부동산 의사결정 룸", primary: "사례 흐름", secondary: "보조 페이지", groupCase: "방문 전 근거", groupDecide: "의사결정 결과", groupTools: "도구",
  },
};
