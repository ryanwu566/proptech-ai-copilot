import { VNextContractError } from "@/lib/vnext-identity-contract";

export type ParcelComponents = {
  county_city: string;
  district_township: string;
  section: string;
  subsection: string | null;
  land_number: string;
};

export type BuildingComponents = {
  county_city: string;
  district_township: string;
  section: string;
  subsection_status: "specified" | "not_applicable";
  subsection: string | null;
  building_number: string;
};

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function id(value: string): string {
  if (!UUID.test(value)) throw new VNextContractError("request.identifier");
  return value;
}

function required(value: string, field: string): string {
  const selected = value.trim();
  if (!selected || selected.length > 160) throw new VNextContractError(`request.${field}`);
  return selected;
}

function optional(value: string | null): string | null {
  const selected = value?.trim() ?? "";
  if (selected.length > 160) throw new VNextContractError("request.subsection");
  return selected || null;
}

export function parcelHypothesisBody(workspaceId: string, input: ParcelComponents) {
  return {
    workspace_id: id(workspaceId),
    components: {
      county_city: required(input.county_city, "county_city"),
      district_township: required(input.district_township, "district_township"),
      section: required(input.section, "section"),
      subsection: optional(input.subsection),
      land_number: required(input.land_number, "land_number"),
    },
  };
}

export function buildingHypothesisBody(workspaceId: string, input: BuildingComponents) {
  const subsectionStatus = input.subsection_status;
  const subsection = optional(input.subsection);
  if ((subsectionStatus !== "specified" && subsectionStatus !== "not_applicable")
    || (subsectionStatus === "specified" && !subsection) || (subsectionStatus === "not_applicable" && subsection)) {
    throw new VNextContractError("request.subsection");
  }
  return {
    workspace_id: id(workspaceId),
    identifier_kind: "cadastral_building_number" as const,
    components: {
      county_city: required(input.county_city, "county_city"),
      district_township: required(input.district_township, "district_township"),
      section: required(input.section, "section"),
      subsection_status: subsectionStatus,
      subsection,
      building_number: required(input.building_number, "building_number"),
    },
  };
}

export function parcelBuildingRelationBody(workspaceId: string, parcelReferenceId: string, buildingReferenceId: string) {
  return {
    workspace_id: id(workspaceId),
    parcel_identity_reference_id: id(parcelReferenceId),
    building_identity_reference_id: id(buildingReferenceId),
  };
}
