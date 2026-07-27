export function ChartEmptyState({ title = "目前無足夠資料可繪圖" }: { title?: string }) {
  return <div role="status" className="flex min-h-[320px] items-center justify-center rounded-xl border border-dashed border-stone-300 bg-stone-50 p-6 text-center text-sm text-slate-600">{title}，不以零值或推估資料補齊。</div>;
}
