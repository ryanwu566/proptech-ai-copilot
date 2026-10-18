"""Bounded Admin read projections over Wave 1A/1B and immutable Wave 1C audit."""
from datetime import datetime, timezone
from uuid import UUID

from services.admin.contracts import AdminSnapshot
from services.vnext.errors import VNextError


class DurableAdminSummarySource:
    def __init__(self, principal, store, local):
        self.principal, self.store, self.local = principal, store, local

    def read(self, section, cursor=None):
        if section in {'providers', 'limits', 'operations'}:
            return self.local.read(section, cursor)
        base = dict(section=section, as_of=datetime.now(timezone.utc), state='available', source='wave_1a')
        if section == 'audit':
            rows, next_cursor = self.store.audit_page(self.principal, cursor)
            base.update(source='wave_1c', state='available' if rows else 'empty')
            return AdminSnapshot(**base, audit=[dict(zip(('timestamp','actor','event_type','target_type','target','reason','command_id','before_state','after_state'), r[:9]), outcome='success', reason_code='authorized') for r in rows], next_cursor=next_cursor)
        if section == 'overview':
            with self.store.transaction(self.principal) as conn:
                count = conn.execute('SELECT count(*) FROM vnext_private.consumer_accounts').fetchone()[0]
            base.update(state='partial', reason='durable_aggregates')
            metrics = [dict(key='accounts',state='known',value=count,source='wave_1a',window='current_snapshot')]
            metrics += [dict(key=k,state='unknown',source='wave_1b',window='last_24h') for k in ('requests','provider_attempts','http_429','http_5xx')]
            return AdminSnapshot(**base, metrics=metrics, operations=self.local.read('operations').operations)
        transaction = self.store.transaction if section == 'users' else self.store.usage_transaction
        with transaction(self.principal) as conn:
            if section == 'users':
                try:
                    after = UUID(cursor) if cursor else UUID(int=0)
                except ValueError:
                    raise VNextError.validation_failed() from None
                rows = conn.execute('SELECT user_id,status,platform_role,created_at FROM vnext_private.consumer_accounts WHERE user_id>%s ORDER BY user_id LIMIT 51', (after,)).fetchall()
                base.update(state='available' if rows else 'empty')
                return AdminSnapshot(**base, users=[dict(zip(('user_id','status','platform_role','created_at'), r)) for r in rows[:50]], next_cursor=str(rows[49][0]) if len(rows)>50 else None)
            # Fixed 24 hourly buckets, a closed capability domain, SQL timeouts,
            # and a hard row limit bound input, execution, and output.
            rows = conn.execute("""
                WITH telemetry AS (
                  SELECT capability,sum(requests)::bigint requests,
                    CASE WHEN sum(provider_accounting_unknown)>0 THEN NULL ELSE sum(provider_attempt_count)::bigint END attempts,
                    sum(responses_429)::bigint r429,sum(responses_5xx)::bigint r5xx,sum(cache_hits)::bigint hits,
                    sum(latency_sum_ms)::float8 / NULLIF(sum(latency_count),0) latency
                  FROM api_usage.hourly WHERE bucket_start>=date_trunc('hour',CURRENT_TIMESTAMP)-interval '23 hours'
                    AND bucket_start<=CURRENT_TIMESTAMP GROUP BY capability),
                quota AS (
                  SELECT capability,sum(admitted)::bigint admitted,sum(rejected)::bigint rejected,sum(reservations)::bigint consumed
                  FROM api_usage.quota_hourly WHERE bucket_start>=date_trunc('hour',CURRENT_TIMESTAMP)-interval '23 hours'
                    AND bucket_start<=CURRENT_TIMESTAMP GROUP BY capability)
                SELECT coalesce(t.capability,q.capability),requests,attempts,r429,r5xx,hits,latency,admitted,rejected,consumed
                FROM telemetry t FULL JOIN quota q USING(capability) ORDER BY 1 LIMIT 50
            """).fetchall()
            usage = [dict(zip(('capability','requests','provider_attempts','http_429','http_5xx','cache_hit','latency_ms','admitted','rejected','quota_consumed'), r)) for r in rows]
            base.update(source='wave_1b', state='partial', window='last_24h', reason='durable_aggregates')
            return AdminSnapshot(**base, usage=usage)
