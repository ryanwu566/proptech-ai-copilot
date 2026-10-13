-- Wave 1B: private telemetry plus authoritative shared quota admission.
CREATE SCHEMA api_usage;
REVOKE ALL ON SCHEMA api_usage FROM PUBLIC;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'proptech_usage_writer') THEN
        CREATE ROLE proptech_usage_writer NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'proptech_usage_reader') THEN
        CREATE ROLE proptech_usage_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN ('proptech_usage_writer','proptech_usage_reader')
               AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls OR rolcanlogin)) THEN
        RAISE EXCEPTION 'Usage role is not a bounded server grant role';
    END IF;
END $$;

CREATE TABLE api_usage.hourly (
    bucket_start timestamptz NOT NULL CHECK (EXTRACT(MINUTE FROM bucket_start AT TIME ZONE 'UTC') = 0 AND EXTRACT(SECOND FROM bucket_start AT TIME ZONE 'UTC') = 0),
    principal_class text NOT NULL CHECK (principal_class IN ('authenticated','anonymous','system')),
    principal_id text NOT NULL DEFAULT '',
    capability text NOT NULL CHECK (capability IN ('geocoding','address_resolution','places','places_request','routes','satellite','ardswc','liquefaction','nlsc','tgos','location','terrain','valuation','trend','finder','market','market_ops','parcel','metadata','identity')),
    provider text NOT NULL CHECK (provider IN ('google_geocoding','google_places','google_routes','earth_engine','ardswc','geologycloud','nlsc','tgos','nlsc_cadastral','tdx_mrt','none','unknown')),
    route_class text NOT NULL CHECK (route_class = 'internal' OR
        (split_part(route_class, ':', 1) IN ('GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS','OTHER')
         AND split_part(route_class, ':', 2) IN ('geocoding','address_resolution','places','places_request','routes','satellite','ardswc','liquefaction','nlsc','tgos','location','terrain','valuation','trend','finder','market','market_ops','parcel','metadata','identity')
         AND length(route_class) <= 40 AND route_class NOT LIKE '%:%:%')),
    status_class text NOT NULL CHECK (status_class IN ('1xx','2xx','3xx','4xx','5xx','other')),
    cache_state text NOT NULL CHECK (cache_state IN ('hit','miss','unknown','coalesced')),
    release_id text NOT NULL CHECK (release_id = 'unknown' OR release_id ~ '^[a-f0-9]{40}$'),
    observations bigint NOT NULL DEFAULT 0 CHECK (observations >= 0),
    requests bigint NOT NULL DEFAULT 0 CHECK (requests >= 0),
    admitted bigint NOT NULL DEFAULT 0 CHECK (admitted >= 0),
    rejected bigint NOT NULL DEFAULT 0 CHECK (rejected >= 0),
    responses_429 bigint NOT NULL DEFAULT 0 CHECK (responses_429 >= 0),
    responses_5xx bigint NOT NULL DEFAULT 0 CHECK (responses_5xx >= 0),
    provider_attempt_count bigint NOT NULL DEFAULT 0 CHECK (provider_attempt_count >= 0),
    provider_accounting_unknown bigint NOT NULL DEFAULT 0 CHECK (provider_accounting_unknown >= 0),
    provider_failures bigint NOT NULL DEFAULT 0 CHECK (provider_failures >= 0),
    provider_timeouts bigint NOT NULL DEFAULT 0 CHECK (provider_timeouts >= 0),
    quota_units bigint NOT NULL DEFAULT 0 CHECK (quota_units >= 0),
    cache_hits bigint NOT NULL DEFAULT 0 CHECK (cache_hits >= 0),
    cache_misses bigint NOT NULL DEFAULT 0 CHECK (cache_misses >= 0),
    cache_unknown bigint NOT NULL DEFAULT 0 CHECK (cache_unknown >= 0),
    coalesced bigint NOT NULL DEFAULT 0 CHECK (coalesced >= 0),
    latency_count bigint NOT NULL DEFAULT 0 CHECK (latency_count >= 0),
    latency_sum_ms bigint NOT NULL DEFAULT 0 CHECK (latency_sum_ms >= 0),
    latency_le_100ms bigint NOT NULL DEFAULT 0 CHECK (latency_le_100ms >= 0),
    latency_le_1000ms bigint NOT NULL DEFAULT 0 CHECK (latency_le_1000ms >= 0),
    latency_le_10000ms bigint NOT NULL DEFAULT 0 CHECK (latency_le_10000ms >= 0),
    CHECK ((principal_class = 'authenticated' AND principal_id ~ '^[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}$')
           OR (principal_class = 'anonymous' AND (principal_id = '' OR principal_id ~ '^[a-f0-9]{64}$'))
           OR (principal_class = 'system' AND principal_id = '')),
    PRIMARY KEY (bucket_start,principal_class,principal_id,capability,provider,route_class,status_class,cache_state,release_id)
);
CREATE INDEX api_usage_principal_time ON api_usage.hourly (principal_id,bucket_start DESC) WHERE principal_class = 'authenticated';

-- Retry tokens describe aggregate flushes, never individual request events.
-- Markers live two hours, longer than the one-hour in-memory replay horizon.
CREATE TABLE api_usage.flush_batches (
    batch_id uuid PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX api_usage_flush_retention ON api_usage.flush_batches (created_at);

ALTER TABLE api_usage.hourly ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage.hourly FORCE ROW LEVEL SECURITY;
ALTER TABLE api_usage.flush_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage.flush_batches FORCE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA api_usage FROM PUBLIC;
GRANT USAGE ON SCHEMA api_usage TO proptech_usage_writer,proptech_usage_reader;
GRANT SELECT,INSERT,UPDATE,DELETE ON api_usage.hourly,api_usage.flush_batches TO proptech_usage_writer;
GRANT SELECT ON api_usage.hourly TO proptech_usage_reader;
CREATE POLICY usage_writer ON api_usage.hourly TO proptech_usage_writer USING (true) WITH CHECK (true);
CREATE POLICY usage_reader ON api_usage.hourly FOR SELECT TO proptech_usage_reader USING (true);
CREATE POLICY usage_batch_writer ON api_usage.flush_batches TO proptech_usage_writer USING (true) WITH CHECK (true);
DO $$
DECLARE client_role text;
BEGIN
    FOREACH client_role IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = client_role) THEN
            EXECUTE format('REVOKE ALL ON SCHEMA api_usage FROM %I', client_role);
            EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA api_usage FROM %I', client_role);
        END IF;
    END LOOP;
END $$;

-- Request roles (including vnext_api) receive no access. The API's dedicated
-- guard login gets EXECUTE only. The definer is neither table owner nor BYPASSRLS.
DO $$
DECLARE role_name text;
BEGIN
    FOREACH role_name IN ARRAY ARRAY['proptech_usage_executor','proptech_usage_guard'] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname=role_name) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',role_name);
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=role_name AND (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolcanlogin)) THEN
            RAISE EXCEPTION 'Unsafe usage grant role';
        END IF;
    END LOOP;
END $$;
GRANT USAGE ON SCHEMA api_usage TO proptech_usage_executor, proptech_usage_guard;

CREATE TABLE api_usage.quota_policy (
    principal_class text PRIMARY KEY CHECK (principal_class IN ('authenticated','anonymous')),
    request_hour integer NOT NULL CHECK (request_hour BETWEEN 1 AND 100000),
    operation_hour integer NOT NULL CHECK (operation_hour BETWEEN 1 AND 100000),
    operation_day integer NOT NULL CHECK (operation_day BETWEEN 1 AND 1000000)
);
INSERT INTO api_usage.quota_policy VALUES ('anonymous',1200,240,1000),('authenticated',6000,600,2000);

CREATE TABLE api_usage.quota_subjects (
    subject text PRIMARY KEY CHECK (subject ~ '^user:[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}$' OR subject ~ '^anon:[a-f0-9]{64}$'),
    principal_class text NOT NULL CHECK ((principal_class='anonymous' AND subject LIKE 'anon:%') OR (principal_class='authenticated' AND subject LIKE 'user:%')),
    hour_bucket timestamptz NOT NULL,
    day_bucket timestamptz NOT NULL,
    requests integer NOT NULL DEFAULT 0 CHECK (requests BETWEEN 0 AND 100000),
    operations integer NOT NULL DEFAULT 0 CHECK (operations BETWEEN 0 AND 100000),
    daily_operations integer NOT NULL DEFAULT 0 CHECK (daily_operations BETWEEN 0 AND 1000000),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX usage_subject_retention ON api_usage.quota_subjects(updated_at);

CREATE TABLE api_usage.quota_hourly (
    bucket_start timestamptz NOT NULL,
    subject text NOT NULL CHECK (subject ~ '^user:[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}$' OR subject ~ '^anon:[a-f0-9]{64}$'),
    capability text NOT NULL CHECK (capability IN ('geocoding','places','routes','satellite','location','terrain','valuation','trend','finder','market','market_ops','parcel','metadata','ardswc','liquefaction','nlsc','tgos','identity')),
    admitted bigint NOT NULL DEFAULT 0 CHECK (admitted>=0),
    rejected bigint NOT NULL DEFAULT 0 CHECK (rejected>=0),
    reservations bigint NOT NULL DEFAULT 0 CHECK (reservations>=0),
    PRIMARY KEY(bucket_start,subject,capability)
);

CREATE TABLE api_usage.reservation_markers (
    subject text NOT NULL REFERENCES api_usage.quota_subjects(subject) ON DELETE CASCADE,
    marker uuid NOT NULL,
    capability text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('request','operation')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(subject,marker)
);
CREATE INDEX usage_marker_retention ON api_usage.reservation_markers(created_at);

ALTER TABLE api_usage.quota_policy ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage.quota_policy FORCE ROW LEVEL SECURITY;
ALTER TABLE api_usage.quota_subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage.quota_subjects FORCE ROW LEVEL SECURITY;
ALTER TABLE api_usage.quota_hourly ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage.quota_hourly FORCE ROW LEVEL SECURITY;
ALTER TABLE api_usage.reservation_markers ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage.reservation_markers FORCE ROW LEVEL SECURITY;
REVOKE ALL ON api_usage.quota_policy,api_usage.quota_subjects,api_usage.quota_hourly,api_usage.reservation_markers FROM PUBLIC;
GRANT SELECT ON api_usage.quota_policy TO proptech_usage_executor;
GRANT SELECT,INSERT,UPDATE,DELETE ON api_usage.quota_subjects,api_usage.quota_hourly,api_usage.reservation_markers TO proptech_usage_executor;
GRANT SELECT ON api_usage.quota_hourly TO proptech_usage_reader;
CREATE POLICY quota_policy_executor ON api_usage.quota_policy FOR SELECT TO proptech_usage_executor USING (true);
CREATE POLICY quota_subject_executor ON api_usage.quota_subjects TO proptech_usage_executor USING (true) WITH CHECK (true);
CREATE POLICY quota_hourly_executor ON api_usage.quota_hourly TO proptech_usage_executor USING (true) WITH CHECK (true);
CREATE POLICY quota_hourly_reader ON api_usage.quota_hourly FOR SELECT TO proptech_usage_reader USING (true);
CREATE POLICY quota_marker_executor ON api_usage.reservation_markers TO proptech_usage_executor USING (true) WITH CHECK (true);

CREATE FUNCTION api_usage.consume(p_subject text,p_class text,p_capability text,p_kind text,p_marker uuid)
RETURNS TABLE(result text,retry_after integer)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_now timestamptz := clock_timestamp();
    v_hour timestamptz := date_trunc('hour',v_now,'UTC');
    v_day timestamptz := date_trunc('day',v_now,'UTC');
    v_policy api_usage.quota_policy%ROWTYPE;
    v_subject api_usage.quota_subjects%ROWTYPE;
    v_marker api_usage.reservation_markers%ROWTYPE;
    v_allowed boolean;
BEGIN
    IF p_subject IS NULL OR p_class IS NULL OR p_capability IS NULL OR p_kind IS NULL OR p_marker IS NULL THEN
        RETURN QUERY SELECT 'invalid'::text,1; RETURN;
    END IF;
    IF NOT ((p_class='authenticated' AND p_subject ~ '^user:[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}$')
            OR (p_class='anonymous' AND p_subject ~ '^anon:[a-f0-9]{64}$'))
       OR p_kind NOT IN ('request','operation')
       OR p_capability NOT IN ('geocoding','places','routes','satellite','location','terrain','valuation','trend','finder','market','market_ops','parcel','metadata','ardswc','liquefaction','nlsc','tgos','identity') THEN
        RETURN QUERY SELECT 'invalid'::text,1; RETURN;
    END IF;
    SELECT * INTO STRICT v_policy FROM api_usage.quota_policy WHERE principal_class=p_class;
    -- All capabilities/kinds for a subject serialize before reading counters.
    -- Hash collisions cause extra serialization, never an allowance increase.
    PERFORM pg_advisory_xact_lock(hashtextextended(p_subject,831));
    IF NOT EXISTS (SELECT 1 FROM api_usage.quota_subjects WHERE subject=p_subject) THEN
        PERFORM pg_advisory_xact_lock(831,1);
        IF (SELECT count(*) FROM api_usage.quota_subjects)>=100000 THEN
            RETURN QUERY SELECT 'capacity'::text,1; RETURN;
        END IF;
        INSERT INTO api_usage.quota_subjects(subject,principal_class,hour_bucket,day_bucket)
        VALUES(p_subject,p_class,v_hour,v_day);
    END IF;
    SELECT * INTO STRICT v_subject FROM api_usage.quota_subjects WHERE subject=p_subject FOR UPDATE;
    -- Select the time after lock waits; an old hour must never reset a newer
    -- hour's counter when concurrent calls straddle the boundary.
    v_now := clock_timestamp();
    v_hour := date_trunc('hour',v_now,'UTC');
    v_day := date_trunc('day',v_now,'UTC');
    DELETE FROM api_usage.reservation_markers WHERE (subject,marker) IN (
        SELECT subject,marker FROM api_usage.reservation_markers WHERE subject=p_subject
        AND created_at<v_now-interval '10 minutes' LIMIT 256
    );
    SELECT * INTO v_marker FROM api_usage.reservation_markers WHERE subject=p_subject AND marker=p_marker;
    IF FOUND THEN
        IF v_marker.capability=p_capability AND v_marker.kind=p_kind AND v_marker.created_at>=v_now-interval '10 minutes' THEN
            RETURN QUERY SELECT 'duplicate'::text,1;
        ELSE
            RETURN QUERY SELECT 'invalid'::text,1;
        END IF;
        RETURN;
    END IF;
    IF (SELECT count(*) FROM api_usage.reservation_markers WHERE subject=p_subject)>=2048 THEN
        RETURN QUERY SELECT 'capacity'::text,1; RETURN;
    END IF;
    IF v_subject.hour_bucket<>v_hour THEN
        v_subject.requests:=0; v_subject.operations:=0;
    END IF;
    IF v_subject.day_bucket<>v_day THEN v_subject.daily_operations:=0; END IF;
    v_allowed := CASE WHEN p_kind='request' THEN v_subject.requests<v_policy.request_hour
        ELSE v_subject.operations<v_policy.operation_hour AND v_subject.daily_operations<v_policy.operation_day END;
    IF v_allowed THEN
        UPDATE api_usage.quota_subjects SET hour_bucket=v_hour,day_bucket=v_day,
            requests=v_subject.requests+CASE WHEN p_kind='request' THEN 1 ELSE 0 END,
            operations=v_subject.operations+CASE WHEN p_kind='operation' THEN 1 ELSE 0 END,
            daily_operations=v_subject.daily_operations+CASE WHEN p_kind='operation' THEN 1 ELSE 0 END,
            updated_at=v_now WHERE subject=p_subject;
        INSERT INTO api_usage.reservation_markers(subject,marker,capability,kind,created_at)
        VALUES(p_subject,p_marker,p_capability,p_kind,v_now);
    END IF;
    INSERT INTO api_usage.quota_hourly(bucket_start,subject,capability,admitted,rejected,reservations)
    VALUES(v_hour,p_subject,p_capability,
        CASE WHEN v_allowed AND p_kind='request' THEN 1 ELSE 0 END,
        CASE WHEN v_allowed THEN 0 ELSE 1 END,
        CASE WHEN v_allowed AND p_kind='operation' THEN 1 ELSE 0 END)
    ON CONFLICT(bucket_start,subject,capability) DO UPDATE SET
        admitted=api_usage.quota_hourly.admitted+EXCLUDED.admitted,
        rejected=api_usage.quota_hourly.rejected+EXCLUDED.rejected,
        reservations=api_usage.quota_hourly.reservations+EXCLUDED.reservations;
    RETURN QUERY SELECT CASE WHEN v_allowed THEN 'admitted' ELSE 'quota' END,
        least(3600,greatest(1,ceil(extract(epoch FROM v_hour+interval '1 hour'-v_now))::integer));
END $$;
ALTER FUNCTION api_usage.consume(text,text,text,text,uuid) OWNER TO proptech_usage_executor;
REVOKE ALL ON FUNCTION api_usage.consume(text,text,text,text,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION api_usage.consume(text,text,text,text,uuid) TO proptech_usage_guard;

CREATE FUNCTION api_usage.prune() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_now timestamptz := clock_timestamp();
BEGIN
    DELETE FROM api_usage.reservation_markers WHERE (subject,marker) IN (
        SELECT subject,marker FROM api_usage.reservation_markers
        WHERE created_at<v_now-interval '10 minutes' LIMIT 5000 FOR UPDATE SKIP LOCKED);
    DELETE FROM api_usage.quota_subjects WHERE subject IN (
        SELECT subject FROM api_usage.quota_subjects
        WHERE updated_at<v_now-interval '2 days'
        AND NOT EXISTS (SELECT 1 FROM api_usage.reservation_markers m WHERE m.subject=quota_subjects.subject)
        LIMIT 5000 FOR UPDATE SKIP LOCKED);
    DELETE FROM api_usage.quota_hourly WHERE (bucket_start,subject,capability) IN (
        SELECT bucket_start,subject,capability FROM api_usage.quota_hourly
        WHERE bucket_start<v_now-interval '30 days' LIMIT 5000 FOR UPDATE SKIP LOCKED);
END $$;
ALTER FUNCTION api_usage.prune() OWNER TO proptech_usage_executor;
REVOKE ALL ON FUNCTION api_usage.prune() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION api_usage.prune() TO proptech_usage_writer;
