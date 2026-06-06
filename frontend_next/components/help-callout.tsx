export function HelpCallout({ children }: { children: string }) {
  return <aside className="flex items-start gap-2.5 rounded-xl border border-cyan-100 bg-cyan-50/65 px-3.5 py-2.5 text-xs leading-5 text-slate-600"><span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-white text-[10px] font-bold text-cyan-700 shadow-sm">?</span><div><span className="font-bold text-slate-700">這頁怎麼用：</span> {children}</div></aside>;
}
