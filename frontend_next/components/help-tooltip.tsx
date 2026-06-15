"use client";

import { useEffect, useId, useState, type ReactNode } from "react";

export function HelpTooltip({ title, children }: { title: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  useEffect(() => {
    function close(event: KeyboardEvent) { if (event.key === "Escape") setOpen(false); }
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);
  return <span className="relative inline-flex align-middle">
    <button type="button" aria-label={`說明：${title}`} aria-expanded={open} aria-controls={id} onClick={() => setOpen((value) => !value)} className="grid h-5 w-5 place-items-center rounded-full border border-cyan-300 bg-cyan-50 text-[11px] font-black text-cyan-800 transition hover:bg-cyan-100 focus:outline-none focus:ring-2 focus:ring-cyan-300">?</button>
    {open && <span id={id} role="tooltip" className="absolute right-0 top-7 z-50 w-64 max-w-[calc(100vw-2rem)] rounded-xl border border-cyan-200 bg-white p-3 text-left shadow-xl sm:left-0 sm:right-auto">
      <strong className="block text-xs text-slate-900">{title}</strong>
      <span className="mt-1 block text-[11px] font-normal leading-5 text-slate-600">{children}</span>
      <button type="button" onClick={() => setOpen(false)} className="mt-2 text-[10px] font-bold text-cyan-700">關閉說明</button>
    </span>}
  </span>;
}
