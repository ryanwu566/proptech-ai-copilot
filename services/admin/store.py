"""Dedicated least-privilege Admin connection. No legacy credential fallback."""
from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from uuid import UUID

from services.postgres_runtime import connect
from services.vnext.errors import VNextError


class AdminStore:
    def __init__(self, database_url=None, usage_database_url=None):
        self.database_url = database_url if database_url is not None else os.getenv('ADMIN_DATABASE_URL', '').strip()
        self.usage_database_url = usage_database_url if usage_database_url is not None else os.getenv('ADMIN_USAGE_DATABASE_URL', '').strip()

    @staticmethod
    def target(url):
        from psycopg.conninfo import conninfo_to_dict
        try:
            options = conninfo_to_dict(url)
        except Exception:
            raise VNextError.provider_unavailable() from None
        # Never rely on libpq environment/service defaults for an authority target.
        if options.get('service') or os.getenv('PGSERVICE') or not options.get('host') or not options.get('dbname'):
            raise VNextError.provider_unavailable()
        # Explicit empties override environment options in libpq. Refuse this
        # ambiguous spelling instead of confusing it with an omitted option.
        if any(k in options and not options[k] for k in ('hostaddr','port')):
            raise VNextError.provider_unavailable()
        return (options['host'], options.get('hostaddr',os.getenv('PGHOSTADDR','')),
                options.get('port',os.getenv('PGPORT') or '5432'), options['dbname'])

    def usage_url(self):
        url = self.usage_database_url or self.database_url
        configured = os.getenv('API_USAGE_DATABASE_URL', '').strip()
        if configured and self.target(configured) != self.target(url):
            raise VNextError.provider_unavailable()
        return url

    @staticmethod
    def verify_role(connection):
        # Check transitive memberships too: SET ROLE must not reach an owner,
        # executor, consumer credential, or a role with elevated attributes.
        row = connection.execute("""
            SELECT current_user=session_user,
              pg_has_role(current_user,'proptech_admin_operator','USAGE'),
              EXISTS(SELECT 1 FROM pg_roles r WHERE
                (pg_has_role(current_user,r.oid,'MEMBER') OR pg_has_role(session_user,r.oid,'MEMBER')) AND
                (r.rolname NOT IN (current_user,'proptech_admin_operator')
                 OR r.rolsuper OR r.rolbypassrls OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
                 OR r.rolname IN ('proptech_admin_executor','vnext_api','anon','authenticated','service_role',
                     'proptech_usage_executor','proptech_usage_writer','proptech_usage_guard')
                 OR r.oid=(SELECT datdba FROM pg_database WHERE datname=current_database())
                 OR EXISTS(SELECT 1 FROM pg_class c WHERE c.relowner=r.oid AND c.relnamespace NOT IN
                     (SELECT oid FROM pg_namespace WHERE nspname IN ('pg_catalog','information_schema')))
                 OR EXISTS(SELECT 1 FROM pg_namespace n WHERE n.nspowner=r.oid AND left(n.nspname,3)<>'pg_'))),
              EXISTS(SELECT 1 FROM pg_roles r WHERE pg_has_role('proptech_admin_executor',r.oid,'MEMBER') AND
                (r.rolname<>'proptech_admin_executor' OR r.rolcanlogin
                 OR r.rolsuper OR r.rolbypassrls OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
                 OR r.rolname IN ('vnext_api','anon','authenticated','service_role','proptech_usage_executor','proptech_usage_writer','proptech_usage_guard')
                 OR r.oid=(SELECT datdba FROM pg_database WHERE datname=current_database())
                 OR EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                   WHERE c.relowner=r.oid AND n.nspname NOT IN ('pg_catalog','information_schema'))
                 OR EXISTS(SELECT 1 FROM pg_namespace n WHERE n.nspowner=r.oid AND left(n.nspname,3)<>'pg_')))
              OR EXISTS(SELECT 1 FROM pg_auth_members m WHERE m.member IN
                (SELECT oid FROM pg_roles WHERE pg_has_role(current_user,oid,'MEMBER')) AND m.admin_option)
              OR has_schema_privilege('proptech_admin_executor','admin_plane','CREATE')
              OR has_database_privilege(current_user,current_database(),'CREATE')
              OR has_database_privilege('proptech_admin_executor',current_database(),'CREATE')
              OR EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                WHERE n.nspname NOT IN ('pg_catalog','information_schema')
                  AND pg_has_role(current_user,p.proowner,'MEMBER'))
              OR EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                WHERE p.proowner=(SELECT oid FROM pg_roles WHERE rolname='proptech_admin_executor')
                  AND NOT (p.oid=ANY(array_remove(ARRAY[
                    to_regprocedure('admin_plane.is_admin()'),
                    to_regprocedure('admin_plane.mutate_account(uuid,text,text,text,uuid)'),
                    to_regprocedure('admin_plane.accept_quota(text,text,integer,integer,integer,text,uuid)'),
                    to_regprocedure('admin_plane.mutate_quota(text,integer,integer,integer,text,uuid)')],NULL))))
              OR EXISTS(SELECT 1 FROM pg_namespace n WHERE left(n.nspname,3)<>'pg_'
                AND n.nspname<>'information_schema' AND
                (has_schema_privilege(current_user,n.oid,'CREATE')
                 OR has_schema_privilege('proptech_admin_executor',n.oid,'CREATE')))
              OR EXISTS(SELECT 1 FROM pg_auth_members m WHERE m.member=
                (SELECT oid FROM pg_roles WHERE rolname='proptech_admin_executor') AND m.admin_option)
        """).fetchone()
        if row is None or not row[0] or not row[1] or row[2] or row[3]:
            raise RuntimeError('Unsafe Admin database principal')

    @contextmanager
    def transaction(self, principal):
        configured = os.getenv('VNEXT_DATABASE_URL', '').strip()
        if configured and self.target(configured) != self.target(self.database_url):
            raise VNextError.provider_unavailable()
        with self._connection(self.database_url, principal) as connection:
            if not connection.execute("SELECT to_regclass('vnext_private.consumer_accounts') IS NOT NULL").fetchone()[0]:
                raise VNextError.provider_unavailable()
            yield connection

    @contextmanager
    def _connection(self, url, principal):
        if not url:
            raise VNextError.provider_unavailable()
        self.target(url)
        try:
            with connect(url, connect_timeout=2) as connection:
                with connection.transaction():
                    connection.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED')
                    connection.execute("SET LOCAL statement_timeout='3000ms'")
                    connection.execute("SET LOCAL lock_timeout='1500ms'")
                    connection.execute("SET LOCAL TIME ZONE 'UTC'")
                    self.verify_role(connection)
                    connection.execute("SELECT set_config('request.jwt.claim.sub',%s,true)", (str(principal.user_id),))
                    if not connection.execute('SELECT admin_plane.is_admin()').fetchone()[0]:
                        raise VNextError.permission_denied()
                    yield connection
        except VNextError:
            raise
        except Exception as exc:
            code = getattr(exc, 'sqlstate', None)
            errors = {'42501': VNextError.permission_denied, '22023': VNextError.validation_failed,
                      'PT409': VNextError.idempotency_conflict, 'P0002': VNextError.not_found}
            raise errors.get(code, VNextError.provider_unavailable)() from None

    @contextmanager
    def usage_transaction(self, principal):
        with self.transaction(principal) as authority:
            url = self.usage_url()
            if self.target(url) == self.target(self.database_url):
                yield authority
            else:
                with self._connection(url, principal) as usage:
                    yield usage

    def owner(self, url, connection):
        fingerprint = hashlib.sha256(json.dumps(self.target(url)).encode()).hexdigest()
        return fingerprint + '_' + str(connection.execute('SELECT id FROM admin_plane.instance').fetchone()[0])

    def account(self, principal, target: UUID):
        with self.transaction(principal) as conn:
            row = conn.execute('SELECT user_id,status,platform_role,created_at FROM vnext_private.consumer_accounts WHERE user_id=%s', (target,)).fetchone()
        if row is None:
            raise VNextError.not_found()
        return dict(zip(('user_id','status','platform_role','created_at'), row))

    def policies(self, principal):
        with self.usage_transaction(principal) as conn:
            rows = conn.execute('SELECT principal_class,request_hour,operation_hour,operation_day FROM api_usage.quota_policy ORDER BY principal_class LIMIT 2').fetchall()
        return [dict(zip(('principal_class','request_hour','operation_hour','operation_day'), row)) for row in rows]

    def audit_page(self, principal, cursor):
        with ExitStack() as stack:
            stores = {'a': stack.enter_context(self.transaction(principal))}
            url = self.usage_url()
            if self.target(url) != self.target(self.database_url):
                stores['u'] = stack.enter_context(self._connection(url, principal))
            anchor = None
            if cursor:
                try:
                    scope, key = cursor.split('_', 1) if '_' in cursor else ('a', cursor)
                    key = UUID(key)
                    if scope not in stores:
                        raise ValueError()
                except ValueError:
                    raise VNextError.validation_failed() from None
                anchor = stores[scope].execute('SELECT timestamp,event_id FROM admin_plane.audit WHERE event_id=%s', (key,)).fetchone()
                if anchor is None:
                    raise VNextError.validation_failed()
                anchor = (*anchor, scope)
            merged = []
            for scope, conn in stores.items():
                predicate, args = '', ()
                if anchor:
                    predicate = 'WHERE (timestamp,event_id)<(%s,%s) OR ((timestamp,event_id)=(%s,%s) AND %s<%s)'
                    args = (*anchor[:2], *anchor[:2], scope, anchor[2])
                rows = conn.execute('SELECT timestamp,actor,event_type,target_type,target,reason,command_id,before_state,after_state,event_id FROM admin_plane.audit ' + predicate + ' ORDER BY timestamp DESC,event_id DESC LIMIT 51', args).fetchall()
                merged.extend((r, scope) for r in rows)
            merged.sort(key=lambda item: (item[0][0], item[0][9], item[1]), reverse=True)
            next_cursor = merged[49][1] + '_' + str(merged[49][0][9]) if len(merged)>50 else None
            return [r for r, _ in merged[:50]], next_cursor

    def command(self, principal, command, target=None):
        if target is not None:
            with self.transaction(principal) as conn:
                row = conn.execute('SELECT admin_plane.mutate_account(%s,%s,%s,%s,%s)',
                    (target,command.field,command.value,command.reason,command.command_id)).fetchone()
            return row[0]
        args = (command.principal_class,command.request_hour,command.operation_hour,command.operation_day,command.reason,command.command_id)
        url = self.usage_url()
        with self.usage_transaction(principal) as usage:
            owner = self.owner(url, usage)
        # Commit acknowledgement is required before dispatch. A lost response
        # yields 503; retry reauthorizes and confirms the durable exact claim.
        with self.transaction(principal) as authority:
            authority.execute('SELECT admin_plane.accept_quota(%s,%s,%s,%s,%s,%s,%s)', (owner, *args)).fetchone()
        # Authorization linearized at acceptance; already accepted work may
        # finish after revocation. A new request/retry always repeats acceptance.
        with self._connection(url, principal) as usage:
            if self.owner(url, usage) != owner:
                raise VNextError.idempotency_conflict()
            row = usage.execute('SELECT admin_plane.mutate_quota(%s,%s,%s,%s,%s,%s)', args).fetchone()
        return row[0]


def get_admin_store():
    return AdminStore()
