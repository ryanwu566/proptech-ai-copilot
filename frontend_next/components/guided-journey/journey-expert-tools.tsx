import { useState, type ReactNode } from "react";

export function JourneyExpertTools({ renderTools }: { renderTools: () => ReactNode }) {
  const [open, setOpen] = useState(false);
  return <details className="rounded-xl border border-stone-200 bg-white" onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary className="cursor-pointer px-3 py-3 text-sm font-bold text-slate-900">查看全部專業工具</summary>
    {open && <div className="border-t border-stone-100 p-3">{renderTools()}</div>}
  </details>;
}
