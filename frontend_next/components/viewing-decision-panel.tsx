"use client";

import { DetailDisclosure } from "@/components/detail-disclosure";
import { Button } from "@/components/ui";
import { useViewMode } from "@/lib/view-mode";
import type { ViewingDecision } from "@/lib/viewing-decision";
import { useExperienceLocale } from "@/components/experience-locale-provider";

const toneClass: Record<ViewingDecision["status"], string> = {
  ready_to_view: "border-emerald-200 bg-emerald-50 text-emerald-950",
  needs_more_data: "border-amber-200 bg-amber-50 text-amber-950",
  clarify_risk_first: "border-rose-200 bg-rose-50 text-rose-950",
};

export function ViewingDecisionPanel({ decision, onNext }: { decision: ViewingDecision; onNext: (targetId: string) => void }) {
  const { copy } = useExperienceLocale();
  const [viewMode] = useViewMode();
  const reasons = viewMode === "beginner" ? decision.reasons.slice(0, 2) : decision.reasons.slice(0, 3);
  return <section id="viewing-decision" className={`min-w-0 scroll-mt-20 rounded-xl border p-4 ${toneClass[decision.status]}`} aria-label={copy("viewing.heading")}>
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <p className="text-[10px] font-bold tracking-[0.16em] opacity-70">VIEWING DECISION</p>
        <h2 className="mt-1 text-xl font-extrabold">{copy("viewing.heading")}</h2>
        <p className="mt-2 text-lg font-black">{decision.label}</p>
      </div>
      <Button className="w-full sm:w-auto" onClick={() => onNext(decision.nextAction.targetId)}>{decision.nextAction.label}</Button>
    </div>
    <ul className="mt-3 space-y-1 text-xs leading-5">
      {reasons.map((reason) => <li key={reason}>• {reason}</li>)}
    </ul>
    {decision.missingCriticalData.length > 0 && <p className="mt-3 rounded-lg bg-white/70 px-3 py-2 text-[11px] font-bold">{copy("viewing.missingLabel")}: {decision.missingCriticalData.join(", ")}</p>}
    {viewMode === "pro" && <div className="mt-3">
      <DetailDisclosure title={copy("viewing.detailTitle")}>
        <div className="grid gap-3 text-xs leading-5 md:grid-cols-3">
          <InfoBlock title={copy("viewing.completedData")} items={decision.completedData} empty={copy("viewing.noCompletedData")} />
          <InfoBlock title={copy("viewing.riskSources")} items={decision.riskSources} empty={copy("viewing.noRiskSources")} />
          <InfoBlock title={copy("viewing.ruleNotes")} items={decision.ruleNotes} />
        </div>
      </DetailDisclosure>
    </div>}
    <p className="mt-3 text-[10px] leading-5 opacity-80">{copy("viewing.boundary")}</p>
  </section>;
}

function InfoBlock({ title, items, empty = "—" }: { title: string; items: string[]; empty?: string }) {
  const visible = items.length ? items : [empty];
  return <div className="rounded-lg bg-white/70 p-3">
    <p className="font-bold">{title}</p>
    <ul className="mt-2 space-y-1">{visible.map((item) => <li key={item}>• {item}</li>)}</ul>
  </div>;
}
