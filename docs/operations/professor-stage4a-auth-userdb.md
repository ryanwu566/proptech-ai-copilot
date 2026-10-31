# Professor Stage 4A auth and user database

Status: controlled activation PASS; backend ready for frontend contract
integration. Overall Stage 4A acceptance is PARTIAL until authenticated live user
flows are demonstrated. Do not rerun provisioning, inspection or activation.
This is a separate branch based on accepted Stage 3, not an amendment to
Stage 1–3 or the historical-data branch. No frontend files are owned here.

## Audit and selected architecture

The current application uses Supabase Auth through supabase-js. Registration and
password login occur at Supabase, which owns password hashes, refresh tokens,
confirmation and recovery. FastAPI verifies asymmetric JWTs via public JWKS;
canonical IDs are the existing UUID subjects. No Auth.js/NextAuth, custom password
store or replacement JWT issuer was found. The browser uses SDK persisted storage
and refresh; it is not an HttpOnly cookie login. Bearer API requests omit cookies.

A read-only aggregate query of the primary connected project on 2026-10-30 found
one Auth user with prior sign-in. `vnext_private.consumer_accounts` and
`vnext_core.cases` were absent there. No identity/credential data was exported.
The later public frontend authority review below resolves the accepted frontend
issuer; it does not establish every historical deployment. Preserve all projects
and user accounts; no password migration, identity deletion, or cloud retirement.

Selected HYBRID: Vercel frontend → HTTPS FastAPI → Professor PostgreSQL for
application data, while Supabase remains the identity provider. Exact contract:
[auth-user-api-v1](../contracts/auth-user-api-v1.md). The linked official
[session documentation](https://supabase.com/docs/guides/auth/sessions) confirms
session_id identifies the provider session; Supabase access JWTs can remain valid
until expiration after remote signout. This limitation is explicit.

## Database layout and migration

`database/userdb/001_professor_users.sql` is a NEW independent operator migration,
not an additional sequence in the frozen valuation/legacy registry. Database
`proptech_app`, private schema `professor_user`, owner remains the DB migration
operator. Request role `professor_user_runtime` is direct LOGIN, no memberships,
no superuser/BYPASSRLS/CREATEDB/CREATEROLE/replication or ownership/DDL authority.
Existing `app_runtime` RIS SELECT and valuation_runtime grants remain unchanged.

Tables: configuration (fixed issuer, schema version, authority approval), users,
profiles, preferences, revoked_sessions, saved_cases, case_activity, case_commands,
reports. Eight user tables have ENABLE+FORCE RLS. Fixed subject comes only from a
verified JWT and transaction-local context. FK ownership, immutable column grants,
CAS, per-user transaction locks and tombstones prevent cross-user writes and
import resurrection. No local auth.users surrogate. Existing Supabase UUID is the
canonical user ID; users are lazily mapped after verified authentication, not
created from browser-provided IDs. New local records default active/consumer only.
No request grant can change role/status, issuer or owner. No Data API exposure.

Cases remain owner-only in this profile. Existing collaboration/workspace APIs
retain their separate, disabled-by-default configuration; no role translation.
Profile display name/locale and preference JSON are private. Reports are retained
user-supplied, unverified snapshots, not authenticated official findings. Case
soft deletion hides associated reports and prevents import retry resurrection.
Retention/legal export and hard erasure need a separately reviewed policy.

## Completed provisioning (reference; do not rerun)

The agent did not run privileged code, read real secret values, apply SQL to a
live database, build images or recreate containers. Inspect the value-free plan:

```bash
python3 -B /home/andy/.codex/worktrees/bb30/proptech-ai-copilot/scripts/ops/professor_stage4a_provision.py --plan
```

When ready to provision the additive schema only, operator command:

```bash
sudo python3 -B /home/andy/.codex/worktrees/bb30/proptech-ai-copilot/scripts/ops/professor_stage4a_provision.py --apply
```

It checks backing devices, exact selfhost postgres_app selection, private ports,
existing volume paths, and fresh schema/role/file names; backs up the entire app
DB in PostgreSQL custom format and verifies its directory without restoring;
creates the role/schema/configuration transactionally; generates a random password
and SCRAM verifier without displaying them; stores its URL in root-only persistent
and root:10001 mode0440 staged files. It does not change existing /etc files.
Rollback/receipt go under `/var/backups/proptech-selfhost/stage4a-userdb/<run>/`.
Full backups stay root-only. No container recreation or runtime activation occurs.

Freshness failures refuse rather than overwriting existing roles/files. If any
phase fails, inspect the sanitized receipt before retrying; the persistent recovery
URL may already exist even if database apply rolled back. If database commit
succeeded but file staging failed, preserve both database and persistent file;
recover using this same script’s `--stage` operation below. Never blindly
rerun, rotate, delete volumes, or remove user records to get past a gate.

After reboot, use the established Stage 2 staging procedure for its existing
files, then restore this one additional URL with the same operator script:

```bash
sudo python3 -B /home/andy/.codex/worktrees/bb30/proptech-ai-copilot/scripts/ops/professor_stage4a_provision.py --stage
```

`--stage` validates protected stored/staged metadata and the exact local role,
database and hostname. It writes only a missing volatile staged file, preserves
an identical existing inode, and refuses conflicting/unsafe files. It makes no
SQL/credential rotation, image or container change. This also recovers a staging
failure after successful SQL commit; if SQL failed instead, restaging alone does
not claim schema success. Existing-user data and persistent URL are preserved.

`configuration.authority_reviewed` intentionally remains FALSE after provisioning.
The command alone cannot activate auth. An operator must confirm the configured
issuer matches the existing frontend/project and reconcile existing hosted account
status/admin authority if present anywhere. For the inspected project the legacy
authority table was absent; do not infer the same for another deployment. Record
the review and explicitly approve local configuration only after this check.
Existing user UUIDs are retained; no password exports. Privileged role/status
imports or authority approval must use a separately reviewed transaction with
backup and update timestamps; the API cannot approve itself.

## Controlled activation still required

Prepared `infra/selfhost/professor-userdb.override.yml` is not installed. It requires
a reviewed clean image built from this branch's backend, services, scripts and
configuration. Do NOT reuse the Stage 2 activation script: its frozen source checks
and exact-five-secret profile intentionally reject this new profile.

Before activation, export only reviewed tracked application source, pin existing
installed dependencies, build without any secret files, and scan layers/history
using the existing credential scanner under operator control. Preserve all Stage
3 ML artifacts/configuration, NLSC/WRA read-only mounts and app/usage/valuation
credentials. Merge the new override last after the *actual active* Stage 1–3 files;
compare JSON in memory and emit names/categories only. The tests validate a
synthetic merge, not unknown root-owned live overrides. No public listener change,
new networks, DB configuration/volume change or paid-provider activation is allowed.

The new entrypoint loads exactly five existing Stage 2 core files plus one isolated
`/run/professor-userdb/professor_user_database_url` mount. Persistent store stays
root:root0600 under `/etc/proptech-selfhost/secrets`; staged host file root:10001
0440 under `/run/proptech-selfhost/secrets`. No directory secret mounts. No admin
credential in API. It rejects inherited user-DB URL aliases, and existing Stage 2
credential/operation guards remain. TLS is pinned verify-full with the existing CA,
postgres_app hostname, proptech_app database and exact dedicated runtime role.
Startup validates issuer approval, RLS and authority/write-grant boundaries before
serving. No URL/password value enters Compose. Uvicorn access logging is off in
this profile to avoid logging credential-bearing URLs. Structured app logging
and runtime-secret redaction remain. Invalid tokens/password-like request values
are not reflected in errors. Never put credentials in URLs or diagnostic output.

Only the API is eligible for later `up --no-deps --force-recreate api` after a
reviewed exact Compose merge and rollback image are recorded. This runbook does
not certify an uninspected host merge; do not execute a guessed Compose command.
No database container or volume is to be recreated. Startup requires authority
approval first. Existing HBA must permit TLS/SCRAM for professor_user_runtime:
review that exact rule before adding one; never broaden to trust/public ports.

## Sessions and frontend coordination

Stage 4A requires authenticated, non-anonymous asymmetric JWTs with session_id,
iat and expiry. Store UUID revocations, never JWT/password/refresh/reset tokens.
Revocations are checked before admission AND inside each user-data transaction.
Local POST /v1/session/logout stops that session, including refreshed JWTs; another
device's session remains available. Frontend must call this endpoint before SDK
local signout. SDK signout alone cannot promise immediate Professor revocation;
remote Supabase account deletion/global logout is visible here only through JWT
expiry unless a future strict introspection/event bridge is implemented.

No new browser cookies or CSRF token protocol: existing explicit Bearer header plus
Origin allowlist applies. Existing pilot-cookie CSRF remains separate. For public
HTTPS, independently verify Vercel origins, CSP/JWKS egress, token expiry/rotation,
provider abuse protections, SMTP/confirmation/recovery and cross-device behavior.
Backend user-data requests reuse existing bounded peer/principal metadata request
budgets and body limits; they never invoke paid providers. This is process/local
quota compatibility, not a claim of global auth signup rate limiting or storage
entitlements. Supabase owns credential-login abuse controls.

Saved Cases, drafts, decision rooms and preferences currently in localStorage are
never silently uploaded. Signing in must preserve local bytes and explicitly ask
for import consent. Report/compare preference saves are explicit owner writes.
UI must say browser-only until server commit. Logout clears private in-memory
views but retains server-owned records. No frontend implementation changes here.

## Acceptance and rollback

Run focused tests only, using the existing Python environment and optional local
PostgreSQL binaries. PostgreSQL tests create fresh directories in
`~/.cache/proptech-stage4a-tests`, Unix sockets only, no TCP listener; production
URLs are removed by repository conftest. The temporary cluster is stopped and
removed. Small worker/connection pools protect the N4505. No full test suite.

Before calling Stage 4A COMPLETE, operator must finish provisioning, authority and
issuer review, clean-image/Compose verification and API-only controlled activation.
Then test authenticated login, profile, cases, reports, cross-device reopening,
logout/revoked refresh and cross-user denial, along with health/readiness and
Stage 1–3 local data/ML regression probes. Capture only sanitized outcomes.

Rollback a later failed activation by restoring the previously recorded API
image/profile; leave additive user tables and committed data intact. Never apply
old image migrations over these tables. App backup is a recovery artifact, not an
automatic overwrite instruction. Include the new schema in regular encrypted,
root-owned backup/restore rehearsals. Restore user data only under an approved
retention/recovery plan. Stage 1–3 remain operational while activation is pending.

Security boundaries: **NEVER touch /dev/sda**. No X9 source access/mutation, public
PostgreSQL, public8080, market_ops, paid providers, Vercel/DNS/Cloud Run/Render
changes, GitHub push, model training, or frontend edits. Keep the accepted CWA
1897–1989 non-fill rule unchanged. This is not production-readiness approval.

## Recorded implementation validation

Final auth/Stage 4A pack: 77 passed (44 new Stage 4A tests, 33 existing JWT tests).
Extended backend/security/ownership pack: 339 passed before a Stage3 historical
fixture stopped at its16GiB free-disk requirement on tmpfs. Complete Stage3
bounded-scope and migration-registry modules rerun on a fresh home-filesystem
basetemp:29 passed. Final operator-script suite:12 passed. Unchanged Supabase
SDK/account contracts:25 passed, including neutral duplicate signup and session
races. Native Node here lacks TypeScript support; a temporary TypeScript loader
was used, with no frontend source or dependency installation changes. Python AST,
JSON, synthetic Compose merge, source credential-signature scan and diff checks
passed. Independent review has no remaining critical/important finding. No full
suite, paid-provider E2E, browser suite, model training or host apply was run.

## Post-provision checkpoint

Operator reported successful provisioning, exit0. Do NOT rerun `--apply` or secret
installation. Runtime activation has NOT been authorized/executed. Agent cannot
read the root0700 backup directory or Docker socket; a successful exit is not a
substitute for live catalog verification. Current status remains PARTIAL.

Live checks after provisioning passed all 12 existing8080 API contracts and the
accepted8081 ML companion health/status/estimate, with unchanged manifest pin and
non-actionable scope. 8080 ML routes remain404 on the older accepted API image;
that is separate from the working8081 companion. No migration or runtime repair
is justified by that expected separation. No model was trained/restarted.
Primary Supabase aggregate still shows one confirmed non-anonymous user, no
banned/deleted users, and no legacy account-authority/workspace-case table.
Expected issuer has one supported asymmetric public key. No user identifiers,
passwords or credential values were fetched. These counts are not an identity-row
checksum comparison; provisioning code performs no Supabase mutations.

The next operator command is **verification only**, NOT activation:

```bash
sudo python3 -B /home/andy/.codex/worktrees/bb30/proptech-ai-copilot/scripts/ops/professor_stage4a_postprovision.py --inspect
```

The reviewed diagnostic never opens credential files, writes SQL, approves account
authority, builds images or recreates containers. It checks protected directory
and leaf metadata, exact tested schema/constraints/policies/effective grants,
functions/relations, role CONNECT/escalation/external reads or writes, current
container guards and bindings. SQL is forced read-only over the existing local
Unix socket; inherited libpq service/password/address settings are cleared.
A sole sanitized receipt is written at `/tmp/professor-stage4a-postprovision-*/diagnosis.json`.
The expected catalog comes from a fresh disposable cluster, not the host. Unknown
catalog drift fails closed and must be diagnosed, never accepted by replacing the
baseline with the unreviewed live catalog. No synthetic users are inserted into
the real DB; ownership proof combines exact catalog matching with the existing
multi-user disposable tests. Role/TLS credential login inside the clean image is
still a separate activation prerequisite.

After that receipt passes, confirm the actual frontend uses the audited issuer,
reconcile local/historical account authority and record explicit approval before
changing authority_reviewed. Then prepare a clean scanned image and exact actual
Compose merge, record rollback, preserve the8081 companion and all databases/data
mounts, and prepare one controlled API-only activation command. No reviewed
activation command is available yet; neither provisioning nor the frozen Stage2
activation script substitutes for that procedure. See machine-readable
`reports/professor-stage4a-auth-userdb/post-provision-verification.json` for the
precise pending gates.

## Read-only transport repair after first inspection

The first operator inspection failed before returning catalog data. Its sanitized
receipt passed provisioning-hash, secret parent/leaf metadata, container health,
private ports, disabled guards, inactive Stage 4A and dataset-mount checks. The
live schema/role/authority query had not been verified; no DB repair or rollback
is justified by this failure.

Cause: `docker exec -e PGSERVICE=` defines an empty service name. libpq then exits2
with `definition of service "" not found` before connecting, even with an explicit
Unix-socket host. The previous psycopg-only SQL tests did not exercise this CLI
environment boundary. The diagnostic now starts only its psql child through
`env -i` with trusted PATH, UTF8 client encoding, password-file suppression and
read-only PGOPTIONS; explicit socket, port, user, database, -X and -w remain.
No schema/catalog/grant/authority gate changed. A real-psql regression reproduces
the old failure and verifies the complete catalog query through the repaired
command under poisoned inherited service/address variables. Focused tests:24
passed; independent security review found no issue. No privileged retry was run
by the agent. Retry only the existing `--inspect` command above, never provisioning
or activation. Successful current-schema verification is still pending.

## PostgreSQL 17/18 catalog representation repair

The next receipt (`/tmp/professor-stage4a-postprovision-us2pg0s1/diagnosis.json`)
completed SQL. All role, issuer, receipt, metadata and runtime-boundary checks
passed; only exact catalog comparison and its derived ownership gate failed.
The host is PostgreSQL17.10; the disposable baseline was PostgreSQL18.6.

PostgreSQL18 additionally records table NOT NULL constraints in pg_constraint.
PostgreSQL17 records table nullability in pg_attribute.attnotnull only. Removing
exactly58 redundant expected18 NOT NULL bookkeeping rows produces full catalog
SHA256 `f04cbbd3748e1c146ba288cd951b56e5d6aef8b1111ddab46381812d59d2d289`,
EXACTLY the hash in the captured live receipt. Every other captured catalog field,
including actual column nullability, ownership FKs, RLS, policies, effective grants,
functions, indexes and triggers, is therefore identical. See the official
[PG17 catalog](https://www.postgresql.org/docs/17/catalog-pg-constraint.html) and
[PG18 catalog](https://www.postgresql.org/docs/18/catalog-pg-constraint.html).

The verifier now selects an exact expected representation for majors17/18. On17,
each omitted expected bookkeeping row must be validated and map one-to-one to
an expected attnotnull column. The actual live catalog is NEVER filtered. On18,
the full original expected catalog is unchanged. Unknown versions or malformed
coverage refuse. Dropped NOT NULL, changed policies, grants, FKs and all other
metadata still mismatch. Neither frozen migration nor frozen baseline changed.
Focused tests:33 passed. Independent security review found no issue.

This is OFFLINE reconciliation of that captured live observation, not a new live
inspection PASS: preserve the original REFUSED receipt unchanged. It closes the
captured schema/ownership gate without rerunning inspection or provisioning. No
DB/secret repair or rollback is indicated. Authority remains explicitly unapproved
(authority_reviewed=false); frontend issuer/account review, clean-image checks,
actual Compose merge/rollback and a separately reviewed API-only activation are
still pending. No operator command is needed for this verifier repair. Machine
proof: `reports/professor-stage4a-auth-userdb/catalog-reconciliation.json`.

## Current authority resolution — PASS

This section supersedes earlier uncertainty about the existing frontend project.
A read-only public observation of `https://proptech-ai-copilot.vercel.app` reports
the accepted release9cc40d645757af4513d9afdf0c008939cc489a77. Its login/signup/account
pages load the immutable auth asset `28_mshq0x50li.js`, SHA256
`39cf21f28d4ca1104c5f229e12bc5e61003ed42db7d2c6a10aa09d0567a4c7ba`.
Manual source review, with credential literals excluded from diagnostics, connects
the public origin constructor to the existing SDK configuration, its single URL
alias and bundled Supabase client constructor. The SDK source Git blob7f04beb6b86010a002747c99ca67b5d0786405de is identical in that release and the accepted
local source. All13 loaded auth-page assets were scanned for public Supabase origin
references; only `https://flyhsjcynreuofbcdxod.supabase.co` occurs.

Canonical project: `flyhsjcynreuofbcdxod`; issuer:
`https://flyhsjcynreuofbcdxod.supabase.co/auth/v1`; audience: `authenticated`.
Authority fingerprint:
`ffd784ac6e456727b17ad7daf4db013351e76b43599c27ec4f4aa830958b588e`.
The prepared backend profile and captured Professor DB issuer match exactly.
No publishable/service key, password, token or secret-value comparison is needed.
The primary Supabase aggregate confirms one UUID user, confirmed/prior sign-in,
authenticated audience/role, zero banned/deleted/anonymous users, and no legacy
consumer-account authority or workspace-case table. The verified UUID maps directly
to local users/profiles/case ownership; no identity or password migration is needed.
No user rows were exported, created, suspended, deleted or modified.

The inactive `osypacuurzkqerfhcqty` valuation-green project was not resumed and is
not bound by this frontend. slice8/slice9/fixture/other references are test fixtures.
The server-local frontend.env.local contains neither public Supabase config name;
that profile is unconfigured, not a competing issuer. It was inspected for public
configuration names only and left untouched. Protected root runtime files were
not read; a future actual Compose merge must keep the now-proven explicit issuer
and audience. No frontend or Vercel configuration was changed.

The audit is deliberately narrow: a manually reviewed immutable asset identity
is mandatory. It is not generic JavaScript taint inference or an assertion that
any matching URL string establishes authority. New release/hash is PENDING until
reviewed; conflicting issuer/audience/provider refuses. A read-only replay of
public deployment metadata can be made with:

```bash
node scripts/ops/professor_stage4a_public_authority.mjs
```

The collector uses bounded same-origin HTTPS GETs only, omits credentials, refuses
redirects, emits public identifiers/hashes only, and performs no login/signup or
SDK execution. It never emits the bundle or key values. The offline evaluator is
`scripts/ops/professor_stage4a_authority.py`; recorded proof lives in
`reports/professor-stage4a-auth-userdb/auth-authority.json`. Regression tests cover
unreviewed/mutated/shadowed source, conflicting projects and legacy aliases,
impossible aggregates and UUID preservation with wrong-issuer refusal.
Focused validation:52 Python tests (19 authority +33 existing JWT) and8 Node
metadata tests passed. Independent security review has no critical/important issue.

Semantic Auth authority is PASS; no additional operator-visible metadata or keys
are required. The captured `configuration.authority_reviewed=false` flag remains
unchanged: recording approval is a separate operator action inside a reviewed
controlled-activation procedure. Clean-image secret scan, runtime TLS/login check,
actual Compose merge/rollback review and API-only recreation are still pending.
At that audit checkpoint Stage 4A overall remained PARTIAL and activation was not
prepared. The final controlled activation procedure below supersedes that gate.
No sudo,
private credential read, DB write, secret replacement, provider activation, frontend
edit, deployment or push occurred.

## Completed controlled activation (reference; do not rerun)

Provisioning, live catalog/ownership and the Supabase account-authority review
are accepted. Do not rerun provisioning or the old post-provision inspections.
The reconciled approval is recorded in
`reports/professor-stage4a-auth-userdb/authority-approval-review.json`. This review
approves Professor PostgreSQL for application data only. Supabase retains users,
passwords, provider sessions, recovery, canonical UUID subjects and JWT issuance.
One existing confirmed user is preserved; no user or password migration occurs.

The agent has no Docker socket/root access and has not built or activated an API
image. The reviewed command therefore has a mandatory preparation phase before
it accepts `ACTIVATE`: it creates the exact clean image, scans all image layers,
history, config, build context and output against installed and actually staged
credentials, validates the **actual host Compose merge**, and prints its immutable
image ID and bounded delta. Unknown/drifted configuration refuses before runtime
changes. Readiness here means this fail-closed operator workflow is ready; it is
not evidence of an already built candidate or a completed live activation.

Use this single command from an interactive terminal:

```bash
sudo python3 -B /home/andy/.codex/worktrees/bb30/proptech-ai-copilot/scripts/ops/professor_stage4a_activation.py --apply
```

Before confirmation the command:

1. Locks Stage2 activation and Stage 4A provisioning/activation, verifies the clean
   committed isolated source and preserved main `next-env.d.ts`, and rejects
   forbidden/unknown backing storage. No secret is written to a checkout.
2. Requires the accepted active image
   `sha256:035a049691b0038f7508acc00c3e9bb82c101a295c9f45edcea8d1b03b3d42a0`,
   the exact active five-file Compose chain and healthy private containers.
   Original `/etc` files are copied privately before any new configuration.
3. Validates protected credential metadata and private STORE/STAGED consistency.
   Same-inode/same-size content drift is rejected by private comparisons; values
   and value hashes never appear in receipts. A private empty Docker config
   avoids inherited registry credentials.
4. Exports committed allowlisted public source, locks installed working API
   package versions, downloads public binary wheels into an isolated helper,
   builds with no build network, and scans every retained candidate image layer.
   There is no copied dotenv, Git directory, credential directory or frontend UI.
5. Validates a Compose delta limited to API image, Stage 4A entrypoint/health,
   explicit issuer/audience/enable/release fields and one dedicated read-only
   user-runtime secret. All other services, ports, networks, data volumes,
   provider guards and read-only NLSC/WRA mounts must remain identical.
6. Runs a transient read-only dedicated-role TLS probe from the **candidate** on
   the existing private app network. Exact catalog/grants and the pending approval
   are checked honestly. Imports, dependency consistency and immutable local
   NLSC/WRA artifacts are checked without provider calls. The pending flag is
   never faked. Records current Stage1/2 API and DB contracts and the existing
   Stage3 companion's pinned model/status on `127.0.0.1:8081`.
7. Writes root-only `ROLLBACK.sh`, `ROLLBACK.md`, original configuration hashes,
   the immutable previous image override and exact `change-plan.json` under
   `/var/backups/proptech-selfhost/stage4a-activation/<run>/`.

Review the printed immutable image, `recreate_only:["api"]`, authorities and
rollback path before entering `ACTIVATE`. If any preparation check refuses,
no API container or authority flag is changed. `--plan` performs this same build
and review preparation without confirmation/activation; it is **not** a purely
read-only command and is not needed before the single `--apply` invocation.

After confirmation, only a transactionally guarded
`professor_user.configuration.authority_reviewed=true` update is permitted. It
requires the exact singleton issuer/schema version and does not touch identity,
profile, case or serving rows. A root-only public-metadata approval witness is
created in `/etc/proptech-selfhost/stage4a-authority-approval.json`. The candidate
must then pass the complete production startup validation before the new override
is installed as `/etc/proptech-selfhost/stage4a-auth.override.yml`.

Only `api` is recreated, using `up --no-deps --no-build --pull never
--force-recreate api`. PostgreSQL and proxy containers retain their IDs/start
times; database volume identities remain identical. The existing standalone
Stage3 companion is observed through its pinned health/status/estimate; the
command never signals or replaces that process. Existing
proxy configuration is tested and its Nginx workers reload after API health to
refresh the upstream address cached by static `proxy_pass`; the proxy container
is not restarted/recreated and its configuration is not changed. Rollback does
the same after the restored API is healthy. Both paths wait up to120seconds for
the proxy's Docker health and actual loopback health/readiness to recover,
including stale unhealthy status and transient502 during worker handoff. Existing
core secret files are not replaced; recreation binds their current inodes plus
the dedicated user-runtime URL. Neither DB admin nor initialization credentials
are mounted into the API. Port8080 stays `127.0.0.1`; PostgreSQL has no host
listener. `market_ops` and paid providers remain disabled; X9 is not required.

Post-activation checks include private TLS/least privilege, live secret-mount
metadata/inodes, issuer/entrypoint/image, health/readiness, NLSC→RIS, WRA matched
and no-match, Market known-special exclusion/coverage, Valuation, Trend, Finder,
Stage3 pinned status, and unauthenticated denial on user-data routes. Logs remain
in memory for scanning. No real user token is requested, no test identity is
created, and no authenticated user data is modified by this workflow. Live
authenticated browser/cross-device acceptance remains frontend integration work;
backend ownership/session/CAS tests use a private disposable database.

Failure after override installation automatically restores only the prior API
image/profile; a failed recovery stops only the API and reports failure. Manual
recovery, if actually needed, is the exact `sudo bash <run>/ROLLBACK.sh` from that
run's evidence. The override moves to a unique inactive file **within `/etc`**;
separate backup filesystems are supported and recovery is repeatable after a
Compose failure. The rollback shell uses an empty environment and private Docker
configuration, so operator environment aliases cannot alter the merge. No schema
rollback, data erasure, database restart, volume
removal or credential replacement occurs. The separately approved authority
decision and any user data remain retained; a retry may accept an already-true
flag only with the exact protected approval witness.

Private evidence contains the actual before/after Compose models and rollback
material. The separately generated `/tmp/professor-stage4a-activation-*/` receipt
contains only whitelisted scanned metadata. Pending, applied and unverified SQL
approval states are distinguished even if a later phase fails. A failed receipt
publication never returns a successful exit. Never rerun activation blindly after
a refusal: inspect the sanitized reason/phase and preserve the evidence.

No `/dev/sda` access, X9 write, serving-data change, public ingress, provider
enablement, frontend change, cloud deployment or push is part of this command.

## Final live acceptance — 2026-10-30

Operator activation completed PASS/exit0 at `2026-10-30T04:13:51.337014+00:00`.
Authoritative private evidence:
`/var/backups/proptech-selfhost/stage4a-activation/20261030T040052Z-8cd21b4e0da2`.
The agent inspected all 22 sanitized receipt artifacts at
`/tmp/professor-stage4a-activation-dpf5uno4`; their names, sizes and hashes are
recorded in `reports/professor-stage4a-auth-userdb/successful-activation-evidence-manifest.json`.
The root-only evidence was not reopened and Docker socket access was not required
to duplicate these successful operator checks. Earlier provisioning/review
sections are historical checkpoints, not current instructions to repeat apply.

Active API image:
`sha256:dce27b6bd9b1d336e8b15c93559642722b5e98f4c21012df4718f220ab4c0cde`;
backend source: `1d4f4db7a991b4f7bb2baead7c3201dc21b50514`. Later acceptance
documentation commits do not require another build or recreation. Only the API
container changed. PostgreSQL and proxy IDs/images, DB volume identities and
Stage3 companion behavior were preserved. The actual Stage 4A merge, full clean
image/history/context/Compose/log credential scan, dedicated role TLS/grants,
reviewed approval flag and six intended read-only secret mounts passed. Container
secret metadata/inodes exactly match the host. No admin/init secret was added
to the API. The scanner covers known installed credential variants and key
signatures; it does not prove the absence of arbitrary unknown encodings.

Supabase remains the issuer and identity authority; Professor PostgreSQL owns
application records. The approval flag is true. A fresh read-only provider
aggregate still finds one confirmed, authenticated, previously signed-in user
created before Stage 4A provisioning, with zero banned/deleted/anonymous users.
No identity row, email, password or token was exported, and no provider user or
credential was changed. No frontend code was modified.

The current loopback API passes all 12 Stage1/2 checks: health/readiness, village
and NLSC→RIS demographics, WRA matched/no-match, Market and the known excluded
special period, Valuation, Trend and Finder. The ML companion's health/status
and known estimate pass with its accepted model/manifest pin and
`is_actionable=false`. The operator's DB before/after snapshots are identical:
451744 stored rows, 451672 official, 72 sample, 117986 reviewed exclusions;
row 38652 remains stored and has zero serving appearances. Persisted Market
coverage remains consistent across 368 regions, with 322 eligible and 46 zero
candidate regions; this is not a nationwide completeness claim.

PostgreSQL has no host5432 listener or published Docker port. Host8080 is bound
only to `127.0.0.1`; `market_ops` and paid providers remain disabled. NLSC/WRA
mounts still use `/srv/proptech-data/DB`; ordinary runtime has no X9 bind.
The main `frontend_next/next-env.d.ts` hash is unchanged. No `/dev/sda` operation,
X9 source write, deployment, push, reprovisioning or reactivation occurred during
this final acceptance pass.

Fresh focused validation:65 tests pass in 18.01 seconds using disposable private
PostgreSQL and signed fixture JWTs. They cover valid session/account/profile,
durable Saved Cases across fresh connections/repositories, logout/new-session
retention of cases/preferences/reports, revoked/refreshed/expired rejection and
cross-user read/update/delete denial. The disposable cluster had no TCP listener
and was stopped/removed by its fixture. Eight fresh live negative auth checks
also pass: six protected resources deny anonymous requests, and malformed and
unsigned expired tokens receive401 without echoing credentials. A correctly
signed expired token is covered by the disposable API tests, not by the unsigned
live probe. The full repository suite was not rerun.

**Remaining acceptance:** a valid real Supabase user session was neither supplied
nor read. The activation receipt explicitly leaves authenticated browser testing
for frontend integration. The one existing identity was not altered, and no
second provider user was created for testing. Therefore actual signed-in live
profile/case writes, backend logout/new provider login, cross-device retention
and real two-user end-to-end denial remain unproven. Backend persistence and
authorization are PASS with the test/catalog basis above; overall live Stage 4A
acceptance remains PARTIAL. No backend defect or additional host apply is
indicated. The frontend owner should consume
`docs/contracts/auth-user-api-v1.md` and record sanitized authorized-user outcomes
without exposing credentials. Public ingress/CORS/SMTP/recovery remain later
work, not part of this activation.

Rollback evidence is complete at the successful apply checkpoint: the exact
reviewed program created/fsynced original protected configuration backups,
configuration hashes, the immutable old-image override, `ROLLBACK.md` and
syntax-checked `ROLLBACK.sh` before asking ACTIVATE. Recovery restores only the
prior API image/profile, preserves all data and the separately approved authority,
uses a same-filesystem inactive override and empty environment, and waits for
bounded API/proxy readiness. The old image is
`sha256:035a049691b0038f7508acc00c3e9bb82c101a295c9f45edcea8d1b03b3d42a0`.
No rollback is required or was performed. The agent did not directly reopen the
root-only rollback files after activation. Detailed acceptance and proof scope:
`reports/professor-stage4a-auth-userdb/final-live-acceptance.json`.
