import { useState, type ReactNode } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function JourneyExpertTools({ renderTools }: { renderTools: () => ReactNode }) {
  const [open, setOpen] = useState(false);
  const { t } = useExperienceLocale();
  return <details data-action-kind="secondary" data-default-open="false" className="rounded-xl border border-stone-200 bg-white" onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary className="cursor-pointer px-3 py-3 text-sm font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-inset">{t("journey.expertSummary")}</summary>
    {open && <div className="border-t border-stone-100 p-3">{renderTools()}</div>}
  </details>;
}
