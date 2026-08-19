"use client";

import { useExperienceLocale } from "@/components/experience-locale-provider";

export type DecisionCaseAction = "new" | "saved" | "none";

export function DecisionCaseActionSelector({ activeAction, onSelect }: { activeAction: DecisionCaseAction; onSelect: (action: Exclude<DecisionCaseAction, "none">) => void }) {
  const { copy } = useExperienceLocale();
  return <section aria-labelledby="decision-case-action-heading" className="min-w-0 rounded-xl border border-cyan-100 bg-white p-4"><h3 id="decision-case-action-heading" className="text-base font-black text-slate-950">{copy("journey.caseActionTitle")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{copy("journey.caseActionDesc")}</p><div className="mt-3 grid gap-2 sm:grid-cols-3"><ActionButton active={activeAction === "new"} label={copy("journey.caseActionNew")} onClick={() => onSelect("new")} activeLabel={copy("journey.caseActionActive")} inactiveLabel={copy("journey.caseActionInactive")} /><ActionButton active={activeAction === "saved"} label={copy("journey.caseActionSaved")} onClick={() => onSelect("saved")} activeLabel={copy("journey.caseActionActive")} inactiveLabel={copy("journey.caseActionInactive")} /><div className="rounded-lg border border-stone-200 bg-stone-50 p-3 text-xs font-bold text-slate-700">{copy("journey.caseActionDefer")}</div></div></section>;
}

function ActionButton({ active, label, onClick, activeLabel, inactiveLabel }: { active: boolean; label: string; onClick: () => void; activeLabel: string; inactiveLabel: string }) { return <button type="button" aria-pressed={active} onClick={onClick} className={active ? "rounded-lg border border-cyan-500 bg-cyan-50 px-3 py-3 text-left text-xs font-black text-cyan-900" : "rounded-lg border border-stone-200 bg-white px-3 py-3 text-left text-xs font-bold text-slate-800 hover:border-cyan-300"}>{label}<span className="mt-1 block text-[10px] font-normal text-slate-500">{active ? activeLabel : inactiveLabel}</span></button>; }
