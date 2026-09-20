# Professional GIS Workspace V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a truthful read-only Parcel/GIS investigation canvas backed only by the authorized Case Parcel Set GET and the currently loaded PropertyEntity graph page.

**Architecture:** A focused strict contract validates the Parcel Set and its route/workspace bindings, the existing VNext client exposes one GET-only method, and a pure view-model builder performs exact loaded-page graph cross-reference with explicit duplicate ambiguity. The existing shell loads the Parcel Set only after Workspace and PropertyEntity authorization succeeds, then renders a non-geographic `PARTIAL` investigation canvas without changing Evidence behavior.

**Tech Stack:** Next.js 16, React 19, strict TypeScript, existing Supabase VNext browser session, Node contract tests, Playwright, pytest.

**Spec:** `docs/superpowers/specs/2026-09-20-professional-gis-workspace-v1-design.md`

## Global Constraints

- Read only: no Parcel Set `POST`, `PUT`, `PATCH`, or `DELETE` frontend method or request.
- Keep the existing Workspace then PropertyEntity authorization order; request the Parcel Set only after both succeed and bind.
- A route Case reference is not loaded Case truth, and no Case-to-Property attachment may be inferred.
- Treat Parcel Set 404 as ambiguous `PARCEL_SET_NOT_AVAILABLE`, never as an empty set.
- Treat a valid zero-member DTO as a loaded set distinct from 404.
- Cross-reference only exact `parcel` node type plus `record_id`; never select among duplicates.
- Validate member order as received; never sort malformed input into validity and never require contiguous positions.
- A loaded Parcel/GIS surface is `PARTIAL`, never `AVAILABLE`, because geometry is `NOT_AVAILABLE`.
- Render no Leaflet map, external tile, marker, coordinate, geometry, NLSC access, or TILE_001 dependency.
- Do not inspect or render arbitrary Evidence values; leave Evidence Rail behavior unchanged.
- Add no migrations, providers, dependencies, secrets, direct Supabase data reads, or service-role credentials.
- Preserve desktop, tablet, mobile, semantic heading/list, text status, and keyboard behavior.
- Make at most one final commit: `feat(workspace): add parcel investigation canvas`.
- Do not push or merge.

## Review Focus

- A syntactically valid DTO with an unknown root/member key must fail closed rather than carry arbitrary data; Task 1 tests both levels.
- A member sequence such as positions `2, 1` must fail rather than be silently sorted; Task 1 pins this behavior.
- Two exact graph nodes for one reference must produce `ambiguous` with no selected metadata; Task 2 pins this behavior.
- A Parcel Set request must not begin when Workspace or PropertyEntity authorization/binding fails; Task 4 records and asserts request order/absence.
- A 404 and a valid zero-member response must render different truthful states; Task 4 tests both copy paths.

---

### Task 1: Strict Case Parcel Set Contract

**Files:**
- Create: `frontend_next/lib/vnext-case-parcel-set-contract.ts`
- Create: `frontend_next/scripts/test-professional-gis-contract.mjs`
- Modify: `frontend_next/package.json`

**Interfaces:**
- Consumes: `VNextContractError` from `@/lib/vnext-identity-contract`.
- Produces: `parseCaseParcelSet(value, { caseId, workspaceId }): CaseParcelSetDTO`, `CaseParcelSetDTO`, `CaseParcelSetMemberDTO`, `ParcelSetStatus`, and `ParcelMemberReviewStatus`.

- [ ] **Step 1: Write the failing contract test harness**

Create a Node test that transpiles the real TypeScript contract and checks hand-built fixtures. The fixture must use distinct UUIDs and non-contiguous but increasing positions to prove contiguity is not required:

```js
const valid = {
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
    { parcel_set_member_id: MEMBER_A, parcel_identity_reference_id: REF_A, position: 2, review_status: "candidate", created_at: NOW, updated_at: NOW },
    { parcel_set_member_id: MEMBER_B, parcel_identity_reference_id: REF_B, position: 7, review_status: "case_rejected", created_at: NOW, updated_at: NOW },
  ],
};

assert.deepEqual(parseCaseParcelSet(valid, { caseId: CASE_ID, workspaceId: WORKSPACE_ID }).members.map((member) => member.position), [2, 7]);
```

Add literal negative cases for malformed UUID/timestamp, version 0, positions 0 and 101, invalid set/member enums, more than 100 members, duplicate member IDs, duplicate reference IDs, duplicate positions, descending order, unknown root key, unknown member key, missing active member, Case mismatch, and Workspace mismatch. For descending order, assert `VNextContractError.path === "case_parcel_set.members.order"` and verify the input array remains `[7, 2]` after failure.

- [ ] **Step 2: Run the contract test and verify RED**

Run:

```powershell
cd frontend_next
node scripts/test-professional-gis-contract.mjs
```

Expected: failure because `lib/vnext-case-parcel-set-contract.ts` or `parseCaseParcelSet` does not exist.

- [ ] **Step 3: Implement the exact parser**

Create focused validators and reject unknown keys before parsing:

```ts
const ROOT_KEYS = [
  "parcel_set_id", "workspace_id", "case_id", "status", "version",
  "active_member_id", "created_at", "updated_at", "reviewed_at", "members",
] as const;

const MEMBER_KEYS = [
  "parcel_set_member_id", "parcel_identity_reference_id", "position",
  "review_status", "created_at", "updated_at",
] as const;

export function parseCaseParcelSet(
  value: unknown,
  expected: { caseId: string; workspaceId: string },
) {
  const item = exactObjectAt(value, "case_parcel_set", ROOT_KEYS);
  const members = arrayAt(item.members, "case_parcel_set.members", parseMember, 100);
  unique(members.map((member) => member.parcel_set_member_id), "case_parcel_set.members.parcel_set_member_id");
  unique(members.map((member) => member.parcel_identity_reference_id), "case_parcel_set.members.parcel_identity_reference_id");
  unique(members.map((member) => member.position), "case_parcel_set.members.position");
  if (members.some((member, index) => index > 0 && members[index - 1].position >= member.position)) {
    throw new VNextContractError("case_parcel_set.members.order");
  }
  // Parse the remaining exact fields, validate active membership, then require
  // parsed.case_id === expected.caseId and parsed.workspace_id === expected.workspaceId.
}
```

Use `integerAt(..., 1, 100)` for positions, `integerAt(..., 1)` for version, strict ISO date parsing, and exact enum arrays. Return a newly constructed object containing only approved fields; never return or spread the source object.

- [ ] **Step 4: Add and run the focused package command**

Add:

```json
"test:workspace-contract": "node scripts/test-professional-gis-contract.mjs"
```

Run:

```powershell
npm run test:workspace-contract
npm run typecheck
```

Expected: all contract cases pass and strict TypeScript reports no errors.

### Task 2: Exact Graph Cross-reference View Model

**Files:**
- Create: `frontend_next/lib/professional-gis.ts`
- Modify: `frontend_next/scripts/test-professional-gis-contract.mjs`

**Interfaces:**
- Consumes: `CaseParcelSetDTO` and `PropertyGraphDTO`.
- Produces: `buildParcelInvestigation(parcelSet, graph): ParcelInvestigationModel` with `matched | missing | ambiguous` cross-reference states and no arbitrary graph/evidence values.

- [ ] **Step 1: Add failing exact-match tests**

Extend the Node harness with real production-module tests covering zero, one, and two exact matches. Include decoy nodes whose labels or IDs look similar but whose `node_type` or `record_id` differ:

```js
const model = buildParcelInvestigation(parcelSet, graphWith([
  parcelNode({ node_id: NODE_A, record_id: REF_A, display_label: "Bounded label" }),
]));
assert.deepEqual(model.members[0].crossReference, {
  kind: "matched",
  displayLabel: "Bounded label",
  referenceStatus: "observed",
  sourceId: "approved-source",
  sourceEnvironment: "production",
});
```

For duplicates, assert `{ kind: "ambiguous" }` exactly so no chosen label, source, or status can leak. Also verify active state stays a boolean independent of each of `candidate`, `case_selected`, and `case_rejected`, and graph `next_cursor` sets `crossReferenceMayBeIncomplete` without changing a missing match into nonexistence.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
cd frontend_next
npm run test:workspace-contract
```

Expected: failure because `buildParcelInvestigation` is absent.

- [ ] **Step 3: Implement the bounded view model**

Use only the exact approved predicate:

```ts
const matches = graph.nodes.filter((node) =>
  node.node_type === "parcel"
  && node.record_id === member.parcel_identity_reference_id
);

const crossReference = matches.length === 0
  ? { kind: "missing" as const }
  : matches.length > 1
    ? { kind: "ambiguous" as const }
    : {
        kind: "matched" as const,
        displayLabel: matches[0].display_label,
        referenceStatus: matches[0].status,
        sourceId: matches[0].source?.source_id ?? null,
        sourceEnvironment: matches[0].source?.environment ?? null,
      };
```

Return only position, member/reference IDs, review status, `active`, the bounded cross-reference, set status/version, and `Boolean(graph.next_cursor)`. Do not expose `source_record_id`, provider ID, normalized identity, evidence, relation data, or actor IDs.

- [ ] **Step 4: Run focused tests and typecheck GREEN**

Run:

```powershell
npm run test:workspace-contract
npm run typecheck
```

Expected: exact/zero/duplicate/pagination/active-state tests pass.

### Task 3: GET-only Authenticated Client

**Files:**
- Modify: `frontend_next/lib/vnext-identity-client.ts`
- Modify: `frontend_next/e2e/professional-workspace.spec.ts`

**Interfaces:**
- Consumes: `parseCaseParcelSet` and the existing private `requestJson`, `identifier`, and authenticated session flow.
- Produces: `vnextIdentityClient.caseParcelSet(caseId, workspaceId): Promise<CaseParcelSetDTO>` and no Parcel Set mutation method.

- [ ] **Step 1: Add a failing browser transport assertion**

Update the approved-read route fixture so a successful context returns a valid Parcel Set and records `{ method, pathname, hostname }`. Assert the set request is:

```ts
expect(requests.filter((request) => request.pathname.endsWith("/parcel-set"))).toEqual([{
  method: "GET",
  pathname: `/v1/cases/${CASE_ID}/parcel-set`,
  hostname: "e2e.test",
}]);
```

Also assert the complete request capture contains no `POST`, `PUT`, `PATCH`, or `DELETE`, no hostname containing `nlsc`, and no arbitrary provider host.

- [ ] **Step 2: Run the focused browser test and verify RED**

Run with retries disabled:

```powershell
cd frontend_next
npm run build:e2e
node e2e/run-e2e.cjs e2e/professional-workspace.spec.ts --retries=0 --grep "GET-only"
```

Expected: failure because no Parcel Set request occurs.

- [ ] **Step 3: Add the one read method**

Add only:

```ts
caseParcelSet: async (caseId: string, workspaceId: string): Promise<CaseParcelSetDTO> => {
  const expectedCase = identifier(caseId);
  const expectedWorkspace = identifier(workspaceId);
  return requestJson(
    `/v1/cases/${expectedCase}/parcel-set`,
    (payload) => parseCaseParcelSet(payload, { caseId: expectedCase, workspaceId: expectedWorkspace }),
  );
},
```

Do not add command keys, bodies, mutation verbs, Parcel Set idempotency helpers, or wrappers for backend mutation endpoints.

- [ ] **Step 4: Typecheck the read method**

Run:

```powershell
npm run typecheck
```

Expected: strict TypeScript passes.

### Task 4: Parcel Load State and Investigation Canvas

**Files:**
- Modify: `frontend_next/components/professional-workspace-shell.tsx`
- Modify: `frontend_next/components/professional-workspace-shell.module.css`
- Modify: `frontend_next/e2e/professional-workspace.spec.ts`

**Interfaces:**
- Consumes: `vnextIdentityClient.caseParcelSet` and `buildParcelInvestigation`.
- Produces: distinct Parcel Set states, Parcel/GIS `PARTIAL` readiness only for a valid set, and semantic investigation-canvas UI.

- [ ] **Step 1: Add failing sequencing and failure-state tests**

Add focused Playwright cases for:

```text
missing/invalid context -> no backend request
Workspace 403/404 -> no Property, graph, Evidence, or Parcel Set request
Property mismatch -> no graph, Evidence, or Parcel Set request
Parcel Set 404 -> PARCEL_SET_NOT_AVAILABLE and no “empty parcel set” claim
Parcel Set 403 -> denied copy, never empty/unavailable copy
Parcel Set malformed JSON/DTO -> invalid-response copy
Parcel Set Case mismatch -> invalid-response copy
Parcel Set Workspace mismatch -> invalid-response copy
Parcel Set transport failure -> infrastructure-error copy
expired session/configuration -> distinct copy
```

Record request events and assert the Parcel Set request event occurs after successful Workspace and Property responses. Graph, Evidence, and Parcel Set may appear in any order after that boundary.

- [ ] **Step 2: Add failing loaded-state and truth-boundary tests**

Cover valid draft/zero members separately from 404, case-reviewed one/many members, every member review state, active member with every review state, exact/zero/duplicate graph matches, and graph pagination. Assert the exact required copy:

```ts
await expect(canvas).toContainText("Parcel review set loaded; no members are currently recorded.");
await expect(canvas).toContainText("Case parcel review state does not confirm canonical Property Identity or legal parcel boundaries.");
await expect(canvas).toContainText("Case-to-Property binding is not available from an approved read in this workspace slice.");
await expect(canvas).toContainText("Additional graph records are available; parcel cross-reference may be incomplete.");
```

Assert a matched item says only “Also present in the currently loaded PropertyEntity graph page.” and a zero match says only “Reference not present in the loaded PropertyEntity graph page.” For duplicates, assert ambiguous/unavailable copy and absence of both duplicate labels.

- [ ] **Step 3: Add failing geometry, security, accessibility, and mobile tests**

Assert:

- Map Canvas contains `Geometry`, `NOT_AVAILABLE`, and “No approved parcel geometry is available in this slice.”
- Map Canvas contains no `.leaflet-container`, `svg`, `canvas`, geographic coordinate label, or marker test ID.
- captured browser requests contain no Supabase REST data API, NLSC, tile host, or provider host;
- captured methods are GET only;
- access token, graph `source_record_id`, provider ID, Evidence `value`, normalized identity sentinel, actor sentinel, and secret sentinel are absent from `body` text;
- Map Canvas and member list have semantic region/heading/list roles;
- module selection remains keyboard-focusable and `aria-pressed` changes;
- 390x844 and tablet viewports have no horizontal overflow.

- [ ] **Step 4: Run the expanded Workspace E2E and verify RED**

Run:

```powershell
npm run build:e2e
node e2e/run-e2e.cjs e2e/professional-workspace.spec.ts --retries=0
```

Expected: the new Parcel/GIS assertions fail against the placeholder.

- [ ] **Step 5: Implement Parcel Set state without weakening context authorization**

Add a discriminated state:

```ts
type ParcelSetState =
  | { kind: "not_available" | "denied" | "configuration_error" | "session_error" | "invalid_response" | "error" }
  | { kind: "ready"; data: CaseParcelSetDTO };

type LoadedContext = {
  workspace: WorkspaceContextDTO;
  property: PropertyDTO;
  graph: PropertyGraphDTO;
  evidence: PropertyEvidenceDTO;
  parcelSet: ParcelSetState;
};
```

After Workspace and Property binding succeeds, start the Parcel Set promise with a local error classifier while graph/Evidence remain authoritative context reads:

```ts
const parcelSetRead = vnextIdentityClient.caseParcelSet(caseId, workspace.workspace_id)
  .then((data) => ({ kind: "ready" as const, data }))
  .catch(classifyParcelSetError);
const [graph, evidence, parcelSet] = await Promise.all([
  vnextIdentityClient.graph(property.property_entity_id),
  vnextIdentityClient.evidence(property.property_entity_id),
  parcelSetRead,
]);
```

Map 404 only to `not_available`, 403 only to `denied`, session/configuration distinctly, `VNextContractError` to `invalid_response`, and transport/unknown errors to `error`. Preserve the current graph/Evidence binding checks and whole-context failure behavior.

- [ ] **Step 6: Implement readiness and semantic canvas**

Update module readiness so Parcel/GIS is `PARTIAL` only when `parcelSet.kind === "ready"`; otherwise it is `NOT_AVAILABLE`. Never return `AVAILABLE` for Parcel/GIS.

Replace the decorative map marker with a neutral semantic body. Render the loaded view model using a heading, definition list, and ordered member list. Keep these separate fields visible for each member:

```tsx
<div><dt>Review state</dt><dd>{member.reviewStatus.toUpperCase()}</dd></div>
<div><dt>Active review focus</dt><dd>{member.active ? "Yes" : "No"}</dd></div>
```

For matched graph nodes render only the reference ID, display label, reference status, source ID/environment, position, review state, and active state. Keep Case details copy and add the Case-to-Property disclosure. Do not claim the loaded PropertyEntity is the Case property.

- [ ] **Step 7: Implement responsive styling without geographic implication**

Remove `.mapMarker` markup/styles. Add focused canvas, summary, member-card, state-banner, disclaimer, and geometry-state classes using the existing neutral grid background. Ensure every flex/grid child has `min-width: 0`, identifiers use `overflow-wrap: anywhere`, the member grid collapses at 720px, and status remains readable without color.

- [ ] **Step 8: Run Workspace tests and focused contracts GREEN**

Run:

```powershell
npm run test:workspace-contract
npm run build:e2e
node e2e/run-e2e.cjs e2e/professional-workspace.spec.ts --retries=0
npm run typecheck
```

Expected: all new and existing Workspace assertions pass with no retries.

### Task 5: Full Verification, Independent Review, and One Commit

**Files:**
- Review all files changed by Tasks 1–4.
- Modify only changed feature/test files if verification or review finds a defect.

**Interfaces:**
- Consumes: the completed Parcel/GIS slice.
- Produces: verification evidence, independent review clearance, and at most one final commit.

- [ ] **Step 1: Run focused backend Case Parcel Set tests**

Run:

```powershell
python -m pytest tests/test_vnext_case_parcel_set_api.py tests/test_vnext_case_parcel_set_service.py tests/test_vnext_case_parcel_set_migration.py -q
```

Expected: all pass without changing backend behavior or migrations.

- [ ] **Step 2: Run VNext identity/auth, hardening, and Workspace suites**

Run:

```powershell
cd frontend_next
npm run test:workspace-contract
npm run test:vnext-hardening
npm run build:e2e
node e2e/run-e2e.cjs e2e/property-identity-auth.spec.ts e2e/vnext-property-identity.spec.ts e2e/professional-workspace.spec.ts --retries=0
```

Expected: all pass with retry-disabled browser execution.

- [ ] **Step 3: Run frontend static and production checks**

Run:

```powershell
npm run typecheck
npm run lint
npm run build
```

Expected: all pass with no TypeScript, lint, or production compilation failures.

- [ ] **Step 4: Run broader Python regression**

From the repository root, run:

```powershell
python -m pytest -q
```

Expected: full suite passes. Report every baseline/environment failure by exact test name rather than omitting it.

- [ ] **Step 5: Perform security and scope audit**

Inspect the diff and request-capture tests for:

```text
no migration change
no dependency or lockfile change
no Parcel Set mutation wrapper or browser mutation
no direct Supabase browser data query
no service-role/provider credential
no NLSC/TILE_001 request or dependency
no arbitrary URL or Evidence value rendering
no Case/Workspace mismatch acceptance
no fake marker, coordinate, tile, or geometry
no hidden graph pagination or hidden DTO sorting
no AVAILABLE Parcel/GIS state
```

Use `git diff --check`, `git diff --stat`, `git status --short`, and targeted `rg` queries; interpret results against the actual diff rather than treating source-text matching as a behavioral test.

- [ ] **Step 6: Request independent whole-change review**

Have a fresh reviewer inspect the diff and verification evidence specifically for route Case treated as loaded truth, Case-to-Property inference, review/active status treated as canonical or legal truth, fake geometry, hidden pagination, late authorization, cross-workspace binding, duplicate graph-node winner selection, arbitrary Evidence leakage, mutations, provider/NLSC dependencies, and unsupported `AVAILABLE` readiness.

For every Critical or Important finding, add a failing focused regression test, verify RED, implement the minimal correction, and rerun the owning suite GREEN.

- [ ] **Step 7: Re-run final verification after review fixes**

Repeat Steps 1–4 plus:

```powershell
git diff --check
git status --short
```

Expected: all required checks pass and the working tree contains only the planned documentation, frontend contract/client/view-model/UI/style/test changes.

- [ ] **Step 8: Create the single permitted commit**

Only after all verification and review gates pass:

```powershell
git add docs/superpowers/specs/2026-09-20-professional-gis-workspace-v1-design.md docs/superpowers/plans/2026-09-20-professional-gis-workspace-v1.md frontend_next/lib/vnext-case-parcel-set-contract.ts frontend_next/lib/professional-gis.ts frontend_next/lib/vnext-identity-client.ts frontend_next/components/professional-workspace-shell.tsx frontend_next/components/professional-workspace-shell.module.css frontend_next/scripts/test-professional-gis-contract.mjs frontend_next/e2e/professional-workspace.spec.ts frontend_next/package.json
git commit -m "feat(workspace): add parcel investigation canvas"
```

Do not push or merge. Return the requested `PROFESSIONAL GIS WORKSPACE V1 RESULT` report with exact verification outcomes and final GO/NO-GO.
