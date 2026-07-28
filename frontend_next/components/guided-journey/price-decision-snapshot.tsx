import { buildPriceDecisionSnapshot } from "@/lib/price-affordability-journey";

type PriceSnapshot = ReturnType<typeof buildPriceDecisionSnapshot>;

export function PriceDecisionSnapshot({ snapshot }: { snapshot: PriceSnapshot }) {
  return <section aria-labelledby="price-decision-snapshot-heading" className="rounded-xl border border-cyan-100 bg-cyan-50/50 p-4">
    <h3 id="price-decision-snapshot-heading" className="text-base font-black text-slate-950">{snapshot.title}</h3>
    <p className="mt-1 text-xs leading-5 text-slate-600">{snapshot.description}</p>
    <dl className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      <SnapshotField label="開價" value={snapshot.askingPriceWan === undefined ? "未提供" : `${snapshot.askingPriceWan} 萬`} />
      <SnapshotField label="估價狀態" value={snapshot.officialValuationStatus} />
      <SnapshotField label="官方估價" value={snapshot.officialEstimateWan === undefined ? "尚未有可採取行動的官方估價" : `${snapshot.officialEstimateWan} 萬`} />
      <SnapshotField label="官方可比成交" value={snapshot.officialComparableCount === undefined ? "資料不足或尚未取得" : `${snapshot.officialComparableCount} 筆`} />
    </dl>
  </section>;
}

function SnapshotField({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-cyan-100 bg-white p-3"><dt className="text-[10px] font-bold text-slate-500">{label}</dt><dd className="mt-1 break-words text-sm font-bold text-slate-900">{value}</dd></div>;
}
