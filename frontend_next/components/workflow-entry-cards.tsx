"use client";
import { HelpTooltip } from "@/components/help-tooltip";
import { HELP_CONTENT } from "@/lib/help-content";
import { useExperienceLocale } from "@/components/experience-locale-provider";

type WorkflowEntryCardsProps = {
  onStartBuying: () => void;
  onOpenTax: () => void;
  onOpenAdvanced: () => void;
  onGuidedDemo: () => void;
  onOpenCompare: () => void;
};

export function WorkflowEntryCards({ onStartBuying, onOpenTax, onOpenAdvanced, onGuidedDemo, onOpenCompare }: WorkflowEntryCardsProps) {
  const { copy } = useExperienceLocale();
  const entries = [
    { key: "buying" as const, eyebrow: copy("workflow.entryBuyingEyebrow"), title: copy("workflow.entryBuyingTitle"), description: copy("workflow.entryBuyingDesc"), action: copy("workflow.entryBuyingAction"), primary: true },
    { key: "demo" as const, eyebrow: copy("workflow.entryDemoEyebrow"), title: copy("workflow.entryDemoTitle"), description: copy("workflow.entryDemoDesc"), action: copy("workflow.entryDemoAction"), primary: false },
    { key: "compare" as const, eyebrow: copy("workflow.entryCompareEyebrow"), title: copy("workflow.entryCompareTitle"), description: copy("workflow.entryCompareDesc"), action: copy("workflow.entryCompareAction"), primary: false },
  ];
  const actions = { buying: onStartBuying, demo: onGuidedDemo, compare: onOpenCompare };
  return <section aria-label={copy("workflow.entryQuestion")} className="space-y-4">
    <div><p className="text-[10px] font-bold tracking-[0.18em] text-cyan-700">{copy("workflow.entryQuestion")}</p><h2 className="mt-1 text-xl font-extrabold text-slate-950">{copy("workflow.entryHeading")}</h2></div>
    <div className="grid gap-4 lg:grid-cols-3">
      {entries.map((entry) => <article key={entry.key} className={`flex min-w-0 flex-col rounded-2xl border p-5 shadow-sm ${entry.primary ? "border-cyan-300 bg-gradient-to-br from-cyan-950 to-slate-900 text-white" : "border-stone-200 bg-white text-slate-950"}`}>
        <p className={`text-[10px] font-bold tracking-[0.18em] ${entry.primary ? "text-cyan-200" : "text-cyan-700"}`}>{entry.eyebrow}</p>
        <div className="mt-2 flex items-center gap-2"><h3 className="text-lg font-extrabold">{entry.title}</h3>{entry.key === "demo" && <HelpTooltip title={HELP_CONTENT.guidedDemo.title}>{HELP_CONTENT.guidedDemo.body}</HelpTooltip>}{entry.key === "compare" && <HelpTooltip title={HELP_CONTENT.caseComparison.title}>{HELP_CONTENT.caseComparison.body}</HelpTooltip>}</div>
        <p className={`mt-2 flex-1 text-sm leading-6 ${entry.primary ? "text-slate-200" : "text-slate-600"}`}>{entry.description}</p>
        <button type="button" onClick={actions[entry.key]} className={`mt-5 w-full rounded-xl px-4 py-3 text-sm font-bold transition ${entry.primary ? "bg-cyan-400 text-slate-950 hover:bg-cyan-300" : "border border-stone-200 bg-stone-50 text-slate-800 hover:border-cyan-300 hover:bg-cyan-50"}`}>{entry.action}</button>
      </article>)}
    </div>
    <div className="flex flex-col gap-2 rounded-xl border border-stone-200 bg-stone-50 p-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-xs text-slate-600">{copy("workflow.entryOtherNote")}</p>
      <div className="flex flex-col gap-2 sm:flex-row">
        <button type="button" onClick={onOpenTax} className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs font-bold text-slate-700">{copy("workflow.entryTaxButton")}</button>
        <button type="button" onClick={onOpenAdvanced} className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs font-bold text-slate-700">{copy("workflow.entryAdvancedButton")}</button>
        <span className="flex items-center gap-1"><HelpTooltip title={HELP_CONTENT.taxOracle.title}>{HELP_CONTENT.taxOracle.body}</HelpTooltip><HelpTooltip title={HELP_CONTENT.mapInsight.title}>{HELP_CONTENT.mapInsight.body}</HelpTooltip><HelpTooltip title={HELP_CONTENT.geoMap.title}>{HELP_CONTENT.geoMap.body}</HelpTooltip><HelpTooltip title={HELP_CONTENT.dataStatus.title}>{HELP_CONTENT.dataStatus.body}</HelpTooltip></span>
      </div>
    </div>
  </section>;
}
