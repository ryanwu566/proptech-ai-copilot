import type { MarketResult } from "../api";
// @ts-expect-error Native TS runner extension.
import { getMarketDisplayState } from "../market-result-state.ts";
// @ts-expect-error Native TS runner extension.
import { hasCompleteAdministrativeArea } from "../journey-property-identity.ts";
// @ts-expect-error Native TS runner extension.
import { isDemoCaseId } from "./demo-case-ids.ts";
// @ts-expect-error Native TS runner extension.
import { buildWorkspaceOverview } from "./overview-model.ts";
import type { NearbyFacilitiesEvidence } from "./nearby-facilities";
import type { RiskEvidenceModel } from "./risk-evidence-model";
import type { VillageDemographicsEvidence } from "./village-demographics";
import type { PropertyCaseWorkspace } from "./workspace-model";

/**
 * Auto Brief: one explicit action that walks the existing evidence steps in a fixed order.
 * Automation never invents evidence; every step ends in its own truthful terminal status.
 * Acquisition is injected as ports so the state machine is provider-free and testable.
 */
export const AUTO_BRIEF_STEP_IDS = ["market", "location", "risk", "money", "brief"] as const;
export type AutoBriefStepId = (typeof AUTO_BRIEF_STEP_IDS)[number];
export type AutoBriefStepStatus = "pending" | "running" | "available" | "partial" | "no_data" | "unavailable" | "needs_input" | "skipped";
export type AutoBriefRunStatus = "idle" | "prechecking" | "running" | "completed" | "completed_with_gaps" | "needs_location" | "cancelled" | "failed" | "interrupted";
export type AutoBriefMode = "real_case" | "demo_fixture";
export type AutoBriefPartStatus = "available" | "partial" | "no_data" | "unavailable";

/** Bounded, display-safe reason codes. Never a provider message; UI maps each to localized copy. */
export type AutoBriefReason =
  | "location_unconfirmed" | "location_revalidation" | "location_admin_incomplete" | "location_pending_candidate" | "location_changed"
  | "case_missing" | "cancelled" | "interrupted" | "reused_saved" | "demo_snapshot" | "not_in_fixture"
  | "partial_evidence" | "no_data" | "provider_unavailable" | "not_saved"
  | "money_inputs_missing" | "money_inputs_stale" | "money_partial";

export type AutoBriefStep = {
  id: AutoBriefStepId;
  status: AutoBriefStepStatus;
  startedAt: string | null;
  completedAt: string | null;
  reason: AutoBriefReason | null;
  retryable: boolean;
  /** Location only: Nearby and demographics stay independent. */
  parts?: { nearby: AutoBriefPartStatus; demographics: AutoBriefPartStatus };
  reused?: boolean;
};

export type AutoBriefRun = {
  runId: string;
  caseId: string;
  mode: AutoBriefMode;
  status: AutoBriefRunStatus;
  /** Accepted location the run is bound to; a different anchor makes the saved run irrelevant. */
  anchorId: string | null;
  startedAt: string;
  updatedAt: string;
  currentStep: AutoBriefStepId | null;
  reason: AutoBriefReason | null;
  steps: AutoBriefStep[];
  /** Unresolved Brief items to verify; null until the Brief step runs. */
  gapCount: number | null;
};

export type AutoBriefBinding = {
  caseId: string;
  journeyAnchorId: string;
  normalizedAddress: string;
  coordinates: { latitude: number; longitude: number };
  city: string;
  district: string;
};

export type AutoBriefStepOutcome = Pick<AutoBriefStep, "status" | "reason"> & Partial<Pick<AutoBriefStep, "parts" | "reused">>;

export type AutoBriefPortInput = {
  binding: AutoBriefBinding;
  workspace: PropertyCaseWorkspace;
  signal: AbortSignal;
  /** False once the run is cancelled, superseded or the case location changed. Every write must check it. */
  canCommit: () => boolean;
};

export type AutoBriefPorts = {
  market(input: AutoBriefPortInput): Promise<AutoBriefStepOutcome>;
  location(input: AutoBriefPortInput): Promise<AutoBriefStepOutcome>;
  risk(input: AutoBriefPortInput): Promise<AutoBriefStepOutcome>;
};

export type AutoBriefStore = {
  read(caseId: string): AutoBriefRun | null;
  write(run: AutoBriefRun): void;
};

const TERMINAL_STEP = new Set<AutoBriefStepStatus>(["available", "partial", "no_data", "unavailable", "needs_input", "skipped"]);
const ACTIVE_RUN = new Set<AutoBriefRunStatus>(["prechecking", "running"]);
const PART_STATUSES: readonly AutoBriefPartStatus[] = ["available", "partial", "no_data", "unavailable"];
const COORDINATE_TOLERANCE = 0.000001;

export function isTerminalStep(status: AutoBriefStepStatus): boolean {
  return TERMINAL_STEP.has(status);
}

export function isActiveRun(status: AutoBriefRunStatus): boolean {
  return ACTIVE_RUN.has(status);
}

export function autoBriefModeFor(caseId: string): AutoBriefMode {
  return isDemoCaseId(caseId) ? "demo_fixture" : "real_case";
}

/** Location gate: a current, confirmed, administratively complete anchor. Never geocodes. */
export function precheckAutoBrief(workspace: PropertyCaseWorkspace | null): { ok: true; binding: AutoBriefBinding } | { ok: false; reason: AutoBriefReason } {
  if (!workspace) return { ok: false, reason: "case_missing" };
  const anchor = workspace.identity.anchor;
  if (workspace.identity.state === "revalidation_required") return { ok: false, reason: "location_revalidation" };
  if (workspace.pendingLocationCandidate) return { ok: false, reason: "location_pending_candidate" };
  if (workspace.identity.state !== "confirmed" || !anchor?.coordinates) return { ok: false, reason: "location_unconfirmed" };
  if (anchor.revalidation.status !== "current" || anchor.revalidation.conflicts.length > 0) return { ok: false, reason: "location_revalidation" };
  if (!hasCompleteAdministrativeArea(anchor)) return { ok: false, reason: "location_admin_incomplete" };
  return { ok: true, binding: {
    caseId: workspace.caseId,
    journeyAnchorId: anchor.journey_anchor_id,
    normalizedAddress: anchor.normalized_address,
    coordinates: { latitude: anchor.coordinates.latitude, longitude: anchor.coordinates.longitude },
    city: anchor.administrative_location.city!.trim(),
    district: anchor.administrative_location.district!.trim(),
  } };
}

/** The same case, still at the same accepted location. Reuses the anchor identity, not a second system. */
export function bindingIsCurrent(binding: AutoBriefBinding, workspace: PropertyCaseWorkspace | null): boolean {
  const check = precheckAutoBrief(workspace);
  if (!check.ok) return false;
  const now = check.binding;
  return now.caseId === binding.caseId && now.journeyAnchorId === binding.journeyAnchorId && now.normalizedAddress === binding.normalizedAddress
    && Math.abs(now.coordinates.latitude - binding.coordinates.latitude) <= COORDINATE_TOLERANCE
    && Math.abs(now.coordinates.longitude - binding.coordinates.longitude) <= COORDINATE_TOLERANCE
    && now.city === binding.city && now.district === binding.district;
}

// ── Domain classifiers: map existing evidence models to step statuses. Missing is never "safe". ──

export function classifyMarketResult(result: MarketResult | undefined | null): AutoBriefStepOutcome {
  const state = getMarketDisplayState(result ?? undefined);
  if (state === "available") return { status: "available", reason: null };
  if (state === "no_data") return { status: "no_data", reason: "no_data" };
  if (state === "unavailable") return { status: "unavailable", reason: "provider_unavailable" };
  return { status: "partial", reason: "partial_evidence" };
}

export function classifyRiskModel(model: RiskEvidenceModel | null | undefined): AutoBriefStepOutcome {
  if (!model || model.rows.length === 0) return { status: "unavailable", reason: "provider_unavailable" };
  if (model.unknownEvidenceCount === 0) return { status: "available", reason: null };
  if (model.unknownEvidenceCount >= model.rows.length) return { status: "unavailable", reason: "provider_unavailable" };
  return { status: "partial", reason: "partial_evidence" };
}

export function classifyNearby(evidence: NearbyFacilitiesEvidence | undefined | null): AutoBriefPartStatus {
  if (!evidence) return "unavailable";
  if (evidence.partial) return "partial";
  return evidence.places.length ? "available" : "no_data";
}

export function classifyDemographics(evidence: VillageDemographicsEvidence | undefined | null): AutoBriefPartStatus {
  if (!evidence) return "unavailable";
  if (evidence.demographics.status === "available") return "available";
  if (evidence.demographics.status === "no_data" || evidence.village.status === "unresolved" || evidence.village.status === "ambiguous") return "no_data";
  return "unavailable";
}

export function combineLocationParts(nearby: AutoBriefPartStatus, demographics: AutoBriefPartStatus, reused: boolean): AutoBriefStepOutcome {
  const parts = { nearby, demographics };
  if (nearby === demographics && nearby !== "partial") {
    return { status: nearby, reason: nearby === "available" ? reused ? "reused_saved" : null : nearby === "no_data" ? "no_data" : "provider_unavailable", parts, reused };
  }
  return { status: "partial", reason: "partial_evidence", parts, reused };
}

/** Money reads saved user inputs only. Missing inputs become needs_input; nothing is assumed. */
export function classifyMoney(workspace: PropertyCaseWorkspace): AutoBriefStepOutcome {
  const finance = workspace.finance;
  if (!finance || workspace.assumptions.activePriceWan === undefined) return { status: "needs_input", reason: "money_inputs_missing" };
  if (finance.freshness.status === "stale") return { status: "needs_input", reason: "money_inputs_stale" };
  if (finance.calculation.query !== "succeeded" || finance.loan.status !== "available") return { status: "needs_input", reason: "money_inputs_missing" };
  if (finance.holding.status === "available" && finance.affordability.status === "assessed" && finance.missingCosts.length === 0) return { status: "available", reason: null };
  return { status: "partial", reason: "money_partial" };
}

/** Demo snapshots: the same classifiers over saved evidence, with no provider at all. */
export function createDemoFixturePorts(): AutoBriefPorts {
  return {
    market: async ({ workspace }) => {
      const result = workspace.marketPrice.market.result;
      if (!result) return { status: "unavailable", reason: "not_in_fixture" };
      const outcome = classifyMarketResult(result);
      return { ...outcome, reason: outcome.reason ?? "demo_snapshot" };
    },
    location: async ({ workspace }) => {
      const outcome = combineLocationParts(classifyNearby(workspace.location.nearbyFacilities), classifyDemographics(workspace.location.villageDemographics), true);
      return outcome.status === "available" ? { ...outcome, reason: "demo_snapshot" } : outcome.status === "unavailable" ? { ...outcome, reason: "not_in_fixture" } : outcome;
    },
    risk: async ({ workspace }) => {
      const outcome = classifyRiskModel(workspace.risk);
      return workspace.risk ? { ...outcome, reason: outcome.reason ?? "demo_snapshot" } : { status: "unavailable", reason: "not_in_fixture" };
    },
  };
}

function emptySteps(): AutoBriefStep[] {
  return AUTO_BRIEF_STEP_IDS.map((id) => ({ id, status: "pending", startedAt: null, completedAt: null, reason: null, retryable: false }));
}

function retryableFor(id: AutoBriefStepId, status: AutoBriefStepStatus): boolean {
  return (id === "market" || id === "location" || id === "risk") && (status === "unavailable" || status === "partial");
}

/** Gaps are any step that did not fully succeed; terminal ≠ success. */
export function finalRunStatus(steps: AutoBriefStep[]): "completed" | "completed_with_gaps" {
  return steps.every((step) => step.status === "available") ? "completed" : "completed_with_gaps";
}

/** A persisted run is read back without resuming anything: an active run becomes "interrupted". */
export function restoreAutoBriefRun(stored: AutoBriefRun | null, workspace: PropertyCaseWorkspace | null): AutoBriefRun | null {
  if (!stored || !workspace || stored.caseId !== workspace.caseId) return null;
  if (stored.anchorId !== (workspace.identity.anchor?.journey_anchor_id ?? null)) return null;
  if (!isActiveRun(stored.status)) return stored;
  return {
    ...stored,
    status: "interrupted",
    reason: "interrupted",
    currentStep: null,
    steps: stored.steps.map((step) => step.status === "running" ? { ...step, status: "pending", startedAt: null, reason: "interrupted" } : step),
  };
}

/** Bounded storage shape check; anything unexpected is discarded rather than trusted. */
export function normalizeAutoBriefRun(value: unknown): AutoBriefRun | null {
  const run = value as Partial<AutoBriefRun> | null;
  if (!run || typeof run !== "object" || typeof run.runId !== "string" || typeof run.caseId !== "string" || !Array.isArray(run.steps)) return null;
  if (run.mode !== "real_case" && run.mode !== "demo_fixture") return null;
  const statuses: AutoBriefRunStatus[] = ["idle", "prechecking", "running", "completed", "completed_with_gaps", "needs_location", "cancelled", "failed", "interrupted"];
  if (!statuses.includes(run.status as AutoBriefRunStatus)) return null;
  const steps: AutoBriefStep[] = [];
  for (const id of AUTO_BRIEF_STEP_IDS) {
    const step = run.steps.find((row) => row && (row as AutoBriefStep).id === id) as AutoBriefStep | undefined;
    if (!step || !["pending", "running", ...TERMINAL_STEP].includes(step.status)) return null;
    const parts = step.parts && PART_STATUSES.includes(step.parts.nearby) && PART_STATUSES.includes(step.parts.demographics) ? { nearby: step.parts.nearby, demographics: step.parts.demographics } : undefined;
    steps.push({ id, status: step.status, startedAt: typeof step.startedAt === "string" ? step.startedAt : null, completedAt: typeof step.completedAt === "string" ? step.completedAt : null,
      reason: typeof step.reason === "string" ? step.reason : null, retryable: retryableFor(id, step.status), ...(parts ? { parts } : {}), ...(step.reused ? { reused: true } : {}) });
  }
  return {
    runId: run.runId.slice(0, 64), caseId: run.caseId, mode: run.mode, status: run.status as AutoBriefRunStatus,
    anchorId: typeof run.anchorId === "string" ? run.anchorId : null,
    startedAt: typeof run.startedAt === "string" ? run.startedAt : "", updatedAt: typeof run.updatedAt === "string" ? run.updatedAt : "",
    currentStep: AUTO_BRIEF_STEP_IDS.includes(run.currentStep as AutoBriefStepId) ? run.currentStep as AutoBriefStepId : null,
    reason: typeof run.reason === "string" ? run.reason : null, steps,
    gapCount: typeof run.gapCount === "number" && Number.isInteger(run.gapCount) && run.gapCount >= 0 ? run.gapCount : null,
  };
}

export type AutoBriefControllerOptions = {
  readWorkspace(caseId: string): PropertyCaseWorkspace | null;
  realPorts: AutoBriefPorts;
  demoPorts?: AutoBriefPorts;
  store?: AutoBriefStore;
  now?: () => string;
  createRunId?: () => string;
};

export type AutoBriefController = ReturnType<typeof createAutoBriefController>;

/**
 * One active run per controller. Every start/retry/cancel bumps the generation; a step result is
 * applied only when its generation is still current and the case is still at the bound location.
 */
export function createAutoBriefController(options: AutoBriefControllerOptions) {
  const now = options.now ?? (() => new Date().toISOString());
  let counter = 0;
  const createRunId = options.createRunId ?? (() => `auto-brief-${Date.now().toString(36)}-${(++counter).toString(36)}`);
  const demoPorts = options.demoPorts ?? createDemoFixturePorts();
  const runs = new Map<string, AutoBriefRun>();
  const listeners = new Set<() => void>();
  let generation = 0;
  let active: { generation: number; caseId: string; abort: AbortController } | null = null;

  function emit() { for (const listener of [...listeners]) listener(); }
  function publish(run: AutoBriefRun) {
    runs.set(run.caseId, run);
    options.store?.write(run);
    emit();
  }

  function snapshot(caseId: string): AutoBriefRun | null {
    const live = runs.get(caseId);
    if (live) {
      // A run kept in memory stays relevant only while its location is unchanged.
      const workspace = options.readWorkspace(caseId);
      if (!isActiveRun(live.status) && live.anchorId !== (workspace?.identity.anchor?.journey_anchor_id ?? null)) return null;
      return live;
    }
    const restored = restoreAutoBriefRun(options.store?.read(caseId) ?? null, options.readWorkspace(caseId));
    if (restored) runs.set(caseId, restored);
    return restored;
  }

  /** Supersede the active run: its late responses are ignored and its unfinished steps are skipped. */
  function invalidate() {
    const previous = active;
    generation += 1;
    active = null;
    if (!previous) return;
    previous.abort.abort();
    const run = runs.get(previous.caseId);
    if (run && isActiveRun(run.status)) stop(run, "cancelled", "cancelled");
  }

  function update(run: AutoBriefRun, patch: Partial<AutoBriefRun>): AutoBriefRun {
    const next = { ...run, ...patch, updatedAt: now() };
    publish(next);
    return next;
  }

  function setStep(run: AutoBriefRun, id: AutoBriefStepId, patch: Partial<AutoBriefStep>): AutoBriefRun {
    return update(run, { steps: run.steps.map((step) => step.id === id ? { ...step, ...patch } : step) });
  }

  async function execute(base: AutoBriefRun, stepIds: readonly AutoBriefStepId[]): Promise<AutoBriefRun> {
    invalidate();
    const mine = ++generation;
    const abort = new AbortController();
    active = { generation: mine, caseId: base.caseId, abort };
    const isCurrent = () => generation === mine && !abort.signal.aborted;
    let run = update(base, { status: "prechecking", reason: null, currentStep: null });

    const check = precheckAutoBrief(options.readWorkspace(base.caseId));
    if (!isCurrent()) return runs.get(base.caseId) ?? run;
    if (!check.ok) {
      run = update(run, { status: check.reason === "case_missing" ? "failed" : "needs_location", reason: check.reason });
      if (active?.generation === mine) active = null;
      return run;
    }
    const binding = check.binding;
    run = update(run, { status: "running", anchorId: binding.journeyAnchorId });
    const ports = run.mode === "demo_fixture" ? demoPorts : options.realPorts;
    const stillBound = () => isCurrent() && bindingIsCurrent(binding, options.readWorkspace(binding.caseId));

    for (const id of stepIds) {
      if (!isCurrent()) return runs.get(base.caseId) ?? run;
      const workspace = options.readWorkspace(binding.caseId);
      if (!workspace) { run = stop(run, "failed", "case_missing"); break; }
      if (!bindingIsCurrent(binding, workspace)) { run = stop(run, "needs_location", "location_changed"); break; }
      run = update(setStep(run, id, { status: "running", startedAt: now(), completedAt: null, reason: null, retryable: false }), { currentStep: id });
      let outcome: AutoBriefStepOutcome;
      let gapCount: number | null = run.gapCount;
      try {
        if (id === "money") outcome = classifyMoney(workspace);
        else if (id === "brief") {
          gapCount = buildWorkspaceOverview(workspace).unresolvedCount;
          outcome = { status: "available", reason: null };
        } else outcome = await ports[id]({ binding, workspace, signal: abort.signal, canCommit: stillBound });
      } catch {
        outcome = { status: "unavailable", reason: "provider_unavailable" };
      }
      // Requests aborted by a page unload settle before "pagehide"; one task later the page is gone,
      // so an unload is never recorded as a provider outcome.
      if (id !== "money" && id !== "brief") await new Promise((resolve) => setTimeout(resolve, 0));
      // A cancelled or superseded run never writes its late result.
      if (!isCurrent()) return runs.get(base.caseId) ?? run;
      if (!bindingIsCurrent(binding, options.readWorkspace(binding.caseId))) { run = stop(run, "needs_location", "location_changed"); break; }
      run = setStep(run, id, { ...outcome, completedAt: now(), retryable: retryableFor(id, outcome.status) });
      if (id === "brief") run = update(run, { gapCount });
    }
    if (isCurrent() && isActiveRun(run.status)) run = update(run, { status: finalRunStatus(run.steps), currentStep: null });
    if (active?.generation === mine) active = null;
    return run;
  }

  function stop(run: AutoBriefRun, status: AutoBriefRunStatus, reason: AutoBriefReason): AutoBriefRun {
    return update(run, {
      status, reason, currentStep: null,
      steps: run.steps.map((step) => isTerminalStep(step.status) ? step : { ...step, status: "skipped", reason, retryable: false, completedAt: step.status === "running" ? now() : step.completedAt }),
    });
  }

  return {
    subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    getRun: snapshot,
    /** Fresh run of every step. Starting again invalidates any earlier run, on any case. */
    start(caseId: string): Promise<AutoBriefRun> {
      const at = now();
      const anchorId = options.readWorkspace(caseId)?.identity.anchor?.journey_anchor_id ?? null;
      return execute({ runId: createRunId(), caseId, mode: autoBriefModeFor(caseId), status: "idle", anchorId, startedAt: at, updatedAt: at, currentStep: null, reason: null, steps: emptySteps(), gapCount: null }, AUTO_BRIEF_STEP_IDS);
    },
    /** Continue an interrupted/cancelled run: only steps that never finished, then the Brief. */
    continue(caseId: string): Promise<AutoBriefRun> | null {
      const run = snapshot(caseId);
      if (!run || (run.status !== "interrupted" && run.status !== "cancelled")) return null;
      const remaining = run.steps.filter((step) => step.id !== "brief" && (step.status === "pending" || step.status === "skipped")).map((step) => step.id);
      return execute(resetSteps(run, [...remaining, "brief"]), [...remaining, "brief"]);
    },
    /** One explicit retry of one domain that ended unavailable or partial. No hidden loops. */
    retryStep(caseId: string, id: AutoBriefStepId): Promise<AutoBriefRun> | null {
      const run = snapshot(caseId);
      const step = run?.steps.find((row) => row.id === id);
      if (!run || isActiveRun(run.status) || !step?.retryable) return null;
      const ids: AutoBriefStepId[] = [id, "money", "brief"];
      return execute(resetSteps(run, ids), ids);
    },
    /**
     * Page is going away: drop the active run without recording any further outcome, so aborted
     * requests are not mistaken for provider failures and the saved run restores as interrupted.
     */
    suspend() {
      generation += 1;
      active?.abort.abort();
      active = null;
      runs.clear();
      emit();
    },
    cancel(caseId: string): AutoBriefRun | null {
      const run = runs.get(caseId);
      if (!run || !isActiveRun(run.status) || active?.caseId !== caseId) return null;
      invalidate();
      return runs.get(caseId) ?? null;
    },
  };

  function resetSteps(run: AutoBriefRun, ids: readonly AutoBriefStepId[]): AutoBriefRun {
    return { ...run, steps: run.steps.map((step) => ids.includes(step.id) ? { id: step.id, status: "pending", startedAt: null, completedAt: null, reason: null, retryable: false } : step) };
  }
}
