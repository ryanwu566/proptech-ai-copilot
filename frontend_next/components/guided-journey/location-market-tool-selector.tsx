import type { LocationMarketToolId } from "@/lib/location-market-journey";

const TOOLS: Array<{ id: LocationMarketToolId; label: string; description: string }> = [
  { id: "commute", label: "通勤參考", description: "最近捷運與生活安排資訊" },
  { id: "terrain", label: "地形與環境", description: "各官方風險圖層的獨立狀態" },
  { id: "market", label: "區域市場資料", description: "官方市場背景與資料證據" },
];

export function LocationMarketToolSelector({ activeTool, onSelect }: { activeTool: LocationMarketToolId | null; onSelect: (tool: LocationMarketToolId) => void }) {
  return <section aria-labelledby="location-market-tools-heading" className="rounded-xl border border-stone-200 bg-white p-4">
    <h3 id="location-market-tools-heading" className="text-sm font-black text-slate-950">其他位置與市場分析</h3>
    <p className="mt-1 text-xs leading-5 text-slate-500">按下後才會開啟對應分析；結果不會合成分數或自動影響估價。</p>
    <div className="mt-3 grid gap-2 sm:grid-cols-3">{TOOLS.map((tool) => <button type="button" key={tool.id} aria-pressed={activeTool === tool.id} onClick={() => onSelect(tool.id)} className={`rounded-lg border p-3 text-left transition focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 ${activeTool === tool.id ? "border-cyan-400 bg-cyan-50" : "border-stone-200 bg-stone-50 hover:border-cyan-200"}`}>
      <span className="block text-xs font-bold text-slate-900">{tool.label}</span><span className="mt-1 block text-[10px] leading-5 text-slate-500">{tool.description}</span>
    </button>)}</div>
  </section>;
}
