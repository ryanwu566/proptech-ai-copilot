import type { PropertyCaseWorkspace } from "./workspace-model";
import type { RoomRead } from "../decision-room-store";
import type { ExperienceLocale } from "../experience-i18n";
// @ts-expect-error Native TS runner extension.
import { casePulseCopy, type PulseMessage } from "./case-pulse-copy.ts";

type PulseSection = "location" | "market" | "risk" | "money" | "decision";
type PulseState = "known" | "available" | "needs_attention" | "not_queried" | "unavailable";
type PulseItem = { section: PulseSection; state: PulseState; message: PulseMessage; href: string; counts?: Record<string, number> };
export type CasePulseModel = { items: PulseItem[]; activity: { section: PulseSection | "nearby"; at: string } | null };

function reliableTimestamp(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value))) return false;
  const day = new Date(`${value.slice(0, 10)}T00:00:00Z`);
  return Number.isFinite(day.getTime()) && day.toISOString().slice(0, 10) === value.slice(0, 10) && Number(value.slice(11, 13)) < 24;
}

/** Pure saved-state projection. No storage writers, provider clients, queries or calculations. */
export function buildCasePulse(workspace: PropertyCaseWorkspace, roomRead: RoomRead): CasePulseModel {
  const base = `/cases/${encodeURIComponent(workspace.caseId)}`;
  const item = (section: PulseSection, state: PulseState, message: PulseMessage, counts?: Record<string, number>): PulseItem => ({ section, state, message, href: `${base}/${section === "money" ? "finance" : section === "decision" ? "decision-room" : section}`, ...(counts ? { counts } : {}) });
  const nearby = workspace.location.nearbyFacilities;
  const location = workspace.identity.state === "confirmed"
    ? item("location", "known", nearby ? nearby.partial ? "nearbyLimited" : "nearbySaved" : "located")
    : ["conflict", "revalidation_required"].includes(workspace.identity.state)
      ? item("location", "needs_attention", "reconfirm") : item("location", "not_queried", "unconfirmed");
  const marketStatus = workspace.marketPrice.market.status;
  const market = marketStatus === "not_started" ? item("market", "not_queried", "notQueried")
    : marketStatus === "unavailable" ? item("market", "unavailable", "unavailable")
      : marketStatus === "stale" || marketStatus === "insufficient" ? item("market", "needs_attention", marketStatus)
        : item("market", "available", marketStatus === "limited" ? "limited" : "available");
  const risk = workspace.risk;
  const riskItem = risk?.freshness.status === "stale" ? item("risk", "needs_attention", "stale")
    : risk && (risk.materialEvidenceCount > 0 || risk.verificationActions.length > 0)
      ? item("risk", "needs_attention", "riskReview", { matched: risk.materialEvidenceCount, verification: risk.verificationActions.length, unknown: risk.unknownEvidenceCount })
      : risk && risk.rows.length > 0 && risk.unknownEvidenceCount === 0 && risk.rows.every((row) => row.usability === "no_match") ? item("risk", "available", "noMatch")
        : !risk && workspace.evidence.risk.query === "not_started" ? item("risk", "not_queried", "notQueried") : item("risk", "needs_attention", "unknown");
  const finance = workspace.finance;
  const money = finance?.freshness.status === "stale" || finance?.calculation.usability === "stale" ? item("money", "needs_attention", "stale")
    : finance?.calculation.usability === "unavailable" || finance?.calculation.query === "failed" || workspace.evidence.finance.query === "failed" ? item("money", "unavailable", "unavailable")
      : finance && ["insufficient", "blocked"].includes(finance.calculation.completeness) ? item("money", "needs_attention", "insufficient")
        : finance?.calculation.query === "succeeded" ? item("money", "available", "moneySaved") : item("money", "not_queried", "notQueried");
  const room = roomRead.status === "ready" || roomRead.status === "empty" ? roomRead.room : null;
  const outstanding = room ? room.items.filter((row) => row.status === "open").length + room.verifications.filter((row) => row.outcome === "needs_follow_up").length : null;
  const decision = outstanding === null ? item("decision", "unavailable", "unavailable")
    : outstanding > 0 ? item("decision", "needs_attention", "outstanding", { outstanding })
      : item("decision", "known", room!.items.length || room!.verifications.length ? "noOpenActions" : "noActions");
  const candidates: Array<{ section: PulseSection | "nearby"; at: string | null | undefined }> = [
    { section: "location", at: workspace.location.property.checkedAt },
    { section: "market", at: workspace.evidence.market.checkedAt },
    { section: "nearby", at: nearby?.checkedAt },
    { section: "risk", at: risk?.freshness.checkedAt },
    { section: "money", at: finance?.freshness.calculatedAt },
    { section: "decision", at: room?.updatedAt },
  ];
  const latest = candidates.filter((row): row is { section: PulseSection | "nearby"; at: string } => reliableTimestamp(row.at))
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at))[0] ?? null;
  return { items: [location, market, riskItem, money, decision], activity: latest };
}

export function presentCasePulse(model: CasePulseModel, locale: ExperienceLocale) {
  const copy = casePulseCopy[locale];
  return {
    title: copy.title,
    items: model.items.map((row) => ({ ...row, label: copy[row.section], text: Object.entries(row.counts ?? {}).reduce((text, [key, value]) => text.replaceAll(`{${key}}`, new Intl.NumberFormat(locale).format(value)), copy[row.message]) })),
    activity: model.activity ? copy[model.activity.section === "decision" ? "roomActivity" : "evidenceActivity"].replace("{section}", copy[model.activity.section]) : null,
  };
}
