-- Wave 1C. No auth or usage schema replacement; no consumer-role mutation grants.
CREATE SCHEMA admin_plane;
REVOKE ALL ON SCHEMA admin_plane FROM PUBLIC;
DO $$
DECLARE r text;
BEGIN
  FOREACH r IN ARRAY ARRAY['proptech_admin_executor','proptech_admin_operator'] LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname=r) THEN
      EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT',r);
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=r AND
      (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolcanlogin OR rolinherit OR rolreplication))
      OR EXISTS(SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=r)) THEN
      RAISE EXCEPTION 'Unsafe admin grant role';
    END IF;
  END LOOP;
END $$;
-- 022 is installed after 020 on the account database and after the strict
-- 021 bootstrap on the dedicated usage database. Never create shadow authority.
DO $foundation$
BEGIN
  IF to_regclass('vnext_private.consumer_accounts') IS NULL AND to_regclass('api_usage.quota_policy') IS NULL THEN
    RAISE EXCEPTION 'Admin requires an account or usage foundation';
  END IF;
  EXECUTE format('GRANT proptech_admin_executor TO %I WITH INHERIT TRUE, SET TRUE',current_user);
END $foundation$;
GRANT USAGE ON SCHEMA admin_plane TO proptech_admin_executor, proptech_admin_operator;
-- PostgreSQL 17 requires both SET membership and target schema CREATE for
-- ownership transfer by a bounded migrator. These temporary grants are removed.
GRANT CREATE ON SCHEMA admin_plane TO proptech_admin_executor;
CREATE TABLE admin_plane.instance (singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), id uuid NOT NULL DEFAULT gen_random_uuid());
INSERT INTO admin_plane.instance(singleton) VALUES(true);
REVOKE ALL ON admin_plane.instance FROM PUBLIC;
GRANT SELECT ON admin_plane.instance TO proptech_admin_operator;
CREATE TABLE admin_plane.claims (
  actor uuid NOT NULL, command_id uuid NOT NULL,
  payload jsonb NOT NULL CHECK(octet_length(payload::text)<=4096),
  accepted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(actor,command_id)
);
ALTER TABLE admin_plane.claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_plane.claims FORCE ROW LEVEL SECURITY;
GRANT SELECT,INSERT ON admin_plane.claims TO proptech_admin_executor;
CREATE POLICY admin_claims_executor ON admin_plane.claims TO proptech_admin_executor USING(true) WITH CHECK(true);

CREATE TABLE admin_plane.commands (
  actor uuid NOT NULL,
  command_id uuid NOT NULL,
  payload jsonb NOT NULL CHECK (octet_length(payload::text)<=4096),
  result jsonb NOT NULL CHECK (octet_length(result::text)<=4096),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(actor,command_id)
);
CREATE TABLE admin_plane.audit (
  event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor uuid NOT NULL,
  command_id uuid NOT NULL,
  timestamp timestamptz NOT NULL DEFAULT clock_timestamp(),
  event_type text NOT NULL CHECK(event_type IN ('account_suspended','account_restored','role_changed','policy_changed')),
  target_type text NOT NULL CHECK(target_type IN ('account','policy')),
  target text NOT NULL CHECK(length(target) BETWEEN 1 AND 64),
  reason text NOT NULL CHECK(length(btrim(reason)) BETWEEN 1 AND 500 AND reason !~ '[[:cntrl:]]'),
  before_state jsonb NOT NULL CHECK(octet_length(before_state::text)<=4096),
  after_state jsonb NOT NULL CHECK(octet_length(after_state::text)<=4096),
  UNIQUE(actor,command_id),
  FOREIGN KEY(actor,command_id) REFERENCES admin_plane.commands(actor,command_id)
);
CREATE INDEX admin_audit_page ON admin_plane.audit (timestamp DESC,event_id DESC);
ALTER TABLE admin_plane.commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_plane.commands FORCE ROW LEVEL SECURITY;
ALTER TABLE admin_plane.audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_plane.audit FORCE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA admin_plane FROM PUBLIC;
GRANT SELECT,INSERT ON admin_plane.commands,admin_plane.audit TO proptech_admin_executor;
CREATE POLICY admin_commands_executor ON admin_plane.commands TO proptech_admin_executor USING(true) WITH CHECK(true);
CREATE POLICY admin_audit_executor ON admin_plane.audit TO proptech_admin_executor USING(true) WITH CHECK(true);
-- Only the dedicated backend operator can set this verified principal GUC.
CREATE FUNCTION admin_plane.actor_uid() RETURNS uuid LANGUAGE sql STABLE SET search_path='' AS $$
  SELECT NULLIF(current_setting('request.jwt.claim.sub',true),'')::uuid
$$;
REVOKE ALL ON FUNCTION admin_plane.actor_uid() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION admin_plane.actor_uid() TO proptech_admin_executor;
CREATE FUNCTION admin_plane.is_admin() RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path='' AS $$
DECLARE answer boolean;
BEGIN
  IF to_regclass('vnext_private.consumer_accounts') IS NOT NULL THEN
    EXECUTE 'SELECT EXISTS(SELECT 1 FROM vnext_private.consumer_accounts WHERE user_id=$1 AND status=''active'' AND platform_role=''platform_admin'')'
      INTO answer USING admin_plane.actor_uid();
    RETURN answer;
  END IF;
  -- Usage-only DB: authority is the server's durable account-DB acceptance.
  -- The usage operator credential is never a consumer, writer, or guard role.
  RETURN admin_plane.actor_uid() IS NOT NULL;
END $$;
ALTER FUNCTION admin_plane.is_admin() OWNER TO proptech_admin_executor;
REVOKE ALL ON FUNCTION admin_plane.is_admin() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION admin_plane.is_admin() TO proptech_admin_operator;
GRANT SELECT ON admin_plane.audit TO proptech_admin_operator;
CREATE POLICY admin_audit_read ON admin_plane.audit FOR SELECT TO proptech_admin_operator USING((SELECT admin_plane.is_admin()));

CREATE FUNCTION admin_plane.immutable_history() RETURNS trigger
LANGUAGE plpgsql SET search_path='' AS $$
BEGIN RAISE EXCEPTION 'Admin history is append-only' USING ERRCODE='42501'; END $$;
REVOKE ALL ON FUNCTION admin_plane.immutable_history() FROM PUBLIC;
CREATE TRIGGER audit_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON admin_plane.audit
  FOR EACH STATEMENT EXECUTE FUNCTION admin_plane.immutable_history();
CREATE TRIGGER commands_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON admin_plane.commands
  FOR EACH STATEMENT EXECUTE FUNCTION admin_plane.immutable_history();

CREATE TRIGGER claims_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON admin_plane.claims
  FOR EACH STATEMENT EXECUTE FUNCTION admin_plane.immutable_history();
CREATE TRIGGER instance_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON admin_plane.instance
  FOR EACH STATEMENT EXECUTE FUNCTION admin_plane.immutable_history();

DO $accounts$
BEGIN
IF to_regclass('vnext_private.consumer_accounts') IS NOT NULL THEN
GRANT USAGE ON SCHEMA vnext_private TO proptech_admin_executor,proptech_admin_operator;
GRANT SELECT,UPDATE(status,platform_role,updated_at) ON vnext_private.consumer_accounts TO proptech_admin_executor;
CREATE POLICY admin_accounts_executor ON vnext_private.consumer_accounts TO proptech_admin_executor USING(true) WITH CHECK(true);
GRANT SELECT ON vnext_private.consumer_accounts TO proptech_admin_operator;
CREATE POLICY admin_accounts_read ON vnext_private.consumer_accounts FOR SELECT TO proptech_admin_operator USING((SELECT admin_plane.is_admin()));

CREATE FUNCTION admin_plane.mutate_account(p_target uuid,p_field text,p_value text,p_reason text,p_key uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE
  a uuid := admin_plane.actor_uid(); p jsonb; old admin_plane.commands%ROWTYPE;
  target_row vnext_private.consumer_accounts%ROWTYPE; before_value jsonb; after_value jsonb; answer jsonb; event text;
BEGIN
  IF current_setting('transaction_isolation')<>'read committed' THEN
    RAISE EXCEPTION 'Read committed required' USING ERRCODE='22023';
  END IF;
  IF p_target IS NULL OR p_key IS NULL OR p_field IS NULL OR p_value IS NULL OR p_reason IS NULL
    OR length(btrim(p_reason)) NOT BETWEEN 1 AND 500 OR length(p_reason)>500 OR p_reason ~ '[[:cntrl:]]'
    OR NOT ((p_field='status' AND p_value IN ('active','suspended')) OR (p_field='platform_role' AND p_value IN ('consumer','platform_admin'))) THEN
    RAISE EXCEPTION 'Invalid command' USING ERRCODE='22023';
  END IF;
  -- Shared across ALL account and policy mutations, including retries.
  -- VOLATILE function + READ COMMITTED ensures reads after a wait see commits.
  PERFORM pg_advisory_xact_lock(832,1);
  IF NOT admin_plane.is_admin() THEN RAISE EXCEPTION 'Denied' USING ERRCODE='42501'; END IF;
  IF a=p_target THEN RAISE EXCEPTION 'Self mutation denied' USING ERRCODE='42501'; END IF;
  IF EXISTS(SELECT 1 FROM admin_plane.claims WHERE actor=a AND command_id=p_key) THEN
    RAISE EXCEPTION 'Idempotency conflict' USING ERRCODE='PT409';
  END IF;
  p := jsonb_build_object('target',p_target,'field',p_field,'value',p_value,'reason',p_reason);
  SELECT * INTO old FROM admin_plane.commands WHERE actor=a AND command_id=p_key;
  IF FOUND THEN
    IF old.payload<>p THEN RAISE EXCEPTION 'Idempotency conflict' USING ERRCODE='PT409'; END IF;
    RETURN old.result;
  END IF;
  SELECT * INTO target_row FROM vnext_private.consumer_accounts WHERE user_id=p_target FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Not found' USING ERRCODE='P0002'; END IF;
  IF target_row.status='active' AND target_row.platform_role='platform_admin'
    AND ((p_field='status' AND p_value='suspended') OR (p_field='platform_role' AND p_value='consumer'))
    AND (SELECT count(*) FROM vnext_private.consumer_accounts WHERE status='active' AND platform_role='platform_admin')<=1 THEN
    RAISE EXCEPTION 'Final administrator protected' USING ERRCODE='42501';
  END IF;
  before_value := jsonb_build_object('status',target_row.status,'platform_role',target_row.platform_role);
  UPDATE vnext_private.consumer_accounts SET
    status=CASE WHEN p_field='status' THEN p_value ELSE status END,
    platform_role=CASE WHEN p_field='platform_role' THEN p_value ELSE platform_role END,
    updated_at=clock_timestamp() WHERE user_id=p_target;
  SELECT jsonb_build_object('status',status,'platform_role',platform_role) INTO after_value
    FROM vnext_private.consumer_accounts WHERE user_id=p_target;
  event := CASE WHEN p_field='platform_role' THEN 'role_changed' WHEN p_value='suspended' THEN 'account_suspended' ELSE 'account_restored' END;
  answer := jsonb_build_object('command_id',p_key,'target',p_target,'before',before_value,'after',after_value);
  INSERT INTO admin_plane.commands(actor,command_id,payload,result) VALUES(a,p_key,p,answer);
  INSERT INTO admin_plane.audit(actor,command_id,event_type,target_type,target,reason,before_state,after_state)
    VALUES(a,p_key,event,'account',p_target::text,p_reason,before_value,after_value);
  RETURN answer;
END $$;
ALTER FUNCTION admin_plane.mutate_account(uuid,text,text,text,uuid) OWNER TO proptech_admin_executor;
REVOKE ALL ON FUNCTION admin_plane.mutate_account(uuid,text,text,text,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION admin_plane.mutate_account(uuid,text,text,text,uuid) TO proptech_admin_operator;

-- Durable acceptance precedes remote work; it is not a success result.
CREATE FUNCTION admin_plane.accept_quota(p_owner text,p_class text,p_requests integer,p_operations integer,p_day integer,p_reason text,p_key uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE a uuid:=admin_plane.actor_uid(); p jsonb; old jsonb;
BEGIN
  IF current_setting('transaction_isolation')<>'read committed' OR p_owner IS NULL OR p_owner !~ '^[a-f0-9]{64}_[a-f0-9-]{36}$' THEN
    RAISE EXCEPTION 'Invalid coordinator' USING ERRCODE='22023';
  END IF;
  IF p_class IS NULL OR p_class NOT IN ('authenticated','anonymous') OR p_key IS NULL
    OR p_requests IS NULL OR p_requests NOT BETWEEN 1 AND 100000
    OR p_operations IS NULL OR p_operations NOT BETWEEN 1 AND 100000
    OR p_day IS NULL OR p_day NOT BETWEEN 1 AND 1000000
    OR p_reason IS NULL OR length(p_reason)>500 OR length(btrim(p_reason)) NOT BETWEEN 1 AND 500 OR p_reason ~ '[[:cntrl:]]' THEN
    RAISE EXCEPTION 'Invalid command' USING ERRCODE='22023';
  END IF;
  PERFORM pg_advisory_xact_lock(832,1);
  IF NOT admin_plane.is_admin() THEN RAISE EXCEPTION 'Denied' USING ERRCODE='42501'; END IF;
  p := jsonb_build_object('owner',p_owner,'quota',jsonb_build_object('principal_class',p_class,'request_hour',p_requests,'operation_hour',p_operations,'operation_day',p_day,'reason',p_reason));
  IF EXISTS(SELECT 1 FROM admin_plane.commands WHERE actor=a AND command_id=p_key AND payload<>p->'quota') THEN
    RAISE EXCEPTION 'Idempotency conflict' USING ERRCODE='PT409';
  END IF;
  SELECT payload INTO old FROM admin_plane.claims WHERE actor=a AND command_id=p_key;
  IF FOUND THEN
    IF old<>p THEN RAISE EXCEPTION 'Idempotency conflict' USING ERRCODE='PT409'; END IF;
    RETURN old;
  END IF;
  INSERT INTO admin_plane.claims(actor,command_id,payload) VALUES(a,p_key,p);
  RETURN p;
END $$;
ALTER FUNCTION admin_plane.accept_quota(text,text,integer,integer,integer,text,uuid) OWNER TO proptech_admin_executor;
REVOKE ALL ON FUNCTION admin_plane.accept_quota(text,text,integer,integer,integer,text,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION admin_plane.accept_quota(text,text,integer,integer,integer,text,uuid) TO proptech_admin_operator;
END IF;
END $accounts$;

DO $usage$
BEGIN
IF to_regclass('api_usage.quota_policy') IS NOT NULL THEN
GRANT USAGE ON SCHEMA api_usage TO proptech_admin_executor,proptech_admin_operator;
GRANT SELECT,UPDATE(request_hour,operation_hour,operation_day) ON api_usage.quota_policy TO proptech_admin_executor;
CREATE POLICY admin_policy_executor ON api_usage.quota_policy TO proptech_admin_executor USING(true) WITH CHECK(true);
GRANT SELECT ON api_usage.quota_policy,api_usage.hourly,api_usage.quota_hourly TO proptech_admin_operator;
CREATE POLICY admin_policy_read ON api_usage.quota_policy FOR SELECT TO proptech_admin_operator USING((SELECT admin_plane.is_admin()));
CREATE POLICY admin_usage_read ON api_usage.hourly FOR SELECT TO proptech_admin_operator USING((SELECT admin_plane.is_admin()));
CREATE POLICY admin_quota_read ON api_usage.quota_hourly FOR SELECT TO proptech_admin_operator USING((SELECT admin_plane.is_admin()));

CREATE FUNCTION admin_plane.mutate_quota(p_class text,p_requests integer,p_operations integer,p_day integer,p_reason text,p_key uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE a uuid:=admin_plane.actor_uid(); p jsonb; old admin_plane.commands%ROWTYPE; before_value jsonb; after_value jsonb; answer jsonb;
BEGIN
  IF current_setting('transaction_isolation')<>'read committed' THEN RAISE EXCEPTION 'Read committed required' USING ERRCODE='22023'; END IF;
  IF p_class IS NULL OR p_class NOT IN ('authenticated','anonymous') OR p_key IS NULL
    OR p_requests IS NULL OR p_requests NOT BETWEEN 1 AND 100000
    OR p_operations IS NULL OR p_operations NOT BETWEEN 1 AND 100000
    OR p_day IS NULL OR p_day NOT BETWEEN 1 AND 1000000
    OR p_reason IS NULL OR length(p_reason)>500 OR length(btrim(p_reason)) NOT BETWEEN 1 AND 500 OR p_reason ~ '[[:cntrl:]]' THEN
    RAISE EXCEPTION 'Invalid command' USING ERRCODE='22023';
  END IF;
  PERFORM pg_advisory_xact_lock(832,1);
  IF NOT admin_plane.is_admin() THEN RAISE EXCEPTION 'Denied' USING ERRCODE='42501'; END IF;
  p := jsonb_build_object('principal_class',p_class,'request_hour',p_requests,'operation_hour',p_operations,'operation_day',p_day,'reason',p_reason);
  IF to_regclass('vnext_private.consumer_accounts') IS NOT NULL AND NOT EXISTS(
    SELECT 1 FROM admin_plane.claims WHERE actor=a AND command_id=p_key AND payload->'quota'=p
  ) THEN RAISE EXCEPTION 'Durable acceptance required' USING ERRCODE='42501'; END IF;
  SELECT * INTO old FROM admin_plane.commands WHERE actor=a AND command_id=p_key;
  IF FOUND THEN
    IF old.payload<>p THEN RAISE EXCEPTION 'Idempotency conflict' USING ERRCODE='PT409'; END IF;
    RETURN old.result;
  END IF;
  SELECT to_jsonb(q) INTO STRICT before_value FROM api_usage.quota_policy q WHERE principal_class=p_class FOR UPDATE;
  UPDATE api_usage.quota_policy SET request_hour=p_requests,operation_hour=p_operations,operation_day=p_day WHERE principal_class=p_class;
  SELECT to_jsonb(q) INTO STRICT after_value FROM api_usage.quota_policy q WHERE principal_class=p_class;
  answer := jsonb_build_object('command_id',p_key,'target',p_class,'before',before_value,'after',after_value);
  INSERT INTO admin_plane.commands(actor,command_id,payload,result) VALUES(a,p_key,p,answer);
  INSERT INTO admin_plane.audit(actor,command_id,event_type,target_type,target,reason,before_state,after_state)
    VALUES(a,p_key,'policy_changed','policy',p_class,p_reason,before_value,after_value);
  RETURN answer;
END $$;
ALTER FUNCTION admin_plane.mutate_quota(text,integer,integer,integer,text,uuid) OWNER TO proptech_admin_executor;
REVOKE ALL ON FUNCTION admin_plane.mutate_quota(text,integer,integer,integer,text,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION admin_plane.mutate_quota(text,integer,integer,integer,text,uuid) TO proptech_admin_operator;
END IF;
END $usage$;
REVOKE CREATE ON SCHEMA admin_plane FROM proptech_admin_executor;
DO $cleanup$
BEGIN
  EXECUTE format('REVOKE proptech_admin_executor FROM %I',current_user);
END $cleanup$;
