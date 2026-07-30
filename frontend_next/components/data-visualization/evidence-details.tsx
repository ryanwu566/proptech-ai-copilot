import type { EvidenceItem } from "@/lib/market-insight-visualization";
import { EVIDENCE_DISCLOSURE_LABELS } from "@/lib/visual-storytelling-copy";

export function EvidenceDetails({ items }: { items: EvidenceItem[] }) {
  return <details className="rounded-xl border border-stone-200 bg-white">
    <summary className="cursor-pointer px-4 py-3 text-sm font-bold text-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-inset">{EVIDENCE_DISCLOSURE_LABELS.knownFields}</summary>
    <div className="border-t border-stone-100 p-4"><dl className="grid gap-2 text-xs text-slate-700 sm:grid-cols-2">{items.map((item) => <div key={item.key}><dt className="font-bold text-slate-800">{item.label}</dt><dd>{item.value}</dd></div>)}</dl></div>
  </details>;
}
