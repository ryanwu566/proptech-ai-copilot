# Supabase Emergency RLS Remediation — 2026-08

Stage -1 Emergency Supabase Security Hotfix.

- Branch: `security/supabase-rls-hotfix`
- Migration: `database/migrations/012_security_rls_deny_by_default.sql`
- Operator verification: `database/verification/verify_rls_deny_by_default.sql`
- Target project: `proptech-valuation-db` (ref `flyhsjcynreuofbcdxod`)
- Author context: authored without live database credentials in the working
  environment. Live application is an **operator step** (see Runbook below).

---

## 1. Detected issue

Supabase Security Advisor reported `rls_disabled_in_public` (ERROR) for tables
in the `public` schema. Any table in `public` without Row Level Security is
automatically reachable through the Supabase auto-generated Data API
(PostgREST) using the project's `anon` API key, which ships enabled with every
Supabase project. Even though the application does not use the Data API, the
API surface exists by default, so tables without RLS are internet-reachable.

Root cause: migration `004_add_pilot_evidence.sql` explicitly deferred RLS as a
manual operator step ("RLS activation is an operator step after the
authenticated Postgres role is selected. Anonymous clients must never receive a
list/select policy."). That operator step was never performed, so the pilot,
tax, professional-review, market, valuation and ledger tables shipped to a live
Supabase project with RLS disabled and the default Data API grants intact.

## 2. Application access model (why this is safe to fix)

Verified from the repository:

- Runtime connects to Postgres **directly** via `psycopg`
  (`services/postgres_runtime.connect` → `psycopg.connect(database_url)`).
- Connection strings: `DATABASE_URL`, `VALUATION_DATABASE_URL`,
  `PILOT_EVIDENCE_DATABASE_URL`, `COMPACT_GREEN_DATABASE_URL`.
- **No** `@supabase/supabase-js`, **no** `createClient`, **no** anon key, **no**
  `service_role` key, **no** `NEXT_PUBLIC_SUPABASE*` anywhere in the repository.
- Frontend (`frontend_next`) talks only to the FastAPI backend via
  `NEXT_PUBLIC_API_BASE_URL`. Its only committed env var is
  `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.
- The only `supabase.co` reference in the codebase is a **negative** assertion
  in `tests/test_plvr_cutover_rehearsal.py` verifying that connection strings
  never leak into rehearsal output.

Consequence: the backend connects as a privileged/owner role that **bypasses**
RLS. Enabling RLS (without FORCE) and revoking `anon`/`authenticated`
privileges closes the unused Data API surface **without affecting backend
functionality**.

## 3. Tables affected

### 3.1 Sensitive public tables that had RLS disabled (primary finding)

| Table | Sensitive columns |
| --- | --- |
| `pilot_contacts` | `contact_ciphertext` |
| `pilot_profiles` | `profile_json` |
| `pilot_feedback` | `free_text`, `privacy_concern`, `willingness_to_pay_json` |
| `professional_reviews` | `reviewer_display_name`, `qualification`, `notes` |
| `tax_analysis_history` | `client_name`, `payload_json` |
| `pilot_campaigns` | access-code hashes |
| `pilot_sessions` | participant/session hashes |
| `pilot_consents` | consent flags |
| `pilot_events` | event metadata |
| `schema_migration_ledger` | migration metadata (no secrets/business data; 6 rows at audit) |

### 3.2 Other public tables created without RLS (defense-in-depth, same fix)

`official_market_releases`, `official_market_artifacts`, `market_transactions`,
`market_transaction_quality_events`, `market_region_period_aggregates`,
`market_region_coverage`, `market_import_runs`, `market_import_checkpoints`,
`official_market_region_coverage`, `real_price_transactions`,
`community_buildings`, `valuation_import_runs`,
`market_district_period_aggregates`, `market_read_model_metadata`.

These hold non-personal market/valuation aggregates and operational metadata,
but there is no reason to expose them through the Data API, so they are covered
by the same deny-by-default sweep.

### 3.3 Public tables that already had RLS enabled (migration 010)

`plvr_dataset_generations`, `plvr_generation_transactions`,
`plvr_generation_market_aggregates`, `plvr_generation_region_coverage`,
`plvr_active_dataset`, `plvr_generation_load_checkpoints`. Migration 012 skips
these (the loop only enables RLS where `relrowsecurity = false`).

### 3.4 Non-public schema (not exposed by default)

`compact_green.*` (migration 011) lives in the `compact_green` schema, which is
**not** exposed by PostgREST's default `db-schemas = public`. No RLS finding is
expected there; it is out of scope for the Advisor `public` finding and is left
unchanged.

## 4. Classification

- `rls_disabled_in_public`: **ERROR** — sensitive/personal data (pilot contacts,
  profiles, feedback, tax client names/payloads, professional reviewer PII)
  reachable via the default anon Data API. Treated as the top-priority finding.
- `function_search_path_mutable`: **WARN** — the four `plvr_guard_*` functions
  had no pinned `search_path`.
- RLS-enabled-no-policy on backend-only tables: **INFO** — acceptable and
  intentional (deny-by-default). No permissive policy is added.

## 5. Exact remediation

Migration `012_security_rls_deny_by_default.sql` (idempotent, transactional,
role-existence guarded, no destructive operations):

1. **Enable RLS** on every base table (`relkind='r'`) in `public` that does not
   already have it (`ENABLE`, not `FORCE`, so the owner/backend role still
   operates). No permissive policy is added → deny-by-default for non-owner
   roles.
2. **Revoke** `ALL` on all tables, sequences and functions in `public` from
   `PUBLIC`, `anon`, and `authenticated`; revoke `USAGE` on schema `public`
   from `anon` and `authenticated` (guarded by `pg_roles` existence).
3. **Function hardening** for `plvr_guard_frozen_generation_manifest`,
   `plvr_guard_generation_transaction`, `plvr_guard_generation_derived_row`,
   `plvr_guard_active_generation`: `ALTER FUNCTION ... SET search_path =
   pg_catalog, public` (safe — they already fully-qualify every referenced
   object) and revoke `EXECUTE` from `PUBLIC`/`anon`/`authenticated`.
4. **Default privileges**: `ALTER DEFAULT PRIVILEGES FOR ROLE <owner> IN SCHEMA
   public REVOKE ALL ... FROM anon/authenticated/PUBLIC` for tables, sequences
   and functions — so future VNext tables (`properties`, `cases`, `evidence`,
   `documents`, `contacts`, CRM) are not auto-exposed.
5. A non-functional `COMMENT ON` marker on `schema_migration_ledger`.

Registered in the runner tuple `scripts/validate_postgres_migration.py :
MIGRATIONS`, applied by `scripts/apply_production_migrations.py` inside a
transaction with checksum recorded in `schema_migration_ledger`.

## 6. RLS before / after

| State | Before | After (expected post-apply) |
| --- | --- | --- |
| RLS on sensitive public tables | disabled | enabled, no policy (deny-all for non-owner) |
| RLS on other public tables | disabled | enabled, no policy |
| RLS on plvr_generation tables | enabled (010) | unchanged (enabled) |

## 7. Grants before / after

| Grantee | Before | After (expected) |
| --- | --- | --- |
| `anon` (tables/seq/func in public) | default Supabase grants present | none (revoked) |
| `authenticated` (tables/seq/func in public) | default Supabase grants present | none (revoked) |
| `anon`/`authenticated` USAGE on schema public | present | revoked |
| owner/backend role | full (owner) | unchanged (still owner) |
| future objects (default privileges) | inherited anon/authenticated | revoked by default |

## 8. Policies

None created. This is intentional deny-by-default. Per instruction, no
`USING (true)` policy is created merely to silence an Advisor warning, and
`TO authenticated` is not treated as authorization. Real ownership-based
policies belong to the later VNext Workspace architecture, not this hotfix.

## 9. Function changes

`plvr_guard_*` (4 functions): pinned `search_path = pg_catalog, public`;
EXECUTE revoked from `PUBLIC`/`anon`/`authenticated`. They remain
`SECURITY INVOKER` (unchanged). No SECURITY DEFINER functions were introduced
or altered.

## 10. Default privilege changes

`ALTER DEFAULT PRIVILEGES FOR ROLE <migration owner> IN SCHEMA public` revoking
tables/sequences/functions from `anon`, `authenticated`, and functions/tables
from `PUBLIC`. Applies to objects created **after** the migration by the owner
role.

## 11. Advisor after

**NOT RUN (no live credentials in the working environment).** Must be re-run by
an operator after applying migration 012. Acceptance target:
`rls_disabled_in_public` ERROR = 0 and sensitive-column exposure Error/Critical
= 0. See Runbook §14.

## 12. Anonymous / authenticated attack verification

**NOT RUN (no live credentials, no `psql`/`supabase` CLI, no reachable
Postgres in the working environment).** A ready-to-run, read-only probe is
provided in `database/verification/verify_rls_deny_by_default.sql` (SET ROLE
anon/authenticated probes + grant/RLS/function checks) plus REST probes in the
Runbook. Expected post-apply: all anon/authenticated SELECT/INSERT/UPDATE/DELETE
on `pilot_contacts`, `pilot_profiles`, `pilot_feedback`, `professional_reviews`,
`tax_analysis_history`, `schema_migration_ledger` fail with `permission denied`
or return zero rows.

## 13. Exposure / log investigation

**UNABLE TO DETERMINE.** No Supabase log/API access was available in the working
environment (no dashboard, no `SUPABASE_ACCESS_TOKEN`, no log export). This
assessment can be neither "NO EVIDENCE FOUND" nor "NO BREACH" without inspecting
the project's API/Postgres/Auth logs. The window of exposure is: from whenever
each affected table was created in the live project until migration 012 is
applied. The affected sensitive tables reportedly held 0 rows at the prior
audit (`schema_migration_ledger` held 6 rows of non-sensitive metadata), which
bounds — but does not eliminate — data-exfiltration risk. See Runbook §Log
Investigation for exactly what an operator must inspect.

## 14. Operator runbook (live steps requiring credentials)

1. **Backup checkpoint** on `flyhsjcynreuofbcdxod` (documented DB snapshot).
2. **Apply migration** (against the live DATABASE_URL, never SQLite):
   ```
   python scripts/apply_production_migrations.py \
     --database-url "<LIVE_POSTGRES_URL>" --release-version <release>
   ```
   Expect `{"status": "pass", ...}`. The runner is transactional and records a
   checksum in `schema_migration_ledger`.
3. **Verify** with `database/verification/verify_rls_deny_by_default.sql` in the
   Supabase SQL Editor. All five queries must meet their documented targets.
4. **REST attack probe** (from a shell, using the project's public anon key):
   ```
   curl -s "https://flyhsjcynreuofbcdxod.supabase.co/rest/v1/pilot_contacts?select=*" \
     -H "apikey: <ANON_KEY>" -H "Authorization: Bearer <ANON_KEY>"
   ```
   Repeat for `pilot_profiles`, `pilot_feedback`, `professional_reviews`,
   `tax_analysis_history`, `schema_migration_ledger`. Each must return an
   empty array `[]` or a permission error — never data.
5. **Re-run Security Advisor**; confirm `rls_disabled_in_public` = 0 ERROR and
   0 Critical/Error sensitive-column findings. Record remaining INFO/WARN.
6. **Log investigation**: inspect Supabase Logs → API (PostgREST) for
   `GET/POST/PATCH/DELETE /rest/v1/pilot_*`, `/rest/v1/tax_analysis_history`,
   `/rest/v1/professional_reviews`; and Postgres/Auth logs, for the exposure
   window. Classify strictly as one of NO EVIDENCE FOUND / POSSIBLE / CONFIRMED
   / UNABLE TO DETERMINE based on what the logs actually show and their
   retention limits.

## 15. Legacy paused project

`proptech-valuation-green` / ref `osypacuurzkqerfhcqty`: **no committed
reference** exists in the repository or deployment configuration (`render.yaml`,
`.github/workflows`, `config/`). Project refs are supplied at runtime via
environment variables, not committed. The legacy project was **not** resumed,
upgraded, deleted, or migrated. No action taken.

## 16. Remaining risks

- Live application of migration 012 has not been executed here; the live posture
  remains vulnerable until an operator applies it (Runbook §14).
- Historical exposure cannot be ruled out without log inspection
  (UNABLE TO DETERMINE, §13).
- `compact_green` schema tables have no RLS; they are not exposed by the default
  PostgREST `public`-only configuration, but if `db-schemas` is ever widened to
  include `compact_green`, they would need the same treatment.
- Real per-user authorization policies are deferred to VNext Workspace
  architecture; until then, sensitive tables are backend-only (no direct client
  access), which is the correct interim posture.
