import type { PropertyCaseVisualModel } from "@/lib/property-case-visualization";

export function PropertyCaseCompletenessChart({ model }: { model: PropertyCaseVisualModel }) {
  return <section className="rounded-2xl border border-stone-200 bg-white p-4" aria-label="案件資料完整度圖表">
    <div className="flex items-baseline justify-between gap-3"><div><p className="text-xs font-bold text-slate-500">COMPLETENESS</p><h3 className="mt-1 text-sm font-black text-slate-900">資料完整度視覺</h3></div><span className="text-xs font-bold text-slate-600">{model.overall.completionRatio === null ? "尚無可評估項目" : `${Math.round(model.overall.completionRatio * 100)}% 已整理`}</span></div>
    <div className="mt-4 space-y-3" role="img" aria-label="案件各區塊資料完成比例"><svg className="h-0 w-0" aria-hidden="true"><title>案件資料完整度</title><desc>各區塊以已完成項目與總項目呈現，並保留缺失狀態。</desc></svg>{model.sections.map((section) => <div key={section.id}><div className="flex items-center justify-between gap-3 text-xs"><span className="font-bold text-slate-800">{section.label}：{stateLabel(section.state)}</span><span className="text-slate-500">{section.completedCount} / {section.totalCount}</span></div><div className="mt-1 h-2 overflow-hidden rounded-full bg-stone-100"><div className="h-full rounded-full bg-cyan-600" style={{ width: `${section.totalCount ? (section.completedCount / section.totalCount) * 100 : 0}%` }} /></div>{section.missingItems.length > 0 && <p className="mt-1 text-[10px] text-amber-700">缺少 {section.missingItems.length} 項：{section.missingItems.slice(0, 2).join("、")}</p>}</div>)}</div>
    <p className="mt-3 text-[11px] leading-5 text-slate-500">圖表只計算明確完成項目；未知、未評估、暫時不可用與阻擋不會被換算成零風險或安全分數。</p>
  </section>;
}

function stateLabel(state: string): string {
  return { completed: "已完成", partial: "部分完成", missing: "缺少資料", blocked: "有阻擋", not_assessed: "尚未評估" }[state] ?? "尚未評估";
}
