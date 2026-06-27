"use client";

import { DetailDisclosure } from "@/components/detail-disclosure";
import { Button } from "@/components/ui";
import { useViewMode } from "@/lib/view-mode";
import type { ViewingDecision } from "@/lib/viewing-decision";

const toneClass: Record<ViewingDecision["status"], string> = {
  ready_to_view: "border-emerald-200 bg-emerald-50 text-emerald-950",
  needs_more_data: "border-amber-200 bg-amber-50 text-amber-950",
  clarify_risk_first: "border-rose-200 bg-rose-50 text-rose-950",
};

export function ViewingDecisionPanel({ decision, onNext }: { decision: ViewingDecision; onNext: (targetId: string) => void }) {
  const [viewMode] = useViewMode();
  const reasons = viewMode === "beginner" ? decision.reasons.slice(0, 2) : decision.reasons.slice(0, 3);
  return <section id="viewing-decision" className={`min-w-0 scroll-mt-20 rounded-xl border p-4 ${toneClass[decision.status]}`} aria-label="這間房值得約看嗎">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <p className="text-[10px] font-bold tracking-[0.16em] opacity-70">VIEWING DECISION</p>
        <h2 className="mt-1 text-xl font-extrabold">這間房值得約看嗎？</h2>
        <p className="mt-2 text-lg font-black">{decision.label}</p>
      </div>
      <Button className="w-full sm:w-auto" onClick={() => onNext(decision.nextAction.targetId)}>{decision.nextAction.label}</Button>
    </div>
    <ul className="mt-3 space-y-1 text-xs leading-5">
      {reasons.map((reason) => <li key={reason}>• {reason}</li>)}
    </ul>
    {decision.missingCriticalData.length > 0 && <p className="mt-3 rounded-lg bg-white/70 px-3 py-2 text-[11px] font-bold">目前缺少：{decision.missingCriticalData.join("、")}</p>}
    {viewMode === "pro" && <div className="mt-3">
      <DetailDisclosure title="查看判斷條件與資料完成度">
        <div className="grid gap-3 text-xs leading-5 md:grid-cols-3">
          <InfoBlock title="已完成資料" items={decision.completedData} empty="尚未完成核心資料。" />
          <InfoBlock title="風險來源" items={decision.riskSources} empty="目前沒有已知高風險來源。" />
          <InfoBlock title="判斷規則" items={decision.ruleNotes} />
        </div>
      </DetailDisclosure>
    </div>}
    <p className="mt-3 text-[10px] leading-5 opacity-80">本區塊只整理既有分析結果，缺資料不會被視為低風險；不代表鑑價、銀行核貸、稅務申報或地質調查結論。</p>
  </section>;
}

function InfoBlock({ title, items, empty = "無" }: { title: string; items: string[]; empty?: string }) {
  const visible = items.length ? items : [empty];
  return <div className="rounded-lg bg-white/70 p-3">
    <p className="font-bold">{title}</p>
    <ul className="mt-2 space-y-1">{visible.map((item) => <li key={item}>• {item}</li>)}</ul>
  </div>;
}
