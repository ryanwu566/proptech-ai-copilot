"use client";

export type AppPage = "儀表板" | "TaxOracle" | "Market Insight Lite" | "Map Insight Lite" | "房價估算" | "Aegis-Credit Lite" | "LexProp Lite" | "歷史案件";

const groups: { label: string; items: { page: AppPage; label: string }[] }[] = [
  { label: "案件決策", items: [{ page: "儀表板", label: "任務首頁" }, { page: "TaxOracle", label: "TaxOracle 稅務快篩" }] },
  { label: "區域洞察", items: [{ page: "Market Insight Lite", label: "Market Insight" }, { page: "Map Insight Lite", label: "Map Insight" }, { page: "房價估算", label: "房價估算" }] },
  { label: "風險模組", items: [{ page: "Aegis-Credit Lite", label: "房貸風險展示" }, { page: "LexProp Lite", label: "判決風險摘要" }] },
  { label: "紀錄", items: [{ page: "歷史案件", label: "History" }] },
];

export function Sidebar({ page, onNavigate, open = false, onClose }: { page: AppPage; onNavigate: (page: AppPage) => void; open?: boolean; onClose?: () => void }) {
  return <><button aria-label="關閉導覽" onClick={onClose} className={`fixed inset-0 z-30 bg-slate-950/35 transition lg:hidden ${open ? "block" : "hidden"}`} /><aside className={`fixed inset-y-0 left-0 z-40 w-48 overflow-y-auto border-r border-stone-200 bg-[#24313a] px-2.5 py-4 pb-20 text-white transition-transform lg:z-20 lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
    <button onClick={() => onNavigate("儀表板")} className="flex items-center gap-2.5 px-2 text-left"><span className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-500/15 text-sm text-cyan-300">⌂</span><span><p className="text-[10px] font-bold tracking-[0.14em] text-white">Urban Copilot</p><h1 className="mt-0.5 text-[9px] font-medium text-slate-400">房產決策工作台</h1></span></button>
    <nav className="mt-6 space-y-4">{groups.map((group) => <div key={group.label}><p className="mb-1 px-2 text-[9px] font-bold tracking-wider text-slate-500">{group.label}</p><div className="space-y-0.5">{group.items.map((item) => <button key={item.page} onClick={() => onNavigate(item.page)} className={`relative w-full rounded-lg px-2.5 py-2 text-left text-[11px] transition ${page === item.page ? "bg-white/10 font-bold text-white shadow-sm" : "text-slate-400 hover:bg-white/5 hover:text-slate-200"}`}>{page === item.page && <span className="absolute bottom-2 left-0 top-2 w-0.5 rounded-full bg-cyan-300" />}{item.label}</button>)}</div></div>)}</nav>
    <div className="absolute bottom-4 left-3 right-3 flex items-center justify-between rounded-lg bg-white/5 px-2.5 py-2 text-[9px] text-slate-400"><span className="flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />系統可用</span><span>Mock</span></div>
  </aside></>;
}
