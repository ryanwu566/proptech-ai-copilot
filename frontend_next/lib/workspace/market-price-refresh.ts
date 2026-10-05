import type { SavedCase, SavedCaseIdentityExpectation } from "../case-storage";
import type { JourneyPropertyIdentityAnchorV1 } from "../journey-property-identity";
import type { MarketResult } from "../api";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { getMarketCommercialState } from "../market-result-state.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { getActionableValuation, getValuationCommercialState } from "../valuation-result-state.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildInputFingerprint, canCommitEvidence } from "./invalidation.ts";
import type { InputFingerprint, PropertyCaseWorkspace } from "./workspace-model";

type RefreshContext<TPayload> = {
  caseId: string;
  revision: number;
  fingerprint: InputFingerprint;
  identity: SavedCaseIdentityExpectation;
  payload: TPayload;
};

type RefreshCommitContext = Pick<RefreshContext<unknown>, "caseId" | "revision" | "fingerprint">;

export type MarketRefreshContext = RefreshContext<{
  county: string;
  district: string;
  road?: string;
}>;

export type ValuationRefreshPayload = {
  city: string;
  district: string;
  road: string;
  address_text: string;
  building_type: string;
  area_ping: number;
  building_age_years: number;
  floor: number;
  lat: number;
  lng: number;
};

export type ValuationTrendRefreshPayload = Pick<ValuationRefreshPayload,
  "city" | "district" | "road" | "building_type" | "area_ping" | "building_age_years"
> & { horizon_months: number[] };

export type ValuationRefreshContext = RefreshContext<ValuationRefreshPayload> & {
  trendPayload: ValuationTrendRefreshPayload;
};

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function sameCoordinates(
  left: JourneyPropertyIdentityAnchorV1["coordinates"],
  right: JourneyPropertyIdentityAnchorV1["coordinates"],
): boolean {
  return Boolean(left && right
    && Math.abs(left.latitude - right.latitude) <= 0.000001
    && Math.abs(left.longitude - right.longitude) <= 0.000001);
}

function activeAnchor(workspace: PropertyCaseWorkspace, saved: SavedCase): JourneyPropertyIdentityAnchorV1 | null {
  const anchor = workspace.identity.anchor;
  const stored = saved.data.propertyIdentityAnchor;
  if (
    saved.id !== workspace.caseId
    || workspace.identity.state !== "confirmed"
    || !anchor
    || !stored
    || anchor.revalidation.status !== "current"
    || stored.revalidation.status !== "current"
    || anchor.journey_anchor_id !== stored.journey_anchor_id
    || anchor.normalized_address !== stored.normalized_address
    || !sameCoordinates(anchor.coordinates, stored.coordinates)
  ) return null;
  return anchor;
}

function identityExpectation(anchor: JourneyPropertyIdentityAnchorV1): SavedCaseIdentityExpectation {
  return {
    journeyAnchorId: anchor.journey_anchor_id,
    normalizedAddress: anchor.normalized_address,
    coordinates: anchor.coordinates!,
  };
}

export function buildMarketRefreshContext(
  workspace: PropertyCaseWorkspace,
  saved: SavedCase,
): MarketRefreshContext | null {
  const anchor = activeAnchor(workspace, saved);
  const county = text(anchor?.administrative_location.city);
  const district = text(anchor?.administrative_location.district);
  if (!anchor || !county || !district) return null;
  const road = text(saved.data.inputs.road);
  const payload = { county, district, ...(road ? { road } : {}) };
  return {
    caseId: workspace.caseId,
    revision: workspace.revision,
    fingerprint: buildInputFingerprint({
      channel: "market",
      caseId: workspace.caseId,
      revision: workspace.revision,
      journeyAnchorId: anchor.journey_anchor_id,
      normalizedAddress: anchor.normalized_address,
      coordinates: anchor.coordinates,
      payload,
    }),
    identity: identityExpectation(anchor),
    payload,
  };
}

export function buildValuationRefreshContext(
  workspace: PropertyCaseWorkspace,
  saved: SavedCase,
): ValuationRefreshContext | null {
  const anchor = activeAnchor(workspace, saved);
  const coordinates = anchor?.coordinates;
  const inputs = saved.data.inputs;
  const city = text(anchor?.administrative_location.city);
  const district = text(anchor?.administrative_location.district);
  const road = text(inputs.road);
  const buildingType = text(inputs.building_type);
  const area = inputs.area_ping;
  const age = inputs.building_age_years;
  const floor = inputs.floor;
  if (
    !anchor
    || !coordinates
    || !city
    || !district
    || !road
    || !buildingType
    || typeof area !== "number"
    || !Number.isFinite(area)
    || area <= 0
    || area > 500
    || typeof age !== "number"
    || !Number.isFinite(age)
    || age < 0
    || typeof floor !== "number"
    || !Number.isInteger(floor)
    || floor < 0
  ) return null;
  const payload = {
    city,
    district,
    road,
    address_text: anchor.normalized_address,
    building_type: buildingType,
    area_ping: area,
    building_age_years: age,
    floor,
    lat: coordinates.latitude,
    lng: coordinates.longitude,
  };
  const trendPayload = {
    city,
    district,
    road,
    building_type: buildingType,
    area_ping: area,
    building_age_years: age,
    horizon_months: [6, 12, 36],
  };
  return {
    caseId: workspace.caseId,
    revision: workspace.revision,
    fingerprint: buildInputFingerprint({
      channel: "valuation",
      caseId: workspace.caseId,
      revision: workspace.revision,
      journeyAnchorId: anchor.journey_anchor_id,
      normalizedAddress: anchor.normalized_address,
      coordinates,
      payload,
    }),
    identity: identityExpectation(anchor),
    payload,
    trendPayload,
  };
}

export function classifyMarketRefresh(result: MarketResult) {
  const state = getMarketCommercialState(result);
  return { ...state, shouldPersist: state.query === "succeeded" };
}

export function classifyValuationRefresh(result: unknown) {
  const state = getValuationCommercialState(result);
  return { ...state, shouldPersist: getActionableValuation(result) !== null };
}

export function canCommitMarketPriceResponse(
  current: RefreshCommitContext,
  response: RefreshCommitContext,
): boolean {
  return current.caseId === response.caseId && canCommitEvidence({
    currentRevision: current.revision,
    responseRevision: response.revision,
    currentFingerprint: current.fingerprint,
    responseFingerprint: response.fingerprint,
  });
}
