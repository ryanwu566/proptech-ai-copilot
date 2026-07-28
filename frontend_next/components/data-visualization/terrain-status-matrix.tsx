import type { TerrainRiskResult } from "@/lib/api";

export function TerrainStatusMatrix({ result }: { result: TerrainRiskResult | null }) {
  if (!result) return <section aria-label="地形與環境狀態矩陣" className="rounded-xl border border-dashed border-stone-300 bg-stone-50 p-4"><h3 className="text-sm font-bold text-slate-900">地形與環境狀態</h3><p className="mt-2 text-xs leading-5 text-slate-600">尚未評估。這不代表沒有風險。</p></section>;
  const rows = [
    { id: "terrain", label: "地勢", status: result.terrain.status, detail: result.terrain.explanation, source: result.terrain.source?.agency },
    ...Object.values(result.hazards).map((hazard) => ({ id: hazard.key, label: hazard.label, status: hazard.matched ? hazard.level : hazard.status, detail: hazard.explanation, source: hazard.source?.agency })),
  ];
  return <section aria-labelledby="terrain-status-matrix-heading" className="rounded-xl border border-amber-200 bg-amber-50/40 p-4">
    <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between"><h3 id="terrain-status-matrix-heading" className="text-sm font-black text-slate-950">地形與環境狀態</h3><span className="text-[10px] text-amber-800">各圖層獨立呈現，不合成總分</span></div>
    <div className="mt-3 overflow-hidden rounded-lg border border-amber-100 bg-white"><div className="hidden grid-cols-[150px_120px_minmax(0,1fr)] gap-3 bg-stone-50 px-3 py-2 text-[10px] font-bold text-slate-500 sm:grid"><span>項目</span><span>狀態</span><span>已知描述</span></div>{rows.map((row) => <TerrainRow key={row.id} row={row} />)}</div>
    {result.risk_factors.length > 0 && <p className="mt-3 rounded-lg border border-amber-300 bg-amber-100 px-3 py-2 text-xs font-bold leading-5 text-amber-950">目前有需要注意的獨立資料訊號，請查看上方結果與官方來源限制；這不是安全認證或購買建議。</p>}
  </section>;
}

function TerrainRow({ row }: { row: { label: string; status: string; detail: string; source?: string } }) {
  const warning = row.status === "high" || row.status === "medium" || row.status === "unavailable" || row.status === "unknown" || row.status === "not_assessed";
  return <div className={`grid gap-1 border-t border-stone-100 px-3 py-3 text-xs sm:grid-cols-[150px_120px_minmax(0,1fr)] sm:gap-3 ${warning ? "bg-amber-50/50" : "bg-white"}`}><span className="font-bold text-slate-800">{row.label}</span><span className="font-bold text-slate-700">{row.status}</span><span className="leading-5 text-slate-600">{row.detail}{row.source ? ` · ${row.source}` : ""}</span></div>;
}
