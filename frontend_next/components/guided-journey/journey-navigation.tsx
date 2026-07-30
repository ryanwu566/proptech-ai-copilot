import { useExperienceLocale } from "@/components/experience-locale-provider";

export function JourneyNavigation({ previousLabel, nextLabel, onPrevious, onNext, hasPrevious, hasNext }: { previousLabel: string; nextLabel: string; onPrevious: () => void; onNext: () => void; hasPrevious: boolean; hasNext: boolean }) {
  const { t } = useExperienceLocale();
  return <div className="mt-5 flex min-w-0 flex-col gap-2 border-t border-stone-200 pt-4 sm:flex-row sm:justify-between">
    <button type="button" data-action-kind="navigation" disabled={!hasPrevious} onClick={onPrevious} className="w-full rounded-lg border border-stone-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 transition hover:border-cyan-300 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 sm:w-auto">{previousLabel}</button>
    <button type="button" data-action-kind="navigation" onClick={onNext} className="w-full rounded-lg border border-cyan-700 bg-white px-4 py-2.5 text-sm font-bold text-cyan-800 transition hover:bg-cyan-50 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 sm:w-auto">{hasNext ? nextLabel : t("journey.finish")}</button>
  </div>;
}
