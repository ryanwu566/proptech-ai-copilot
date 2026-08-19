"use client";

import type { JourneyAffordabilityContext } from "@/lib/price-affordability-journey";
import { buildAffordabilityDecisionSnapshot } from "@/lib/price-affordability-journey";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function AffordabilityDecisionSnapshot({ context }: { context: JourneyAffordabilityContext }) {
  const { copy } = useExperienceLocale();
  const snapshot = buildAffordabilityDecisionSnapshot(context);
  return <section aria-labelledby="affordability-snapshot-heading" className="rounded-xl border border-violet-100 bg-violet-50/50 p-4">
    <h3 id="affordability-snapshot-heading" className="text-base font-black text-slate-950">{snapshot.title}</h3>
    <p className="mt-1 text-xs leading-5 text-slate-600">{snapshot.description}</p>
    <dl className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{[
      [copy("journey.affordSnapshotPrice"), snapshot.propertyPriceWan === undefined ? copy("journey.affordSnapshotNotProvided") : `${snapshot.propertyPriceWan}`],
      [copy("journey.affordSnapshotDown"), snapshot.downPaymentWan === undefined ? copy("journey.affordSnapshotNotCalculated") : `${snapshot.downPaymentWan}`],
      [copy("journey.affordSnapshotLoan"), snapshot.loanAmountWan === undefined ? copy("journey.affordSnapshotNotCalculated") : `${snapshot.loanAmountWan}`],
      [copy("journey.affordSnapshotMonthly"), snapshot.monthlyPayment === undefined ? copy("journey.affordSnapshotNotCalculated") : `${snapshot.monthlyPayment}`],
      [copy("journey.affordSnapshotHolding"), snapshot.monthlyHoldingCost === undefined ? copy("journey.affordSnapshotNotCalculated") : `${snapshot.monthlyHoldingCost}`],
      [copy("journey.affordSnapshotBurden"), snapshot.incomeBurdenRatio === undefined ? copy("journey.affordSnapshotBurdenNotAssessed") : copy("journey.affordSnapshotBurdenAvailable")],
      ["TaxOracle", snapshot.taxOracleStatus],
      [copy("journey.affordSnapshotMissing"), snapshot.missingDataLabels.length ? snapshot.missingDataLabels.join(", ") : copy("journey.affordSnapshotMissingNone")],
    ].map(([label, value]) => <SnapshotField key={label} label={label} value={value} />)}</dl>
  </section>;
}

function SnapshotField({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-violet-100 bg-white p-3"><dt className="text-[10px] font-bold text-slate-500">{label}</dt><dd className="mt-1 break-words text-sm font-bold text-slate-900">{value}</dd></div>;
}
