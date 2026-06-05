import type { AppPage } from "@/components/sidebar";

const labels: Record<AppPage, string> = {
  儀表板: "任務首頁", TaxOracle: "TaxOracle 稅務先知", "Market Insight Lite": "Market Insight 區域行情", "Map Insight Lite": "Map Insight 地圖洞察", "Aegis-Credit Lite": "房貸風險展示", "LexProp Lite": "判決風險摘要", 歷史案件: "歷史案件",
};

export function Topbar({ page, onMenu }: { page: AppPage; onMenu: () => void }) {
  return <header className="sticky top-0 z-10 flex h-12 items-center justify-between border-b border-stone-200 bg-[#f7f5f0]/90 px-4 backdrop-blur sm:px-5 lg:px-7"><div className="flex min-w-0 items-center gap-3"><button onClick={onMenu} className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-stone-200 bg-white text-sm text-slate-600 lg:hidden" aria-label="開啟導覽">☰</button><p className="truncate text-xs font-bold text-slate-600">{labels[page]}</p></div><div className="flex shrink-0 items-center gap-2 text-[9px] font-semibold text-slate-500 sm:text-[10px]"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /><span className="hidden sm:inline">展示資料模式</span><span className="sm:hidden">Mock</span></div></header>;
}
