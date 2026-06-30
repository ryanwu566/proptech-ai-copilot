"use client";

export type AppPage = "儀表板" | "TaxOracle" | "Market Insight Lite" | "Map Insight Lite" | "房價估算" | "Aegis-Credit Lite" | "Terrain Risk" | "歷史案件";

const groups: { label: string; items: { page: AppPage; label: string }[] }[] = [
  { label: "工作台", items: [{ page: "儀表板", label: "看房決策工作台" }] },
  { label: "地圖", items: [{ page: "Map Insight Lite", label: "地圖洞察" }] },
  { label: "案件", items: [{ page: "歷史案件", label: "案件保存與比較" }] },
  { label: "更多工具", items: [
    { page: "房價估算", label: "實價登錄估算" },
    { page: "Terrain Risk", label: "地勢與災害風險" },
    { page: "TaxOracle", label: "TaxOracle 稅務快篩" },
    { page: "Aegis-Credit Lite", label: "貸款與資金壓力" },
    { page: "Market Insight Lite", label: "區域行情背景" },
  ] },
];

export function Sidebar({ page, onNavigate, open = false, onClose }: { page: AppPage; onNavigate: (page: AppPage) => void; open?: boolean; onClose?: () => void }) {
  return <><button aria-label="關閉選單" onClick={onClose} className={`fixed inset-0 z-30 bg-slate-950/35 transition lg:hidden ${open ? "block" : "hidden"}`} /><aside className={`fixed inset-y-0 left-0 z-40 w-48 overflow-y-auto border-r border-stone-200 bg-[#24313a] px-2.5 py-4 pb-20 text-white transition-transform lg:z-20 lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
    <button onClick={() => onNavigate("儀表板")} className="flex items-center gap-2.5 px-2 text-left"><span className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-500/15 text-sm text-cyan-300">AI</span><span><p className="text-[10px] font-bold tracking-[0.14em] text-white">Urban Copilot</p><h1 className="mt-0.5 text-[9px] font-medium text-slate-400">看房決策助手</h1></span></button>
    <nav className="mt-6 space-y-4">{groups.map((group) => <div key={group.label}><p className="mb-1 px-2 text-[9px] font-bold tracking-wider text-slate-500">{group.label}</p><div className="space-y-0.5">{group.items.map((item) => <button key={item.page} onClick={() => onNavigate(item.page)} className={`relative w-full rounded-lg px-2.5 py-2 text-left text-[11px] transition ${page === item.page ? "bg-white/10 font-bold text-white shadow-sm" : "text-slate-400 hover:bg-white/5 hover:text-slate-200"}`}>{page === item.page && <span className="absolute bottom-2 left-0 top-2 w-0.5 rounded-full bg-cyan-300" />}{item.label}</button>)}</div></div>)}</nav>
    <div className="absolute bottom-4 left-3 right-3 flex items-center justify-between rounded-lg bg-white/5 px-2.5 py-2 text-[9px] text-slate-400"><span className="flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />系統可用</span><span>正式資料模式</span></div>
  </aside></>;
}
