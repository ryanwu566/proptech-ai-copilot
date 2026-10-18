/**
 * Pure answer-first presentation of one deterministic Copilot answer.
 * Input is the answer and the context it was produced from; nothing else. No fetch,
 * storage, clock, React or provider access. Composition only re-arranges evidence that
 * is already inside `answer.used`: it never changes the status, resolves a conflict,
 * adds a number or cites a reference that does not resolve in this context.
 */
import type { AnswerStatus, CopilotAnswer, CopilotContext, CopilotEvidence, CopilotTopic } from "./grounded-copilot";
import type { EvidenceStatus } from "./case-evidence";

export const COMPOSE_LIMITS = { keyFacts: 4, missingPreview: 3, followups: 2 } as const;

export type FactOrigin = "user_entered" | "saved_source" | "saved_assumption" | "saved_calculation" | "scenario_assumption" | "user_record" | "derived";
export type KeyFact = {
  kind: "asking_unit" | "market_band" | "monthly_housing" | "commute" | "risk" | "observation";
  /** Evidence id used for the label of an observation-backed fact. */
  evidenceId: string; origin: FactOrigin; refs: string[]; states: EvidenceStatus[];
  value: number | string | null; unit: string;
  band: { low: number; high: number; unit: string } | null;
  /** Saved text context in its source language, e.g. destination and travel mode. */
  context: string[];
};
export type Headline =
  | { kind: "market_band"; position: "below" | "within" | "above"; askingUnit: number; low: number; high: number; unit: string; refs: string[] }
  | { kind: "finance_housing"; monthly: number; unit: string; incomeMissing: boolean; refs: string[] }
  | { kind: "commute"; minutes: number; unit: string; destination: string; mode: string; refs: string[] }
  | { kind: "risk"; recorded: number; noMatch: number; unresolved: number; refs: string[] }
  | { kind: "scenario_payment"; letter: string; monthly: number; unit: string; complete: boolean; refs: string[] }
  | { kind: "decision_records"; questions: number; tasks: number; refs: string[] }
  | { kind: "supported" | "partial"; used: number; missing: number; refs: string[] }
  | { kind: "insufficient" | "legal_unsupported" | "live_not_requested" | "invalid_output" | "conflict_price" | "conflict_identity"; refs: string[] };
export type NextActionKind =
  | "review_price_conflict" | "verify_identity" | "verify_legal" | "inspect_saved_dates" | "refresh_market" | "review_market" | "enter_area"
  | "enter_income" | "complete_finance" | "review_finance" | "verify_commute" | "review_risk_sources" | "review_risk"
  | "open_scenarios" | "open_decision_room" | "open_location" | "open_overview" | "inspect_missing" | "inspect_evidence" | "none";
export type NextAction = { kind: NextActionKind; href: string | null };
export type MissingItem = { ref: string; id: string; status: EvidenceStatus; href: string };
export type AnswerPresentation = {
  status: AnswerStatus; headline: Headline & { qualified: boolean };
  keyFacts: KeyFact[]; missingItems: MissingItem[]; missingTotal: number; openMissing: boolean;
  nextAction: NextAction; followups: CopilotTopic[];
  fullEvidenceRefs: string[]; provenanceRefs: string[];
};

const PRIORITY: Partial<Record<CopilotTopic, string[]>> = {
  market: ["market-p25", "market-p75", "property-area", "market-total", "market-unit", "market-samples", "market-period"],
  valuation: ["valuation-estimate", "valuation-comparables"],
  finance: ["finance-income", "finance-management", "finance-rate", "finance-repair", "finance-burden", "finance-tax"],
  commute: ["commute-duration", "commute-destination", "commute-mode", "transit-context"],
};
const STATUS_RANK: EvidenceStatus[] = ["stale", "unavailable", "not_run", "insufficient", "unsupported", "no_coverage", "limited", "no_match", "available"];
/** "If applicable" rows stay in the full list but never take a preview slot. */
const LOW_VALUE = ["finance-grace-payment", "finance-post-grace"];
const RELATED: Record<CopilotTopic, CopilotTopic[]> = {
  market: ["finance", "risk"], valuation: ["market", "finance"], finance: ["scenario", "market"], commute: ["location", "risk"],
  location: ["commute", "risk"], risk: ["location", "decision"], scenario: ["finance", "decision"], decision: ["market", "risk"],
  identity: ["market", "risk"], compare: ["market", "finance"], legal: ["market", "risk"], current: ["market", "finance"], unknown: ["market", "finance"],
};
const SECTION_ACTIONS: Partial<Record<CopilotTopic, NextActionKind>> = { commute: "verify_commute", scenario: "open_scenarios", decision: "open_decision_room", location: "open_location", identity: "open_overview" };

/** The active price may be the asking price or a valuation midpoint; its trust class is not fixed, so it is never a key fact. */
const NO_FACT = ["price-active", "price-basis"];
/** Finance inputs are saved assumptions; only computed outputs are saved calculations. */
const FINANCE_INPUTS = ["finance-price", "finance-basis", "finance-down-ratio", "finance-down", "finance-rate", "finance-term", "finance-grace", "finance-income", "finance-management", "finance-repair", "finance-home-tax", "finance-land-tax", "finance-insurance"];
function origin(row: CopilotEvidence): FactOrigin {
  if (["price-asking", "property-area"].includes(row.id)) return "user_entered";
  if (row.id.startsWith("room-")) return "user_record";
  if (row.id.startsWith("scenario-")) return "scenario_assumption";
  if (FINANCE_INPUTS.includes(row.id)) return "saved_assumption";
  if (row.id.startsWith("finance-")) return "saved_calculation";
  return "saved_source";
}

export function composeAnswer(answer: CopilotAnswer, context: CopilotContext): AnswerPresentation {
  const root = `/cases/${encodeURIComponent(context.caseId)}`;
  // A foreign or stale answer contributes nothing, not even its status.
  // Rows must be this context's own evidence objects; lookalike copies are not citations.
  const own = (row: CopilotEvidence) => context.evidence.includes(row);
  if (answer.contextKey !== context.key || !answer.used.every(own) || !answer.missing.every(own)) return closed(root);
  const byId = new Map(answer.used.map((row) => [row.id, row]));
  /** All-or-nothing: every input must be in this answer and resolve to the same context row. */
  const cite = (...rows: Array<CopilotEvidence | undefined>): string[] | null =>
    rows.every((row) => row && own(row) && answer.used.includes(row)) ? rows.map((row) => row!.ref) : null;
  const num = (id: string) => { const row = byId.get(id); return row && typeof row.value === "number" ? row : undefined; };
  const str = (id: string) => { const row = byId.get(id); return row && typeof row.value === "string" ? row : undefined; };
  const missingIds = new Set(answer.missing.map((row) => row.id));
  const primaryTopics = answer.topics;

  const headline = ((): Headline => {
    if (answer.failure) return { kind: "invalid_output", refs: [] };
    if (answer.conflicts.includes("identity")) return { kind: "conflict_identity", refs: [] };
    if (answer.conflicts.includes("asking_price")) return { kind: "conflict_price", refs: cite(byId.get("price-asking"), byId.get("room-asking")) ?? [] };
    if (primaryTopics.includes("legal")) return { kind: "legal_unsupported", refs: [] };
    if (primaryTopics.includes("current")) return { kind: "live_not_requested", refs: [] };
    if (answer.status === "insufficient_evidence" || !answer.used.length) return { kind: "insufficient", refs: [] };
    for (const topic of primaryTopics) {
      const specific = topicHeadline(topic);
      if (specific) return specific;
    }
    const kind = answer.status === "supported" ? "supported" : "partial";
    return { kind, used: answer.used.length, missing: answer.missing.length, refs: [] };
  })();

  function topicHeadline(topic: CopilotTopic): Headline | null {
    if (topic === "market") {
      const band = answer.insights.find((item) => item.kind === "asking_unit_vs_band");
      const asking = num("price-asking"); const p25 = num("market-p25");
      const refs = band && cite(...band.refs.map((ref) => answer.used.find((row) => row.ref === ref)));
      if (band && refs && asking && p25) {
        const position = band.values.position < 0 ? "below" : band.values.position > 0 ? "above" : "within";
        return { kind: "market_band", position, askingUnit: band.values.askingUnitWan, low: band.values.p25Wan, high: band.values.p75Wan, unit: p25.unit, refs };
      }
      // Without a complete unit-price band there is no like-for-like market headline;
      // a total price against a regional median total is not promoted to an answer.
    }
    if (topic === "finance") {
      const housing = num("finance-housing");
      const refs = cite(housing);
      const insight = answer.insights.find((item) => item.kind === "known_housing");
      if (housing && refs && insight) return { kind: "finance_housing", monthly: housing.value as number, unit: housing.unit, incomeMissing: !num("finance-income") || missingIds.has("finance-income"), refs };
    }
    if (topic === "commute") {
      const duration = num("commute-duration"); const destination = str("commute-destination"); const mode = str("commute-mode");
      const refs = cite(duration, destination, mode);
      if (refs) return { kind: "commute", minutes: duration!.value as number, unit: duration!.unit, destination: destination!.value as string, mode: mode!.value as string, refs };
    }
    if (topic === "risk") {
      const used = answer.used.filter((row) => row.topic === "risk");
      const refs = cite(...used);
      if (used.length && refs) return { kind: "risk", recorded: used.filter((row) => row.status !== "no_match").length, noMatch: used.filter((row) => row.status === "no_match").length, unresolved: answer.missing.filter((row) => row.topic === "risk").length, refs };
    }
    if (topic === "scenario") {
      for (const letter of ["A", "B", "C"]) {
        const payment = num(`scenario-${letter}-paymentTwd`);
        const refs = cite(payment);
        if (payment && refs) return { kind: "scenario_payment", letter, monthly: payment.value as number, unit: payment.unit, complete: payment.limitation === "scenario_assumptions", refs };
      }
    }
    if (topic === "decision") {
      const questions = num("room-open-questions"); const tasks = num("room-open-tasks");
      const refs = cite(questions, tasks);
      if (refs) return { kind: "decision_records", questions: questions!.value as number, tasks: tasks!.value as number, refs };
    }
    return null;
  }

  const keyFacts: KeyFact[] = [];
  const covered = new Set<string>();
  const fact = (kind: KeyFact["kind"], rows: Array<CopilotEvidence | undefined>, partial: Partial<KeyFact> = {}) => {
    const refs = cite(...rows);
    if (!refs || keyFacts.length >= COMPOSE_LIMITS.keyFacts || refs.every((ref) => covered.has(ref))) return;
    refs.forEach((ref) => covered.add(ref));
    const first = rows[0]!;
    keyFacts.push({ kind, evidenceId: first.id, origin: origin(first), refs, states: rows.map((row) => row!.status), value: first.value, unit: first.unit, band: null, context: [], ...partial });
  };
  if (headline.kind === "conflict_price") {
    // Both observations, in evidence order; neither is presented as correct.
    fact("observation", [byId.get("price-asking")]); fact("observation", [byId.get("room-asking")]);
  } else if (!["conflict_identity", "invalid_output", "insufficient", "legal_unsupported", "live_not_requested"].includes(headline.kind)) {
    for (const topic of primaryTopics) topicFacts(topic);
    // Fill to at least two facts with cited numeric observations in evidence order.
    for (const row of answer.used) if (keyFacts.length < 2 && typeof row.value === "number" && row.topic !== "risk" && !NO_FACT.includes(row.id)) fact("observation", [row]);
  }

  function topicFacts(topic: CopilotTopic) {
    if (topic === "market") {
      const band = answer.insights.find((item) => item.kind === "asking_unit_vs_band");
      const asking = num("price-asking"); const area = num("property-area"); const p25 = num("market-p25"); const p75 = num("market-p75");
      if (asking && area && (area.value as number) > 0 && `${asking.unit}／${area.unit}` === (p25?.unit ?? `${asking.unit}／${area.unit}`)) {
        fact("asking_unit", [asking, area], { origin: "derived", value: (asking.value as number) / (area.value as number), unit: `${asking.unit}／${area.unit}` });
      }
      if (band && p25 && p75) fact("market_band", [p25, p75], { value: null, unit: p25.unit, band: { low: band.values.p25Wan, high: band.values.p75Wan, unit: p25.unit } });
      else if (!band) fact("observation", [num("market-unit")]);
    }
    if (topic === "finance") { fact("monthly_housing", [num("finance-housing")]); fact("observation", [num("finance-price")]); fact("observation", [num("finance-rate")]); }
    if (topic === "commute") {
      const duration = num("commute-duration"); const destination = str("commute-destination"); const mode = str("commute-mode");
      if (cite(duration, destination, mode)) fact("commute", [duration, destination, mode], { context: [destination!.value as string, mode!.value as string] });
      else fact("observation", [duration]);
      fact("observation", [num("commute-distance")]);
    }
    if (topic === "risk") for (const row of answer.used.filter((item) => item.topic === "risk")) fact("risk", [row], { value: null });
    if (topic === "scenario") for (const name of ["paymentTwd", "purchaseCashTwd"]) fact("observation", [num(`scenario-A-${name}`)]);
    if (topic === "decision") for (const id of ["room-asking", "room-open-questions", "room-open-tasks"]) fact("observation", [num(id)]);
    if (topic === "valuation") fact("observation", [num("valuation-estimate")]);
    if (topic === "location") for (const id of ["poi-transit", "poi-school", "poi-convenience"]) fact("observation", [num(id)]);
  }

  const priority = primaryTopics.flatMap((topic) => PRIORITY[topic] ?? []);
  const rank = (row: CopilotEvidence) => [priority.includes(row.id) ? priority.indexOf(row.id) : priority.length, STATUS_RANK.indexOf(row.status)];
  const missingItems = answer.missing
    .map((row, index) => ({ row, index, rank: rank(row) }))
    .filter(({ row }) => !LOW_VALUE.includes(row.id))
    .sort((a, b) => a.rank[0] - b.rank[0] || a.rank[1] - b.rank[1] || a.index - b.index)
    .slice(0, COMPOSE_LIMITS.missingPreview)
    .map(({ row }) => ({ ref: row.ref, id: row.id, status: row.status, href: row.href }));

  const nextAction = ((): NextAction => {
    const href = (section: string) => `${root}/${section}`;
    if (answer.failure) return { kind: "inspect_evidence", href: href("evidence") };
    if (answer.conflicts.includes("identity")) return { kind: "verify_identity", href: href("overview") };
    if (answer.conflicts.includes("asking_price")) return { kind: "review_price_conflict", href: href("decision-room") };
    if (primaryTopics.includes("legal")) return { kind: "verify_legal", href: href("overview") };
    if (primaryTopics.includes("current")) return { kind: "inspect_saved_dates", href: href("evidence") };
    // A multi-topic question has no single owning section; its gaps are reviewed together.
    const focused = primaryTopics.filter((item) => item !== "identity" && item !== "unknown" && item !== "compare");
    if (focused.length > 2) return answer.missing.length ? { kind: "inspect_missing", href: href("evidence") } : { kind: "inspect_evidence", href: href("evidence") };
    const topic = focused[0] ?? primaryTopics[0];
    const missingIn = (prefix: string) => answer.missing.some((row) => row.id.startsWith(prefix));
    // The area is entered in Overview; market evidence is reviewed or refreshed in Market.
    if ((topic === "market" || topic === "valuation") && missingIds.has("property-area") && !missingIn("market-")) return { kind: "enter_area", href: href("overview") };
    if (topic === "market" || topic === "valuation") return { kind: missingIn("market-") || missingIn("valuation-estimate") ? "refresh_market" : "review_market", href: href("market") };
    if (topic === "finance") return { kind: missingIds.has("finance-income") ? "enter_income" : answer.missing.some((row) => row.topic === "finance" && !LOW_VALUE.includes(row.id)) ? "complete_finance" : "review_finance", href: href("finance") };
    if (topic === "risk") return { kind: answer.missing.some((row) => row.topic === "risk") ? "review_risk_sources" : "review_risk", href: href("risk") };
    const section = topic && SECTION_ACTIONS[topic];
    if (section) return { kind: section, href: href(({ verify_commute: "location", open_scenarios: "scenarios", open_decision_room: "decision-room", open_location: "location", open_overview: "overview" } as Record<string, string>)[section]) };
    if (missingItems.length) return { kind: "inspect_missing", href: href("evidence") };
    return { kind: "none", href: null };
  })();

  // One topic suggests related topics; several topics suggest narrowing to one of them.
  const drill: CopilotTopic[] = ["market", "finance", "risk", "commute"];
  const followups = (primaryTopics.length > 1 ? drill.filter((topic) => primaryTopics.includes(topic)) : RELATED[primaryTopics[0] ?? "unknown"].filter((topic) => !primaryTopics.includes(topic))).slice(0, COMPOSE_LIMITS.followups);
  const refs = answer.used.filter((row) => cite(row)).map((row) => row.ref);
  return {
    status: answer.status, headline: { ...headline, qualified: answer.status === "partially_supported" },
    keyFacts, missingItems, missingTotal: answer.missing.length, openMissing: answer.status === "insufficient_evidence" || !answer.used.length,
    nextAction, followups, fullEvidenceRefs: refs, provenanceRefs: refs,
  };
}

function closed(root: string): AnswerPresentation {
  return { status: "insufficient_evidence", headline: { kind: "insufficient", refs: [], qualified: false }, keyFacts: [], missingItems: [], missingTotal: 0, openMissing: true, nextAction: { kind: "inspect_evidence", href: `${root}/evidence` }, followups: [], fullEvidenceRefs: [], provenanceRefs: [] };
}
