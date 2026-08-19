"use client";

import { buildPriceDecisionSnapshot } from "@/lib/price-affordability-journey";
import { useExperienceLocale } from "@/components/experience-locale-provider";

type PriceSnapshot = ReturnType<typeof buildPriceDecisionSnapshot>;

export function PriceDecisionSnapshot({ snapshot }: { snapshot: PriceSnapshot }) {
  const { copy } = useExperienceLocale();
  return <section aria-labelledby="price-decision-snapshot-heading" className="rounded-xl border border-cyan-100 bg-cyan-50/50 p-4">
    <h3 id="price-decision-snapshot-heading" className="text-base font-black text-slate-950">{snapshot.title}</h3>
    <p className="mt-1 text-xs leading-5 text-slate-600">{snapshot.description}</p>
    <dl className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      <SnapshotField label={copy("journey.priceSnapshotAskingPrice")} value={snapshot.askingPriceWan === undefined ? copy("journey.priceSnapshotNotProvided") : `${snapshot.askingPriceWan}`} />
      <SnapshotField label={copy("journey.priceSnapshotValuationStatus")} value={snapshot.officialValuationStatus} />
      <SnapshotField label={copy("journey.priceSnapshotOfficialEstimate")} value={snapshot.officialEstimateWan === undefined ? copy("journey.priceSnapshotNoEstimate") : `${snapshot.officialEstimateWan}`} />
      <SnapshotField label={copy("journey.priceSnapshotComparables")} value={snapshot.officialComparableCount === undefined ? copy("journey.priceSnapshotInsufficient") : `${snapshot.officialComparableCount}`} />
    </dl>
  </section>;
}

function SnapshotField({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-cyan-100 bg-white p-3"><dt className="text-[10px] font-bold text-slate-500">{label}</dt><dd className="mt-1 break-words text-sm font-bold text-slate-900">{value}</dd></div>;
}
