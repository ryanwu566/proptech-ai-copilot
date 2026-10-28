"use client";

import { api } from "@/lib/api";
import { readSavedCases, updateSavedCaseLocationEvidence, updateSavedCaseMarketEvidence, updateSavedCaseRiskEvidence, type SavedCaseIdentityExpectation } from "@/lib/case-storage";
import { createBrowserCaseRepository } from "./case-repository";
import { buildMarketRefreshContext, classifyMarketRefresh } from "./market-price-refresh";
import { buildRiskEvidenceModel, buildRiskQueryContext, buildStoredRiskEvidenceSnapshot } from "./risk-evidence-model";
import { captureNearbyFacilities, NEARBY_CATEGORIES, NEARBY_RADIUS_M, shareNearbyAcquisition } from "./nearby-facilities";
import { captureVillageDemographics, shareVillageDemographicsAcquisition } from "./village-demographics";
import {
  classifyDemographics, classifyMarketResult, classifyNearby, classifyRiskModel, combineLocationParts, createAutoBriefController, normalizeAutoBriefRun,
  type AutoBriefController, type AutoBriefPortInput, type AutoBriefPorts, type AutoBriefRun, type AutoBriefStepOutcome, type AutoBriefStore,
} from "./auto-brief";

/** Only the bounded step summary is kept, per case; never provider payloads or errors. */
export const AUTO_BRIEF_STORAGE_KEY = "proptech.autoBrief.v1";
const MAX_STORED_RUNS = 10;
const UNAVAILABLE: AutoBriefStepOutcome = { status: "unavailable", reason: "provider_unavailable" };
const NOT_SAVED: AutoBriefStepOutcome = { status: "unavailable", reason: "not_saved" };

function readStore(): Record<string, unknown> {
  try {
    const value = JSON.parse(window.localStorage.getItem(AUTO_BRIEF_STORAGE_KEY) ?? "{}");
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch { return {}; }
}

const browserStore: AutoBriefStore = {
  read: (caseId) => normalizeAutoBriefRun(readStore()[caseId]),
  write(run) {
    try {
      const rows = { ...readStore(), [run.caseId]: run } as Record<string, AutoBriefRun>;
      const kept = Object.entries(rows).sort(([, a], [, b]) => String(b?.updatedAt).localeCompare(String(a?.updatedAt))).slice(0, MAX_STORED_RUNS);
      window.localStorage.setItem(AUTO_BRIEF_STORAGE_KEY, JSON.stringify(Object.fromEntries(kept)));
    } catch { /* Storage is a convenience; the run itself stays in memory. */ }
  },
};

function expectation({ binding, workspace }: AutoBriefPortInput): SavedCaseIdentityExpectation {
  return { journeyAnchorId: binding.journeyAnchorId, normalizedAddress: binding.normalizedAddress, coordinates: binding.coordinates, snapshotVersion: workspace.storageVersion };
}

/** Real case ports: the same API calls, payload builders and guarded writers the manual views use. */
const realPorts: AutoBriefPorts = {
  async market(input) {
    const { binding, workspace, signal, canCommit } = input;
    const saved = readSavedCases().find((row) => row.id === binding.caseId);
    const context = saved ? buildMarketRefreshContext(workspace, saved) : null;
    if (!context || context.payload.county !== binding.city || context.payload.district !== binding.district) return UNAVAILABLE;
    let result;
    try { result = await api.marketInsight(context.payload.county, context.payload.district, context.payload.road, undefined, signal); }
    catch { return UNAVAILABLE; }
    if (!canCommit()) return UNAVAILABLE;
    if (!classifyMarketRefresh(result).shouldPersist) return UNAVAILABLE;
    const persisted = await updateSavedCaseMarketEvidence(binding.caseId, result, context.identity, canCommit);
    return persisted ? classifyMarketResult(result) : NOT_SAVED;
  },

  /** Reuses saved Nearby and demographics; acquires only a part that was never saved for this anchor. */
  async location(input) {
    const { binding, canCommit } = input;
    const repository = createBrowserCaseRepository();
    const key = [binding.caseId, binding.journeyAnchorId, binding.coordinates];
    let workspace = input.workspace;
    let reused = true;
    let nearby = workspace.location.nearbyFacilities;
    if (!nearby) {
      reused = false;
      const origin = { lat: binding.coordinates.latitude, lng: binding.coordinates.longitude };
      const expected = expectation(input);
      try {
        // Shared with the Location panel so a confirmation already in flight is not duplicated.
        const acquired = await shareNearbyAcquisition(JSON.stringify(key), async () => {
          const evidence = captureNearbyFacilities(await api.mapNearby(origin, [...NEARBY_CATEGORIES], NEARBY_RADIUS_M), origin);
          return { evidence, saved: canCommit() && await updateSavedCaseLocationEvidence(binding.caseId, { nearbyFacilities: evidence }, expected, canCommit) };
        });
        nearby = acquired.saved ? acquired.evidence : undefined;
      } catch { nearby = undefined; }
      if (!canCommit()) return UNAVAILABLE;
      workspace = repository.getCase(binding.caseId) ?? workspace;
    }
    let demographics = workspace.location.villageDemographics;
    if (!demographics) {
      reused = false;
      const origin = { latitude: binding.coordinates.latitude, longitude: binding.coordinates.longitude };
      const expected = expectation({ ...input, workspace });
      try {
        const acquired = await shareVillageDemographicsAcquisition(JSON.stringify([binding.caseId, binding.journeyAnchorId, origin]), async () => {
          const evidence = captureVillageDemographics(await api.locationDemographics(origin.latitude, origin.longitude), origin);
          return { evidence, persisted: canCommit() && await updateSavedCaseLocationEvidence(binding.caseId, { villageDemographics: evidence }, expected, canCommit) };
        });
        demographics = acquired.persisted ? acquired.evidence : undefined;
      } catch { demographics = undefined; }
      if (!canCommit()) return UNAVAILABLE;
    }
    return combineLocationParts(classifyNearby(nearby), classifyDemographics(demographics), reused);
  },

  async risk(input) {
    const { binding, workspace, canCommit } = input;
    const context = buildRiskQueryContext(workspace);
    if (!context) return UNAVAILABLE;
    let model;
    try { model = buildRiskEvidenceModel(await api.terrainRiskAnalyze(context.payload)); }
    catch { return UNAVAILABLE; }
    if (!canCommit()) return UNAVAILABLE;
    const persisted = await updateSavedCaseRiskEvidence(binding.caseId, { ...buildStoredRiskEvidenceSnapshot(model), checked_at: model.freshness.checkedAt }, expectation(input), canCommit);
    return persisted ? classifyRiskModel(model) : NOT_SAVED;
  },
};

let controller: AutoBriefController | null = null;

/** One controller per tab, so a run survives in-app navigation between case sections. */
export function getAutoBriefController(): AutoBriefController {
  if (!controller) {
    const repository = createBrowserCaseRepository();
    controller = createAutoBriefController({ readWorkspace: (caseId) => repository.getCase(caseId), realPorts, store: browserStore });
    // A reload or tab close interrupts the run; nothing resumes until the buyer chooses to.
    const suspend = controller.suspend;
    window.addEventListener("pagehide", suspend);
  }
  return controller;
}
