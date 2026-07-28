export function JourneyToolCard({ title, productLabel, description, onOpen, primary = false }: { title: string; productLabel: string; description: string; onOpen: () => void; primary?: boolean }) {
  return <article className={"rounded-2xl border p-4 " + (primary ? "border-cyan-300 bg-cyan-50/70" : "border-stone-200 bg-white")}>
    <p className="text-[10px] font-bold tracking-wider text-cyan-700">{productLabel}</p>
    <h3 className="mt-1 text-base font-bold text-slate-950">{title}</h3>
    <p className="mt-2 text-xs leading-5 text-slate-600">{description}</p>
    <button type="button" onClick={onOpen} className={"mt-4 w-full rounded-lg px-3 py-2.5 text-sm font-bold transition focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 " + (primary ? "bg-cyan-700 text-white hover:bg-cyan-800" : "border border-stone-300 bg-white text-slate-800 hover:border-cyan-300")}>查看工具</button>
  </article>;
}
