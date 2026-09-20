# Stage 1 Live Truth Closure Runbook

Status: operator procedure only; no production provisioning has been executed

## Purpose and fixed scope

This procedure provisions one production acceptance bundle for authenticated,
read-only Stage 1 verification:

- one existing Supabase Auth user, identified only by its exact `auth.users.id` UUID;
- one team workspace labelled `[PROD ACCEPTANCE TEST] Stage 1 Workspace`;
- one active `viewer` membership for that user;
- one unverified PropertyEntity labelled
  `[PROD ACCEPTANCE TEST] Stage 1 Unverified Property`;
- one property graph node created by the existing database trigger.

It does not create or change an Auth user, canonical identity reference,
parcel/building hypothesis, relation, identity decision, evidence item, Case,
or confirmation. Empty graph relations and empty evidence are the expected
acceptance state.

The provisioning program never accepts browser keys, publishable/anonymous
keys, privileged API JWTs, user bearer tokens, or a normal `vnext_api`
connection. Its only database input is the server/operator-only PostgreSQL URL
in `STAGE1_ACCEPTANCE_DATABASE_URL`. Do not place that value in source control,
command arguments, screenshots, tickets, logs, or retained shell history.
Remote operator URLs must explicitly use `sslmode=verify-full`; plaintext,
downgrade-capable, and non-host-verifying modes are refused.

## Safety model

The repository audit found no migration after 017. Migration 016 adds a
terminal-state guard only for Cases; it does not prevent the bounded workspace,
membership, or PropertyEntity archive/reactivation transitions used here.
Migration 017 adds the legacy import ledger and does not change those lifecycle
rules. No trigger in migrations 015–017 makes the workspace, membership, or
PropertyEntity transitions terminal. No migration is required for this closure.

Normal invocation is a read-only database transaction. It verifies:

- migration ledger checksums for migrations 013 through 017 and that 017 is the
  terminal numeric migration (an unreviewed later migration fails closed);
- every required VNext table and the enabled property graph trigger;
- an existing exact Auth user UUID;
- a non-request operator role with sufficient privileges and RLS bypass;
- the restricted `vnext_api` request role, including `NOINHERIT`, no inherited
  role memberships, no elevated role attributes, forced RLS on every VNext
  table, non-`vnext_api` table ownership, and the exact reviewed policy
  schema/table bindings, names, commands, roles, and normalized predicates;
- no conflicting UUID or acceptance marker;
- the entire workspace-scoped VNext row footprint.

Mutation requires exactly one explicit mode: `--apply-provision` or
`--apply-archive`. Each mutation uses one transaction and one transaction-level
advisory lock. Any failed check aborts the transaction and emits only a bounded
reason code.

Archival is the rollback mechanism. It changes the exact membership to
`removed`, the exact property to `archived`, and the exact workspace to
`archived`, with coherent lifecycle timestamps. It never physically removes
the workspace, membership, property, or immutable graph node.

Reactivation uses `--apply-provision` on an archived bundle. It is allowed only
when the original UUIDs, fixed labels, creator UUID, viewer role, graph-node
ownership, lifecycle shape, and complete attached-row counts still match. Any
new Case, reference, relation, evidence, resolution, audit, idempotency, import,
membership, property, or graph row makes reactivation refuse.

## Before the approved window

1. Confirm the deployed database contains reviewed migrations 013–017 and that
   the deployed backend release contains this script and the six-request smoke
   harness.
2. Record the approved production change, operator, release commit, planned
   user UUID, newly generated workspace UUID, and newly generated property
   UUID. UUIDs are identifiers, not authentication tokens.
3. Confirm the selected Supabase Auth user can sign in and is dedicated or
   approved for production acceptance. Do not copy an access token into the
   change record.
4. Supply `STAGE1_ACCEPTANCE_DATABASE_URL` through the approved operator secret
   injection mechanism. The URL must authenticate directly to PostgreSQL as an
   authorized operator, never as `vnext_api` or an API role.

## Read-only preflight — mandatory

Run without either apply switch:

```text
python scripts/provision_stage1_acceptance.py --auth-user-id <existing-auth-user-uuid> --workspace-id <new-workspace-uuid> --property-id <new-property-uuid>
```

Required result before first provisioning:

```json
{"bundle_state":"empty","mode":"dry_run","next_action":"provision","status":"ready"}
```

Any other result stops the operation. Do not work around a refusal by editing
production rows, disabling RLS, disabling triggers, or changing the script.

## Provision — separate human approval required

After an authorized human approves the exact three UUIDs and the preflight
result, run the same command with `--apply-provision`:

```text
python scripts/provision_stage1_acceptance.py --auth-user-id <existing-auth-user-uuid> --workspace-id <approved-workspace-uuid> --property-id <approved-property-uuid> --apply-provision
```

Required result:

```json
{"action":"provisioned","bundle_state":"active","mode":"provision","status":"pass"}
```

Repeat the read-only preflight. It must report `bundle_state` as `active` and
`next_action` as `none`. A repeated approved provision command is also a no-op
only when the exact active bundle still matches.

## Read-only browser acceptance

Sign in through the normal production Email/Password UI as the acceptance user
and open:

```text
/vnext/property-identity/<approved-workspace-uuid>/<approved-property-uuid>
```

Accept only when:

- workspace context and the unverified PropertyEntity render;
- the graph loads with exactly its property node and no synthetic relations;
- the evidence panel loads with no evidence rows;
- the workspace role is `viewer`;
- parcel, building, and relation mutation controls are unavailable or disabled.

Do not submit any command from the browser.

## Authenticated production smoke

Supply the acceptance user's short-lived bearer token only through the approved
ephemeral secret channel. Never put it in a command argument or retained log.
Set these environment inputs:

```text
SMOKE_API_BASE_URL=<production-backend-https-origin>
SMOKE_USER_BEARER_TOKEN=<ephemeral-user-access-token>
SMOKE_WORKSPACE_ID=<approved-workspace-uuid>
SMOKE_PROPERTY_ENTITY_ID=<approved-property-uuid>
SMOKE_WRITE_MODE=false
```

Run:

```text
python scripts/authenticated_identity_smoke.py
```

The exact request sequence is:

1. authenticated `GET /v1`;
2. authenticated `GET /v1/workspaces/{workspace_id}/context`;
3. authenticated `GET /v1/properties/{property_id}`;
4. authenticated `GET /v1/properties/{property_id}/graph`;
5. authenticated `GET /v1/properties/{property_id}/evidence`;
6. unauthenticated `GET /v1` control, which must return the structured 401.

All six checks must pass. The harness remains GET-only, refuses privileged-role
JWTs, disables redirects, requires HTTPS for remote hosts, bounds response-body
handling, and never renders bearer material or response bodies.

## Archive — approved rollback

After acceptance, or immediately if acceptance fails for a reason attributable
to the fixture, obtain separate human approval and run:

```text
python scripts/provision_stage1_acceptance.py --auth-user-id <existing-auth-user-uuid> --workspace-id <approved-workspace-uuid> --property-id <approved-property-uuid> --apply-archive
```

Required result is `action=archived`, `bundle_state=archived`, and
`status=pass`. Repeat the read-only preflight and confirm it reports the exact
archived bundle. The graph node remains as immutable tagged history, while the
removed membership immediately denies the acceptance user further workspace
access.

If later reactivation is explicitly approved, first run the read-only preflight
against the same three UUIDs. Only `bundle_state=archived` and
`next_action=reactivate` permits the exact `--apply-provision` command. Any drift
is a stop condition.

## Evidence to retain

Retain the approved UUIDs, release commit, human approval reference, bounded
JSON results, six PASS lines with generated correlation IDs, and browser
acceptance result. Do not retain the operator database URL or bearer token.

## Offline verification

```text
python -m pytest tests/test_stage1_acceptance_provisioning.py tests/test_authenticated_identity_smoke.py -q
python -m pytest tests/test_vnext_property_graph.py tests/test_vnext_property_api.py tests/test_frontend_vnext_property_identity.py -q
```

The optional real-PostgreSQL RLS suite still requires the repository's explicit
disposable-database safety gate. Never point that test suite at production.
