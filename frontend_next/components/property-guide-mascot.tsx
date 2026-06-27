"use client";

import type { WorkflowStatus } from "@/lib/workflow-status";
import { BUYING_WIZARD_STEPS, getActiveWizardStep, type BuyingWizardStep } from "@/lib/buying-wizard-status";
import { useViewMode } from "@/lib/view-mode";

export function PropertyGuideMascot({ stage, riskSignal = "unknown", workflowStatus, activeWizardStep, caseMessage }: { stage: "start" | "finder" | "valuation" | "loan" | "location" | "complete"; riskSignal?: "green" | "yellow" | "red" | "unknown"; workflowStatus?: WorkflowStatus; activeWizardStep?: BuyingWizardStep; caseMessage?: string }) {
  const [viewMode] = useViewMode();
  const messages = {
    start: "第一次用可以先看動畫，或直接跑一次示範。看到 ? 可以點開，我會用白話解釋每個功能。",
    finder: "先不用想太多，填預算和地點就好。",
    valuation: "這一步是看價格合不合理。",
    loan: "買得起不只看總價，還要看月付和持有成本。",
    location: "區位分數高也要實地確認交通、噪音與環境。",
    complete: "分析完成後，可以保存案件或匯出報告和家人討論。",
  };
  const riskMessages = {
    green: "目前條件相對健康，但仍要實地確認屋況與議價空間。",
    yellow: "可以繼續看，但建議先補查風險並保留議價空間。",
    red: "目前風險偏高，建議先比較其他路段或物件。",
    unknown: messages[stage],
  };
  const wizardStep = activeWizardStep
    ? BUYING_WIZARD_STEPS.find((step) => step.id === activeWizardStep)
    : workflowStatus ? getActiveWizardStep(workflowStatus) : undefined;
  return <div className="flex min-w-0 items-center gap-3 rounded-xl border border-amber-300 bg-gradient-to-br from-yellow-50 to-amber-100 p-3 shadow-md ring-2 ring-yellow-200/70" aria-label="黃色看房助手" role="status">
    <div className="relative grid h-12 w-12 shrink-0 place-items-center rounded-[18px] bg-yellow-300 shadow-sm">
      <span className="absolute left-3 top-4 h-2 w-2 rounded-full bg-slate-800" /><span className="absolute right-3 top-4 h-2 w-2 rounded-full bg-slate-800" />
      <span className="mt-4 h-1.5 w-5 rounded-full bg-amber-700" />
      <span className="absolute -bottom-1 left-2 h-3 w-2 rounded-full bg-yellow-400" /><span className="absolute -bottom-1 right-2 h-3 w-2 rounded-full bg-yellow-400" />
    </div>
    <div className="min-w-0"><p className="text-xs font-extrabold tracking-wider text-amber-800">黃色看房助手</p><p className="mt-1 text-xs font-medium leading-5 text-slate-700">{caseMessage || (wizardStep ? wizardStep.guide : riskMessages[riskSignal])}</p><p className="mt-1 text-[10px] leading-4 text-amber-800">{viewMode === "pro" ? "現在會顯示完整分析細節，包含可比成交、資料品質和規則追蹤。" : "我會先幫你看重點，細節先收起來，想看完整資料可以切到專業模式。"}</p></div>
  </div>;
}
