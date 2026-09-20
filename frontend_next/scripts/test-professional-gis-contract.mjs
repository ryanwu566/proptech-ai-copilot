import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function transpile(relativePath) {
  const sourcePath = path.join(frontendRoot, relativePath);
  const result = ts.transpileModule(fs.readFileSync(sourcePath, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
    fileName: sourcePath,
    reportDiagnostics: true,
  });
  const errors = (result.diagnostics ?? []).filter((diagnostic) => diagnostic.category === ts.DiagnosticCategory.Error);
  if (errors.length > 0) {
    throw new Error(ts.formatDiagnostics(errors, {
      getCanonicalFileName: (name) => name,
      getCurrentDirectory: () => frontendRoot,
      getNewLine: () => "\n",
    }));
  }
  return result.outputText;
}

function dataModule(source) {
  return `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
}

const identityModuleUrl = dataModule(transpile("lib/vnext-identity-contract.ts"));
const parcelContractSource = transpile("lib/vnext-case-parcel-set-contract.ts")
  .replaceAll('"@/lib/vnext-identity-contract"', JSON.stringify(identityModuleUrl));
const parcelContractModuleUrl = dataModule(parcelContractSource);
const parcelContract = await import(parcelContractModuleUrl);
const identityContract = await import(identityModuleUrl);
const { parseCaseParcelSet } = parcelContract;
const { VNextContractError } = identityContract;
const professionalGis = await import(dataModule(transpile("lib/professional-gis.ts")));
const { buildParcelInvestigation } = professionalGis;

const apiModuleUrl = dataModule('export const API_BASE = "https://api.example";');
const authModuleUrl = dataModule(`
  export async function getVNextAccessToken() { return { status: "authenticated", accessToken: "client-test-token" }; }
  export function getVNextSessionGeneration() { return 11; }
  export function isVNextSessionGenerationCurrent(generation) { return generation === 11; }
  export async function expireVNextSession() { return true; }
`);
const manualIdentityModuleUrl = dataModule(`
  export function buildingHypothesisBody() { throw new Error("not used"); }
  export function parcelBuildingRelationBody() { throw new Error("not used"); }
  export function parcelHypothesisBody() { throw new Error("not used"); }
`);
const clientSource = transpile("lib/vnext-identity-client.ts")
  .replaceAll('"@/lib/api"', JSON.stringify(apiModuleUrl))
  .replaceAll('"@/lib/vnext-auth-session"', JSON.stringify(authModuleUrl))
  .replaceAll('"@/lib/vnext-identity-contract"', JSON.stringify(identityModuleUrl))
  .replaceAll('"@/lib/vnext-case-parcel-set-contract"', JSON.stringify(parcelContractModuleUrl))
  .replaceAll('"@/lib/vnext-manual-identity"', JSON.stringify(manualIdentityModuleUrl));
const { vnextIdentityClient } = await import(dataModule(clientSource));

const CASE_ID = "11111111-1111-4111-8111-111111111111";
const WORKSPACE_ID = "22222222-2222-4222-8222-222222222222";
const SET_ID = "33333333-3333-4333-8333-333333333333";
const MEMBER_A = "44444444-4444-4444-8444-444444444444";
const MEMBER_B = "55555555-5555-4555-8555-555555555555";
const REF_A = "66666666-6666-4666-8666-666666666666";
const REF_B = "77777777-7777-4777-8777-777777777777";
const NOW = "2026-09-20T08:00:00Z";

function member(overrides = {}) {
  return {
    parcel_set_member_id: MEMBER_A,
    parcel_identity_reference_id: REF_A,
    position: 2,
    review_status: "candidate",
    created_at: NOW,
    updated_at: NOW,
    ...overrides,
  };
}

function validDto(overrides = {}) {
  return {
    parcel_set_id: SET_ID,
    workspace_id: WORKSPACE_ID,
    case_id: CASE_ID,
    status: "draft",
    version: 1,
    active_member_id: null,
    created_at: NOW,
    updated_at: NOW,
    reviewed_at: null,
    members: [
      member(),
      member({
        parcel_set_member_id: MEMBER_B,
        parcel_identity_reference_id: REF_B,
        position: 7,
        review_status: "case_rejected",
      }),
    ],
    ...overrides,
  };
}

function parse(value) {
  return parseCaseParcelSet(value, { caseId: CASE_ID, workspaceId: WORKSPACE_ID });
}

function expectContractError(value, expectedPath) {
  assert.throws(
    () => parse(value),
    (error) => error instanceof VNextContractError && (!expectedPath || error.path === expectedPath),
  );
}

const parsed = parse(validDto());
assert.deepEqual(parsed.members.map((item) => item.position), [2, 7]);
assert.equal(parsed.status, "draft");
assert.equal(parsed.active_member_id, null);

const active = parse(validDto({ status: "case_reviewed", active_member_id: MEMBER_B, reviewed_at: NOW }));
assert.equal(active.active_member_id, MEMBER_B);
assert.equal(active.status, "case_reviewed");

expectContractError(validDto({ parcel_set_id: "not-a-uuid" }), "case_parcel_set.parcel_set_id");
expectContractError(validDto({ created_at: "2026-09-20" }), "case_parcel_set.created_at");
expectContractError(validDto({ created_at: "2026-02-30T08:00:00Z" }), "case_parcel_set.created_at");
expectContractError(validDto({ version: 0 }), "case_parcel_set.version");
expectContractError(validDto({ status: "approved" }), "case_parcel_set.status");
expectContractError(validDto({ members: [member({ position: 0 })] }), "case_parcel_set.members[0].position");
expectContractError(validDto({ members: [member({ position: 101 })] }), "case_parcel_set.members[0].position");
expectContractError(validDto({ members: [member({ review_status: "selected" })] }), "case_parcel_set.members[0].review_status");

const tooManyMembers = Array.from({ length: 101 }, (_, index) => member({ position: index + 1 }));
expectContractError(validDto({ members: tooManyMembers }), "case_parcel_set.members");

expectContractError(validDto({ members: [member(), member({ parcel_identity_reference_id: REF_B, position: 7 })] }), "case_parcel_set.members.parcel_set_member_id");
expectContractError(validDto({ members: [member(), member({ parcel_set_member_id: MEMBER_B, position: 7 })] }), "case_parcel_set.members.parcel_identity_reference_id");
expectContractError(validDto({ members: [member(), member({ parcel_set_member_id: MEMBER_B, parcel_identity_reference_id: REF_B, position: 2 })] }), "case_parcel_set.members.position");

const descending = validDto({
  members: [
    member({ position: 7 }),
    member({ parcel_set_member_id: MEMBER_B, parcel_identity_reference_id: REF_B, position: 2 }),
  ],
});
expectContractError(descending, "case_parcel_set.members.order");
assert.deepEqual(descending.members.map((item) => item.position), [7, 2]);

expectContractError({ ...validDto(), unexpected: true }, "case_parcel_set.unexpected");
expectContractError(validDto({ members: [{ ...member(), unexpected: true }] }), "case_parcel_set.members[0].unexpected");
const rootWithEmptyUnknownKey = validDto();
rootWithEmptyUnknownKey[""] = true;
rootWithEmptyUnknownKey.unexpected_after_empty = true;
expectContractError(rootWithEmptyUnknownKey, "case_parcel_set.");
const memberWithEmptyUnknownKey = member();
memberWithEmptyUnknownKey[""] = true;
memberWithEmptyUnknownKey.unexpected_after_empty = true;
expectContractError(validDto({ members: [memberWithEmptyUnknownKey] }), "case_parcel_set.members[0].");
expectContractError(validDto({ active_member_id: "88888888-8888-4888-8888-888888888888" }), "case_parcel_set.active_member_id");
expectContractError(validDto({ case_id: "99999999-9999-4999-8999-999999999999" }), "case_parcel_set.case_id");
expectContractError(validDto({ workspace_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" }), "case_parcel_set.workspace_id");

const validLeapDate = "2024-02-29T23:59:59.123456789+14:00";
const leapDateDto = parse(validDto({
  created_at: validLeapDate,
  members: [member({ created_at: validLeapDate })],
}));
assert.equal(leapDateDto.created_at, validLeapDate);
assert.equal(leapDateDto.members[0].created_at, validLeapDate);

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;
const clientRequests = [];
globalThis.window = { setTimeout, clearTimeout };
globalThis.fetch = async (url, options) => {
  clientRequests.push({ url: String(url), options });
  return new Response(JSON.stringify(validDto()), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
};
try {
  const clientParcelSet = await vnextIdentityClient.caseParcelSet(CASE_ID, WORKSPACE_ID);
  assert.equal(clientParcelSet.case_id, CASE_ID);
  assert.equal(clientParcelSet.workspace_id, WORKSPACE_ID);
  assert.equal(clientRequests.length, 1);
  assert.equal(clientRequests[0].url, `https://api.example/v1/cases/${CASE_ID}/parcel-set`);
  assert.equal(clientRequests[0].options.method, "GET");
  assert.equal(clientRequests[0].options.body, undefined);
  assert.equal(clientRequests[0].options.headers.get("Authorization"), "Bearer client-test-token");
} finally {
  globalThis.fetch = originalFetch;
  globalThis.window = originalWindow;
}

const PROPERTY_ID = "88888888-8888-4888-8888-888888888888";
const PROPERTY_NODE_ID = "99999999-9999-4999-8999-999999999999";
const PARCEL_NODE_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const PARCEL_NODE_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const OTHER_REF = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const NEXT_CURSOR = `next.${"a".repeat(43)}`;

function propertyDto() {
  return {
    property_entity_id: PROPERTY_ID,
    workspace_id: WORKSPACE_ID,
    lifecycle_state: "unverified",
    display_label: "Loaded PropertyEntity",
    confirmation_summary: {
      available: false,
      human_confirmed: false,
      confirmation_id: null,
      confirmed_at: null,
      confirmed_by: null,
      resolution_id: null,
    },
    version: 1,
    created_at: NOW,
    updated_at: NOW,
  };
}

function source() {
  return {
    source_id: "approved-source",
    source_type: "official",
    environment: "production",
    provider_id: "provider-must-not-leak",
    source_record_id: "record-must-not-leak",
    retrieved_at: NOW,
  };
}

function parcelNode(overrides = {}) {
  return {
    node_id: PARCEL_NODE_A,
    node_type: "parcel",
    record_id: REF_A,
    display_label: "Bounded label",
    status: "observed",
    source: source(),
    valid_from: null,
    valid_to: null,
    ...overrides,
  };
}

function graphWith(nodes, nextCursor = null) {
  return {
    property: propertyDto(),
    nodes: [
      {
        node_id: PROPERTY_NODE_ID,
        node_type: "property",
        record_id: PROPERTY_ID,
        display_label: "Loaded PropertyEntity",
        status: null,
        source: null,
        valid_from: null,
        valid_to: null,
      },
      ...nodes,
    ],
    relations: [],
    as_of: NOW,
    next_cursor: nextCursor,
  };
}

const matched = buildParcelInvestigation(
  parse(validDto({ members: [member()] })),
  graphWith([
    parcelNode(),
    parcelNode({ node_id: PARCEL_NODE_B, node_type: "building", display_label: "Wrong type" }),
    parcelNode({ node_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", record_id: OTHER_REF, display_label: "Wrong reference" }),
  ]),
);
assert.deepEqual(matched.members[0].crossReference, {
  kind: "matched",
  displayLabel: "Bounded label",
  referenceStatus: "observed",
  sourceId: "approved-source",
  sourceEnvironment: "production",
});

const missing = buildParcelInvestigation(
  parse(validDto({ members: [member()] })),
  graphWith([parcelNode({ record_id: OTHER_REF })], NEXT_CURSOR),
);
assert.deepEqual(missing.members[0].crossReference, { kind: "missing" });
assert.equal(missing.crossReferenceMayBeIncomplete, true);

const ambiguous = buildParcelInvestigation(
  parse(validDto({ members: [member()] })),
  graphWith([
    parcelNode({ display_label: "Duplicate A" }),
    parcelNode({ node_id: PARCEL_NODE_B, display_label: "Duplicate B" }),
  ]),
);
assert.deepEqual(ambiguous.members[0].crossReference, { kind: "ambiguous" });

for (const reviewStatus of ["candidate", "case_selected", "case_rejected"]) {
  const activeModel = buildParcelInvestigation(
    parse(validDto({ active_member_id: MEMBER_A, members: [member({ review_status: reviewStatus })] })),
    graphWith([]),
  );
  assert.equal(activeModel.members[0].active, true);
  assert.equal(activeModel.members[0].reviewStatus, reviewStatus);
}

process.stdout.write("PROFESSIONAL_GIS_CONTRACT=pass\n");
