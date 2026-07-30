import { useState, type ReactNode } from "react";

export function JourneyExpertTools({ renderTools }: { renderTools: () => ReactNode }) {
  const [open, setOpen] = useState(false);
  return <details data-action-kind="secondary" data-default-open="false" className="rounded-xl border border-stone-200 bg-white" onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary className="cursor-pointer px-3 py-3 text-sm font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-inset">專家工具與直接入口</summary>
    {open && <div className="border-t border-stone-100 p-3">{renderTools()}</div>}
  </details>;
}
