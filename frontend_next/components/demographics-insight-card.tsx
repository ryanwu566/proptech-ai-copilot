"use client";

import type { ReactNode } from "react";
import type { DemographicsAvailable, DemographicsInsight, VillageResolution } from "@/lib/api";
import { SectionCard, MetricTile } from "@/components/product-ui";
import { Notice } from "@/components/ui";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { villageDemographicsCopy, type VillageDemographicsCopyKey } from "@/lib/workspace/village-demographics-copy";
import {
  demographicsFreshness,
  demographicsViewState,
  formatBoundaryVintage,
  formatDemographicsCount,
  formatDemographicsMonth,
  formatDemographicsRatio,
  formatDemographicsSignedCount,
  formatDemographicsSignedRatio,
  formatHouseholdSizeValue,
  hasSufficientTrend,
  type DemographicsViewState,
} from "@/lib/workspace/village-demographics";

// Presentation rules: ratio null -> localized "insufficient" (never 0), ratio 0 -> "0.0%" (a real observed
// value). No filling, interpolation, forecasting or smoothing. Raw RIS keys, village codes and backend
// reason codes are never rendered.

type Copy = (key: VillageDemographicsCopyKey, values?: Record<string, string | number>) => string;
/** Workspace-only states that exist before or around an acquisition. */
export type DemographicsPendingState = "loading" | "not_run" | "confirm_first";

const STATE_TEST_IDS: Record<Exclude<DemographicsViewState, "available">, (village?: VillageResolution) => string> = {
  unavailable: (village) => village?.status === "unavailable" ? "demographics-village-unavailable" : "demographics-unavailable",
  unresolved: () => "demographics-village-unresolved",
  ambiguous: () => "demographics-village-ambiguous",
  no_data: () => "demographics-no-data",
};

function CardShell({ copy, state, children, action }: { copy: Copy; state: string; children: ReactNode; action?: ReactNode }) {
  return (
    <SectionCard title={copy("title")} description={copy("description")}>
      <div data-testid="demographics-insight" data-demographics-state={state} className="min-w-0 space-y-4 [overflow-wrap:anywhere]">
        {children}
        {action}
      </div>
    </SectionCard>
  );
}

function CaveatFooter({ copy, auditFlagged }: { copy: Copy; auditFlagged?: boolean }) {
  return (
    <div className="space-y-2">
      {auditFlagged && (
        <div data-testid="demographics-audit-warning" className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
          {copy("auditWarning")}
        </div>
      )}
      <ul className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] leading-5 text-slate-500">
        {(["caveatOfficial", "caveatBoundary", "caveatIdentity", "caveatNotAdvice"] as const).map((key) => (
          <li key={key} className="break-words">• {copy(key)}</li>
        ))}
      </ul>
    </div>
  );
}

function AdministrativeHeader({ copy, village }: { copy: Copy; village: VillageResolution }) {
  const rows = [["county", village.county], ["district", village.town], ["village", village.village]] as const;
  return (
    <div className="rounded-xl border border-stone-200 bg-stone-50 px-4 py-3">
      <p className="text-xs font-semibold text-slate-500">{copy("adminTitle")}</p>
      <dl data-testid="demographics-admin-location" className="mt-2 grid min-w-0 grid-cols-1 gap-2 min-[420px]:grid-cols-3">
        {rows.map(([key, value]) => (
          <div key={key} className="min-w-0" data-testid={`demographics-admin-${key}`}>
            <dt className="text-[10px] font-semibold text-slate-500">{copy(key)}</dt>
            <dd className="break-words text-base font-bold text-slate-900">{value ?? copy("insufficient")}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function SourceFooter({ copy, village, insight, checkedAt }: { copy: Copy; village?: VillageResolution; insight?: DemographicsAvailable; checkedAt?: string }) {
  const { locale, formatDate } = useExperienceLocale();
  const vintage = formatBoundaryVintage(village?.source_vintage, locale);
  const freshness = insight ? demographicsFreshness(insight) : undefined;
  return (
    <dl data-testid="demographics-source" className="grid min-w-0 gap-2 rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs text-slate-600 sm:grid-cols-2">
      <div className="min-w-0">
        <dt className="font-semibold text-slate-500">{copy("sourceLabel")}</dt>
        <dd className="break-words">{copy("sourceValue")}</dd>
        {vintage && <dd className="break-words text-[10px] text-slate-500">{copy("boundaryVintage", { date: vintage })}</dd>}
      </div>
      <div className="min-w-0">
        <dt className="font-semibold text-slate-500">{copy("freshnessLabel")}</dt>
        {freshness && <dd data-testid="demographics-freshness" data-freshness={freshness.kind} className="break-words">
          {freshness.kind === "unknown" ? copy("freshUnknown") : copy(freshness.kind === "stale" ? "freshStale" : "freshCurrent", { months: freshness.months ?? 0 })}
        </dd>}
        {checkedAt && Number.isFinite(Date.parse(checkedAt)) && <dd className="break-words text-[10px] text-slate-500">{copy("checkedAt", { date: formatDate(checkedAt) })}</dd>}
      </div>
    </dl>
  );
}

export function DemographicsInsightCard({
  village,
  demographics,
  checkedAt,
  pending,
  action,
  loading = false,
}: {
  village?: VillageResolution;
  demographics?: DemographicsInsight;
  checkedAt?: string;
  pending?: DemographicsPendingState;
  action?: ReactNode;
  loading?: boolean;
}) {
  const { copyFrom, locale } = useExperienceLocale();
  const copy: Copy = (key, values) => copyFrom(villageDemographicsCopy, key, values);
  const orInsufficient = (value: string | null) => value ?? copy("insufficient");
  const pendingState = loading ? "loading" : pending;

  if (pendingState) {
    return (
      <CardShell copy={copy} state={pendingState} action={action}>
        <div data-testid={`demographics-${pendingState === "loading" ? "loading" : pendingState === "not_run" ? "not-run" : "confirm-first"}`} role="status"
          className="grid min-h-24 place-items-center rounded-xl border border-dashed border-stone-300 bg-stone-50 px-4 text-center text-sm text-slate-500">
          {copy(pendingState === "loading" ? "loading" : pendingState === "not_run" ? "notRun" : "confirmFirst")}
        </div>
      </CardShell>
    );
  }

  // Every outcome renders a state; a missing payload is "unavailable", never a silently absent section.
  const state = demographicsViewState(village, demographics);
  if (state !== "available" || demographics?.status !== "available") {
    const fallback = state === "available" ? "unavailable" : state;
    const count = village?.candidate_count;
    const message = fallback === "ambiguous"
      ? typeof count === "number" ? copy("stateAmbiguousCount", { count }) : copy("stateAmbiguous")
      : copy(fallback === "unresolved" ? "stateUnresolved" : fallback === "no_data" ? "stateNoData" : "stateUnavailable");
    return (
      <CardShell copy={copy} state={fallback} action={action}>
        <div data-testid={STATE_TEST_IDS[fallback](village)}><Notice tone="warning">{message}</Notice></div>
        <SourceFooter copy={copy} village={village} checkedAt={checkedAt} />
        <CaveatFooter copy={copy} />
      </CardShell>
    );
  }

  const auditFlagged = Array.isArray(demographics.audit_reasons) && demographics.audit_reasons.length > 0;
  const trendLabel = copy(demographics.trend_status === "increasing" ? "trendIncreasing" : demographics.trend_status === "decreasing" ? "trendDecreasing" : "trendStable");
  const household = formatHouseholdSizeValue(demographics.average_household_size);

  return (
    <CardShell copy={copy} state="available" action={action}>
      {village?.status === "resolved" && <AdministrativeHeader copy={copy} village={village} />}

      <div data-testid="demographics-available" className="space-y-4">
        <div className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs text-slate-600">
          {copy("statisticMonth")}：
          <span data-testid="demographics-statistic-month" className="font-bold text-slate-900">
            {orInsufficient(formatDemographicsMonth(demographics.statistic_yyymm, locale))}
          </span>
        </div>

        {/* 1 col at 390px, 2 cols from 420px, 3 cols on wide screens. */}
        <div className="grid min-w-0 grid-cols-1 gap-3 min-[420px]:grid-cols-2 xl:grid-cols-3">
          <MetricTile label={copy("population")} value={orInsufficient(formatDemographicsCount(demographics.total_population, locale))} note={copy("populationUnit")} />
          <MetricTile label={copy("households")} value={orInsufficient(formatDemographicsCount(demographics.household_count, locale))} note={copy("householdsUnit")} />
          <MetricTile label={copy("householdSize")} value={household === null ? copy("insufficient") : copy("householdSizeValue", { value: household })} />
          <MetricTile label={copy("age0to14")} value={orInsufficient(formatDemographicsRatio(demographics.child_ratio))} />
          <MetricTile label={copy("age15to64")} value={orInsufficient(formatDemographicsRatio(demographics.working_age_ratio))} />
          <MetricTile label={copy("age65plus")} value={orInsufficient(formatDemographicsRatio(demographics.elderly_ratio))} />
        </div>

        <div data-testid="demographics-trend" className="min-w-0 rounded-xl border border-stone-200 bg-stone-50 p-3">
          <p className="text-xs font-bold text-slate-800">{copy("trendTitle")}</p>
          {hasSufficientTrend(demographics) ? (
            <div className="mt-2 space-y-2">
              <p data-testid="demographics-trend-summary" className="break-words text-xs leading-5 text-slate-600">
                {copy("trendSummary", {
                  from: orInsufficient(formatDemographicsMonth(demographics.first_month, locale)),
                  to: orInsufficient(formatDemographicsMonth(demographics.last_month, locale)),
                  count: demographics.observed_month_count,
                  trend: trendLabel,
                })}
              </p>
              <div className="grid grid-cols-1 gap-2 min-[420px]:grid-cols-3">
                <MiniStat label={copy("populationChange")} value={orInsufficient(formatDemographicsSignedCount(demographics.population_change, locale))} />
                <MiniStat label={copy("populationChangeRatio")} value={orInsufficient(formatDemographicsSignedRatio(demographics.population_change_ratio))} />
                <MiniStat label={copy("householdChange")} value={orInsufficient(formatDemographicsSignedCount(demographics.household_change, locale))} />
              </div>
              {demographics.has_month_gaps && (
                <p data-testid="demographics-month-gap-caveat" className="break-words text-[10px] leading-5 text-amber-700">{copy("monthGap")}</p>
              )}
            </div>
          ) : (
            <p data-testid="demographics-trend-insufficient" className="mt-2 text-xs leading-5 text-slate-500">{copy("trendInsufficient")}</p>
          )}
        </div>

        <SourceFooter copy={copy} village={village} insight={demographics} checkedAt={checkedAt} />
        <CaveatFooter copy={copy} auditFlagged={auditFlagged} />
      </div>
    </CardShell>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-stone-200 bg-white px-3 py-2">
      <p className="text-[10px] font-semibold text-slate-500">{label}</p>
      <p className="mt-0.5 break-words text-sm font-bold text-slate-900">{value}</p>
    </div>
  );
}
