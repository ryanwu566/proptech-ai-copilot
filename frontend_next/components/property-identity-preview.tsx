"use client";

import { useMemo, useState } from "react";
import { PropertyIdentityReview, type PropertyIdentityReviewApi } from "@/components/property-identity-review";
import { parseProperty, parsePropertyEvidence, parsePropertyGraph } from "@/lib/vnext-identity-contract";
import { VNextOutcomeUnknownError } from "@/lib/vnext-identity-client";

const WORKSPACE = "11111111-1111-4111-8111-111111111111";
const PROPERTY = "22222222-2222-4222-8222-222222222222";
const CONFIRMATION = "33333333-3333-4333-8333-333333333333";
const PROPERTY_NODE = "44444444-4444-4444-8444-444444444444";
const PARCEL_NODE = "55555555-5555-4555-8555-555555555555";
const BUILDING_NODE = "66666666-6666-4666-8666-666666666666";
const PROPOSED_PARCEL_NODE = "77777777-7777-4777-8777-777777777777";
const PROPOSED_BUILDING_NODE = "88888888-8888-4888-8888-888888888888";
const EVIDENCE = "99999999-9999-4999-8999-999999999999";
const DATE = "2026-09-01T00:00:00Z";
const source = { source_id: "fixture-user", source_type: "user", environment: "production", provider_id: null, source_record_id: null, retrieved_at: DATE };

const property = parseProperty({
  property_entity_id: PROPERTY, workspace_id: WORKSPACE, lifecycle_state: "active", display_label: "示範房產 · 臺北市中正區",
  confirmation_summary: { available: true, human_confirmed: true, confirmation_id: CONFIRMATION, confirmed_at: DATE, confirmed_by: WORKSPACE, resolution_id: CONFIRMATION },
  version: 1, created_at: DATE, updated_at: DATE,
});

const otherProperty = parseProperty({
  property_entity_id: "abababab-abab-4bab-8bab-abababababab", workspace_id: "cdcdcdcd-cdcd-4dcd-8dcd-cdcdcdcdcdcd",
  lifecycle_state: "unverified", display_label: "另一個示範房產",
  confirmation_summary: { available: false, human_confirmed: false, confirmation_id: null, confirmed_at: null, confirmed_by: null, resolution_id: null },
  version: 1, created_at: DATE, updated_at: DATE,
});

const nodes = [
  { node_id: PROPERTY_NODE, node_type: "property", record_id: PROPERTY, display_label: property.display_label, status: null, source: null, valid_from: null, valid_to: null },
  { node_id: PARCEL_NODE, node_type: "parcel", record_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", display_label: "仁愛段 123 地號", status: "observed", source, valid_from: DATE, valid_to: null },
  { node_id: BUILDING_NODE, node_type: "building", record_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", display_label: "仁愛段 567 建號", status: "disputed", source, valid_from: DATE, valid_to: null },
  { node_id: PROPOSED_PARCEL_NODE, node_type: "parcel", record_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", display_label: "仁愛段 124 地號", status: "unverified", source, valid_from: DATE, valid_to: null },
  { node_id: PROPOSED_BUILDING_NODE, node_type: "building", record_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", display_label: "仁愛段 568 建號", status: "unverified", source, valid_from: DATE, valid_to: null },
];

function relation(id: string, from: string, to: string, type: string, status: string, direction = "directed") {
  return { relation_id: id, from_node_id: from, to_node_id: to, relation_type: type, direction, confidence: null, confidence_method: null,
    source, evidence_id: EVIDENCE, status, valid_from: DATE, valid_to: null, supersedes_relation_id: null, created_at: DATE,
    confirmation_id: status === "confirmed" ? CONFIRMATION : null };
}

const graphFixtures = {
  confirmed: parsePropertyGraph({ property, nodes: [nodes[0], nodes[1]], relations: [relation("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", PROPERTY_NODE, PARCEL_NODE, "property_parcel", "confirmed")], as_of: null, next_cursor: null }),
  disputed: parsePropertyGraph({ property, nodes: [nodes[0], nodes[2]], relations: [relation("ffffffff-ffff-4fff-8fff-ffffffffffff", PROPERTY_NODE, BUILDING_NODE, "property_building", "disputed")], as_of: null, next_cursor: null }),
  proposed: parsePropertyGraph({ property, nodes: [nodes[0], nodes[3], nodes[4]], relations: [
    relation("12121212-1212-4121-8121-121212121212", PROPERTY_NODE, PROPOSED_PARCEL_NODE, "property_parcel", "proposed"),
    relation("13131313-1313-4131-8131-131313131313", PROPERTY_NODE, PROPOSED_BUILDING_NODE, "property_building", "proposed"),
    relation("14141414-1414-4141-8141-141414141414", PROPOSED_PARCEL_NODE, PROPOSED_BUILDING_NODE, "parcel_building", "proposed", "bidirectional"),
  ], as_of: null, next_cursor: null }),
};

const sharedGraph = parsePropertyGraph({ property, nodes: [nodes[0], nodes[1],
  { node_id: "15151515-1515-4151-8151-151515151515", node_type: "property", record_id: "16161616-1616-4161-8161-161616161616", display_label: "外部房產", status: null, source: null, valid_from: null, valid_to: null },
  { node_id: "17171717-1717-4171-8171-171717171717", node_type: "building", record_id: "18181818-1818-4181-8181-181818181818", display_label: "外部房產的地籍建號", status: "observed", source, valid_from: DATE, valid_to: null },
], relations: [
  ...graphFixtures.confirmed.relations,
  relation("19191919-1919-4191-8191-191919191919", "15151515-1515-4151-8151-151515151515", PARCEL_NODE, "property_parcel", "confirmed"),
  relation("20202020-2020-4202-8202-202020202020", PARCEL_NODE, "17171717-1717-4171-8171-171717171717", "parcel_building", "confirmed", "bidirectional"),
  relation("21212121-2121-4212-8212-212121212121", "15151515-1515-4151-8151-151515151515", "17171717-1717-4171-8171-171717171717", "property_building", "confirmed"),
], as_of: null, next_cursor: null });

const evidenceFixture = parsePropertyEvidence({ property, evidence: [{
  evidence_id: EVIDENCE, workspace_id: WORKSPACE, fact_type: "manual.cadastral.observation", value: { fixture: true }, has_private_value_reference: false,
  value_schema: "fixture-v1", source, effective_from: DATE, effective_to: null, expires_at: null, coverage_status: "unknown", coverage: {},
  status: "user_provided", quality_confidence: null, quality_method: null, quality_status: "not_checked", quality: {},
  license_status: "not_applicable", license_reference: null, license: {}, lineage: {}, content_hash: "f".repeat(64), version: 1,
  supersedes_evidence_id: null, created_at: DATE,
}], next_cursor: null });

const failedEvidence = parsePropertyEvidence({ property, evidence: evidenceFixture.evidence.map((item) => ({ ...item, quality_status: "failed" })), next_cursor: null });
const partnerUnverifiedEvidence = parsePropertyEvidence({ property, evidence: evidenceFixture.evidence.map((item) => ({
  ...item, status: "unverified", source: { ...source, source_type: "partner", source_id: "fixture-partner" },
})), next_cursor: null });

function fixtureApi(state: string): PropertyIdentityReviewApi {
  const emptyGraph = parsePropertyGraph({ property, nodes: [nodes[0]], relations: [], as_of: null, next_cursor: null });
  const emptyEvidence = parsePropertyEvidence({ property, evidence: [], next_cursor: null });
  let proposedGraph = graphFixtures.proposed;
  let currentEvidence = evidenceFixture;
  function addProposedReference(kind: "parcel" | "building", label: string) {
    const referenceId = crypto.randomUUID();
    const nodeId = crypto.randomUUID();
    const relationId = crypto.randomUUID();
    proposedGraph = parsePropertyGraph({ ...proposedGraph,
      nodes: [...proposedGraph.nodes, { node_id: nodeId, node_type: kind, record_id: referenceId, display_label: label,
        status: "unverified", source, valid_from: DATE, valid_to: null }],
      relations: [relation(relationId, PROPERTY_NODE, nodeId, `property_${kind}`, "proposed"), ...proposedGraph.relations],
    });
    if (kind === "building") currentEvidence = parsePropertyEvidence({ property, evidence: [{ ...evidenceFixture.evidence[0],
      evidence_id: crypto.randomUUID(), fact_type: "building.manual_cadastral_claim.v1" }, ...currentEvidence.evidence], next_cursor: null });
    return { property_entity_id: PROPERTY, identity_reference_id: referenceId, relation_id: relationId,
      display_value: label, reference_status: "unverified" as const, relation_status: "proposed" as const };
  }
  return {
    async graphByStatus(_propertyId, status) {
      const prior = JSON.parse(window.sessionStorage.getItem("identity-preview-graph-requests") ?? "[]") as string[];
      window.sessionStorage.setItem("identity-preview-graph-requests", JSON.stringify([...prior, status]));
      if (state === "slow") await new Promise((resolve) => setTimeout(resolve, 900));
      if (state === "network-error") throw new VNextOutcomeUnknownError();
      if (state === "error") throw new Error("fixture load failure");
      return state === "empty" ? emptyGraph : state === "shared" && status === "confirmed" ? sharedGraph : status === "proposed" ? proposedGraph : graphFixtures[status];
    },
    async evidence() {
      if (state === "slow") await new Promise((resolve) => setTimeout(resolve, 900));
      if (state === "error") throw new Error("fixture load failure");
      return state === "empty" ? emptyEvidence : state === "quality-failed" ? failedEvidence : state === "source-unverified" ? partnerUnverifiedEvidence : currentEvidence;
    },
    async createParcelHypothesis(_propertyId, _workspaceId, components) {
      return addProposedReference("parcel", `${components.section} ${components.land_number} 地號`);
    },
    async createBuildingHypothesis(_propertyId, _workspaceId, components) {
      return addProposedReference("building", `${components.section} ${components.building_number} 建號`);
    },
    async createParcelBuildingRelation(_workspaceId, parcelId, buildingId) {
      const allNodes = [...proposedGraph.nodes, ...graphFixtures.confirmed.nodes, ...graphFixtures.disputed.nodes];
      const parcelNode = allNodes.find((node) => node.record_id === parcelId && node.node_type === "parcel");
      const buildingNode = allNodes.find((node) => node.record_id === buildingId && node.node_type === "building");
      if (!parcelNode || !buildingNode) throw new Error("Existing fixture references required");
      const mergedNodes = [...new Map([...proposedGraph.nodes, parcelNode, buildingNode].map((node) => [node.node_id, node] as const)).values()];
      const relationId = crypto.randomUUID();
      proposedGraph = parsePropertyGraph({ ...proposedGraph, nodes: mergedNodes,
        relations: [relation(relationId, parcelNode.node_id, buildingNode.node_id, "parcel_building", "proposed", "bidirectional"), ...proposedGraph.relations] });
      currentEvidence = parsePropertyEvidence({ property, evidence: [{ ...evidenceFixture.evidence[0],
        evidence_id: crypto.randomUUID(), fact_type: "parcel_building.manual_relation.v1" }, ...currentEvidence.evidence], next_cursor: null });
      return { workspace_id: WORKSPACE, parcel_identity_reference_id: parcelId, building_identity_reference_id: buildingId,
        relation_id: relationId, direction: "bidirectional", relation_status: "proposed" };
    },
  };
}

export function PropertyIdentityPreview({ state }: { state: string }) {
  const api = useMemo(() => fixtureApi(state), [state]);
  const [switched, setSwitched] = useState(false);
  return <>
    {state === "switch" && <button type="button" onClick={() => setSwitched(true)}>切換示範房產</button>}
    <PropertyIdentityReview property={switched ? otherProperty : property} role="member" api={api} preview />
  </>;
}
