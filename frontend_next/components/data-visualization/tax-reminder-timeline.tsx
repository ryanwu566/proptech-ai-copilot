"use client";

import type { TaxVisualModel } from "@/lib/tax-visualization";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function TaxReminderTimeline({ model }: { model: TaxVisualModel }) {
  const { copy } = useExperienceLocale();
  const missingLabel = model.missingDocs.length ? `${model.missingDocs.length}` : copy("viz.taxReminderNoMissing");
  const monitorLabel = model.entersFiveYearMonitoring === null ? copy("viz.taxReminderMonitorNotAssessed") : model.entersFiveYearMonitoring ? copy("viz.taxReminderMonitorYes") : copy("viz.taxReminderMonitorNo");
  return <section aria-label={copy("viz.taxReminderTitle")} className="rounded-xl border border-amber-200 bg-amber-50 p-4"><h3 className="text-sm font-bold text-amber-950">{copy("viz.taxReminderTitle")}</h3><p className="mt-2 text-xs leading-5 text-amber-900">{copy("viz.taxReminderMissing")}: {missingLabel}; {copy("viz.taxReminderMonitor")}: {monitorLabel}</p><DetailDisclosure title={copy("viz.taxReminderDetailsTitle")}><div className="space-y-3 text-xs text-slate-700"><div><p className="font-bold">{copy("viz.taxReminderMissingList")}</p>{model.missingDocs.length ? <ul className="mt-1 list-disc pl-5">{model.missingDocs.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-1">{copy("viz.taxReminderNoMissingItems")}</p>}</div><div><p className="font-bold">{copy("viz.taxReminderTimelineLabel")}</p>{model.reminderTimeline.length ? <ol className="mt-1 list-decimal pl-5">{model.reminderTimeline.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ol> : <p className="mt-1">{copy("viz.taxReminderNoTimeline")}</p>}</div></div></DetailDisclosure></section>;
}
