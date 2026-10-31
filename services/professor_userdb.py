"""Private Professor user persistence; explicit opt-in, no password/token store.

No provider calls, fallback credentials or in-memory production persistence.
Supabase issuer and subject remain canonical. Legacy workspace data is separate.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
import json
import os
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from services.vnext.accounts import Account
from services.vnext.db_principal import DatabasePrincipalContext
from services.vnext.durable_cases import (
    Activity, CaseRecord, CaseService, CommandReceipt, MAX_COMMAND_RECEIPTS,
    MonitoringPreferences,
)
from services.vnext.errors import ErrorCode, VNextError


ROLE = 'professor_user_runtime'
DATABASE_ENV = 'PROFESSOR_USER_DATABASE_URL'


def enabled():
    raw = os.environ.get('PROFESSOR_USERDB_ENABLED', 'false')
    if raw not in {'true', 'false'}:
        raise VNextError(ErrorCode.ACCOUNT_UNAVAILABLE)
    return raw == 'true'


def validate_url(value):
    """Only dedicated local direct-login identity; TLS options installed in code."""
    try:
        p = urlsplit(value)
        if (p.scheme not in {'postgres','postgresql'} or p.username != ROLE
            or p.hostname != 'postgres_app' or p.path != '/proptech_app'
            or p.port not in (None,5432) or not p.password or p.query or p.fragment):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('user_database_url_invalid') from None
    return value


@lru_cache(maxsize=1)
def get_repository():
    if not enabled():
        raise VNextError(ErrorCode.MAINTENANCE, details={'reason_code':'persistence_pending'})
    try:
        from psycopg_pool import ConnectionPool
        url = validate_url(os.environ.get(DATABASE_ENV, ''))
        pool = ConnectionPool(conninfo=url, min_size=0, max_size=3, timeout=5,
            kwargs={'prepare_threshold':None, 'connect_timeout':3,
                    'sslmode':'verify-full','sslrootcert':'/run/selfhost-ca/ca.crt',
                    'options':'-c statement_timeout=5000 -c lock_timeout=2000'})
        return UserRepository(DatabasePrincipalContext(pool, expected_role=ROLE))
    except Exception:
        raise VNextError(ErrorCode.ACCOUNT_UNAVAILABLE) from None


def close_pool():
    if get_repository.cache_info().currsize:
        get_repository().context.close()
        get_repository.cache_clear()


class UserRepository:
    def __init__(self, context):
        self.context = context

    @contextmanager
    def transaction(self, principal):
        try:
            with self.context.transaction(principal) as connection:
                # Serialize admission, revocation and writes across workers/devices.
                connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',
                                   ('professor-user:'+str(principal.user_id),))
                if principal.session_id is not None:
                    if (principal.token_expires_at is None
                        or principal.token_expires_at <= datetime.now(timezone.utc)
                        or connection.execute('SELECT 1 FROM professor_user.revoked_sessions WHERE user_id=%s AND session_id=%s',
                            (principal.user_id,principal.session_id)).fetchone()):
                        raise VNextError.authentication_required()
                yield connection
        except VNextError:
            raise
        except Exception:
            raise VNextError(ErrorCode.MAINTENANCE) from None

    @staticmethod
    def _configuration(c, issuer):
        row = c.execute('SELECT issuer,migration_version,authority_reviewed FROM professor_user.configuration WHERE singleton').fetchone()
        if row != (issuer,1,True):
            raise VNextError(ErrorCode.ACCOUNT_UNAVAILABLE)

    def admit(self, p):
        if (p.session_id is None or not isinstance(p.session_id, UUID)
            or p.token_issued_at is None or p.token_expires_at is None
            or p.token_expires_at <= datetime.now(timezone.utc)):
            raise VNextError.authentication_required()
        with self.transaction(p) as c:
            self._configuration(c,p.issuer)
            c.execute('INSERT INTO professor_user.users(id,issuer) VALUES (%s,%s) ON CONFLICT DO NOTHING', (p.user_id,p.issuer))
            row = c.execute('SELECT issuer FROM professor_user.users WHERE id=%s',(p.user_id,)).fetchone()
            if row != (p.issuer,):
                raise VNextError.authentication_required()
            if c.execute('SELECT 1 FROM professor_user.revoked_sessions WHERE user_id=%s AND session_id=%s',(p.user_id,p.session_id)).fetchone():
                raise VNextError.authentication_required()

    def get_account(self, *, principal):
        with self.transaction(principal) as c:
            self._configuration(c,principal.issuer)
            row = c.execute('SELECT id,status,platform_role,created_at,updated_at FROM professor_user.users WHERE id=%s',(principal.user_id,)).fetchone()
            return Account(*row) if row else None

    @staticmethod
    def _active(c,p):
        row = c.execute('SELECT status FROM professor_user.users WHERE id=%s',(p.user_id,)).fetchone()
        if row is None:
            raise VNextError(ErrorCode.ACCOUNT_UNAVAILABLE)
        if row[0]!='active':
            raise VNextError(ErrorCode.ACCOUNT_SUSPENDED)

    def logout(self,p):
        with self.transaction(p) as c:
            self._active(c,p)
            c.execute('INSERT INTO professor_user.revoked_sessions(user_id,session_id) VALUES (%s,%s) ON CONFLICT DO NOTHING',(p.user_id,p.session_id))

    def _document(self,p,kind,expected=None,changes=None):
        # All SQL identifiers are fixed internal alternatives, never client text.
        table,columns = ('profiles','user_id,revision,display_name,locale,created_at,updated_at') if kind=='profile' else ('preferences','user_id,revision,data,created_at,updated_at')
        with self.transaction(p) as c:
            self._active(c,p)
            c.execute(f'INSERT INTO professor_user.{table}(user_id) VALUES (%s) ON CONFLICT DO NOTHING',(p.user_id,))
            if expected is not None:
                if kind=='profile':
                    fields = [k for k in ('display_name','locale') if k in changes]
                    assignments = ','.join(k+'=%s' for k in fields)
                    values = [changes[k] for k in fields]
                else:
                    assignments, values = 'data=%s',[Jsonb(changes)]
                row = c.execute(f'UPDATE professor_user.{table} SET {assignments},revision=revision+1,updated_at=clock_timestamp() WHERE user_id=%s AND revision=%s RETURNING {columns}',(*values,p.user_id,expected)).fetchone()
                if row is None: raise VNextError.version_conflict()
            else:
                row = c.execute(f'SELECT {columns} FROM professor_user.{table} WHERE user_id=%s',(p.user_id,)).fetchone()
            if row is None: raise VNextError(ErrorCode.MAINTENANCE)
            return dict(zip(columns.split(','),row))

    def profile(self,p): return self._document(p,'profile')
    def preferences(self,p): return self._document(p,'preferences')
    def update_profile(self,p,expected,changes): return self._document(p,'profile',expected,changes)
    def update_preferences(self,p,expected,data): return self._document(p,'preferences',expected,data)

    def create_report(self,p,case_id,title,payload):
        with self.transaction(p) as c:
            self._active(c,p)
            if not c.execute('SELECT id FROM professor_user.saved_cases WHERE id=%s AND owner_id=%s AND deleted_at IS NULL FOR UPDATE',(case_id,p.user_id)).fetchone():
                raise VNextError.not_found()
            row = c.execute('INSERT INTO professor_user.reports(id,owner_id,case_id,title,payload) VALUES (%s,%s,%s,%s,%s) RETURNING id,case_id,title,payload,provenance,created_at',(uuid4(),p.user_id,case_id,title,Jsonb(payload))).fetchone()
            return self._report_dict(row)

    @staticmethod
    def _report_dict(row):
        return dict(zip(('id','case_id','title','payload','provenance','created_at'),row))

    def report(self,p,id):
        with self.transaction(p) as c:
            self._active(c,p)
            row = c.execute('SELECT id,case_id,title,payload,provenance,created_at FROM professor_user.reports WHERE id=%s AND owner_id=%s',(id,p.user_id)).fetchone()
            if row is None: raise VNextError.not_found()
            return self._report_dict(row)

    def reports(self,p,offset,limit):
        with self.transaction(p) as c:
            self._active(c,p)
            return [self._report_dict(r) for r in c.execute('SELECT id,case_id,title,payload,provenance,created_at FROM professor_user.reports WHERE owner_id=%s ORDER BY created_at DESC,id LIMIT %s OFFSET %s',(p.user_id,limit,offset)).fetchall()]

    def delete_report(self,p,id):
        with self.transaction(p) as c:
            self._active(c,p)
            if c.execute('DELETE FROM professor_user.reports WHERE id=%s AND owner_id=%s',(id,p.user_id)).rowcount!=1:
                raise VNextError.not_found()


class PostgresCaseRepository:
    def __init__(self, users): self.users=users

    @contextmanager
    def transaction(self,p):
        with self.users.transaction(p) as c:
            self.users._active(c,p)
            yield CaseTransaction(c,p)


class CaseTransaction:
    COLUMNS = 'id,owner_id,import_key,import_digest,snapshot,user_authored,title,notes,created_at,updated_at,revision,monitoring,deleted_at'
    def __init__(self,c,p): self.c,self.p=c,p

    def _row(self,row):
        if row is None: return None
        if row[-1] is not None: raise VNextError.not_found()
        return CaseRecord(*row[:11], monitoring=MonitoringPreferences(**row[11]))

    def get(self,id):
        return self._row(self.c.execute(f'SELECT {self.COLUMNS} FROM professor_user.saved_cases WHERE id=%s AND owner_id=%s FOR UPDATE',(id,self.p.user_id)).fetchone())

    def find_import(self,owner_id,import_key):
        return self._row(self.c.execute(f'SELECT {self.COLUMNS} FROM professor_user.saved_cases WHERE owner_id=%s AND import_key=%s FOR UPDATE',(owner_id,import_key)).fetchone())

    def list_accessible(self,user_id,*,scope,offset,limit):
        if scope=='shared': return []
        return [self._row(r) for r in self.c.execute(f'SELECT {self.COLUMNS} FROM professor_user.saved_cases WHERE owner_id=%s AND deleted_at IS NULL ORDER BY updated_at DESC,id LIMIT %s OFFSET %s',(user_id,limit,offset)).fetchall()]

    def insert(self,r):
        self.c.execute('INSERT INTO professor_user.saved_cases(id,owner_id,import_key,import_digest,snapshot,user_authored,title,notes,created_at,updated_at,revision,monitoring) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(r.id,r.owner_id,r.import_key,r.import_digest,Jsonb(r.snapshot),Jsonb(r.user_authored),r.title,r.notes,r.created_at,r.updated_at,r.revision,Jsonb(r.monitoring.model_dump())))

    def replace(self,r,*,expected_revision):
        return self.c.execute('UPDATE professor_user.saved_cases SET title=%s,notes=%s,monitoring=%s,revision=%s,updated_at=%s WHERE id=%s AND owner_id=%s AND revision=%s AND deleted_at IS NULL',(r.title,r.notes,Jsonb(r.monitoring.model_dump()),r.revision,r.updated_at,r.id,self.p.user_id,expected_revision)).rowcount==1

    def append_activity(self,id,event):
        self.c.execute('INSERT INTO professor_user.case_activity(case_id,owner_id,revision,actor_id,kind,occurred_at) VALUES (%s,%s,%s,%s,%s,%s)',(id,self.p.user_id,event.revision,event.actor_id,event.kind,event.occurred_at))

    def list_activity(self,id,*,offset,limit):
        return [Activity(revision=r[0],actor_id=r[1],kind=r[2],occurred_at=r[3]) for r in self.c.execute('SELECT revision,actor_id,kind,occurred_at FROM professor_user.case_activity WHERE case_id=%s AND owner_id=%s ORDER BY revision DESC LIMIT %s OFFSET %s',(id,self.p.user_id,limit,offset)).fetchall()]

    def find_command(self,actor_id,method,route,key_hash,now):
        row=self.c.execute('SELECT actor_id,method,route,key_hash,request_fingerprint,case_id,revision,created_at,expires_at FROM professor_user.case_commands WHERE actor_id=%s AND method=%s AND route=%s AND key_hash=%s AND expires_at>%s',(actor_id,method,route,key_hash,now)).fetchone()
        return CommandReceipt(*row) if row else None

    def append_command(self,r):
        self.c.execute('DELETE FROM professor_user.case_commands WHERE ctid IN (SELECT ctid FROM professor_user.case_commands WHERE actor_id=%s AND expires_at<=%s LIMIT 100)',(r.actor_id,r.created_at))
        if self.c.execute('SELECT count(*) FROM professor_user.case_commands WHERE actor_id=%s',(r.actor_id,)).fetchone()[0]>=MAX_COMMAND_RECEIPTS:
            raise VNextError(ErrorCode.MAINTENANCE)
        self.c.execute('INSERT INTO professor_user.case_commands(actor_id,method,route,key_hash,request_fingerprint,case_id,revision,created_at,expires_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',tuple(r.__dict__.values()))

    def delete(self,id,expected):
        if self.c.execute('UPDATE professor_user.saved_cases SET deleted_at=clock_timestamp(),updated_at=clock_timestamp(),revision=revision+1 WHERE id=%s AND owner_id=%s AND revision=%s AND deleted_at IS NULL',(id,self.p.user_id,expected)).rowcount!=1:
            raise VNextError.version_conflict()


class PrivateCaseService(CaseService):
    def membership(self,p,case_id,request,*,idempotency_key):
        self.open(p,case_id)  # other users receive404, never a resource oracle
        raise VNextError.unsupported_input()

    def delete(self,p,case_id,expected_revision):
        with self._transaction(p) as t:
            self._role(p,t.get(case_id))
            t.delete(case_id,expected_revision)


def validate_configuration():
    """Fail before serving if issuer, role, schema or reviewed authority is absent."""
    from services.vnext.auth import get_supabase_jwt_verifier, AuthenticatedPrincipal
    issuer=get_supabase_jwt_verifier().issuer
    p=AuthenticatedPrincipal(UUID(int=0),str(UUID(int=0)),issuer)
    repo=get_repository()
    with repo.transaction(p) as c:
        repo._configuration(c,issuer)
        tables=c.execute("SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='professor_user' AND c.relkind='r' AND c.relname<>'configuration'").fetchall()
        unsafe=c.execute("""
            SELECT has_column_privilege('professor_user.users','status','INSERT,UPDATE')
                OR has_column_privilege('professor_user.users','platform_role','INSERT,UPDATE')
                OR has_table_privilege('professor_user.users','DELETE,TRUNCATE')
                OR has_table_privilege('professor_user.configuration','INSERT,UPDATE,DELETE,TRUNCATE')
                OR has_column_privilege('professor_user.saved_cases','owner_id','UPDATE')
                OR has_column_privilege('professor_user.profiles','user_id','UPDATE')
                OR EXISTS(SELECT 1 FROM pg_class x JOIN pg_namespace n ON n.oid=x.relnamespace
                    WHERE n.nspname<>'professor_user' AND left(n.nspname,3)<>'pg_'
                    AND n.nspname<>'information_schema' AND x.relkind IN ('r','p','v','f')
                    AND (has_table_privilege(x.oid,'INSERT,UPDATE,DELETE,TRUNCATE')
                         OR has_any_column_privilege(x.oid,'INSERT,UPDATE,REFERENCES')))
                OR EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                    WHERE left(n.nspname,3)<>'pg_' AND n.nspname<>'information_schema'
                    AND p.prosecdef AND has_schema_privilege(n.oid,'USAGE')
                    AND has_function_privilege(p.oid,'EXECUTE'))
        """).fetchone()
        if unsafe is None or unsafe[0]:
            raise VNextError(ErrorCode.ACCOUNT_UNAVAILABLE)
        validate_grants(c)
        expected={'users','profiles','preferences','revoked_sessions','saved_cases','case_activity','case_commands','reports'}
        if {r[0] for r in tables}!=expected or not all(r[1] and r[2] for r in tables):
            raise VNextError(ErrorCode.ACCOUNT_UNAVAILABLE)


def validate_grants(c):
    """Effective table AND column privilege allowlist, including PUBLIC grants."""
    updates={
        'profiles':{'display_name','locale','revision','updated_at'},
        'preferences':{'data','revision','updated_at'},
        'saved_cases':{'title','notes','monitoring','revision','updated_at','deleted_at'},
    }
    deletes={'case_commands','reports'}
    rows=c.execute("""
        SELECT x.relname,has_table_privilege(x.oid,'SELECT'),
            has_table_privilege(x.oid,'DELETE'),
            has_table_privilege(x.oid,'TRUNCATE,TRIGGER,REFERENCES'),
            a.attname,has_column_privilege(x.oid,a.attnum,'SELECT'),
            has_column_privilege(x.oid,a.attnum,'INSERT'),
            has_column_privilege(x.oid,a.attnum,'UPDATE'),
            has_column_privilege(x.oid,a.attnum,'REFERENCES')
        FROM pg_class x JOIN pg_namespace n ON n.oid=x.relnamespace
        JOIN pg_attribute a ON a.attrelid=x.oid AND a.attnum>0 AND NOT a.attisdropped
        WHERE n.nspname='professor_user' AND x.relkind='r'
    """).fetchall()
    for table,select,delete,extra,column,colselect,insert,update,references in rows:
        expected_insert=(table!='configuration' and (table!='users' or column in {'id','issuer'}))
        if (not select or not colselect or delete!=(table in deletes) or extra or references
            or insert!=expected_insert or update!=(column in updates.get(table,set()))):
            raise VNextError(ErrorCode.ACCOUNT_UNAVAILABLE)
