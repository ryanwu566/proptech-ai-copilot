import type { ReleaseReadinessSummary } from "@/lib/release-readiness";

type Props = { summary: ReleaseReadinessSummary };

const tone: Record<ReleaseReadinessSummary["state"], string> = {
  ready: "border-emerald-200 bg-emerald-50 text-emerald-900",
  partial: "border-amber-200 bg-amber-50 text-amber-900",
  blocked: "border-rose-200 bg-rose-50 text-rose-900",
};

export function ReleaseReadinessNotice({ summary }: Props) {
  return (
    <section className={`rounded-xl border p-4 ${tone[summary.state]}`} aria-label="Release readiness" role="status" aria-live="polite">
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="mt-1 h-2.5 w-2.5 rounded-full bg-current" />
        <div>
          <p className="text-xs font-bold uppercase tracking-wide">{summary.label}</p>
          <p className="mt-1 text-sm leading-6">{summary.detail}</p>
        </div>
      </div>
    </section>
  );
}
