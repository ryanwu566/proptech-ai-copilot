import type { AmenityCategoryModel } from "@/lib/location-market-journey";

export function AmenityCategoryChart({ categories }: { categories: readonly AmenityCategoryModel[] }) {
  const hasData = categories.some((item) => item.count !== null);
  if (!hasData) {
    const unavailable = categories.some((item) => item.status === "unavailable");
    return <section aria-label="生活機能分類圖" className="rounded-xl border border-dashed border-stone-300 bg-stone-50 p-4"><h3 className="text-sm font-bold text-slate-900">生活機能分類摘要</h3><p className="mt-2 text-xs leading-5 text-slate-600">{unavailable ? "目前無法取得生活機能分類資料，請稍後再試。" : "尚未取得可呈現的生活機能分類資料。"}</p></section>;
  }
  const maxCount = Math.max(1, ...categories.flatMap((item) => item.count === null ? [] : [item.count]));
  return <section aria-label="生活機能分類圖" className="rounded-xl border border-stone-200 bg-white p-4">
    <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between"><h3 className="text-sm font-black text-slate-950">生活機能分類摘要</h3><span className="text-[10px] text-slate-500">API 可取得的搜尋結果摘要，不代表生活品質分數</span></div>
    <div role="img" aria-label="生活機能分類搜尋結果數量水平長條圖" className="mt-4 space-y-3">{categories.map((item) => <div key={item.id} className="grid grid-cols-[72px_minmax(0,1fr)_auto] items-center gap-2 text-xs">
      <span className="font-bold text-slate-700">{item.label}</span><div className="h-3 rounded-full bg-stone-100"><div className="h-3 rounded-full bg-cyan-600" style={{ width: item.count === null ? "0%" : `${(item.count / maxCount) * 100}%` }} /></div><span className="whitespace-nowrap font-bold text-slate-800">{item.count === null ? item.statusLabel : `${item.count} 筆`}</span>
    </div>)}</div>
    <p className="mt-3 text-[11px] leading-5 text-slate-500">數量僅反映目前 API 可取得的分類結果；缺少資料不會補成 0，也不會重新加權。</p>
  </section>;
}
