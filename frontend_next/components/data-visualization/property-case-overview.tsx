import type { PropertyCaseVisualModel } from "@/lib/property-case-visualization";

export function PropertyCaseOverview({ model }: { model: PropertyCaseVisualModel }) {
  const cards = [
    model.sections.find((section) => section.id === "basic"),
    model.sections.find((section) => section.id === "financial"),
    model.sections.find((section) => section.id === "due_diligence"),
    model.sections.find((section) => section.id === "viewing_offer"),
  ].filter((section): section is NonNullable<typeof section> => Boolean(section));
  return <section className="rounded-2xl border border-cyan-200 bg-white p-5 shadow-sm" aria-label="案件摘要儀表板">
    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
      <div className="min-w-0"><p className="text-[10px] font-bold tracking-[0.18em] text-cyan-700">CASE OVERVIEW</p><h2 className="mt-1 truncate text-xl font-black text-slate-950">{model.headline}</h2><p className="mt-1 truncate text-sm text-slate-600">{model.addressSummary}</p><p className="mt-2 text-xs font-bold text-slate-500">案件狀態：{model.decisionStatus}</p></div>
      <p className="max-w-md rounded-xl bg-stone-50 px-3 py-2 text-xs leading-5 text-slate-600">{model.summary}</p>
    </div>
    <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{cards.map((section) => <article key={section.id} className="rounded-xl border border-stone-200 bg-stone-50 p-3"><p className="text-xs font-bold text-slate-800">{section.label}</p><p className="mt-2 text-lg font-black text-slate-950">{section.completedCount} / {section.totalCount}</p><p className="mt-1 text-[11px] text-slate-600">{stateLabel(section.state)}；缺少 {section.missingItems.length} 項</p></article>)}</div>
    <p className="mt-3 text-[11px] leading-5 text-amber-800">完整度只表示目前明確資料的整理比例，不是風險分數、投資分數、安全判定或購買建議。</p>
  </section>;
}

function stateLabel(state: string): string {
  return { completed: "已完成", partial: "部分完成", missing: "缺少資料", blocked: "有阻擋", not_assessed: "尚未評估" }[state] ?? "尚未評估";
}
