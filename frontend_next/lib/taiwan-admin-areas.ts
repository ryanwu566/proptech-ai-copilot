import registry from "./taiwan-admin-areas.json";

export type TaiwanAdminArea = {
  county: string;
  districts: string[];
};

type TaiwanAdminAreaRegistry = {
  schema_version: string;
  areas: TaiwanAdminArea[];
};

const REGISTRY = registry as TaiwanAdminAreaRegistry;

export const TAIWAN_ADMIN_AREAS: TaiwanAdminArea[] = REGISTRY.areas;
export const TAIWAN_COUNTIES = TAIWAN_ADMIN_AREAS.map((area) => area.county);

const COUNTY_ALIAS = new Map<string, string>(
  TAIWAN_COUNTIES.flatMap((county) => [
    [normalizeKey(county), county],
    [normalizeKey(county.replace("臺", "台")), county],
    [normalizeKey(county.replace(/[市縣]$/, "")), county],
    [normalizeKey(county.replace("臺", "台").replace(/[市縣]$/, "")), county],
  ]),
);

export function normalizeTaiwanCounty(value: string): string {
  return COUNTY_ALIAS.get(normalizeKey(value)) ?? "";
}

export function getDistrictsForCounty(county: string): string[] {
  const canonicalCounty = normalizeTaiwanCounty(county);
  return TAIWAN_ADMIN_AREAS.find((area) => area.county === canonicalCounty)?.districts ?? [];
}

export function normalizeTaiwanDistrict(county: string, value: string): string {
  const normalizedValue = normalizeKey(value);
  if (!normalizedValue) return "";
  const districts = getDistrictsForCounty(county);
  return districts.find((district) => normalizeKey(district) === normalizedValue) ?? "";
}

function normalizeKey(value: string): string {
  return value.trim().replace(/\s+/g, "").replace(/臺/g, "台");
}
