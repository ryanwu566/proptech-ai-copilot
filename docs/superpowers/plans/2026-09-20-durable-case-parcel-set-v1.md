# Durable Case Parcel Set V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one durable, workspace-scoped, ordered parcel-review set per Case without changing or implying canonical Property Identity confirmation.

**Architecture:** Add two RLS-protected `vnext_core` tables in one migration, with database-enforced workspace, parcel-type, ordering, active-member, vocabulary, and version invariants. Expose them through a focused PostgreSQL repository, an application service that reuses `vnext_private.idempotency_records`, and a thin feature-gated FastAPI router; every successful mutation appends to the existing `vnext_private.audit_events` table in the same transaction.

**Tech Stack:** PostgreSQL 16 SQL/RLS/triggers, psycopg 3, Python 3.11+, FastAPI, Pydantic v2, pytest, Docker-backed disposable PostgreSQL.

**Spec:** `C:/Users/吳奕陽/.codex/attachments/0ca8d2b3-cc93-43da-8430-88c4918f8a97/pasted-text.txt` (`STAGE 2 — DURABLE MULTI-PARCEL CASE SET V1`, supplied as the authoritative design)

## Global Constraints

- Work on branch `feature/multiparcel-gis-case-set-v1` based on the current `origin/main`; do not push or merge.
- Add at most one migration, numbered `018`; register it as `production_runner` without changing any historical migration.
- Preserve migrations and normalized registry checksums 001–017 byte-for-byte, advance the frozen migration boundary through 018, and make `019` the next safe sequence.
- Create exactly one durable parcel set per Case for V1 and cap it at 100 members.
- Use set states `draft` and `case_reviewed`; use member states `candidate`, `case_selected`, and `case_rejected` so Case review cannot be mistaken for canonical identity confirmation.
- Every mutation requires an authenticated principal, workspace membership in `owner`, `admin`, `manager`, or `member`, a 16–128 character `Idempotency-Key`, a bounded strict DTO, and an optimistic expected version (`0` only for initialization; `>= 1` otherwise).
- `viewer` may read but may not mutate.
- Never update `property_identity_references.reference_status`, insert a confirmed `property_relations` row, insert an `identity_decisions` row, or insert a `case_property_links` row as part of this workflow.
- Store no geometry, boundary, raw cadastral payload, address, title/ownership data, provider payload, or provider integration.
- Do not add DELETE endpoints or grant DELETE privileges.
- Reuse `vnext_private.audit_events` and `vnext_private.idempotency_records`; do not add a parcel-set event table.
- Audit metadata is allowlisted and limited to stable IDs, bounded state/action values, role, member count, and versions.
- A mutation that changes membership, member disposition, or ordering returns a reviewed set to `draft`; changing only the active member preserves `case_reviewed` because active means current Case focus, not parcel disposition.
- Marking a set `case_reviewed` requires at least one member and no remaining `candidate` members; an all-rejected set is valid because review can conclude that no candidate belongs in the Case set.
- Make one final implementation commit only: `feat(gis): add durable case parcel set`.

## Review Focus

- A Case ID paired with another workspace ID must yield a bounded not-found/permission response and create no idempotency, parcel-set, member, or audit row.
- Reusing one idempotency key with a different expected version, member ID, order, or disposition must return `idempotency_conflict` and perform no second mutation.
- Two distinct keys racing with the same expected version must produce one success and one `version_conflict`, with no partial reorder or duplicate member.
- Reordering must contain every current member exactly once, reject duplicates/omissions/foreign IDs, and preserve the prior order on failure.
- Case review and member selection must leave identity-reference status, identity decisions, confirmed Property relations, and Case-to-Property links byte-for-byte/count-for-count unchanged.

---

### Task 1: Add the migration and schema contract

**Files:**
- Create: `tests/test_vnext_case_parcel_set_migration.py`
- Create: `database/migrations/018_vnext_case_parcel_set_v1.sql`
- Modify: `database/migration_registry.json`
- Modify: `tests/test_apply_production_migrations.py`
- Modify: `tests/test_vnext_migration_rehearsal_postgres.py`
- Modify: `tests/test_vnext_stage1_exit_gate.py`
- Modify: `tests/test_vnext_parcel_hypothesis.py`
- Modify: `tests/test_vnext_parcel_evidence.py`
- Modify: every other migration-boundary assertion that currently requires `next_safe_sequence(...) == 18` or asserts that no `018_*.sql` exists

**Interfaces:**
- Consumes: `vnext_core.cases`, `vnext_core.property_identity_references`, `vnext_core.workspace_members`, `auth.uid()`, and role `vnext_api` from migrations 013–017.
- Produces: `vnext_core.case_parcel_sets` and `vnext_core.case_parcel_set_members`, with RLS and grants usable by the repository in Task 3.

- [ ] **Step 1: Write the failing static migration contract**

Create tests that load migration 018 and assert all of the following concrete contracts:

```python
from pathlib import Path

from scripts import apply_production_migrations as runner
from scripts.migration_registry import checksum, load_registry, next_safe_sequence

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database/migrations/018_vnext_case_parcel_set_v1.sql"


def test_case_parcel_set_migration_is_registered_last() -> None:
    registrations = load_registry()
    assert registrations[-1].filename == MIGRATION.name
    assert registrations[-1].sha256 == checksum(MIGRATION)
    assert registrations[-1].execution_policy == "production_runner"
    assert runner.MIGRATIONS[-1] == MIGRATION
    assert next_safe_sequence(registrations) == 19


def test_case_parcel_set_schema_has_bounded_case_local_invariants() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "create table vnext_core.case_parcel_sets" in sql
    assert "create table vnext_core.case_parcel_set_members" in sql
    assert "unique (workspace_id, case_id)" in sql
    assert "unique (workspace_id, parcel_set_id, parcel_identity_reference_id)" in sql
    assert "check (position between 1 and 100)" in sql
    assert "check (status in ('draft', 'case_reviewed'))" in sql
    assert "check (review_status in ('candidate', 'case_selected', 'case_rejected'))" in sql
    assert "reference.reference_type <> 'parcel'" in sql
    assert "active_member_id" in sql
    assert "version >= 1" in sql
    assert "enable row level security" in sql
    assert "force row level security" in sql
    assert "grant select, insert, update on vnext_core.case_parcel_sets to vnext_api" in sql
    assert "grant select, insert, update on vnext_core.case_parcel_set_members to vnext_api" in sql
    assert "grant delete" not in sql
    assert "geometry" not in sql
    assert "postgis" not in sql
```

Also assert that both tables have active-member SELECT policies, writer-only INSERT/UPDATE policies, no DELETE policies, and trigger functions with fixed `search_path` values.

- [ ] **Step 2: Run the static contract and verify RED**

Run:

```powershell
pytest -q tests/test_vnext_case_parcel_set_migration.py tests/test_apply_production_migrations.py
```

Expected: FAIL because migration 018 and its registry entry do not exist.

- [ ] **Step 3: Implement migration 018**

The migration must perform these exact schema actions:

1. Add a unique index on `vnext_core.cases(workspace_id, case_id)` only if the existing catalog does not already provide one, so composite foreign keys cannot cross workspaces.
2. Create `case_parcel_sets` with:
   - `parcel_set_id uuid primary key default gen_random_uuid()`
   - `workspace_id uuid not null`
   - `case_id uuid not null`
   - `status text not null default 'draft'`
   - `version bigint not null default 1`
   - `active_member_id uuid`
   - `created_by_user_id uuid not null`
   - `created_at`, `updated_at`, and nullable `reviewed_at` timestamps
   - composite workspace/Case FK, creator FK, one-set-per-Case unique constraint, composite set identity unique constraint, bounded state/version/review-time checks.
3. Create `case_parcel_set_members` with:
   - `parcel_set_member_id uuid primary key default gen_random_uuid()`
   - `workspace_id`, `parcel_set_id`, and `parcel_identity_reference_id` UUIDs
   - `position smallint not null`
   - `review_status text not null default 'candidate'`
   - creator and timestamps
   - composite FKs to the set and identity reference, unique reference membership, unique deferrable position, composite member identity, positions 1–100, and the bounded Case vocabulary.
4. Add a nullable composite FK from `(workspace_id, parcel_set_id, active_member_id)` to the member identity so an active member can only belong to its own set.
5. Add a `BEFORE INSERT OR UPDATE` member guard that rejects any referenced identity row whose `reference_type` is not `parcel`, rejects immutable-ID/creator changes, and allows only bounded disposition/position/timestamp changes.
6. Add a `BEFORE UPDATE` set guard that makes identity/creator timestamps immutable, requires `version = OLD.version + 1`, requires `updated_at > OLD.updated_at`, and enforces `reviewed_at` exactly when status is `case_reviewed`.
7. Add indexes for `(workspace_id, case_id)`, ordered members, reference lookup, and active-member lookup.
8. Enable and force RLS on both tables.
9. Grant only SELECT/INSERT/UPDATE to `vnext_api`.
10. Add policies allowing all active roles to SELECT and only `owner/admin/manager/member` to INSERT/UPDATE, with creator identity checks on inserts.
11. Add comments explicitly stating that Case review is not official/canonical parcel confirmation and does not change Property Identity.

- [ ] **Step 4: Register the immutable migration**

Append registry order 19, sequence 18, logical ID `production-018-vnext-case-parcel-set-v1`, filename `018_vnext_case_parcel_set_v1.sql`, policy `production_runner`, and the canonical SHA-256 printed by:

```powershell
python -c "from pathlib import Path; from scripts.migration_registry import checksum; print(checksum(Path('database/migrations/018_vnext_case_parcel_set_v1.sql')))"
```

Update every expectation for registry count, production migration count, next sequence, table count, foreign-key floor, trigger-function floor, and mutable-table allowlist. Preserve the safety assertions rather than deleting or weakening them: they must now assert that migration 018 is the registered legitimate boundary, migrations 001–017 retain their normalized checksums, no `019_*.sql` exists, and `next_safe_sequence(...) == 19`. The only new mutable tables permitted for `vnext_api` are `case_parcel_sets` and `case_parcel_set_members`.

- [ ] **Step 5: Run static and disposable migration tests**

Run:

```powershell
pytest -q tests/test_vnext_case_parcel_set_migration.py tests/test_apply_production_migrations.py tests/test_vnext_migration_rehearsal_postgres.py
```

Expected: PASS; the rehearsal must prove clean apply, existing-prefix upgrade, and repeat apply with migration 018 in the ledger.

- [ ] **Step 6: Keep the one-commit policy**

Do not commit. Record this task as complete and leave its files for the final implementation commit.

---

### Task 2: Define the domain and idempotent application service

**Files:**
- Create: `tests/test_vnext_case_parcel_set_service.py`
- Create: `services/vnext/case_parcel_set.py`
- Create: `services/vnext/case_parcel_set_service.py`
- Modify: `services/vnext/persistence.py`

**Interfaces:**
- Consumes: `AuthenticatedPrincipal`, `WorkspaceAuthorizer`, `CASE_WRITE_ROLES`, `IdempotencyDecision`, `IdempotencyReservation`, `PostgresIdempotencyRepository`, and `VNextError`.
- Produces: `ParcelSetStatus`, `ParcelMemberReviewStatus`, `CaseParcelSetMemberRecord`, `CaseParcelSetRecord`, `CaseParcelSetOutcome`, and `CaseParcelSetApplicationService` methods used by the API in Task 4.

- [ ] **Step 1: Write failing domain/service tests**

Use in-memory fake authorizer, writer, and idempotency repository objects to cover:

```python
service.initialize(
    principal=member,
    workspace_id=WORKSPACE_ID,
    case_id=CASE_ID,
    expected_version=0,
    idempotency_key="parcel-set-create-0001",
    request_id="request-create",
)
service.add_member(
    principal=member,
    workspace_id=WORKSPACE_ID,
    case_id=CASE_ID,
    parcel_identity_reference_id=PARCEL_ID,
    expected_version=1,
    idempotency_key="parcel-set-add-0001",
    request_id="request-add",
)
service.review_member(
    principal=member,
    workspace_id=WORKSPACE_ID,
    case_id=CASE_ID,
    member_id=MEMBER_ID,
    review_status=ParcelMemberReviewStatus.CASE_SELECTED,
    expected_version=2,
    idempotency_key="parcel-set-review-member-0001",
    request_id="request-review-member",
)
service.set_active_member(
    principal=member,
    workspace_id=WORKSPACE_ID,
    case_id=CASE_ID,
    active_member_id=MEMBER_ID,
    expected_version=3,
    idempotency_key="parcel-set-active-0001",
    request_id="request-active",
)
service.reorder(
    principal=member,
    workspace_id=WORKSPACE_ID,
    case_id=CASE_ID,
    ordered_member_ids=(MEMBER_ID, OTHER_MEMBER_ID),
    expected_version=4,
    idempotency_key="parcel-set-reorder-0001",
    request_id="request-reorder",
)
service.mark_case_reviewed(
    principal=member,
    workspace_id=WORKSPACE_ID,
    case_id=CASE_ID,
    expected_version=5,
    idempotency_key="parcel-set-case-review-0001",
    request_id="request-case-review",
)
service.get(principal=viewer, case_id=CASE_ID)
```

Assert writer roles are required before reservation; canonical fingerprints include workspace, Case ID, expected version, and command-specific values; replay calls `get` rather than the mutation; pending replay maps to `maintenance`; failed replay recreates the allowlisted stored error; mismatched replay reference type/ID maps to `internal_error`; and any writer error marks the reservation failed without leaking exception text.

Add validation tests for expected version zero/nonzero rules, duplicate reorder IDs, empty/over-100 reorder payloads, and unbounded values.

- [ ] **Step 2: Run the service tests and verify RED**

Run:

```powershell
pytest -q tests/test_vnext_case_parcel_set_service.py
```

Expected: FAIL on missing `services.vnext.case_parcel_set` and `case_parcel_set_service`.

- [ ] **Step 3: Add immutable domain records**

Implement these concrete public types in `case_parcel_set.py`:

```python
class ParcelSetStatus(str, Enum):
    DRAFT = "draft"
    CASE_REVIEWED = "case_reviewed"


class ParcelMemberReviewStatus(str, Enum):
    CANDIDATE = "candidate"
    CASE_SELECTED = "case_selected"
    CASE_REJECTED = "case_rejected"


@dataclass(frozen=True)
class CaseParcelSetMemberRecord:
    parcel_set_member_id: UUID
    workspace_id: UUID
    parcel_set_id: UUID
    parcel_identity_reference_id: UUID
    position: int
    review_status: ParcelMemberReviewStatus
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CaseParcelSetRecord:
    parcel_set_id: UUID
    workspace_id: UUID
    case_id: UUID
    status: ParcelSetStatus
    version: int
    active_member_id: UUID | None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    members: tuple[CaseParcelSetMemberRecord, ...]


@dataclass(frozen=True)
class CaseParcelSetOutcome:
    record: CaseParcelSetRecord
    replayed: bool
```

- [ ] **Step 4: Implement one generic idempotent command boundary**

`CaseParcelSetApplicationService` exposes `get`, `initialize`, `add_member`, `review_member`, `set_active_member`, `reorder`, and `mark_case_reviewed`. Each command must:

1. validate its bounded inputs;
2. authorize `CASE_WRITE_ROLES` before reserving idempotency;
3. reserve against the concrete Case-specific route (including `member_id` for member review);
4. fingerprint canonical JSON containing every behavior-changing input;
5. on replay, validate `response_reference_type == "case_parcel_set"`, load the set by Case ID, and confirm its `parcel_set_id` matches the stored reference;
6. on a new reservation, call exactly one repository mutation;
7. mark failures through the existing idempotency repository with only the allowlisted error code/status.

The read method authorizes through repository/RLS and never requires a write role.

- [ ] **Step 5: Expand only the audit metadata allowlist**

Add these bounded keys to `_AUDIT_METADATA_KEYS` in `persistence.py`:

```python
"parcel_set_id",
"parcel_set_member_id",
"parcel_set_status",
"review_status",
"active_member_id",
"member_count",
```

Do not add raw request bodies, address/display values, geometry, provider data, tokens, or documents.

- [ ] **Step 6: Run service tests and existing persistence tests**

Run:

```powershell
pytest -q tests/test_vnext_case_parcel_set_service.py tests/test_vnext_persistence.py tests/test_vnext_authorization.py
```

Expected: PASS.

- [ ] **Step 7: Keep the one-commit policy**

Do not commit. Record this task as complete and leave its files for the final implementation commit.

---

### Task 3: Implement atomic PostgreSQL persistence and real-database invariants

**Files:**
- Create: `services/vnext/case_parcel_set_repository.py`
- Modify: `tests/test_vnext_rls_postgres.py`

**Interfaces:**
- Consumes: the two Task 1 tables, Task 2 records/enums, `DatabasePrincipalContext`, `WorkspaceAuthorizer`, `_append_audit`, `_bounded_text`, and `CASE_WRITE_ROLES`.
- Produces: `PostgresCaseParcelSetRepository.get`, `.initialize`, `.add_member`, `.review_member`, `.set_active_member`, `.reorder`, and `.mark_case_reviewed`.

- [ ] **Step 1: Add real-PostgreSQL tests before repository code**

Extend the disposable Postgres harness to apply migration 018 and add focused tests that cover:

- clean migration/catalog/RLS/grants;
- viewer read and direct/API-layer viewer write denial;
- writer initialization and exactly one set per Case;
- cross-workspace Case/reference/member denial;
- address, building, and geo-reference rejection by the database parcel-type guard;
- duplicate parcel member and position prevention;
- deterministic ordering and exact-list reorder validation;
- set/clear active member and foreign-set active-member rejection;
- stale expected version with no partial write;
- same-key replay with no duplicate audit/domain write;
- two-thread same-version distinct-key race with exactly one winner;
- review requiring members and no `candidate` dispositions;
- review status reset to `draft` after member/disposition/order change but not after active-member-only change;
- audit rows for all six mutations containing only allowlisted IDs/state/version/role/count;
- identity boundary snapshots before and after selection/review: reference status unchanged, no new `identity_decisions`, no new confirmed `property_relations`, no new `case_property_links`, and no PropertyEntity mutation.

- [ ] **Step 2: Run the new real-PostgreSQL selection and verify RED**

Run the new tests by name, for example:

```powershell
pytest -q tests/test_vnext_rls_postgres.py -k "case_parcel_set"
```

Expected: FAIL because `PostgresCaseParcelSetRepository` does not exist.

- [ ] **Step 3: Implement safe row mapping and reads**

The repository must read one set by Case ID under the caller’s database principal, then read members ordered by `(position, parcel_set_member_id)`. Absence, tenant invisibility, and archived/missing Case conditions return `not_found`; database exception text is never surfaced.

- [ ] **Step 4: Implement one locked mutation pattern**

For every non-initialization command, use one transaction and this ordering:

1. require a writer role;
2. `SELECT` the set `FOR UPDATE` by workspace and Case;
3. compare the locked version to `expected_version`, returning `version_conflict` on mismatch;
4. validate command-specific membership/state under the same connection;
5. write the member/set changes;
6. update the set exactly once with `version = version + 1` and `updated_at = clock_timestamp()`;
7. append one audit event;
8. finalize the pending idempotency record to `succeeded` with response type `case_parcel_set` and the set ID;
9. return the fully ordered set before commit.

Any failure in steps 4–8 rolls back the domain write, audit write, and success finalization together. Map SQLSTATE `23503` to `not_found`, `23505`/`23514` to `validation_failed`, `40001` to `version_conflict`, `42501` to `permission_denied`, `40P01` to `maintenance`, and everything else to `internal_error`.

- [ ] **Step 5: Implement command-specific rules**

- `initialize`: require `expected_version == 0`; verify Case exists in the workspace; insert one draft set; audit `case_parcel_set.created`.
- `add_member`: verify the identity reference exists in the same workspace and is `parcel`; append at `max(position)+1`; cap at 100; reset review to draft; audit `case_parcel_set.member_added`.
- `review_member`: update only the named member’s bounded Case disposition; reset set review to draft; audit `case_parcel_set.member_case_reviewed`.
- `set_active_member`: accept `None` to clear; otherwise verify member belongs to the same set; preserve set review status; audit `case_parcel_set.active_member_changed`.
- `reorder`: require an exact, duplicate-free permutation of all current IDs; update positions atomically under the deferrable unique constraint; reset review to draft; audit `case_parcel_set.reordered`.
- `mark_case_reviewed`: require at least one member and zero candidates; set `case_reviewed` plus `reviewed_at`; audit `case_parcel_set.case_reviewed`.

- [ ] **Step 6: Run real-PostgreSQL tests and verify GREEN**

Run:

```powershell
pytest -q tests/test_vnext_rls_postgres.py -k "case_parcel_set"
```

Expected: PASS, including the concurrency and canonical-identity boundary tests.

- [ ] **Step 7: Keep the one-commit policy**

Do not commit. Record this task as complete and leave its files for the final implementation commit.

---

### Task 4: Add the bounded authenticated API

**Files:**
- Create: `tests/test_vnext_case_parcel_set_api.py`
- Create: `backend/api/v1/case_parcel_set.py`
- Modify: `backend/api/v1/router.py`
- Modify: `services/vnext/feature_flags.py`
- Modify: `tests/test_vnext_auth_api.py`
- Modify: `tests/test_vnext_stage1_exit_gate.py`

**Interfaces:**
- Consumes: `CaseParcelSetApplicationService`, `PostgresCaseParcelSetRepository`, `PostgresIdempotencyRepository`, auth dependencies, feature flags, and VNext error envelopes.
- Produces: the seven required `/v1/cases/{case_id}/parcel-set` read/command routes and OpenAPI contracts.

- [ ] **Step 1: Write failing API/security tests**

Use `TestClient`, a real signed fixture JWT verifier, dependency overrides, and a fake parcel-set service. Assert:

- unauthenticated and invalid-signature calls return structured 401 errors;
- forged identity headers/query fields return 422;
- feature disabled returns 404;
- all request models reject extra fields;
- every command requires an Idempotency-Key of 16–128 allowlisted characters;
- expected versions are bounded and initialization accepts only zero;
- reorder accepts 1–100 UUIDs and rejects duplicates;
- error bodies never contain SQL, exception, token, address, or provider content;
- GET contains one bounded ordered member list, `case_reviewed` wording, and no canonical/official confirmation fields;
- routes contain no DELETE operation;
- no code in the router/service imports or calls a provider adapter;
- success responses carry `Cache-Control: private, no-store` through existing middleware.

- [ ] **Step 2: Run API tests and verify RED**

Run:

```powershell
pytest -q tests/test_vnext_case_parcel_set_api.py
```

Expected: FAIL because the router and DTOs do not exist.

- [ ] **Step 3: Add a default-off rollout flag**

Add `CASE_PARCEL_SET_V1_ENV = "FEATURE_CASE_PARCEL_SET_V1"` and `case_parcel_set_v1: bool = False` to `VNextFeatureFlags`, load it with the existing `_ENABLED` vocabulary, expose it from `enabled("case_parcel_set_v1")`, and include it in `/v1` context output. Keep example/production configuration default-off and add no client-visible secret.

- [ ] **Step 4: Define strict bounded DTOs**

Use `ConfigDict(extra="forbid")` for:

```python
class InitializeParcelSetRequest(_StrictModel):
    workspace_id: UUID
    expected_version: Literal[0]

class AddParcelMemberRequest(_StrictModel):
    workspace_id: UUID
    parcel_identity_reference_id: UUID
    expected_version: Annotated[int, Field(ge=1)]

class ReviewParcelMemberRequest(_StrictModel):
    workspace_id: UUID
    review_status: ParcelMemberReviewStatus
    expected_version: Annotated[int, Field(ge=1)]

class SetActiveParcelMemberRequest(_StrictModel):
    workspace_id: UUID
    active_member_id: UUID | None
    expected_version: Annotated[int, Field(ge=1)]

class ReorderParcelMembersRequest(_StrictModel):
    workspace_id: UUID
    ordered_member_ids: Annotated[list[UUID], Field(min_length=1, max_length=100)]
    expected_version: Annotated[int, Field(ge=1)]

class MarkParcelSetCaseReviewedRequest(_StrictModel):
    workspace_id: UUID
    expected_version: Annotated[int, Field(ge=1)]
```

The response DTO contains set/member IDs, workspace/Case IDs, Case-scoped states, version, active member, timestamps, and ordered members only. It must not contain `property_entity_id`, `identity_status`, `reference_status`, `confirmed`, `official`, geometry, address, or provider fields.

- [ ] **Step 5: Implement the exact route surface**

Add:

```text
GET  /v1/cases/{case_id}/parcel-set
POST /v1/cases/{case_id}/parcel-set
POST /v1/cases/{case_id}/parcel-set/members
POST /v1/cases/{case_id}/parcel-set/members/{member_id}/review
POST /v1/cases/{case_id}/parcel-set/active-member
POST /v1/cases/{case_id}/parcel-set/reorder
POST /v1/cases/{case_id}/parcel-set/review
```

Every route depends on authentication, forged-identity rejection, and the default-off parcel-set feature. Commands require the bounded shared idempotency header and pass the correlation request ID. Initialization returns 201 for a new set and 200 for replay; other commands return 200. Include the router once under `/v1` and add no DELETE route.

- [ ] **Step 6: Run API and auth/contract tests**

Run:

```powershell
pytest -q tests/test_vnext_case_parcel_set_api.py tests/test_vnext_auth_api.py tests/test_vnext_stage1_exit_gate.py
```

Expected: PASS.

- [ ] **Step 7: Keep the one-commit policy**

Do not commit. Record this task as complete and leave its files for the final implementation commit.

---

### Task 5: Run regression, security, and final repository gates

**Files:**
- Modify only files required to fix failures caused by Tasks 1–4; do not broaden the feature.

**Interfaces:**
- Consumes: all Task 1–4 outputs.
- Produces: a verified branch with one implementation commit and no push/merge.

- [ ] **Step 1: Run focused Case/Property Identity/RLS/migration/API tests**

Run:

```powershell
pytest -q tests/test_vnext_case_parcel_set_migration.py tests/test_vnext_case_parcel_set_service.py tests/test_vnext_case_parcel_set_api.py tests/test_vnext_workspace_case_migration.py tests/test_vnext_property_graph_migration.py tests/test_vnext_identity_resolution_migration.py tests/test_vnext_identity_confirmation_migration.py tests/test_vnext_legacy_case_import_migration.py tests/test_vnext_persistence.py tests/test_vnext_property_api.py tests/test_vnext_rls_postgres.py tests/test_vnext_migration_rehearsal_postgres.py tests/test_vnext_stage1_exit_gate.py tests/test_vnext_auth_api.py tests/test_authenticated_identity_smoke.py tests/test_deployment_configuration_contract.py
```

Expected: PASS with real disposable PostgreSQL tests exercised, not skipped for a missing database URL.

- [ ] **Step 2: Run the complete project test suite**

Run:

```powershell
pytest -q
```

Expected: PASS. Report every failing test by name if the baseline exposes unrelated failures; do not omit observed failures.

- [ ] **Step 3: Prove scope exclusions statically**

Run:

```powershell
rg -n -i "postgis|geometry|polygon|cadastral boundary|nlsc|provider" database/migrations/018_vnext_case_parcel_set_v1.sql services/vnext/case_parcel_set*.py backend/api/v1/case_parcel_set.py
rg -n "@(router\.)?delete|\.delete\(" backend/api/v1/case_parcel_set.py services/vnext/case_parcel_set*.py
rg -n -i "token|secret|password|service_role" backend/api/v1/case_parcel_set.py services/vnext/case_parcel_set*.py
```

Expected: no functional geometry/provider/DELETE/secret matches; comments may mention the explicit absence of official geometry and must be reviewed manually.

- [ ] **Step 4: Run formatting and repository checks**

Run:

```powershell
git diff --check
git status --short
git diff --stat
```

Expected: no whitespace errors; only planned files are changed.

- [ ] **Step 5: Invoke verification-before-completion and request code review**

Use the required Superpowers verification workflow, inspect fresh command output, then use the code-review workflow for a whole-branch review. Address only findings within this Stage 2 scope and rerun affected tests.

- [ ] **Step 6: Create the only implementation commit**

Stage the reviewed files and commit exactly once:

```powershell
git add database/migrations/018_vnext_case_parcel_set_v1.sql database/migration_registry.json services/vnext/persistence.py services/vnext/feature_flags.py services/vnext/case_parcel_set.py services/vnext/case_parcel_set_service.py services/vnext/case_parcel_set_repository.py backend/api/v1/case_parcel_set.py backend/api/v1/router.py tests docs/superpowers/plans/2026-09-20-durable-case-parcel-set-v1.md
git commit -m "feat(gis): add durable case parcel set"
```

Do not push and do not merge.

- [ ] **Step 7: Verify the committed branch**

Run:

```powershell
git status --short
git log -1 --oneline --decorate
git diff --check origin/main...HEAD
```

Expected: clean worktree, one new commit named `feat(gis): add durable case parcel set`, and no whitespace errors.
