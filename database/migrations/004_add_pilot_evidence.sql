-- Pilot Evidence Operations v1
-- Additive only. The application schema in services/pilot_evidence.py is the
-- SQLite-compatible reference; apply equivalent statements to Postgres using
-- uuid/text IDs and JSONB where appropriate. Rollback: drop these tables in
-- reverse dependency order only after a reviewed retention decision.

create table if not exists pilot_campaigns (
  campaign_id text primary key,
  access_code_hash text not null,
  status text not null default 'active',
  starts_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  is_test_fixture boolean not null default false
);

create table if not exists pilot_sessions (
  session_id text primary key,
  session_token_hash text not null,
  campaign_id text not null references pilot_campaigns(campaign_id),
  participant_hash text not null,
  workflow_id text not null,
  locale text not null,
  device_class text not null,
  viewport_class text not null,
  completion_status text not null default 'active',
  current_step text,
  consent_version text,
  publication_permission boolean not null default false,
  started_at timestamptz not null,
  completed_at timestamptz,
  abandoned_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  is_test_fixture boolean not null default false
);

create table if not exists pilot_consents (
  session_id text primary key references pilot_sessions(session_id) on delete cascade,
  participation boolean not null,
  interaction_metrics boolean not null,
  written_feedback boolean not null,
  follow_up_contact boolean not null,
  publication boolean not null,
  audio_collected boolean not null default false,
  transcript_stored boolean not null default false,
  version text not null,
  created_at timestamptz not null default now()
);

create table if not exists pilot_profiles (
  session_id text primary key references pilot_sessions(session_id) on delete cascade,
  profile_json jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists pilot_contacts (
  session_id text primary key references pilot_sessions(session_id) on delete cascade,
  contact_ciphertext text not null,
  created_at timestamptz not null default now()
);

create table if not exists pilot_events (
  event_id text primary key,
  session_id text not null references pilot_sessions(session_id) on delete cascade,
  event_type text not null,
  metadata_json jsonb not null,
  occurred_at timestamptz not null default now(),
  idempotency_key text not null,
  unique (session_id, idempotency_key)
);

create table if not exists pilot_feedback (
  session_id text primary key references pilot_sessions(session_id) on delete cascade,
  task_completion text not null,
  result_clarity smallint not null check (result_clarity between 1 and 5),
  source_clarity smallint not null check (source_clarity between 1 and 5),
  limitation_clarity smallint not null check (limitation_clarity between 1 and 5),
  entry_ease smallint not null check (entry_ease between 1 and 5),
  meeting_usefulness smallint not null check (meeting_usefulness between 1 and 5),
  trust_level smallint not null check (trust_level between 1 and 5),
  reuse_likelihood smallint not null check (reuse_likelihood between 1 and 5),
  most_confusing_step text not null default '',
  missing_capability text not null default '',
  current_alternative text not null default '',
  decision_maker_role text not null default '',
  privacy_concern text not null default '',
  required_integration text not null default '',
  free_text text not null default '',
  willingness_to_pay_json jsonb not null default '{}'::jsonb,
  provenance text not null default 'user_submitted',
  verification_status text not null default 'unverified',
  publication_status text not null default 'private',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists professional_reviews (
  review_id text primary key,
  reviewer_role text not null,
  reviewer_display_name text,
  qualification text not null,
  qualification_verification_status text not null default 'unverified',
  consent_to_display_name boolean not null default false,
  reviewed_capability text not null,
  reviewed_rule_version text not null,
  reviewed_product_version text not null,
  review_scope text not null,
  outcome text not null,
  notes text not null default '',
  required_changes text not null default '',
  reviewed_at timestamptz not null default now(),
  publication_status text not null default 'private',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_pilot_sessions_campaign on pilot_sessions(campaign_id);
create index if not exists idx_pilot_events_session on pilot_events(session_id);
create index if not exists idx_pilot_feedback_publication on pilot_feedback(publication_status, verification_status);
create index if not exists idx_pilot_profiles_session on pilot_profiles(session_id);

-- RLS activation is an operator step after the authenticated Postgres role is
-- selected. Anonymous clients must never receive a list/select policy.
-- Public aggregate reads should use a security-definer view that filters
-- is_test_fixture=true and publication/verification states.
