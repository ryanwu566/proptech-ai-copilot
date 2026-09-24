"use client";

import type { ReactNode } from "react";
import type {
  DemographicsAvailable,
  DemographicsInsight,
  VillageResolution,
} from "@/lib/api";
import { SectionCard, MetricTile } from "@/components/product-ui";
import { Notice } from "@/components/ui";

// ---------------------------------------------------------------------------
// Pure formatting helpers (exported for deterministic unit testing).
// Rules:
//   ratio 0.187 -> "18.7%"
//   ratio null  -> "資料不足" (never rendered as 0)
//   ratio 0     -> "0.0%"     (a real observed value)
// No filling, interpolation, forecasting, or smoothing is performed anywhere.
// ---------------------------------------------------------------------------

export const INSUFFICIENT_LABEL = "資料不足";

export function formatRatio(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return INSUFFICIENT_LABEL;
  return `${(value * 100).toFixed(1)}%`;
}

export function formatHouseholdSize(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return INSUFFICIENT_LABEL;
  return `${value.toFixed(2)} 人`;
}

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return INSUFFICIENT_LABEL;
  return value.toLocaleString("zh-TW");
}

// Signed integer change, e.g. +120 / -45 / 0.
export function formatSignedCount(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return INSUFFICIENT_LABEL;
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toLocaleString("zh-TW")}`;
}

// Signed ratio change, e.g. +1.8% / -0.4% / null -> 資料不足.
export function formatSignedRatio(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return INSUFFICIENT_LABEL;
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(1)}%`;
}

// ROC yyymm (e.g. "11507") -> "民國115年07月". Falls back to raw text otherwise.
export function formatRocMonth(value: string | null | undefined): string {
  if (!value) return INSUFFICIENT_LABEL;
  const text = String(value).trim();
  if (/^\d{5,6}$/.test(text)) {
    const year = text.slice(0, text.length - 2);
    const month = text.slice(text.length - 2);
    return `民國${Number(year)}年${month}月`;
  }
  return text;
}

export function trendLabel(status: DemographicsAvailable["trend_status"]): string {
  switch (status) {
    case "increasing":
      return "人口增加";
    case "decreasing":
      return "人口減少";
    case "stable":
    default:
      return "人口大致持平";
  }
}

// A trend summary is only meaningful with at least two observed months.
export function hasSufficientTrend(demographics: DemographicsAvailable): boolean {
  return demographics.observed_month_count >= 2;
}

// ---------------------------------------------------------------------------
// Presentational helpers
// ---------------------------------------------------------------------------

function CardShell({ children }: { children: ReactNode }) {
  return (
    <SectionCard title="里人口概況" description="官方村里人口統計，供區位理解參考。">
      <div data-testid="demographics-insight" className="min-w-0 space-y-4">
        {children}
      </div>
    </SectionCard>
  );
}

const AUDIT_CAVEATS = [
  "官方人口統計",
  "行政界可能調整",
  "歷史比較依同一行政 identity",
  "僅供區位理解，不代表投資建議",
];

function CaveatFooter({ auditFlagged }: { auditFlagged?: boolean }) {
  return (
    <div className="space-y-2">
      {auditFlagged && (
        <div
          data-testid="demographics-audit-warning"
          className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800"
        >
          此期資料有品質註記
        </div>
      )}
      <ul className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] leading-5 text-slate-400">
        {AUDIT_CAVEATS.map((item) => (
          <li key={item} className="break-words">• {item}</li>
        ))}
      </ul>
    </div>
  );
}

function AdministrativeHeader({ village }: { village: VillageResolution }) {
  const parts = [village.county, village.town, village.village].filter(Boolean) as string[];
  const label = parts.length > 0 ? parts.join(" ") : INSUFFICIENT_LABEL;
  return (
    <div className="rounded-xl border border-stone-200 bg-stone-50 px-4 py-3">
      <p className="text-xs font-semibold text-slate-500">行政位置</p>
      <p data-testid="demographics-admin-location" className="mt-1 break-words text-base font-bold text-slate-900">
        {label}
      </p>
      {village.village_code && (
        <p className="mt-1 break-all text-[10px] text-slate-400">村里代碼 {village.village_code}</p>
      )}
    </div>
  );
}

function StateNotice({ testId, children }: { testId: string; children: ReactNode }) {
  return (
    <CardShell>
      <div data-testid={testId}>
        <Notice tone="warning">{children}</Notice>
      </div>
      <CaveatFooter />
    </CardShell>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function DemographicsInsightCard({
  village,
  demographics,
  loading = false,
}: {
  village?: VillageResolution;
  demographics?: DemographicsInsight;
  loading?: boolean;
}) {
  if (loading) {
    return (
      <CardShell>
        <div
          data-testid="demographics-loading"
          className="grid min-h-24 place-items-center rounded-xl border border-dashed border-stone-300 bg-stone-50 text-sm text-slate-500"
        >
          正在載入人口統計…
        </div>
      </CardShell>
    );
  }

  // Backward compatibility: a legacy response without demographics must not crash.
  if (!demographics && !village) return null;

  // Village resolution states take precedence when demographics cannot apply.
  if (village) {
    if (village.status === "unavailable") {
      return <StateNotice testId="demographics-village-unavailable">目前無法取得此地點的村里人口資料。</StateNotice>;
    }
    if (village.status === "unresolved") {
      return <StateNotice testId="demographics-village-unresolved">無法對應到明確的村里範圍，暫不顯示人口統計。</StateNotice>;
    }
    if (village.status === "ambiguous") {
      const count = village.candidate_count;
      return (
        <StateNotice testId="demographics-village-ambiguous">
          此位置落在多個村里交界{typeof count === "number" ? `（${count} 個候選）` : ""}，無法唯一判定，暫不顯示人口統計。
        </StateNotice>
      );
    }
  }

  if (!demographics || demographics.status === "no_data") {
    return <StateNotice testId="demographics-no-data">此村里目前沒有可用的人口統計資料。</StateNotice>;
  }

  // status === "available"
  const auditFlagged = Array.isArray(demographics.audit_reasons) && demographics.audit_reasons.length > 0;
  const sufficientTrend = hasSufficientTrend(demographics);

  return (
    <CardShell>
      {village && village.status === "resolved" ? (
        <AdministrativeHeader village={village} />
      ) : null}

      <div data-testid="demographics-available" className="space-y-4">
        <div className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs text-slate-600">
          統計月份：
          <span data-testid="demographics-statistic-month" className="font-bold text-slate-900">
            {formatRocMonth(demographics.statistic_yyymm)}
          </span>
        </div>

        {/* Metrics grid: 3 cols desktop, 2 cols small, 1 col at 390px */}
        <div className="grid min-w-0 grid-cols-1 gap-3 min-[420px]:grid-cols-2 xl:grid-cols-3">
          <MetricTile label="總人口" value={formatCount(demographics.total_population)} note="人" />
          <MetricTile label="戶數" value={formatCount(demographics.household_count)} note="戶" />
          <MetricTile label="平均每戶人口" value={formatHouseholdSize(demographics.average_household_size)} />
          <MetricTile label="0–14 歲比例" value={formatRatio(demographics.child_ratio)} />
          <MetricTile label="15–64 歲比例" value={formatRatio(demographics.working_age_ratio)} />
          <MetricTile label="65 歲以上比例" value={formatRatio(demographics.elderly_ratio)} />
        </div>

        {/* Trend */}
        <div
          data-testid="demographics-trend"
          className="min-w-0 rounded-xl border border-stone-200 bg-stone-50 p-3"
        >
          <p className="text-xs font-bold text-slate-800">近期人口變化</p>
          {sufficientTrend ? (
            <div className="mt-2 space-y-2">
              <p data-testid="demographics-trend-summary" className="break-words text-xs leading-5 text-slate-600">
                {formatRocMonth(demographics.first_month)} 至 {formatRocMonth(demographics.last_month)}
                （共 {demographics.observed_month_count} 個月）· {trendLabel(demographics.trend_status)}
              </p>
              <div className="grid grid-cols-1 gap-2 min-[420px]:grid-cols-3">
                <MiniStat label="人口變化" value={formatSignedCount(demographics.population_change)} />
                <MiniStat label="人口變化率" value={formatSignedRatio(demographics.population_change_ratio)} />
                <MiniStat label="戶數變化" value={formatSignedCount(demographics.household_change)} />
              </div>
              {demographics.has_month_gaps && (
                <p
                  data-testid="demographics-month-gap-caveat"
                  className="break-words text-[10px] leading-5 text-amber-700"
                >
                  ⚠ 觀測月份不連續，未補月、未插值。
                </p>
              )}
            </div>
          ) : (
            <p data-testid="demographics-trend-insufficient" className="mt-2 text-xs leading-5 text-slate-500">
              歷史資料不足
            </p>
          )}
        </div>

        <CaveatFooter auditFlagged={auditFlagged} />
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
