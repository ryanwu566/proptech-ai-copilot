import type { PropertyGraphDTO } from "@/lib/vnext-identity-contract";
import type {
  CaseParcelSetDTO,
  ParcelMemberReviewStatus,
  ParcelSetStatus,
} from "@/lib/vnext-case-parcel-set-contract";

export type ParcelGraphCrossReference =
  | { kind: "missing" }
  | { kind: "ambiguous" }
  | {
    kind: "matched";
    displayLabel: string;
    referenceStatus: PropertyGraphDTO["nodes"][number]["status"];
    sourceId: string | null;
    sourceEnvironment: "production" | "demo" | "test" | null;
  };

export type ParcelInvestigationMember = {
  memberId: string;
  parcelIdentityReferenceId: string;
  position: number;
  reviewStatus: ParcelMemberReviewStatus;
  active: boolean;
  crossReference: ParcelGraphCrossReference;
};

export type ParcelInvestigationModel = {
  status: ParcelSetStatus;
  version: number;
  crossReferenceMayBeIncomplete: boolean;
  members: ParcelInvestigationMember[];
};

export function buildParcelInvestigation(
  parcelSet: CaseParcelSetDTO,
  graph: PropertyGraphDTO,
): ParcelInvestigationModel {
  return {
    status: parcelSet.status,
    version: parcelSet.version,
    crossReferenceMayBeIncomplete: Boolean(graph.next_cursor),
    members: parcelSet.members.map((member) => {
      const matches = graph.nodes.filter((node) => (
        node.node_type === "parcel"
        && node.record_id === member.parcel_identity_reference_id
      ));
      const crossReference: ParcelGraphCrossReference = matches.length === 0
        ? { kind: "missing" }
        : matches.length > 1
          ? { kind: "ambiguous" }
          : {
              kind: "matched",
              displayLabel: matches[0].display_label,
              referenceStatus: matches[0].status,
              sourceId: matches[0].source?.source_id ?? null,
              sourceEnvironment: matches[0].source?.environment ?? null,
            };
      return {
        memberId: member.parcel_set_member_id,
        parcelIdentityReferenceId: member.parcel_identity_reference_id,
        position: member.position,
        reviewStatus: member.review_status,
        active: parcelSet.active_member_id === member.parcel_set_member_id,
        crossReference,
      };
    }),
  };
}
