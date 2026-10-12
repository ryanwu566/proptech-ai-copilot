import type { JourneyPropertyContext } from "./location-market-journey";
import type { ValuationInputs } from "./valuation-share";

export type JourneyValuationFormInputs = Omit<ValuationInputs, "area_ping" | "building_age_years" | "floor"> & {
  address_text: string; area_ping: number | undefined; building_age_years: number | undefined; floor: number | undefined;
};

function cityKey(city: string | undefined): string { return city?.trim().replaceAll("台", "臺") ?? ""; }
export function journeyValuationCitiesMatch(first: string | undefined, second: string | undefined): boolean { return cityKey(first) === cityKey(second); }

// Form defaults are display assumptions. Reading them does not make journey facts known.
export function getJourneyValuationFormInputs(context: JourneyPropertyContext): JourneyValuationFormInputs {
  return {
    city: context.city ?? "", district: context.district ?? "", road: context.road ?? "",
    address_text: context.addressSummary ?? "", building_type: context.buildingType || "住宅大樓",
    area_ping: context.areaPing ?? 30, building_age_years: context.buildingAgeYears ?? 15, floor: context.floor ?? 8,
  };
}

// Publish only fields the user edited, or the full payload they explicitly submitted.
export function getJourneyValuationInputPatch(inputs: Partial<JourneyValuationFormInputs>, context?: JourneyPropertyContext): Partial<JourneyPropertyContext> {
  return {
    ...("city" in inputs ? { city: context?.city && cityKey(inputs.city) === cityKey(context.city) ? context.city : inputs.city } : {}),
    ...("district" in inputs ? { district: inputs.district } : {}),
    ...("road" in inputs ? { road: inputs.road } : {}),
    ...("address_text" in inputs ? { addressSummary: inputs.address_text } : {}),
    ...("building_type" in inputs ? { buildingType: inputs.building_type } : {}),
    ...("area_ping" in inputs ? { areaPing: inputs.area_ping } : {}),
    ...("building_age_years" in inputs ? { buildingAgeYears: inputs.building_age_years } : {}),
    ...("floor" in inputs ? { floor: inputs.floor } : {}),
  };
}

export function journeyValuationInputsMatchContext(inputs: JourneyValuationFormInputs, context: JourneyPropertyContext): boolean {
  const incoming = getJourneyValuationFormInputs(context);
  return (Object.keys(incoming) as (keyof JourneyValuationFormInputs)[]).every(key => {
    const actual = inputs[key], expected = incoming[key];
    if (key === "city") return cityKey(inputs.city) === cityKey(context.city);
    const numericContext = key === "area_ping" ? context.areaPing : key === "building_age_years" ? context.buildingAgeYears : key === "floor" ? context.floor : null;
    if (numericContext === undefined && (actual === undefined || typeof actual === "number" && (!Number.isFinite(actual) || actual < 0))) return true;
    return typeof actual === "string" && typeof expected === "string" ? actual.trim() === expected.trim() : actual === expected;
  });
}

export function getSubmittedJourneyValuationInputs(inputs: JourneyValuationFormInputs): (ValuationInputs & { address_text: string }) | null {
  const { area_ping, building_age_years, floor } = inputs;
  if (!inputs.city.trim() || !inputs.district.trim() || !inputs.road.trim()
    || typeof area_ping !== "number" || !Number.isFinite(area_ping) || area_ping <= 0
    || typeof building_age_years !== "number" || !Number.isFinite(building_age_years) || building_age_years < 0
    || typeof floor !== "number" || !Number.isFinite(floor) || floor < 0) return null;
  return { ...inputs, area_ping, building_age_years, floor };
}
