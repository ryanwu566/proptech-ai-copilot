"use client";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { compactComparableExplanation, DECISION_DIMENSIONS, type DecisionCandidate } from "@/lib/workspace/comparable-explanation";
import { comparableCopy, formatComparableValue } from "@/lib/comparable-explanation-copy";

export function ComparableExplanation({ value, report = false, stale = false }: { value: unknown; report?: boolean; stale?: boolean }) {
  const { locale } = useExperienceLocale(); const c = comparableCopy(locale);
  const trace = compactComparableExplanation(value);
  const number = (n: number) => new Intl.NumberFormat(locale).format(n);
  const limitation = <p className="text-dense">{c.selectionLimit} {c.parkingLimit} {c.missingLimit}</p>;
  const summary = trace ? <>
    {stale && <p role="status">{c.stale}</p>}
    <p className="text-body" data-testid="comparable-counts">{c.included}: {number(trace.selected_count)} · {c.considered}: {number(trace.considered_count)} · {c.excluded}: {number(trace.excluded_count)}</p>
    <p className="text-dense">{c.scope}: {c[trace.scope]} · {c.reference}: {trace.reference_period} · {c.recencyReference}: {trace.recency_reference_period}</p>
    {trace.window_start && <p className="text-dense">{c.window}: {trace.window_start}–{trace.reference_period}</p>}
    <p className="text-dense">{c.coverage}</p>
  </> : <p role="status">{c.unavailable}</p>;

  if (report) return <div data-testid="report-comparable-explanation" className="mt-3 break-words">
    <h3 className="text-subsection">{c.report}</h3>{summary}
    {trace && <><p className="text-dense">{c.orderRule}</p>{Object.entries(trace.reason_counts).length > 0 && <p className="text-dense">{c.counts}: {Object.entries(trace.reason_counts).map(([reason, n]) => `${c[reason as keyof typeof c]}: ${number(n!)}`).join("; ")}</p>}{limitation}</>}
  </div>;

  function card(row: DecisionCandidate) {
    return <article key={row.candidate_id} className="min-w-0 border-t border-[color:var(--border-subtle)] py-3" aria-label={`${row.status === "included" ? c.included : c.excluded} ${row.candidate_id}`}>
      <h4 className="text-label">{row.status === "included" ? c.included : c.excluded} · {row.transaction_period ?? c.unknown} · {row.dimensions.location.comparable}</h4>
      <ul className="list-disc pl-5 text-dense">{row.reasons.map((reason) => <li key={reason}>{reason === "scope" ? `${c.scope}: ${trace ? c[trace.scope] : c.unknown}` : c[reason]}</li>)}</ul>
      <dl className="mt-2 grid gap-3 text-dense sm:grid-cols-2 lg:grid-cols-3">
        {DECISION_DIMENSIONS.map((key) => { const d = row.dimensions[key]; return <div key={key} className="min-w-0">
          <dt className="font-semibold">{key === "community_distance" ? c.community_distance_label : c[key]} · {c[d.role]}</dt>
          <dd>{c.target}: {formatComparableValue(d.target, key, locale)} · {c.value}: {formatComparableValue(d.comparable, key, locale)}</dd>
          {d.difference !== null && <dd>{c.difference}: {formatComparableValue(d.difference, key, locale)}</dd>}
          {d.threshold && <dd>{c.threshold}: {d.threshold.map((v) => formatComparableValue(v, key, locale)).join("–")}</dd>}
        </div>; })}
      </dl>
    </article>;
  }
  return <DetailsDisclosure summary={c.title} className="mt-4 break-words" data-testid="comparable-explanation">
    {summary}
    {trace && <>
      <div data-testid="selected-comparable-explanations">{trace.selected.map(card)}</div>
      <DetailsDisclosure summary={`${c.examples} (${trace.excluded_examples.length})`} data-testid="excluded-comparable-explanations">
        <p className="text-dense">{c.bound}</p>
        <h3 className="text-subsection">{c.counts}</h3>
        <ul className="list-disc pl-5 text-dense">{Object.entries(trace.reason_counts).map(([reason, n]) => <li key={reason}>{c[reason as keyof typeof c]}: {number(n!)}</li>)}</ul>
        {trace.excluded_examples.map(card)}
      </DetailsDisclosure>
      <DetailsDisclosure summary={c.rules}>
        <ul className="list-disc pl-5 text-dense"><li>{c.eligibilityRule}</li><li>{c.geographyRule}</li><li>{c.orderRule}</li><li>{c.scoreRule}</li><li>{c.outlierRule}</li>{trace.outlier_fallback && <li>{c.fallbackRule}</li>}</ul>
        <p className="text-meta">{trace.selection_version} · {trace.version}</p>
      </DetailsDisclosure>
      <h3 className="mt-3 text-subsection">{c.limits}</h3><p className="text-dense">{c.distanceMethod}</p>{limitation}
    </>}
  </DetailsDisclosure>;
}
