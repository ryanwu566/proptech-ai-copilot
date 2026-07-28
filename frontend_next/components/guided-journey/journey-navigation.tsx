export function JourneyNavigation({ previousLabel, nextLabel, onPrevious, onNext, hasPrevious, hasNext }: { previousLabel: string; nextLabel: string; onPrevious: () => void; onNext: () => void; hasPrevious: boolean; hasNext: boolean }) {
  return <div className="mt-5 flex flex-col gap-2 border-t border-stone-200 pt-4 sm:flex-row sm:justify-between">
    <button type="button" disabled={!hasPrevious} onClick={onPrevious} className="rounded-lg border border-stone-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 transition hover:border-cyan-300 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2">{previousLabel}</button>
    <button type="button" onClick={onNext} className="rounded-lg bg-cyan-700 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-cyan-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2">{hasNext ? nextLabel : "回到第一步"}</button>
  </div>;
}
