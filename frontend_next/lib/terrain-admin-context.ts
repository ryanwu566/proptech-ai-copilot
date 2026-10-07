import type { LocationInsightResult } from "./api";

export type AcceptedTerrainAdministrativeContext = { city?: string; district?: string };

export function acceptedTerrainAdministrativeContext(location: LocationInsightResult | undefined): AcceptedTerrainAdministrativeContext {
  if (location?.geocoding_acceptance?.accepted_for_analysis !== true) return {};
  const village = location.village_resolution;
  if (village?.status !== "resolved") return {};
  const city = typeof village.county === "string" ? village.county.trim() : "";
  const district = typeof village.town === "string" ? village.town.trim() : "";
  return { ...(city ? { city } : {}), ...(district ? { district } : {}) };
}
