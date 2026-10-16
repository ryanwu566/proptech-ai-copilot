/** Local, deterministic authority layer. No transport, credentials, model SDK or provider imports. */
// @ts-expect-error Native TS runner extension.
import { evidenceFields, projectCaseEvidence, type EvidenceField, type EvidenceStatus } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { calculateScenario, parseScenarioSave, SCENARIO_FIELDS } from "./scenario-model.ts";
// @ts-expect-error Native TS runner extension.
import { scenarioContext } from "./scenario-context.ts";
export { scenarioContext };
import type { PropertyCaseWorkspace } from "./workspace-model";
import type { RoomRead } from "../decision-room-store";

export type CopilotTopic = "identity" | "market" | "valuation" | "finance" | "location" | "commute" | "risk" | "scenario" | "decision" | "compare" | "legal" | "current" | "unknown";
export type AnswerStatus = "supported" | "partially_supported" | "insufficient_evidence" | "conflicting_evidence";
export type CopilotEvidence = {
  id: string; ref: string; topic: CopilotTopic; label: string; value: string | number | null;
  unit: string; status: EvidenceStatus; source: string; limitation: string; href: string;
  origin: "saved_snapshot"; checkedAt: string | null; updatedAt: string | null;
  missingReason: string | null;
};
export type CopilotContext = {
  caseId: string; title: string; address: string; savedAt: string; key: string;
  identityState: PropertyCaseWorkspace["identity"]["state"];
  liveEvidence: "not_requested"; evidence: CopilotEvidence[];
  conflicts: Array<"identity" | "asking_price">;
};
export type CopilotAnswer = {
  contextKey: string; topics: CopilotTopic[]; status: AnswerStatus;
  used: CopilotEvidence[]; missing: CopilotEvidence[];
  conflicts: CopilotContext["conflicts"]; followups: CopilotTopic[];
  insights: Array<{ kind: "asking_vs_market" | "known_housing"; refs: string[]; values: Record<string, number> }>;
  failure?: "invalid_responder_output";
};
const summaryTopics: CopilotTopic[] = ["identity", "market", "valuation", "finance", "location", "commute", "risk", "scenario", "decision"];
const usable = (row: CopilotEvidence) => row.value !== null && ["available", "limited", "no_match"].includes(row.status) && row.missingReason === null;

/** Accept one already-authorized workspace, never a case collection or raw configuration. */
export function assembleCopilotContext(workspace: PropertyCaseWorkspace, extras: { scenarioRaw?: string | null; roomRead?: RoomRead } = {}): CopilotContext {
  const model = projectCaseEvidence(workspace);
  const root = `/cases/${encodeURIComponent(model.caseId)}`;
  const identityInvalid = ["conflict", "revalidation_required"].includes(model.identity.state);
  const evidence: CopilotEvidence[] = evidenceFields(model).map((field) => ({
    id: field.id, ref: `${model.caseId}:${field.id}`, topic: fieldTopic(field), label: field.label,
    value: field.value, unit: field.unit, status: field.status, source: field.source,
    limitation: field.limitation, href: `${root}/${field.domain}`, origin: "saved_snapshot",
    checkedAt: field.freshness.checkedAt, updatedAt: field.freshness.sourceUpdatedAt, missingReason: field.missingReason,
    // The shared legacy projection retains some POI/TDX fields with unknown
    // relation. They cannot support claims after this property's identity changes.
    ...(identityInvalid && field.domain === "location" ? { value: null, status: "stale" as const, missingReason: "stale" } : {}),
  }));
  function add(id: string, topic: CopilotTopic, value: string | number | null, section: string, options: Partial<Pick<CopilotEvidence, "unit" | "status" | "source" | "limitation" | "missingReason" | "checkedAt">> = {}) {
    if (evidence.some(row => row.id === id)) return;
    evidence.push({ id, ref: `${model.caseId}:${id}`, topic, label: id, value, unit: "", status: value === null ? "not_run" : "limited", source: section, limitation: "", href: `${root}/${section}`, origin: "saved_snapshot", checkedAt: null, updatedAt: null, missingReason: value === null ? "not_preserved" : null, ...options });
  }
  add("identity-anchor", "identity", model.identity.state, "overview", { limitation: model.identity.limitation });
  // Browser identity is never parcel, zoning, building, ownership or legal authority.
  add("identity-legal", "legal", null, "overview", { status: "unsupported", limitation: model.identity.limitation });
  add("live-evidence", "current", null, "overview", { missingReason: "not_requested" });
  add("compare-selection", "compare", null, "overview", { missingReason: "explicit_selection_required" });

  const scenarios = extras.scenarioRaw && extras.scenarioRaw.length <= 100_000 ? parseScenarioSave(extras.scenarioRaw, scenarioContext(workspace)) : null;
  if (scenarios) {
    scenarios.drafts.forEach((draft, index) => {
      const letter = ["A", "B", "C"][index];
      const result = calculateScenario(draft);
      for (const name of ["offerTwd", "ratePercent", "loanYears", "downValue"] as const) add(`scenario-${letter}-${name}`, "scenario", draft[name], "scenarios", { unit: name.endsWith("Twd") ? "TWD" : name === "ratePercent" || name === "downValue" && draft.downMode === "ratio" ? "%" : name === "loanYears" ? "year" : "TWD" });
      for (const name of ["paymentTwd", "purchaseCashTwd", "monthlyOwnershipTwd", "holdingCashTwd"] as const) add(`scenario-${letter}-${name}`, "scenario", result[name], "scenarios", { unit: "TWD", limitation: result.costsComplete ? "scenario_assumptions" : "known_subtotal" });
      for (const name of SCENARIO_FIELDS.filter((field) => draft[field] === null)) add(`scenario-${letter}-${name}`, "scenario", null, "scenarios", { missingReason: "missing_input" });
    });
  } else add("scenario-saved", "scenario", null, "scenarios", { missingReason: extras.scenarioRaw ? "stale_or_invalid" : "not_preserved" });

  const roomRead = extras.roomRead;
  const room = roomRead?.status === "ready" && roomRead.room.caseId === model.caseId ? roomRead.room : null;
  if (room) {
    add("room-asking", "decision", room.askingPrice.priceWan, "decision-room", { unit: "萬元", checkedAt: room.askingPrice.checkedDate || null, limitation: "user_record" });
    add("room-notes", "decision", room.notes.length, "decision-room", { limitation: "user_record" });
    add("room-open-questions", "decision", room.items.filter((row) => row.kind === "question" && row.status === "open").length, "decision-room", { limitation: "user_record" });
    add("room-open-tasks", "decision", room.items.filter((row) => row.kind === "task" && row.status === "open").length, "decision-room", { limitation: "user_record" });
    add("room-followup", "decision", room.verifications.filter((row) => row.outcome === "needs_follow_up").length, "decision-room", { limitation: "user_record" });
  } else add("room-saved", "decision", null, "decision-room", { missingReason: roomRead && roomRead.status !== "empty" ? "unavailable_or_invalid" : "not_preserved" });
  const conflicts: CopilotContext["conflicts"] = [];
  if (["conflict", "revalidation_required"].includes(model.identity.state)) conflicts.push("identity");
  if (room?.askingPrice.priceWan != null && model.price.asking.value !== null && room.askingPrice.priceWan !== model.price.asking.value) conflicts.push("asking_price");
  const context = { caseId: model.caseId, title: model.title.slice(0, 300), address: model.displayAddress.slice(0, 500), savedAt: model.savedAt, identityState: model.identity.state, liveEvidence: "not_requested" as const, evidence, conflicts };
  // The existing parser validates required inputs but tolerates extra JSON keys.
  // Revision binding must not retain those keys, even as internal metadata.
  const scenarioInputs = scenarios ? [...scenarios.drafts, scenarios.baseline].map(draft => draft ? [draft.downMode, ...SCENARIO_FIELDS.map(field => draft[field])] : null) : null;
  // Exact in-memory binding, not a durable revision or a payload to send to a model.
  return { ...context, key: JSON.stringify([context, workspace.revision, model.checklistIdentityToken, scenarioInputs, room?.revision, room?.updatedAt]) };
}

function fieldTopic(field: EvidenceField<string | number>): CopilotTopic {
  if (field.id.startsWith("valuation-")) return "valuation";
  if (field.id.startsWith("commute-") || field.id === "transit-context") return "commute";
  return ({ overview: "identity", market: "market", finance: "finance", location: "location", risk: "risk" } as const)[field.domain];
}

const topicPatterns: Array<[CopilotTopic, RegExp]> = [
  ["legal", /zoning|parcel|ownership|legal|分區|地號|地籍|權利|所有權|用途地域|地番|登記|용도지역|필지|소유권/i],
  ["current", /current|live|最新|即時|現時|現在の|リアルタイム|실시간|최신/i],
  ["identity", /identity|address|身分|地址|物件識別|住所|식별|주소/i],
  ["market", /market|asking|price|市場|開價|價格|相場|価格|시장|가격/i],
  ["valuation", /valuation|estimate|估價|推估|估值|査定|推定|추정|감정/i],
  ["finance", /finance|mortgage|afford|monthly|loan|財務|房貸|負擔|月付|資金|ローン|返済|대출|재무|상환/i],
  ["location", /location|poi|amenit|school|區位|生活機能|設施|周辺|施設|입지|시설/i],
  ["commute", /commute|route|通勤|路線|経路|출퇴근|경로/i],
  ["risk", /risk|terrain|safe|flood|風險|地形|安全|淹水|リスク|洪水|위험|안전|지형/i],
  ["scenario", /scenario|情境|シナリオ|시나리오/i],
  ["decision", /decision|決策|決定|의사결정/i],
  ["compare", /compare|比較|비교/i],
];
export function answerQuestion(context: CopilotContext, question: string, previous?: CopilotAnswer): CopilotAnswer {
  const bounded = question.trim().slice(0, 1000);
  let topics = topicPatterns.filter(([, pattern]) => pattern.test(bounded)).map(([topic]) => topic);
  const generic = /summary|report|evidence|missing|next|摘要|報告|證據|缺|下一步|要約|レポート|根拠|不足|次|요약|보고서|근거|누락|다음/i.test(bounded);
  if (!topics.length) topics = generic ? previous?.contextKey === context.key ? previous.topics : summaryTopics : ["unknown"];
  // A request for unsupported legal/current facts cannot borrow adjacent market evidence.
  if (topics.includes("legal")) topics = ["legal"];
  else if (topics.includes("current")) topics = ["current"];
  const conflicts = context.conflicts.filter((kind) => kind === "identity" || topics.includes("market") || topics.includes("decision"));
  const selected = context.evidence.filter((row) => topics.includes(row.topic) || conflicts.includes("asking_price") && ["price-asking", "room-asking"].includes(row.id));
  const used = selected.filter(usable);
  const missing = selected.filter((row) => !usable(row));
  const status: AnswerStatus = conflicts.length ? "conflicting_evidence" : !used.length ? "insufficient_evidence" : missing.length || used.some((row) => row.status !== "available" || row.limitation) ? "partially_supported" : "supported";
  const insights: CopilotAnswer["insights"] = [];
  const asking = used.find(row => row.id === "price-asking");
  const median = used.find(row => row.id === "market-total");
  if (!conflicts.length && typeof asking?.value === "number" && typeof median?.value === "number" && median.value > 0) insights.push({ kind: "asking_vs_market", refs: [asking.ref, median.ref], values: { differenceWan: asking.value - median.value } });
  const housing = used.find(row => row.id === "finance-housing");
  if (!conflicts.length && typeof housing?.value === "number") insights.push({ kind: "known_housing", refs: [housing.ref], values: { monthlyTwd: housing.value } });
  return { contextKey: context.key, topics, status, used, missing, conflicts, insights, followups: [...new Set<CopilotTopic>([...topics.filter((topic) => summaryTopics.includes(topic)), "risk", "finance", "decision"])].slice(0, 4) };
}

export function resolveCitation(context: CopilotContext, ref: string): CopilotEvidence | null {
  return context.evidence.find((row) => row.ref === ref) ?? null;
}

/** Future model boundary: no user/evidence prose, secrets, raw state or model authority.
 * A provider can only echo the complete evidence selection. It cannot weaken missing
 * evidence, suppress conflicts, change numbers or write authoritative claims.
 */
export function buildReasoningRequest(context: CopilotContext, answer: CopilotAnswer) {
  const active = answer.contextKey === context.key ? answer : answerQuestion(context, "unsupported");
  const rows = active.used.map(row => resolveCitation(context, row.ref)).filter((row): row is CopilotEvidence => row !== null && usable(row));
  return { version: 1, topics: active.topics, evidence: rows.map((row) => ({ ref: row.ref, value: typeof row.value === "number" ? row.value : null, status: row.status })), missing: active.missing.filter(row => resolveCitation(context, row.ref)).map((row) => row.ref), hasConflict: context.conflicts.length > 0 };
}
export function validateResponderOutput(context: CopilotContext, expected: CopilotAnswer, output: unknown): CopilotAnswer {
  const valid = output && typeof output === "object" && !Array.isArray(output) && Object.keys(output).length === 1 && "refs" in output && Array.isArray(output.refs)
    && output.refs.length === expected.used.length && new Set(output.refs).size === output.refs.length
    && output.refs.every((ref: unknown) => typeof ref === "string" && resolveCitation(context, ref) !== null && expected.used.some((row) => row.ref === ref));
  if (valid && expected.contextKey === context.key) return expected;
  const base = expected.contextKey === context.key ? expected : answerQuestion(context, "unsupported");
  return { ...base, contextKey: context.key, status: "insufficient_evidence", used: [], insights: [], failure: "invalid_responder_output" };
}

/** Requests are bound to exact evidence context and sequence; cancellation is final. */
export function createResponseGate() {
  let sequence = 0;
  return {
    begin(key: string) { return { key, sequence: ++sequence }; },
    accepts(ticket: { key: string; sequence: number }, currentKey: string) { return ticket.key === currentKey && ticket.sequence === sequence; },
    cancel() { sequence++; },
  };
}
