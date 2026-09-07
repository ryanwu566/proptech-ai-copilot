# Stage 1 Live Migration Ledger Reconciliation

Status: read-only classification complete; reconciliation execution blocked
Inspected: 2026-09-07 (Asia/Taipei)
Live project: Supabase project ref `flyhsjcynreuofbcdxod`
Authoritative source: `origin/main` at `a8331e1b30da27b8992ea8f4b040a04666543170`
Readiness branch: `ops/stage1-production-readiness`
Starting readiness commit: `ce808fbb05c4da520b51ff8559474feb6b7c3c82`

This document reconciles repository migration intent, the custom production ledger,
Supabase migration history, and the live PostgreSQL catalog. It authorizes no database
change. The live session issued only `SELECT`, `WITH ... SELECT`, and `SHOW` statements
against application data needed for the preservation check, `pg_catalog`,
`information_schema`, the custom ledger, and Supabase migration-history metadata. It
did not execute a migration or any live mutation statement.

## Decision

**Reconciliation gate: BLOCKED.** All 18 logical registry entries are confidently
classified and there is a deterministic reconciliation plan, but executing that plan
requires a separately reviewed and authorized live mutation window.

| Classification | Count | Migrations |
| --- | ---: | --- |
| `APPLIED_AND_LEDGERED` | 6 | 001, both distinct 002 entries, 003, 007, 010 |
| `APPLIED_BUT_UNLEDGERED` | 4 | 004, 005, 006, 012 |
| `NOT_APPLIED` | 8 | 008, 009, 011, 013, 014, 015, 016, 017 |
| `PARTIALLY_APPLIED` | 0 | none |
| `AMBIGUOUS` | 0 | none |

There is no unexplained checksum mismatch and no runner defect. The runner correctly
fails closed on the historical 007 checksum representation. Production rollout
remains blocked.

## Authoritative migration registry

The registry contains 18 logical entries. The duplicate numeric sequence 002 is two
different migrations and is deliberately not collapsed. The next safe sequence is
018, and no `018_*.sql` file exists.

| Order | Logical ID | Seq. | Filename | Execution policy | Repository SHA-256 |
| ---: | --- | ---: | --- | --- | --- |
| 1 | `legacy-001-dedupe-key` | 001 | `001_add_dedupe_key_to_real_price_transactions.sql` | `legacy_operator` | `2eb4a3e8652d3f18cac9c200d38b3bf350e77bd36aa103f8b76ecf4004143223` |
| 2 | `legacy-002-market-direct-indexes` | 002 | `002_add_market_direct_query_indexes.sql` | `legacy_operator` | `2cb6da19a01415ffee34845aa294843257cce7f9991803e0ca470e3405cfc310` |
| 3 | `legacy-002-valuation-import-runs` | 002 | `002_expand_valuation_import_runs.sql` | `legacy_operator` | `0108c13fad4d0310e291c0d2e041868c7d59b8fb2f47739831139fa3039b2d64` |
| 4 | `legacy-003-market-region-coverage` | 003 | `003_add_market_region_coverage.sql` | `legacy_operator` | `267db5dcba4c12646b78f480b289cbd289a323bc205a0a8fe5ba507290efb16b` |
| 5 | `production-004-pilot-evidence` | 004 | `004_add_pilot_evidence.sql` | `production_runner` | `ba2a3f21605983f13b16648e344e3a71baf677ee7e086d155a39dc9b2220b516` |
| 6 | `production-005-pilot-security-indexes` | 005 | `005_add_pilot_security_indexes.sql` | `production_runner` | `7da6cffddc6a715bfc041fe37eb9ebf19574e30ef5379a4917db6bc634614d3c` |
| 7 | `production-006-tax-analysis-history` | 006 | `006_add_tax_analysis_history.sql` | `production_runner` | `cc0e6bc09b4f0736c6ddb012ff34912db0385339c93d329d39203e696dc3d1c0` |
| 8 | `production-007-schema-migration-ledger` | 007 | `007_add_schema_migration_ledger.sql` | `production_runner` | `1d1d20edf40b9d2782dd9e314d7e4a2d35ac0aaac5d1570494e58f3e3d982996` |
| 9 | `production-008-official-market-pipeline` | 008 | `008_add_official_market_pipeline.sql` | `production_runner` | `22e0a282a40692e05054388fe2e4aa5f25c253e733b2aedd50f4d30446b788d9` |
| 10 | `production-009-official-market-coverage` | 009 | `009_separate_official_market_region_coverage.sql` | `production_runner` | `c14084726fa101f3a93e700525abe90f1caee46f542f5a37a13d5d545b3526f7` |
| 11 | `production-010-plvr-generation-schema` | 010 | `010_add_plvr_generation_schema.sql` | `production_runner` | `fcf69fc2d3b5e6419e2d94a6d92abc03c9b4424204e9bd129b85ea749ebed4a5` |
| 12 | `compact-green-011-schema` | 011 | `011_add_plvr_compact_green_schema.sql` | `compact_green_operator` | `107ba18c7db124a40183dc048581f821c853499feca203f874152c5b0dab2af2` |
| 13 | `production-012-security-rls-deny-default` | 012 | `012_security_rls_deny_by_default.sql` | `production_runner` | `bb1551d4e7fda1d3c7df99e3fd64a53f7fb05a8dcfb7ec0049c18ae6c2dfa056` |
| 14 | `production-013-vnext-workspace-case-foundation` | 013 | `013_vnext_workspace_case_foundation.sql` | `production_runner` | `322c66295975a612d03b39d46c2fdb4fdb0a7e4be6212ae3f4488fee4ce73952` |
| 15 | `production-014-vnext-property-graph-evidence-foundation` | 014 | `014_vnext_property_graph_evidence_foundation.sql` | `production_runner` | `0b465671d513a4b182af8c56e784e8a7e161ed019e6218934ce30625cde7dacd` |
| 16 | `production-015-vnext-identity-resolution-candidates` | 015 | `015_vnext_identity_resolution_candidates.sql` | `production_runner` | `b87b582e013d3733fe8db179681489fcc950ea6998b7c23552b0fa88a044361f` |
| 17 | `production-016-vnext-identity-confirmation-case-links` | 016 | `016_vnext_identity_confirmation_case_links.sql` | `production_runner` | `b0f5ae9694fbb6dcb64d467aa9338778b3c83e7d0da3c5bbab9f710dbebd3636` |
| 18 | `production-017-vnext-legacy-saved-case-import` | 017 | `017_vnext_legacy_saved_case_import.sql` | `production_runner` | `0753b222597d7e0d6cbc618a17bc1d07d047a0d499318936c29880a119182efa` |

## Exact live custom ledger

`public.schema_migration_ledger` contains exactly these six rows and no others:

| Migration ID | Schema version | Applied at | Release version | Stored checksum |
| --- | --- | --- | --- | --- |
| `001_add_dedupe_key_to_real_price_transactions` | `schema-001` | `2026-08-14 03:43:49.208983+00` | `phase2f-approval-a-ledger-baseline` | `557eef5065a66083aadb1c189ed68dc1271cfdfff48547abcf7f54be9fee0bcd` |
| `002_add_market_direct_query_indexes` | `schema-002` | `2026-08-14 03:43:49.208983+00` | `phase2f-approval-a-ledger-baseline` | `ca201d932388090018e5543f89d69d43d812c6596e995d354b30b50f52e1203f` |
| `002_expand_valuation_import_runs` | `schema-002` | `2026-08-14 03:43:49.208983+00` | `phase2f-approval-a-ledger-baseline` | `da83474b55277316a7e8a35c490eb2a31595781bc2331f2d1aba69caea2c8caa` |
| `003_add_market_region_coverage` | `schema-003` | `2026-08-14 03:43:49.208983+00` | `phase2f-approval-a-ledger-baseline` | `34171ca38e64509c29ae2075874388cf9736ae3df7752c6ae105118d3ee90ce5` |
| `007_add_schema_migration_ledger` | `schema-007` | `2026-08-14 03:43:49.208983+00` | `phase2f-approval-a-ledger-baseline` | `f4a8ef650ab6bbce8bd1909345785411f350eb6aabe23d0d377fb674ef5934f5` |
| `010_add_plvr_generation_schema` | `schema-010` | `2026-08-14 03:43:49.208983+00` | `phase2f-approval-a-ledger-baseline` | `fcf69fc2d3b5e6419e2d94a6d92abc03c9b4424204e9bd129b85ea749ebed4a5` |

Supabase's separate `supabase_migrations.schema_migrations` history corroborates the
unledgered historical execution path:

| Version | Name | Stored statement SHA-256 | Comparison |
| --- | --- | --- | --- |
| `20260818094700` | `add_pilot_evidence` | `ba2a3f21605983f13b16648e344e3a71baf677ee7e086d155a39dc9b2220b516` | exact registry match |
| `20260818094730` | `add_pilot_security_indexes` | `7da6cffddc6a715bfc041fe37eb9ebf19574e30ef5379a4917db6bc634614d3c` | exact registry match |
| `20260818094742` | `add_tax_analysis_history` | `cc0e6bc09b4f0736c6ddb012ff34912db0385339c93d329d39203e696dc3d1c0` | exact registry match |
| `20260828031611` | `security_rls_deny_by_default` | `be150b2576aca111f0b6bc3075532c4b0808174b912ac46abb5a8409bdfaa6e0` | raw text differs only in comments/whitespace; executable-normalized stored and repository hashes both equal `f19ef88fbd02c95382024b3d7217649ccf98eafad794f18e4030e1a22ad2c2dd` |

The unrelated history row `20260819031213 retire_blue_legacy_plvr_generation_data`
is not a repository migration-registry entry and is not mapped to 001–017.

## Full migration matrix

“Pending” below means absent from the custom ledger's production-runner subset; it
does not claim that the catalog effect is absent.

| Order / logical ID | Filename / policy | Runner state | Custom ledger | Catalog evidence | Classification | Proposed rollout action |
| --- | --- | --- | --- | --- | --- | --- |
| 1 `legacy-001-dedupe-key` | `001_add_dedupe_key_to_real_price_transactions.sql`; `legacy_operator` | not managed | present | `dedupe_key` and exact partial unique index present | `APPLIED_AND_LEDGERED` | normalize historical checksum only as part of the controlled ledger operation; no migration execution |
| 2 `legacy-002-market-direct-indexes` | `002_add_market_direct_query_indexes.sql`; `legacy_operator` | not managed | present | both exact predicate indexes present | `APPLIED_AND_LEDGERED` | same checksum normalization; no migration execution |
| 3 `legacy-002-valuation-import-runs` | `002_expand_valuation_import_runs.sql`; `legacy_operator` | not managed | present | all ten added columns match type, default, and nullability | `APPLIED_AND_LEDGERED` | same checksum normalization; no migration execution |
| 4 `legacy-003-market-region-coverage` | `003_add_market_region_coverage.sql`; `legacy_operator` | not managed | present | exact six-column legacy table, primary key, and two indexes present | `APPLIED_AND_LEDGERED` | same checksum normalization; no migration execution |
| 5 `production-004-pilot-evidence` | `004_add_pilot_evidence.sql`; `production_runner` | pending by row absence | absent | all eight tables, columns, defaults, constraints, and four indexes match; Supabase history hash matches | `APPLIED_BUT_UNLEDGERED` | controlled baseline row after reasserting catalog and history fingerprints |
| 6 `production-005-pilot-security-indexes` | `005_add_pilot_security_indexes.sql`; `production_runner` | pending by row absence | absent | all three exact indexes present; Supabase history hash matches | `APPLIED_BUT_UNLEDGERED` | controlled baseline row; do not replay as a substitute for provenance |
| 7 `production-006-tax-analysis-history` | `006_add_tax_analysis_history.sql`; `production_runner` | pending by row absence | absent | exact table, sequence-backed key, and two indexes present; Supabase history hash matches | `APPLIED_BUT_UNLEDGERED` | controlled baseline row; preserve `HISTORY-001` |
| 8 `production-007-schema-migration-ledger` | `007_add_schema_migration_ledger.sql`; `production_runner` | ledgered, but current runner checksum gate fails | present | exact five columns, primary key, and index present; 012 later changed RLS/comment | `APPLIED_AND_LEDGERED` | reconcile stored CRLF hash to canonical registry hash under separate authorization |
| 9 `production-008-official-market-pipeline` | `008_add_official_market_pipeline.sql`; `production_runner` | pending by row absence | absent | all seven unambiguous new table names are absent; the existing `market_region_coverage` is proven to be the six-column 003 table, not the release-based 008 shape | `NOT_APPLIED` | later normal runner execution after ledger reconciliation and rollout prerequisites |
| 10 `production-009-official-market-coverage` | `009_separate_official_market_region_coverage.sql`; `production_runner` | pending by row absence | absent | `official_market_region_coverage` and its index are absent; the conditional rename predicate is false on the legacy 003 table | `NOT_APPLIED` | later normal runner execution immediately after 008 |
| 11 `production-010-plvr-generation-schema` | `010_add_plvr_generation_schema.sql`; `production_runner` | ledgered/skipped | present | six tables, 31 constraints, 14 catalog indexes, four functions, five triggers, three views, six RLS-enabled tables, and six comments match | `APPLIED_AND_LEDGERED` | no action |
| 12 `compact-green-011-schema` | `011_add_plvr_compact_green_schema.sql`; `compact_green_operator` | not managed | absent | schema `compact_green` and all eight compact tables are absent | `NOT_APPLIED` | no action on this production database; retain separate compact-green runbook |
| 13 `production-012-security-rls-deny-default` | `012_security_rls_deny_by_default.sql`; `production_runner` | pending by row absence | absent | executable-normalized Supabase history matches; all 22 public tables have RLS, no policies/FORCE, grants are closed, guards/default ACL/comment match | `APPLIED_BUT_UNLEDGERED` | controlled baseline row after one final security assertion |
| 14 `production-013-vnext-workspace-case-foundation` | `013_vnext_workspace_case_foundation.sql`; `production_runner` | pending by row absence | absent | `vnext_api`, `vnext_core`, and `vnext_private` are absent; therefore its role, schemas, five tables, functions, triggers, policies, grants, and comments are absent | `NOT_APPLIED` | later normal runner execution |
| 15 `production-014-vnext-property-graph-evidence-foundation` | `014_vnext_property_graph_evidence_foundation.sql`; `production_runner` | pending by row absence | absent | both required VNext schemas are absent; all effects are inside or depend on them and none has a public-side durable effect | `NOT_APPLIED` | later normal runner execution |
| 16 `production-015-vnext-identity-resolution-candidates` | `015_vnext_identity_resolution_candidates.sql`; `production_runner` | pending by row absence | absent | all four new tables and the altered `vnext_core.cases` target are absent with `vnext_core` | `NOT_APPLIED` | later normal runner execution |
| 17 `production-016-vnext-identity-confirmation-case-links` | `016_vnext_identity_confirmation_case_links.sql`; `production_runner` | pending by row absence | absent | both new tables and every altered VNext target are absent with the VNext schemas | `NOT_APPLIED` | later normal runner execution |
| 18 `production-017-vnext-legacy-saved-case-import` | `017_vnext_legacy_saved_case_import.sql`; `production_runner` | pending by row absence | absent | `vnext_private.legacy_case_imports` and its dependent VNext objects are absent | `NOT_APPLIED` | later normal runner execution |

## Durable-effect inventory and catalog evidence

### 001 — legacy dedupe key

- Expected: nullable `text` column `real_price_transactions.dedupe_key`; unique
  partial btree index `uq_real_price_source_dedupe_key` on `(source, dedupe_key)`
  where `dedupe_key IS NOT NULL`.
- Live: column type/nullability and the index expression, uniqueness, and predicate
  match exactly. No constraints, functions, triggers, RLS, policy, grant, comment, or
  seed effect is encoded by 001.

### 002 — market direct-query indexes

- Expected: `idx_market_direct_query_county_district_period` on
  `(city, district, transaction_period DESC)` and
  `idx_market_direct_query_county_period` on `(city, transaction_period DESC)`;
  both predicates require source `official_plvr_opendata`, positive
  `unit_price_per_ping`, and positive `area_ping`.
- Live: both non-unique btree definitions and predicates match exactly. No other
  durable effect is encoded by this 002 file.

### 002 — valuation import-run expansion

- Expected columns on `valuation_import_runs`: nullable `text` `city_scope`,
  `district_scope`, and `road_scope`, each default `''`; non-null `integer`
  `input_file_count`, `read_rows`, `accepted_rows`, `inserted_rows`, `updated_rows`,
  `skipped_duplicate_rows`, and `excluded_rows`, each default `0`.
- Live: all ten columns match type, nullability, and default. No index, constraint,
  function, trigger, RLS, policy, grant, comment, or seed effect is encoded.

### 003 — legacy market-region coverage

- Expected table `market_region_coverage`: `county text NOT NULL`, `district text NOT
  NULL`, `coverage_status text NOT NULL`, `valid_market_candidate_count integer NOT
  NULL DEFAULT 0`, nullable `source_updated_at date`, and `reconciled_at timestamptz
  NOT NULL`; primary key `(county, district)`; indexes
  `idx_market_region_coverage_county` and `idx_market_region_coverage_status`.
- Live: all columns, defaults/nullability, primary key, and both indexes match. The
  absence of `release_id` proves this is not the similarly named 008 table.

### 004 — pilot evidence

- Expected eight tables and columns:
  - `pilot_campaigns`: `campaign_id`, `access_code_hash`, `status`, `starts_at`,
    `expires_at`, `created_at`, `updated_at`, `is_test_fixture`.
  - `pilot_sessions`: `session_id`, `session_token_hash`, `campaign_id`,
    `participant_hash`, `workflow_id`, `locale`, `device_class`, `viewport_class`,
    `completion_status`, `current_step`, `consent_version`,
    `publication_permission`, `started_at`, `completed_at`, `abandoned_at`,
    `created_at`, `updated_at`, `is_test_fixture`.
  - `pilot_consents`: `session_id`, five consent booleans, `audio_collected`,
    `transcript_stored`, `version`, `created_at`.
  - `pilot_profiles`: `session_id`, `profile_json`, `created_at`, `updated_at`.
  - `pilot_contacts`: `session_id`, `contact_ciphertext`, `created_at`.
  - `pilot_events`: `event_id`, `session_id`, `event_type`, `metadata_json`,
    `occurred_at`, `idempotency_key`.
  - `pilot_feedback`: `session_id`, `task_completion`, seven bounded 1–5 ratings,
    seven text feedback fields, `willingness_to_pay_json`, `provenance`,
    `verification_status`, `publication_status`, `created_at`, `updated_at`.
  - `professional_reviews`: `review_id`, reviewer identity/qualification fields,
    consent, reviewed capability/version/scope/outcome fields, notes/change fields,
    `reviewed_at`, `publication_status`, `created_at`, `updated_at`.
- Expected constraints: eight primary keys; session foreign keys (cascade for
  consents/profiles/contacts/events/feedback); campaign foreign key; unique event
  `(session_id, idempotency_key)`; seven feedback rating checks. Expected explicit
  indexes: `idx_pilot_sessions_campaign`, `idx_pilot_events_session`,
  `idx_pilot_feedback_publication`, and `idx_pilot_profiles_session`.
- Live: all 88 table columns, their types/defaults/nullability, all 22 primary-key,
  foreign-key, unique, and rating-check constraints, and all four indexes match. The eight tables
  are owned by `postgres`. Migration 004 deliberately creates no function, trigger,
  RLS policy, grant, comment, or seed row and defers RLS to an operator step. Current
  RLS/grants are attributable to 012, not 004.

### 005 — pilot security/performance indexes

- Expected and live exact: `idx_pilot_sessions_completion_updated` on
  `(completion_status, updated_at)`, `idx_pilot_events_idempotency` on
  `(session_id, idempotency_key)`, and `idx_professional_reviews_publication` on
  `(publication_status, reviewed_at)`. No other durable effect is encoded.

### 006 — tax-analysis history

- Expected table `tax_analysis_history`: sequence-backed `bigserial id` primary key;
  non-null `case_id`, `client_name`, `eligibility_status`, `signal_color` text;
  non-null `risk_score integer`; non-null `payload_json jsonb`; non-null
  `created_at timestamptz DEFAULT now()`; indexes
  `idx_tax_analysis_history_created_at` and `idx_tax_analysis_history_case_id` with
  their descending time keys.
- Live: table columns, sequence default, primary key, and both indexes match; owner is
  `postgres`. The migration contains no seed row. The separately required preservation
  row is verified below.

### 007 — custom migration ledger

- Expected table `schema_migration_ledger` with non-null primary-key
  `migration_id text`, non-null `schema_version text`, non-null `applied_at
  timestamptz DEFAULT now()`, nullable `release_version text`, nullable `checksum
  text`; index `idx_schema_migration_ledger_applied_at` on `applied_at DESC`.
- Live: all structural effects match. Migration 012 subsequently enabled RLS and set
  the current table comment, so those later effects do not conflict with 007.

### 008 — official-market pipeline

- Expected tables: `official_market_releases`, `official_market_artifacts`,
  `market_transactions`, `market_transaction_quality_events`,
  `market_region_period_aggregates`, release-shaped `market_region_coverage`,
  `market_import_runs`, and `market_import_checkpoints`.
- Expected columns cover release/source/status/count metadata; artifact lineage and
  retention; transaction identity, geography, prices, validation, dedupe and import
  time; quality-event reason/time; period aggregate statistics and coverage/data
  status; release-shaped coverage (`release_id`, geography, `latest_period`, count,
  source date); and restartable import-run/checkpoint state.
- Expected constraints include all primary/foreign/unique keys, status/sample-status
  checks, nonnegative byte/count checks, and release delete behavior. Explicit indexes:
  `idx_market_transactions_region_period`, `idx_market_transactions_release`,
  `idx_market_transactions_quality`, `idx_market_aggregates_region_period`, and
  partial unique `uq_market_active_release` where `is_active`.
- Live: the seven unambiguous new names are absent. The one colliding name,
  `market_region_coverage`, has the exact 003 shape, not the 008 shape. No 008
  function, trigger, RLS, policy, grant, comment, or seed effect exists in the SQL.

### 009 — separated official coverage

- Expected: conditionally rename an 008-shaped `market_region_coverage` only when it
  has `release_id` and lacks `valid_market_candidate_count`; otherwise preserve the
  legacy table; ensure `official_market_region_coverage` with seven release/geography/
  coverage columns, composite primary key, release foreign key, and index
  `idx_official_market_region_coverage_region_period`.
- Live: the rename predicate is false on the 003 table, and the official table/index
  are absent. There are no other durable effects.

### 010 — PLVR generation schema

- Expected six tables:
  - `plvr_dataset_generations` (21 manifest, expected-count/range, validation/state,
    and lifecycle columns).
  - `plvr_generation_transactions` (27 generation/lineage/identity, period/geography,
    price, canonical-status, publishability, and load-time columns).
  - `plvr_generation_market_aggregates` (14 generation/geography/period, aggregate,
    coverage/data/method/time columns).
  - `plvr_generation_region_coverage` (9 generation/geography/period/status/reason/time
    columns).
  - `plvr_active_dataset` (5 active/previous generation pointer columns).
  - `plvr_generation_load_checkpoints` (10 source cursor/count/completion/time columns).
- Expected and live: 31 primary/foreign/unique/check constraints; six explicit
  performance indexes plus eight constraint indexes (14 catalog indexes total); RLS
  enabled but not forced on all six tables; no RLS policies or grants in 010.
- Expected and live functions: `plvr_guard_frozen_generation_manifest`,
  `plvr_guard_generation_transaction`, `plvr_guard_generation_derived_row`, and
  `plvr_guard_active_generation`, all security-invoker. Expected and live triggers:
  `trg_plvr_frozen_generation_manifest`, `trg_plvr_generation_transaction`,
  `trg_plvr_generation_aggregate`, `trg_plvr_generation_coverage`, and
  `trg_plvr_active_generation`.
- Expected and live `security_invoker=true` views: `plvr_active_transactions`,
  `plvr_active_market_aggregates`, and `plvr_active_region_coverage`; each joins the
  generation table to the active pointer, and the transaction view additionally
  requires `publishable`.
- All six operator-boundary comments match. The migration is schema-only and seeds no
  dataset or active pointer.

### 011 — compact-green schema

- Expected schema `compact_green`; tables `compact_generations`, `compact_artifacts`,
  `compact_geographies`, `compact_roads`, `compact_building_types`,
  `compact_transaction_facts`, `compact_transaction_evidence`, and
  `compact_market_aggregates`; 12 unique/performance/covering indexes. The SQL has an
  explicit transaction and is schema-only: the documented generation ID, dataset
  hash, and expected row counts are comments, not seed operations.
- Live: schema and all eight tables are absent. This migration belongs to the separate
  `compact_green_operator`, not the production runner for this database.

### 012 — deny-by-default security hotfix

- Expected: dynamically enable (not FORCE) RLS on every ordinary public table; create
  no permissive policy; revoke all public-schema table/sequence/function privileges
  from `PUBLIC`, `anon`, and `authenticated`; revoke direct public-schema `USAGE` from
  `anon` and `authenticated`; pin the four PLVR guard functions to search path
  `pg_catalog, public` and revoke their execution; close creator-default table,
  sequence, and function privileges for `anon`/`authenticated` and default table/
  function privileges for `PUBLIC`; set the ledger security comment.
- Provenance: Supabase history version `20260828031611` contains an executable body
  identical to the repository SQL after removing comments and whitespace. Both
  normalized hashes are
  `f19ef88fbd02c95382024b3d7217649ccf98eafad794f18e4030e1a22ad2c2dd`.
- Live: 22/22 public base tables have RLS enabled; 0/22 use FORCE; zero public policies
  exist. `anon` and `authenticated` have effective privileges on 0/25 public
  tables/views, 0/3 sequences, and 0/4 routines. Actual relation/function ACLs contain
  zero `PUBLIC` entries. The four guards are security-invoker and have exactly the
  pinned search path. Current-owner default ACLs contain no `PUBLIC`, `anon`, or
  `authenticated` entries prohibited by 012. The ledger comment matches.
- Nuance: schema `public` retains PostgreSQL's `PUBLIC=USAGE`, so `anon` and
  `authenticated` inherit schema usage even though their direct ACL entries are absent.
  This is also the result of executing the exact 012 SQL: 012 revokes direct grants
  from those roles but does not revoke schema usage from the `PUBLIC` pseudo-role.
  Relation/routine privileges and RLS still deny the Data API roles. This is not
  evidence of partial execution.

### 013 — VNext workspace/case foundation

- Expected role/schemas: create and harden non-superuser, no-BYPASSRLS, no-password
  login role `vnext_api`; comment it; require `auth.users` and `auth.uid()`; create
  `vnext_core` and `vnext_private`; revoke `PUBLIC`; grant bounded schema/function
  access; set restrictive default privileges and schema comments.
- Expected tables/columns: `workspaces` (10 identity/type/name/status/version/owner/time
  columns), `workspace_members` (11 workspace/user/role/status/lifecycle columns),
  `cases` (13 workspace/purpose/status/title/identity/assignment/version/time columns),
  `idempotency_records` (14 actor/route/key/fingerprint/status/response/time columns),
  and `audit_events` (13 actor/event/resource/request/outcome/metadata/time columns).
- Expected: 46 named foreign/unique/check constraints plus primary keys; 13 explicit
  indexes; functions `guard_case_update`, `guard_idempotency_update`, and
  `guard_audit_append_only` with their three triggers; ENABLE and FORCE RLS on all five
  tables; nine policies (`workspace_members_self_select`,
  `workspaces_active_member_select`, three `cases_*`, three `idempotency_*`, and
  `audit_actor_insert`); bounded `vnext_api` grants; four comments. No seed rows.
- Live: `vnext_api`, `vnext_core`, and `vnext_private` are all absent. The migration has
  no public-side durable object, so every durable effect is absent.

### 014 — VNext property graph/evidence foundation

- Expected tables/columns: `property_entities` (9 identity/status/label/version/time
  columns), `property_identity_references` (17 type/key/display/source/confidence/
  status/validity/supersession/creator columns), `evidence_items` (33 value/reference,
  source/provider, time/coverage/status/quality/license/lineage/hash/version/raw-ref/
  supersession/creator columns), `property_graph_nodes` (6 typed target/creator
  columns), `property_relations` (20 endpoint/type/direction/confidence/source/evidence/
  status/validity/confirmation/supersession/creator columns), `evidence_lineage` (9
  parent/child/transformation/creator columns), and `evidence_links` (8 evidence/
  subject/type/scope/creator columns).
- Expected: 104 named scope-safe foreign/unique/check constraints plus primary keys;
  18 explicit indexes; four functions (`guard_property_graph_node_target`,
  `append_property_graph_node`, `guard_property_relation_endpoints`,
  `guard_graph_evidence_append_only`); ten graph-materialization, endpoint, and
  append-only triggers; ENABLE and FORCE RLS on all seven tables; 14 member-select/
  writer-insert policies; `PUBLIC` revokes and bounded `vnext_api` SELECT/INSERT
  grants; five immutability/provenance comments. No seed rows.
- Live: required schemas are absent, and 014 creates no public-side durable object.

### 015 — identity resolution and candidates

- Expected: add workspace-scoped uniqueness to `cases`; create
  `identity_resolutions` (20 input/normalization/status/coverage/ambiguity/human-gate/
  supersession/version/request lifecycle columns), `resolution_attempts` (21 bounded
  provider/source/outcome/error/time/creator columns), `identity_candidates` (26
  normalized identity, provenance, rank/confidence/coverage/support/supersession/
  human-gate/creator columns), and `identity_conflicts` (15 competing-resource/type/
  severity/basis/state/creator columns).
- Expected: 82 named tenant-scope, lifecycle, bounded-enum/JSON/count, provenance,
  immutable-human-gate, and foreign/unique/check constraints; 14 explicit indexes;
  functions `guard_identity_candidate_support` and
  `guard_identity_resolution_append_only`; five support-scope/append-only triggers;
  ENABLE and FORCE RLS on all four tables; eight select/insert policies; `PUBLIC`
  revokes, bounded SELECT/INSERT grants, and four comments. No seed rows and no
  PropertyEntity creation/confirmation.
- Live: `vnext_core` is absent; every table and altered target is absent.

### 016 — human confirmation and case links

- Expected alterations: add workspace-record uniqueness and
  `response_error_code`/check to `idempotency_records`; add
  `identity_confirmation_id`, foreign/check constraints, and confirmation index to
  `property_relations`; replace `guard_case_update` with the command-aware version.
- Expected new tables/columns: `identity_decisions` (30 resolution/candidate/property/
  reference/evidence, decision/reason/version, immutable candidate/source/coverage/
  support snapshots, creation flags, actor/request/idempotency/time columns) and
  `case_property_links` (13 case/property/resolution/confirmation/actor/version/
  supersession/request/idempotency/time columns).
- Expected: 46 named atomicity/version/snapshot/provenance/human-decision/scope/
  foreign/unique/check constraints; 10 explicit indexes; six functions
  (`guard_identity_decision`, `guard_slice6_append_only`,
  `guard_confirmed_property_relation`, `guard_case_property_link`,
  `guard_case_property_link_commit`, and replaced `guard_case_update`); six guard,
  append-only, confirmation, and deferred-commit triggers; ENABLE and FORCE RLS on the
  two new tables; five policies including owner/admin decision/link writes and the
  human-confirmed relation path; `PUBLIC` revokes, bounded grants, and two comments.
  No seed row, automatic confirmation, or automatic case attachment is encoded.
- Live: both VNext schemas and all altered targets are absent.

### 017 — legacy SavedCase import

- Expected private table `legacy_case_imports` with 16 bounded workspace/case/actor,
  hashed legacy client ID, format/version/copy mode, client/import time, accepted/
  dropped/warning class, idempotency, and request columns; 15 named scope/uniqueness/
  enum/array/check constraints plus primary key; index
  `idx_vnext_legacy_case_imports_actor`; function `guard_legacy_case_import`; guard and
  append-only triggers; ENABLE and FORCE RLS; actor select/insert policies; `PUBLIC`
  revoke, bounded `vnext_api` SELECT/INSERT grant, and one copy-only/raw-data-exclusion
  comment. No seed row, PropertyEntity, resolution, confirmation, or case link.
- Live: `vnext_private` and all dependencies are absent.

## Runner pending set and actual control flow

The runner selects the 13 registry entries whose policy is `production_runner` and
checks the custom ledger by filename stem. Since only 007 and 010 of those 13 have
rows, the exact ordered set difference is:

1. `004_add_pilot_evidence` — `APPLIED_BUT_UNLEDGERED`
2. `005_add_pilot_security_indexes` — `APPLIED_BUT_UNLEDGERED`
3. `006_add_tax_analysis_history` — `APPLIED_BUT_UNLEDGERED`
4. `008_add_official_market_pipeline` — `NOT_APPLIED`
5. `009_separate_official_market_region_coverage` — `NOT_APPLIED`
6. `012_security_rls_deny_by_default` — `APPLIED_BUT_UNLEDGERED`
7. `013_vnext_workspace_case_foundation` — `NOT_APPLIED`
8. `014_vnext_property_graph_evidence_foundation` — `NOT_APPLIED`
9. `015_vnext_identity_resolution_candidates` — `NOT_APPLIED`
10. `016_vnext_identity_confirmation_case_links` — `NOT_APPLIED`
11. `017_vnext_legacy_saved_case_import` — `NOT_APPLIED`

The runner does not precompute that set. On a live non-dry run today it would, inside
one transaction, encounter unledgered 004–006 first and execute their guarded
statements, then reach the ledgered 007 row and reject its historical CRLF checksum as
`migration_checksum_drift`. The transaction would roll back, and it would not reach
008 onward. This is correct fail-closed behavior. It is not safe or useful to invoke
the runner until the separate ledger reconciliation is authorized and complete.

## Checksum analysis

| Ledger migration | Stored checksum result | Evidence |
| --- | --- | --- |
| 001 | `EXPECTED_HISTORICAL_BASELINE` | stored checksum exactly equals current raw CRLF file bytes; registry equals canonical LF bytes |
| 002 direct indexes | `EXPECTED_HISTORICAL_BASELINE` | same exact CRLF-versus-canonical-LF relationship |
| 002 valuation expansion | `EXPECTED_HISTORICAL_BASELINE` | same exact CRLF-versus-canonical-LF relationship |
| 003 | `EXPECTED_HISTORICAL_BASELINE` | same exact CRLF-versus-canonical-LF relationship |
| 007 | `EXPECTED_HISTORICAL_BASELINE` | same exact CRLF-versus-canonical-LF relationship; this is the production runner's current fail-closed blocker |
| 010 | `MATCH` | stored checksum equals the registry's canonical LF checksum |

No ledger row has an `UNEXPLAINED_MISMATCH`. The checksum relationship is reproducible
from the current immutable files; it is not an inference from object names.

## Security baseline

- PostgreSQL server version: 17.6; inspected database/current role: `postgres` /
  `postgres` (connection details were not logged).
- Public base tables: 22; RLS enabled: 22; FORCE RLS: 0; policies: 0.
- Public relations checked, including three views: 25. `anon` and `authenticated` have
  effective privileges on zero.
- Public sequences checked: 3; `anon` and `authenticated` have effective privileges
  on zero.
- Public routines checked: 4; `anon` and `authenticated` have effective EXECUTE on
  zero. All four are security-invoker with `search_path=pg_catalog, public`.
- Actual public relation/function ACLs have zero `PUBLIC` entries. Current-owner public
  default ACLs have zero entries prohibited by 012.
- The direct public-schema ACL has no `anon` or `authenticated` entry; inherited
  `PUBLIC=USAGE` remains as described under 012.
- `vnext_core`, `vnext_private`, and role `vnext_api` are absent.

## HISTORY-001

A bounded data query verified exactly one row where
`public.tax_analysis_history.id = 1` and `case_id = 'HISTORY-001'`.

**HISTORY-001: PRESENT.** No other row content was selected, and the row was not
modified.

## Deterministic reconciliation plan — not authorized

The future operation must be designed as one reviewed, auditable, transactional
reconciliation—not ad-hoc console edits. No executable mutation SQL is provided here.

1. Reassert immutable preconditions immediately before the window: `origin/main`, all
   18 registry hashes, the exact six custom-ledger rows/fields, the four corroborating
   Supabase history fingerprints, catalog fingerprints for 001–012, security counts,
   and `HISTORY-001`.
2. In a separately reviewed reconciliation transaction, normalize only the five
   reproducibly historical CRLF checksum values (001, both 002s, 003, 007) to their
   canonical registry checksums. Preserve migration IDs, schema versions, original
   `applied_at`, and original release metadata unless the approved audit design adds
   separate reconciliation metadata outside those historical fields.
3. In the same deterministic mechanism, baseline canonical custom-ledger rows for
   004, 005, 006, and 012 only after exact catalog/history preconditions match. Record
   a distinct reviewed reconciliation release identifier. Do not execute their SQL as
   a provenance substitute.
4. Commit only if all postconditions hold: ten expected custom-ledger rows, canonical
   checksums, unchanged business-row counts/content, unchanged security posture, and
   `HISTORY-001` still present. Otherwise roll back.
5. After a fresh backup/PITR checkpoint and separate rollout authorization, the normal
   runner is then eligible to apply only the seven genuinely absent production
   migrations in order: 008, 009, 013, 014, 015, 016, 017. Migration 013 creates the
   restricted `vnext_api` role without a credential; credential provisioning and
   runtime verification remain separate controlled operations.
6. Do not run 011 on this database. It remains owned by the separate compact-green
   operator path.

There are no partial or ambiguous migrations requiring manual schema remediation.
The only future ledger operations are the controlled checksum normalization and four
exact-equivalence baselines above; the only future actual migrations are the seven
genuinely absent production-runner entries.

## Scope verification

This gate performed no live write, custom-ledger mutation, migration application,
schema or role creation, Auth change, user/workspace creation, feature enablement, or
deployment. It created no Migration 018 and changed no source, migration, SQL, Hero,
or Stage 2 file. The separate worktree at `C:\Projects\proptech-ai-copilot` was not
edited.

**Production rollout: BLOCKED.**
