"use client";

import type { LoanVisualModel } from "@/lib/loan-visualization";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function CalculationEvidenceDetails({ model }: { model: LoanVisualModel }) {
  const { copy } = useExperienceLocale();
  return <DetailDisclosure title={copy("viz.loanEvidenceTitle")}><div className="space-y-3 text-xs text-slate-700"><dl className="grid gap-2 sm:grid-cols-2">{model.evidence.map((item) => <div key={item.key}><dt className="font-bold text-slate-800">{item.label}</dt><dd>{item.value}</dd></div>)}</dl><div className="max-w-full overflow-x-auto"><table className="w-full min-w-[620px] text-left"><thead><tr className="bg-stone-50"><th className="p-2">{copy("viz.loanSensitivityRate")}</th><th>{copy("viz.loanSensitivityPayment")}</th><th>{copy("viz.loanSensitivityInterest")}</th><th>{copy("viz.loanSensitivityRelative")}</th></tr></thead><tbody>{model.sensitivity.map((item, index) => <tr key={`${item.annualInterestRate}-${index}`} className="border-t border-stone-100"><td className="p-2">{item.annualInterestRate}%</td><td>{item.monthlyPayment.toLocaleString()} 元</td><td>{item.totalInterest.toLocaleString()} 元</td><td>{item.differenceFromBase === 0 ? copy("viz.loanSensitivityBase") : `${item.differenceFromBase > 0 ? "+" : ""}${item.differenceFromBase.toLocaleString()} 元`}</td></tr>)}</tbody></table></div></div></DetailDisclosure>;
}
