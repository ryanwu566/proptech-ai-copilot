-- Independent operator-only Stage 4A migration. Requires freshly provisioned
-- professor_user_runtime role. No legacy migrations, auth.users or serving data.
CREATE SCHEMA professor_user;
REVOKE ALL ON SCHEMA professor_user FROM PUBLIC;
GRANT USAGE ON SCHEMA professor_user TO professor_user_runtime;
CREATE TABLE professor_user.configuration (
 singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
 issuer text NOT NULL UNIQUE CHECK (issuer ~ '^https://[a-z0-9-]+\.supabase\.co/auth/v1$'),
 migration_version integer NOT NULL DEFAULT 1 CHECK (migration_version=1),
 authority_reviewed boolean NOT NULL DEFAULT false
);
CREATE FUNCTION professor_user.subject() RETURNS uuid LANGUAGE sql STABLE
 SET search_path='' AS $$ SELECT nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
REVOKE ALL ON FUNCTION professor_user.subject() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION professor_user.subject() TO professor_user_runtime;
CREATE TABLE professor_user.users (
 id uuid PRIMARY KEY,
 issuer text NOT NULL REFERENCES professor_user.configuration(issuer) ON DELETE RESTRICT,
 status text NOT NULL DEFAULT 'active' CHECK(status IN ('active','suspended')),
 platform_role text NOT NULL DEFAULT 'consumer' CHECK(platform_role IN ('consumer','platform_admin')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE FUNCTION professor_user.active() RETURNS boolean LANGUAGE sql STABLE
 SET search_path='' AS $$ SELECT EXISTS(SELECT 1 FROM professor_user.users
 WHERE id=professor_user.subject() AND status='active') $$;
REVOKE ALL ON FUNCTION professor_user.active() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION professor_user.active() TO professor_user_runtime;
CREATE TABLE professor_user.profiles (
 user_id uuid PRIMARY KEY REFERENCES professor_user.users(id) ON DELETE RESTRICT,
 revision bigint NOT NULL DEFAULT 1 CHECK(revision>0),
 display_name text NOT NULL DEFAULT '' CHECK(length(display_name)<=80),
 locale text NOT NULL DEFAULT 'zh-TW' CHECK(locale IN ('zh-TW','en','ja','ko')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE professor_user.preferences (
 user_id uuid PRIMARY KEY REFERENCES professor_user.users(id) ON DELETE RESTRICT,
 revision bigint NOT NULL DEFAULT 1 CHECK(revision>0),
 data jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(data)='object' AND octet_length(data::text)<=32768),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE professor_user.revoked_sessions (
 user_id uuid NOT NULL REFERENCES professor_user.users(id) ON DELETE RESTRICT,
 session_id uuid NOT NULL, revoked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(user_id,session_id)
);
CREATE TABLE professor_user.saved_cases (
 id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES professor_user.users(id) ON DELETE RESTRICT,
 import_key text NOT NULL CHECK(length(import_key) BETWEEN 1 AND 160),
 import_digest text NOT NULL CHECK(import_digest ~ '^[a-f0-9]{64}$'),
 snapshot jsonb NOT NULL CHECK(jsonb_typeof(snapshot)='object'),
 user_authored jsonb NOT NULL CHECK(jsonb_typeof(user_authored)='object'),
 title text NOT NULL CHECK(length(title) BETWEEN 1 AND 500),
 notes text NOT NULL DEFAULT '' CHECK(length(notes)<=8000),
 monitoring jsonb NOT NULL DEFAULT '{"cadence":"off","refresh_policy":"manual_only","execution_status":"not_configured","delivery_status":"not_configured"}',
 revision bigint NOT NULL CHECK(revision>0),
 created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL,
 deleted_at timestamptz,
 UNIQUE(owner_id,import_key), UNIQUE(id,owner_id),
 CHECK(octet_length(snapshot::text)+octet_length(user_authored::text)<=524288)
);
CREATE INDEX saved_cases_owner_updated ON professor_user.saved_cases(owner_id,updated_at DESC,id) WHERE deleted_at IS NULL;
CREATE TABLE professor_user.case_activity (
 case_id uuid NOT NULL, owner_id uuid NOT NULL, revision bigint NOT NULL CHECK(revision>0),
 actor_id uuid NOT NULL CHECK(actor_id=owner_id), kind text NOT NULL
 CHECK(kind IN ('case_imported','metadata_updated','monitoring_updated')),
 occurred_at timestamptz NOT NULL,
 PRIMARY KEY(case_id,revision),
 FOREIGN KEY(case_id,owner_id) REFERENCES professor_user.saved_cases(id,owner_id) ON DELETE RESTRICT
);
CREATE TABLE professor_user.case_commands (
 actor_id uuid NOT NULL, method text NOT NULL, route text NOT NULL,
 key_hash text NOT NULL CHECK(key_hash ~ '^[a-f0-9]{64}$'),
 request_fingerprint text NOT NULL CHECK(request_fingerprint ~ '^[a-f0-9]{64}$'),
 case_id uuid NOT NULL, revision bigint NOT NULL, created_at timestamptz NOT NULL,
 expires_at timestamptz NOT NULL CHECK(expires_at>created_at),
 PRIMARY KEY(actor_id,method,route,key_hash),
 FOREIGN KEY(case_id,actor_id) REFERENCES professor_user.saved_cases(id,owner_id) ON DELETE RESTRICT
);
CREATE INDEX case_commands_expiry ON professor_user.case_commands(actor_id,expires_at);
CREATE TABLE professor_user.reports (
 id uuid PRIMARY KEY, owner_id uuid NOT NULL,
 case_id uuid NOT NULL, title text NOT NULL CHECK(length(title) BETWEEN 1 AND 200),
 payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object' AND octet_length(payload::text)<=262144),
 provenance text NOT NULL DEFAULT 'user_supplied_unverified' CHECK(provenance='user_supplied_unverified'),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(case_id,owner_id) REFERENCES professor_user.saved_cases(id,owner_id) ON DELETE RESTRICT
);
CREATE INDEX reports_owner_created ON professor_user.reports(owner_id,created_at DESC,id);

-- SECURITY INVOKER throughout; no privilege-escalating functions or public grants.
GRANT SELECT ON professor_user.configuration, professor_user.users TO professor_user_runtime;
GRANT INSERT(id,issuer) ON professor_user.users TO professor_user_runtime;
ALTER TABLE professor_user.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE professor_user.users FORCE ROW LEVEL SECURITY;
CREATE POLICY own_user_read ON professor_user.users FOR SELECT TO professor_user_runtime USING(id=professor_user.subject());
CREATE POLICY own_user_register ON professor_user.users FOR INSERT TO professor_user_runtime
 WITH CHECK(id=professor_user.subject() AND status='active' AND platform_role='consumer');

DO $$ DECLARE t text; col text; BEGIN
 FOREACH t IN ARRAY ARRAY['profiles','preferences','revoked_sessions','saved_cases','case_activity','case_commands','reports'] LOOP
  col := CASE WHEN t IN ('profiles','preferences','revoked_sessions') THEN 'user_id'
              WHEN t='case_commands' THEN 'actor_id' ELSE 'owner_id' END;
  EXECUTE format('ALTER TABLE professor_user.%I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE professor_user.%I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('REVOKE ALL ON professor_user.%I FROM PUBLIC',t);
  EXECUTE format('CREATE POLICY owner_active ON professor_user.%I TO professor_user_runtime USING (%I=professor_user.subject() AND professor_user.active()) WITH CHECK (%I=professor_user.subject() AND professor_user.active())',t,col,col);
 END LOOP;
END $$;
CREATE POLICY own_revocation_read ON professor_user.revoked_sessions FOR SELECT TO professor_user_runtime USING(user_id=professor_user.subject());
REVOKE ALL ON professor_user.configuration,professor_user.users FROM PUBLIC;
GRANT SELECT,INSERT ON professor_user.profiles,professor_user.preferences,professor_user.saved_cases,professor_user.case_activity,professor_user.case_commands,professor_user.reports,professor_user.revoked_sessions TO professor_user_runtime;
GRANT UPDATE(display_name,locale,revision,updated_at) ON professor_user.profiles TO professor_user_runtime;
GRANT UPDATE(data,revision,updated_at) ON professor_user.preferences TO professor_user_runtime;
GRANT UPDATE(title,notes,monitoring,revision,updated_at,deleted_at) ON professor_user.saved_cases TO professor_user_runtime;
GRANT DELETE ON professor_user.reports,professor_user.case_commands TO professor_user_runtime;
CREATE POLICY expired_receipt_only ON professor_user.case_commands AS RESTRICTIVE FOR DELETE TO professor_user_runtime USING(expires_at<=clock_timestamp());
CREATE POLICY live_report_case ON professor_user.reports AS RESTRICTIVE TO professor_user_runtime
 USING(EXISTS(SELECT 1 FROM professor_user.saved_cases c WHERE c.id=case_id AND c.owner_id=professor_user.subject() AND c.deleted_at IS NULL))
 WITH CHECK(EXISTS(SELECT 1 FROM professor_user.saved_cases c WHERE c.id=case_id AND c.owner_id=professor_user.subject() AND c.deleted_at IS NULL));
CREATE FUNCTION professor_user.case_tombstone() RETURNS trigger LANGUAGE plpgsql SET search_path='' AS $$
BEGIN
 IF OLD.deleted_at IS NOT NULL THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='case_deleted'; END IF;
 IF NEW.revision<>OLD.revision+1 THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='case_revision_invalid'; END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION professor_user.case_tombstone() FROM PUBLIC;
CREATE TRIGGER saved_case_tombstone BEFORE UPDATE ON professor_user.saved_cases FOR EACH ROW EXECUTE FUNCTION professor_user.case_tombstone();
COMMENT ON SCHEMA professor_user IS 'Private Professor application data; Supabase remains identity/password provider. Never expose via Data API.';
