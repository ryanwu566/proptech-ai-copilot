// @ts-expect-error Native TS runner extension.
import { isActiveRun } from "./auto-brief.ts";
// @ts-expect-error Native TS runner extension.
import { NEARBY_RADIUS_M } from "./nearby-facilities.ts";
// @ts-expect-error Native TS runner extension.
import { nearbyPoiGroup, type NearbyPoiGroup, type NearbyPoiKind } from "./nearby-poi-category.ts";
import type { AutoBriefRun, AutoBriefStepId, AutoBriefStepStatus } from "./auto-brief";
import type { NearbyFacilitiesEvidence } from "./nearby-facilities";

/**
 * The cinematic Auto Brief is a view of the A1-1 run, never a second source of truth.
 * Scenes follow the run's real steps; a short presentation beat may trail the run but can
 * never show a step's result before that step is terminal.
 */
export const AUTO_BRIEF_SCENES = ["lockin", "market", "location", "risk", "money", "converge", "complete"] as const;
export type AutoBriefScene = (typeof AUTO_BRIEF_SCENES)[number] | "halted";
export type AutoBriefRailId = "lockin" | AutoBriefStepId;
export const AUTO_BRIEF_RAIL: readonly AutoBriefRailId[] = ["lockin", "market", "location", "risk", "money", "brief"];
/** Presentation beat between scenes; transitions stay within 150–450ms. Zero when motion is skipped. */
export const AUTO_BRIEF_BEAT_MS = 450;

/**
 * Showcase pacing (DEMO_FIXTURE only): how long each scene stays before the next, so the provider-free
 * example reads as a ~45–60s story. Real cases never wait on these; skip and reduced motion bypass them.
 */
export const SHOWCASE_SCENE_MS: Readonly<Record<Exclude<AutoBriefScene, "complete" | "halted">, number>> = {
  lockin: 3500, market: 7000, location: 11000, risk: 9000, money: 7000, converge: 7500,
};

export function sceneHold(scene: AutoBriefScene, showcase: boolean): number {
  if (!showcase || scene === "complete" || scene === "halted") return AUTO_BRIEF_BEAT_MS;
  return SHOWCASE_SCENE_MS[scene];
}

const STEP_SCENE: Record<AutoBriefStepId, AutoBriefScene> = { market: "market", location: "location", risk: "risk", money: "money", brief: "converge" };

/** The scene the real run is in right now. */
export function targetScene(run: AutoBriefRun): AutoBriefScene {
  if (run.status === "completed" || run.status === "completed_with_gaps") return "complete";
  if (!isActiveRun(run.status)) return "halted";
  if (run.status === "prechecking" || !run.currentStep) return "lockin";
  return STEP_SCENE[run.currentStep];
}

const order = (scene: AutoBriefScene) => (AUTO_BRIEF_SCENES as readonly string[]).indexOf(scene);

/**
 * Next scene to display. Advances one scene per beat toward the target, jumps when motion is off,
 * and resets immediately when the run restarts, retries, stops or halts.
 */
export function nextScene(shown: AutoBriefScene, target: AutoBriefScene, motion: boolean): { scene: AutoBriefScene; wait: boolean } {
  if (shown === target) return { scene: shown, wait: false };
  if (!motion || target === "halted" || shown === "halted" || order(target) < order(shown)) return { scene: target, wait: false };
  return { scene: AUTO_BRIEF_SCENES[order(shown) + 1], wait: true };
}

/** A scene may show evidence only once its own step is terminal. */
export function sceneStep(scene: AutoBriefScene): AutoBriefStepId | null {
  if (scene === "market" || scene === "location" || scene === "risk" || scene === "money") return scene;
  if (scene === "converge") return "brief";
  return null;
}

export type RailStatus = AutoBriefStepStatus | "needs_location";

/** Progress rail: the location lock-in plus the five real steps, each with its own status. */
export function railItems(run: AutoBriefRun): Array<{ id: AutoBriefRailId; status: RailStatus; current: boolean }> {
  const lockin: RailStatus = run.status === "prechecking" ? "running" : run.status === "needs_location" && !run.steps.some((step) => step.startedAt) ? "needs_location" : run.anchorId ? "available" : "pending";
  return [
    { id: "lockin", status: lockin, current: run.status === "prechecking" },
    ...run.steps.map((step) => ({ id: step.id, status: step.status as RailStatus, current: isActiveRun(run.status) && run.currentStep === step.id })),
  ];
}

/** Reveal order: property → transport → schools → daily convenience → parks / medical / food. */
export const POI_REVEAL_ORDER: readonly NearbyPoiGroup[] = ["transit", "education", "shopping", "parks", "healthcare", "food", "other"];
const MAX_PLOTTED = 60;
const METERS_PER_DEGREE_LAT = 110_540;
const METERS_PER_DEGREE_LNG = 111_320;

export type PlottedPoi = { id: string; kind: NearbyPoiKind; group: NearbyPoiGroup; x: number; y: number; wave: number };

/**
 * Schematic placement of saved places around the property (percent of a square stage, 50/50 = property).
 * No basemap and no provider call: positions are derived from the saved coordinates only.
 */
export function plotNearby(evidence: NearbyFacilitiesEvidence | undefined | null): { points: PlottedPoi[]; groups: Array<{ group: NearbyPoiGroup; count: number; wave: number }> } {
  if (!evidence) return { points: [], groups: [] };
  const present = POI_REVEAL_ORDER.filter((group) => evidence.places.some((place) => nearbyPoiGroup(place.kind) === group));
  const wave = (group: NearbyPoiGroup) => present.indexOf(group);
  const cos = Math.cos(evidence.origin.lat * Math.PI / 180);
  const radius = evidence.radiusM || NEARBY_RADIUS_M;
  const points = [...evidence.places].sort((a, b) => a.distanceM - b.distanceM).slice(0, MAX_PLOTTED).map((place) => {
    const dx = (place.lng - evidence.origin.lng) * METERS_PER_DEGREE_LNG * cos / radius;
    const dy = (place.lat - evidence.origin.lat) * METERS_PER_DEGREE_LAT / radius;
    const clamp = (value: number) => Math.max(4, Math.min(96, value));
    const group = nearbyPoiGroup(place.kind);
    return { id: place.id, kind: place.kind, group, x: clamp(50 + dx * 46), y: clamp(50 - dy * 46), wave: wave(group) };
  });
  return { points, groups: present.map((group) => ({ group, count: evidence.places.filter((place) => nearbyPoiGroup(place.kind) === group).length, wave: wave(group) })) };
}

export const RAIL_SCENE: Readonly<Record<AutoBriefRailId, AutoBriefScene>> = { lockin: "lockin", market: "market", location: "location", risk: "risk", money: "money", brief: "converge" };

/**
 * Showcase rail: a fixture run finishes instantly, so chapters not yet presented stay "pending" and the
 * presented chapter is current. Never shows a chapter as further along than the real run.
 */
export function presentRail(items: ReturnType<typeof railItems>, shown: AutoBriefScene): ReturnType<typeof railItems> {
  if (shown === "complete" || shown === "halted") return items;
  return items.map((item) => {
    const at = order(RAIL_SCENE[item.id]);
    return at > order(shown) ? { ...item, status: "pending", current: false } : { ...item, current: at === order(shown) };
  });
}
