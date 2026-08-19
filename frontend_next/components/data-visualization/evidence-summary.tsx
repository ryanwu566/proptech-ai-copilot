"use client";

import type { EvidenceItem } from "@/lib/market-insight-visualization";
import { EVIDENCE_DISCLOSURE_LABELS } from "@/lib/visual-storytelling-copy";
import { ExperienceStatePanel } from "@/components/experience-state-panel";
import { useExperienceLocale } from "@/components/experience-locale-provider";

const SUMMARY_KEYS = new Set(["source_name", "source_updated_at", "period", "transaction_count", "coverage_status", "data_status"]);

export function EvidenceSummary({ items }: { items: EvidenceItem[] }) {
  const { copy } = useExperienceLocale();
  const summaryItems = items.filter((item) => SUMMARY_KEYS.has(item.key));
  if (!summaryItems.length) return <ExperienceStatePanel state="not_assessed" title={copy("viz.evidenceEmptyTitle")} explanation={copy("viz.evidenceEmptyExplanation")} nextAction={copy("viz.evidenceEmptyNextAction")} />;
  return <section data-evidence-summary="true" aria-labelledby="market-evidence-summary-heading" className="rounded-xl border border-cyan-100 bg-cyan-50/50 p-4">
    <h3 id="market-evidence-summary-heading" className="text-sm font-bold text-slate-900">{copy("viz.evidenceHeading")}</h3>
    <p className="mt-1 text-xs leading-5 text-slate-600">{copy("viz.evidenceDescription")}</p>
    <dl className="mt-3 grid gap-2 text-xs text-slate-700 sm:grid-cols-2">{summaryItems.map((item) => <div key={item.key}><dt className="font-bold text-slate-800">{item.label}</dt><dd className="break-words">{item.value}</dd></div>)}</dl>
  </section>;
}
