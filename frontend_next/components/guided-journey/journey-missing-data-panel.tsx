export function JourneyMissingDataPanel({ title, items }: { title: string; items: readonly string[] }) {
  return <section aria-labelledby="journey-missing-data-heading" className="rounded-xl border border-amber-200 bg-amber-50/70 p-4">
    <h3 id="journey-missing-data-heading" className="text-sm font-black text-amber-950">{title}</h3>
    {items.length ? <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-amber-900">{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-2 text-xs leading-5 text-amber-900">目前沒有額外待補項目；各項資料仍應分別查看來源與限制。</p>}
  </section>;
}
