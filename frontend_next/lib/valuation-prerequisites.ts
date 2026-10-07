import type { JourneyPropertyContext } from "./location-market-journey";

export type ValuationSelection = { city: string; district: string; road: string };
export type ValuationPrerequisiteLists = { cities: string[]; districts: string[]; roads: string[] };

export function initialValuationSelection(
  context: Pick<JourneyPropertyContext, "city" | "district" | "road"> | undefined,
  embedded: boolean,
): ValuationSelection {
  return {
    city: context?.city?.trim() ?? (embedded ? "" : "台北市"),
    district: context?.district?.trim() ?? (embedded ? "" : "大安區"),
    road: context?.road?.trim() ?? "",
  };
}

export async function loadValuationPrerequisites(
  source: {
    cities(): Promise<string[]>;
    districts(city: string): Promise<string[]>;
    roads(city: string, district: string): Promise<string[]>;
  },
  selection: ValuationSelection,
): Promise<ValuationPrerequisiteLists> {
  let providerCities: string[] = [];
  let providerDistricts: string[] = [];
  let providerRoads: string[] = [];
  try { providerCities = await source.cities(); } catch {}
  if (selection.city) {
    try { providerDistricts = await source.districts(selection.city); } catch {}
  }
  if (selection.city && selection.district) {
    try { providerRoads = await source.roads(selection.city, selection.district); } catch {}
  }
  const cities = selection.city && !providerCities.includes(selection.city)
    ? [selection.city, ...providerCities]
    : providerCities;
  const districts = selection.district && !providerDistricts.includes(selection.district)
    ? [selection.district, ...providerDistricts]
    : providerDistricts;
  const roads = selection.road && !providerRoads.includes(selection.road)
    ? [selection.road, ...providerRoads]
    : providerRoads;
  return { cities, districts, roads };
}
