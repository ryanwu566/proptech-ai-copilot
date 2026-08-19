"use client";

import type { TerrainRiskResult } from "@/lib/api";
import { buildTerrainReferenceEvidence, terrainReferenceStateLabel } from "@/lib/terrain-reference-evidence";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function TerrainStatusMatrix({ result }: { result: TerrainRiskResult | null }) {
  const { copy } = useExperienceLocale();
  if (!result) return <section aria-label={copy("viz.terrainTitle")} className="rounded-xl border border-dashed border-stone-300 bg-stone-50 p-4"><h3 className="text-sm font-bold text-slate-900">{copy("viz.terrainTitle")}</h3><p className="mt-2 text-xs leading-5 text-slate-600">{copy("viz.terrainNotAssessed")}</p></section>;
  const evidence = buildTerrainReferenceEvidence(result);
  const rows = evidence.layers.map((layer) => ({ id: layer.layer_id, label: layer.display_name, status: terrainReferenceStateLabel(layer.state), detail: layer.caveat, source: layer.source_name }));
  return <section aria-labelledby="terrain-status-matrix-heading" className="rounded-xl border border-amber-200 bg-amber-50/40 p-4">
    <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between"><h3 id="terrain-status-matrix-heading" className="text-sm font-black text-slate-950">{copy("viz.terrainTitle")}</h3><span className="text-[10px] text-amber-800">{copy("viz.terrainLayerIndependent")}</span></div>
    <div className="mt-3 overflow-hidden rounded-lg border border-amber-100 bg-white"><div className="hidden grid-cols-[150px_120px_minmax(0,1fr)] gap-3 bg-stone-50 px-3 py-2 text-[10px] font-bold text-slate-500 sm:grid"><span>{copy("viz.terrainItemLabel")}</span><span>{copy("viz.terrainStatusLabel")}</span><span>{copy("viz.terrainDescLabel")}</span></div>{rows.map((row) => <TerrainRow key={row.id} row={row} />)}</div>
    {result.risk_factors.length > 0 && <p className="mt-3 rounded-lg border border-amber-300 bg-amber-100 px-3 py-2 text-xs font-bold leading-5 text-amber-950">{copy("viz.terrainRiskSignal")}</p>}
  </section>;
}

function TerrainRow({ row }: { row: { label: string; status: string; detail: string; source?: string } }) {
  const warning = ["部分可用", "涵蓋有限", "暫時不可用", "檢查失敗", "未知", "未評估", "Partial", "Limited", "Unavailable", "Error", "Unknown", "Not assessed"].includes(row.status);
  return <div className={`grid gap-1 border-t border-stone-100 px-3 py-3 text-xs sm:grid-cols-[150px_120px_minmax(0,1fr)] sm:gap-3 ${warning ? "bg-amber-50/50" : "bg-white"}`}><span className="font-bold text-slate-800">{row.label}</span><span className="font-bold text-slate-700">{row.status}</span><span className="leading-5 text-slate-600">{row.detail}{row.source ? ` · ${row.source}` : ""}</span></div>;
}
