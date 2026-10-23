"use client";

import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { Message } from "@/components/design-system/message";
import { Section } from "@/components/design-system/section";
import { MetricItem, MetricRow, SummaryStrip } from "@/components/design-system/summary-strip";
import { StatusLabel } from "@/components/design-system/status-label";
import { formatDistance, formatDuration, formatExactDate, formatMonthlyTwd } from "@/lib/commercial/formatters";
import { buildWorkspaceOverview, type OverviewItem, type WorkspaceOverviewModel } from "@/lib/workspace/overview-model";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { OverviewSection } from "./overview-section";
import styles from "./overview-view.module.css";
import { financePriceSourceLabel } from "@/lib/finance-price-provenance";
import { ChecklistView } from "@/components/evidence/checklist-view";

import { useExperienceLocale } from "@/components/experience-locale-provider";
import { resolveTaskReadiness } from "@/lib/commercial/readiness";
import { overviewViewCopy, presentOverviewItem, hazardName, presentRiskResult, presentWanText, presentMissingCost, presentMonthlyTwd, presentDistance, presentDuration, readinessDetailFor } from "@/lib/workspace/overview-presentation";

function useOverviewCopy() {
  const { locale, copyFrom } = useExperienceLocale();
  const c = (key: keyof typeof overviewViewCopy.en, values?: Record<string, string>) => copyFrom(overviewViewCopy, key, values);
  const fresh = (key: WorkspaceOverviewModel["domains"]["market"]["freshness"]) => c(`fresh_${key}`);
  return { locale, c, fresh };
}

export function OverviewView() {
  const { locale, c, fresh } = useOverviewCopy();
  const workspace = useWorkspace();
  const overview = buildWorkspaceOverview(workspace);
  return <div className={styles.page} data-testid="commercial-overview-workspace">
    <header className="workspace-view__heading">
      <p className="text-meta">{c("eyebrow", { revision: String(workspace.revision) })}</p>
      <h1 className="text-page">{c("title")}</h1>
      <p className="text-body">{c("intro")}</p>
    </header>

    {/* Readiness first: one line a buyer reads before anything else. */}
    <SummaryStrip label={c("statusLabel")} className={styles.readiness}>
      <MetricItem label={c("readinessLabel")} value={<StatusLabel semanticRole={overview.readiness.role}>{(locale === "zh-TW" ? overview.readiness : resolveTaskReadiness(overview.readiness.task, overview.readiness.value, readinessDetailFor(locale, workspace.identity.state === "unconfirmed" && workspace.identity.anchor === null))).label[locale]}</StatusLabel>} note={c("readinessNote", { count: String(overview.unresolvedCount) })} />
    </SummaryStrip>

    <Section title={c("decisionTitle")} description={c("decisionDescription")}>
      <div className={styles.decisionGrid}>
        <DecisionGroup title={c("attention")} items={[...overview.blockers, ...overview.attention]} empty={c("attentionEmpty")} />
        <DecisionGroup title={c("known")} items={overview.known} empty={c("knownEmpty")} />
        <DecisionGroup title={c("unknown")} items={overview.unknown} empty={c("unknownEmpty")} />
      </div>
    </Section>

    {/* Supporting context: four quieter domain summaries below the decision summary. */}
    <div className={styles.domains}>
      <MarketSummary model={overview} />
      <LocationSummary model={overview} />
      <RiskSummary model={overview} />
      <FinanceSummary model={overview} />
    </div>

    <ChecklistView key={workspace.caseId} workspace={workspace} />

    <Section title={c("saveTitle")} description={c("saveDescription")}>
      <div className={styles.savePanel}>
        <p className="text-dense">{c("saveNote")}</p>
        <DetailsDisclosure summary={c("saveDisclosure")}>
          <dl className={styles.provenance}>
            <div><dt>{c("savedAt")}</dt><dd>{formatExactDate(overview.snapshot.savedAt)}</dd></div>
            <div><dt>{c("marketDomain")}</dt><dd>{fresh(overview.domains.market.freshness)}</dd></div>
            <div><dt>{c("locationDomain")}</dt><dd>{fresh(overview.domains.location.freshness)}</dd></div>
            <div><dt>{c("riskDomain")}</dt><dd>{fresh(overview.domains.risk.freshness)}</dd></div>
            <div><dt>{c("financeDomain")}</dt><dd>{fresh(overview.domains.finance.freshness)}</dd></div>
            <div><dt>{c("identityBoundary")}</dt><dd>{c("identityBoundaryText")}</dd></div>
          </dl>
        </DetailsDisclosure>
      </div>
    </Section>

    <Section title={c("nextTitle")}><DecisionGroup title={c("next")} items={overview.actions} empty={c("nextEmpty")} links /></Section>
  </div>;
}

function DecisionGroup({ title, items, empty, links = false }: { title: string; items: OverviewItem[]; empty: string; links?: boolean }) {
  const { locale, c } = useOverviewCopy();
  return <section className={styles.decisionGroup}>
    <h3 className="text-subsection">{title}</h3>
    {items.length ? <ul className={styles.list}>{items.map((entry) => <li key={entry.id}>
      <strong>{presentOverviewItem(entry, locale).label}</strong><p className="text-dense">{presentOverviewItem(entry, locale).reason}</p>
      {links && <a href={entry.href}>{c("goTo", { section: c(`section_${entry.section}`) })}</a>}
    </li>)}</ul> : <p className="text-dense">{empty}</p>}
  </section>;
}

function MarketSummary({ model }: { model: WorkspaceOverviewModel }) {
  const { locale, c, fresh } = useOverviewCopy();
  const basis = useWorkspace().assumptions.activePriceBasis;
  const market = model.domains.market;
  return <OverviewSection title={c("marketTitle")} description={c("marketDescription")} href={market.href} linkLabel={c("marketLink")} testId="overview-market-summary">
    <div className={styles.metricRows}>
      <MetricRow label={c("asking")} value={market.askingPrice ? presentWanText(market.askingPrice.formatted, locale) : c("notProvided")} />
      <MetricRow label={c("activePrice", { label: locale === "zh-TW" ? market.activePrice.label : c(`basis_${basis}`) })} value={presentWanText(market.activePrice.formatted, locale)} />
      <MetricRow label={c("marketMedian")} value={market.marketMedianUnit ? presentWanText(market.marketMedianUnit.formatted, locale) : c("notYet")} />
      <MetricRow label={c("estimateRange")} value={(market.estimateRange ? presentWanText(market.estimateRange, locale) : null) ?? (market.valuationStatus === "unavailable" ? c("estimateUnavailable") : c("notYet"))} />
    </div>
    <StatusLabel semanticRole={market.freshness === "stale" || market.freshness === "unavailable" || market.freshness === "partial" ? "warning" : "information"}>{fresh(market.freshness)}</StatusLabel>
  </OverviewSection>;
}

function LocationSummary({ model }: { model: WorkspaceOverviewModel }) {
  const { locale, c, fresh } = useOverviewCopy();
  const location = model.domains.location;
  const modeKey = `mode_${location.route?.mode}`;
  const mode = Object.hasOwn(overviewViewCopy[locale], modeKey) ? c(modeKey as keyof typeof overviewViewCopy.en) : c("otherMode");
  return <OverviewSection title={c("locationTitle")} description={c("locationDescription")} href={location.href} linkLabel={c("locationLink")} testId="overview-location-summary">
    {location.route ? <div className={styles.routeSummary}>
      <strong>{c("routeSaved", { destination: location.route.destination })}</strong>
      <p>{(locale === "zh-TW" ? formatDuration(location.route.durationMinutes) : presentDuration(location.route.durationMinutes, locale))} · {(locale === "zh-TW" ? formatDistance(location.route.distanceM) : presentDistance(location.route.distanceM, locale))} · {mode}</p>
    </div> : <p className="text-body">{c("routeNone")}</p>}
    {location.secondaryTransitStatus === "unavailable" && <Message variant="warning">{c("transitUnavailable")}</Message>}
    <StatusLabel semanticRole={location.freshness === "stale" ? "warning" : "information"}>{fresh(location.freshness)}</StatusLabel>
  </OverviewSection>;
}

function RiskSummary({ model }: { model: WorkspaceOverviewModel }) {
  const { locale, c, fresh } = useOverviewCopy();
  const risk = model.domains.risk;
  return <OverviewSection title={c("riskTitle")} description={c("riskDescription")} href={risk.href} linkLabel={c("riskLink")} testId="overview-risk-summary">
    <div className={styles.metricRows}>
      {risk.materialMatchedEvidence.map((row) => <MetricRow key={row.key} label={hazardName(row.key, locale, row.label)} value={presentRiskResult(row.result, locale)} />)}
      {risk.noMatchEvidence.map((row) => <MetricRow key={row.key} label={c("riskNoMatch", { label: hazardName(row.key, locale, row.label) })} value={presentRiskResult(row.result, locale)} />)}
      {risk.unknownOrUnavailableEvidence.map((row) => <MetricRow key={row.key} label={c("riskUnknown", { label: hazardName(row.key, locale, row.label) })} value={presentRiskResult(row.result, locale)} />)}
    </div>
    {!risk.materialMatchedEvidence.length && !risk.noMatchEvidence.length && !risk.unknownOrUnavailableEvidence.length && <p className="text-body">{c("riskNone")}</p>}
    <StatusLabel semanticRole={risk.freshness === "stale" || risk.freshness === "unavailable" ? "warning" : "information"}>{fresh(risk.freshness)}</StatusLabel>
  </OverviewSection>;
}

function FinanceSummary({ model }: { model: WorkspaceOverviewModel }) {
  const { locale, c, fresh } = useOverviewCopy();
  const finance = model.domains.finance;
  return <OverviewSection title={c("financeTitle")} description={c("financeDescription")} href={finance.href} linkLabel={c("financeLink")} testId="overview-finance-summary">
    <div className={styles.metricRows}>
      <MetricRow label={c("priceBasis")} value={(locale === "zh-TW" ? financePriceSourceLabel(finance.priceSource) : c(`source_${finance.priceSource ?? "none"}`))} />
      <MetricRow label={c("monthlyPayment")} value={finance.freshness === "stale" ? c("staleSnapshot") : (locale === "zh-TW" ? formatMonthlyTwd(finance.monthlyPaymentTwd) : presentMonthlyTwd(finance.monthlyPaymentTwd, locale))} />
      <MetricRow label={c("monthlyHousing")} value={finance.freshness === "stale" ? c("staleSnapshot") : (locale === "zh-TW" ? formatMonthlyTwd(finance.knownRecurringMonthlyTwd) : presentMonthlyTwd(finance.knownRecurringMonthlyTwd, locale))} />
      <MetricRow label={c("affordability")} value={finance.affordabilityStatus === "stale" ? c("staleAssessment") : finance.affordabilityStatus === "assessed" ? c("assessed") : c("unassessed")} />
    </div>
    {finance.freshness === "stale" && <Message variant="warning">{c("financeStale")}</Message>}
    {finance.freshness !== "stale" && finance.calculationStatus === "succeeded" && finance.affordabilityStatus === "unassessed" && <Message variant="warning">{c("financeUnassessed")}</Message>}
    {finance.missingCosts.length > 0 && <ul className={styles.compactList}>{finance.missingCosts.map((cost) => <li key={cost}>{presentMissingCost(cost, locale)}</li>)}</ul>}
    <StatusLabel semanticRole={finance.freshness === "stale" ? "warning" : "information"}>{fresh(finance.freshness)}</StatusLabel>
  </OverviewSection>;
}
