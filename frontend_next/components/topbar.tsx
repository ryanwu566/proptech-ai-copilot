import type { AppPage } from "@/components/sidebar";
import { ViewModeToggle } from "@/components/view-mode-toggle";

const labels: Record<AppPage, string> = {
  儀表板: "任務首頁", TaxOracle: "TaxOracle 稅務先知", "Market Insight Lite": "Market Insight 區域行情", "Map Insight Lite": "Map Insight 地圖洞察", 房價估算: "實價登錄可比成交估算", "Aegis-Credit Lite": "房貸風險展示", "Terrain Risk": "地勢與災害風險分析", 歷史案件: "歷史案件",
};

export function Topbar({ page, onMenu, onTour }: { page: AppPage; onMenu: () => void; onTour: () => void }) {
  return <header className="sticky top-0 z-10 flex min-h-12 items-center justify-between gap-2 border-b border-stone-200 bg-[#f7f5f0]/90 px-4 py-1 backdrop-blur sm:px-5 lg:px-7"><div className="flex min-w-0 items-center gap-3"><button onClick={onMenu} className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-stone-200 bg-white text-sm text-slate-600 lg:hidden" aria-label="開啟選單">☰</button><p className="truncate text-xs font-bold text-slate-600">{labels[page]}</p></div><div className="flex shrink-0 items-center gap-2 text-[9px] font-semibold text-slate-500 sm:text-[10px]"><ViewModeToggle compact /><button onClick={onTour} className="hidden rounded-md border border-cyan-200 bg-cyan-50 px-2.5 py-1.5 font-bold text-cyan-800 sm:block">操作導覽</button></div></header>;
}
