"""Fail-closed catalog audit for the dedicated, immutable usage subsystem."""
from __future__ import annotations

import re

CHECKSUM = '00ed7d4b78de6d92c285ab8cd87241d1477bee2ce6e97caef6bbf6e2f43b98af'
MIGRATION_ID = '021_api_usage_quota_ledger'
RUNTIME = 'proptech_usage_runtime_v1'
ROLES = tuple('proptech_usage_' + name for name in ('executor', 'guard', 'reader', 'writer'))
TABLES = ('hourly', 'flush_batches', 'quota_policy', 'quota_subjects', 'quota_hourly', 'reservation_markers')
FUNCTIONS = ('api_usage.consume(text,text,text,text,uuid)', 'api_usage.prune()')
PRIVILEGES = ('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN')
TABLE_GRANTS = {
    'hourly': {'writer': {'SELECT','INSERT','UPDATE','DELETE'}, 'reader': {'SELECT'}},
    'flush_batches': {'writer': {'SELECT','INSERT','UPDATE','DELETE'}},
    'quota_policy': {'executor': {'SELECT'}},
    'quota_subjects': {'executor': {'SELECT','INSERT','UPDATE','DELETE'}},
    'quota_hourly': {'executor': {'SELECT','INSERT','UPDATE','DELETE'}, 'reader': {'SELECT'}},
    'reservation_markers': {'executor': {'SELECT','INSERT','UPDATE','DELETE'}},
}
POLICIES = {
    ('hourly','usage_writer','*','proptech_usage_writer','true','true'),
    ('hourly','usage_reader','r','proptech_usage_reader','true',None),
    ('flush_batches','usage_batch_writer','*','proptech_usage_writer','true','true'),
    ('quota_policy','quota_policy_executor','r','proptech_usage_executor','true',None),
    ('quota_subjects','quota_subject_executor','*','proptech_usage_executor','true','true'),
    ('quota_hourly','quota_hourly_executor','*','proptech_usage_executor','true','true'),
    ('quota_hourly','quota_hourly_reader','r','proptech_usage_reader','true',None),
    ('reservation_markers','quota_marker_executor','*','proptech_usage_executor','true','true'),
}


class BootstrapRefused(RuntimeError):
    """Only bounded categories may cross the CLI boundary; never SQL/DSNs."""


def require(condition, category='security_posture_mismatch'):
    if not condition:
        raise BootstrapRefused(category)


def verify_security(c, *, actor, migration_text, runtime=False):
    """Audit final privileges, membership options, RLS and definer bodies."""
    names = (*ROLES, RUNTIME) if runtime else ROLES
    rows = c.execute("SELECT rolname,rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication,rolcanlogin,rolinherit FROM pg_roles WHERE left(rolname,15)='proptech_usage_' ORDER BY rolname").fetchall()
    require({r[0] for r in rows} == set(names))
    for row in rows:
        require(not any(row[1:6]))
        require(row[6:] == ((True, True) if row[0] == RUNTIME else (False, False)))
    schemas = c.execute("SELECT nspname,pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname IN ('api_usage','api_usage_bootstrap') ORDER BY nspname").fetchall()
    require(schemas == [('api_usage',actor), ('api_usage_bootstrap',actor)])
    require(not c.execute("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname NOT LIKE 'pg\\_%' ESCAPE '\\' AND nspname NOT IN ('api_usage','api_usage_bootstrap','public','information_schema'))").fetchone()[0])
    require(not c.execute("SELECT EXISTS(SELECT 1 FROM pg_depend d JOIN pg_namespace n ON n.oid=d.refobjid WHERE d.refclassid='pg_namespace'::regclass AND n.nspname='public')").fetchone()[0])
    require(not c.execute("SELECT EXISTS(SELECT 1 FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid WHERE r.relnamespace IN ('api_usage'::regnamespace,'api_usage_bootstrap'::regnamespace) AND NOT t.tgisinternal)").fetchone()[0])
    require(not c.execute("SELECT EXISTS(SELECT 1 FROM pg_rewrite w JOIN pg_class r ON r.oid=w.ev_class WHERE r.relnamespace IN ('api_usage'::regnamespace,'api_usage_bootstrap'::regnamespace))").fetchone()[0])
    require(not c.execute("SELECT EXISTS(SELECT 1 FROM pg_attribute a JOIN pg_class r ON r.oid=a.attrelid WHERE r.relnamespace IN ('api_usage'::regnamespace,'api_usage_bootstrap'::regnamespace) AND a.attacl IS NOT NULL)").fetchone()[0])
    require(not c.execute('SELECT EXISTS(SELECT 1 FROM pg_event_trigger)').fetchone()[0])
    relations = c.execute("SELECT relname,relkind,pg_get_userbyid(relowner),relrowsecurity,relforcerowsecurity FROM pg_class WHERE relnamespace='api_usage'::regnamespace AND relkind NOT IN ('i','t') ORDER BY relname").fetchall()
    require(relations == sorted((t,'r',actor,True,True) for t in TABLES))
    rows = c.execute("SELECT c.relname,p.polname,p.polcmd,pg_get_userbyid(p.polroles[1]),pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid),p.polpermissive,cardinality(p.polroles) FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid WHERE c.relnamespace='api_usage'::regnamespace").fetchall()
    require({r[:6] for r in rows} == POLICIES and all(r[6:] == (True,1) for r in rows))
    bodies = dict(re.findall(r'CREATE FUNCTION api_usage\.(\w+)\(.*?AS \$\$(.*?)\$\$;', migration_text, re.S))
    functions = c.execute("SELECT p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig,p.prosrc,l.lanname,p.provolatile,p.proleakproof FROM pg_proc p JOIN pg_language l ON l.oid=p.prolang WHERE p.pronamespace='api_usage'::regnamespace ORDER BY p.proname").fetchall()
    require(len(functions)==2 and set(bodies)=={'consume','prune'})
    for name, owner, definer, config, body, language, volatility, leakproof in functions:
        require(owner=='proptech_usage_executor' and definer and config==['search_path=""'])
        require(body==bodies.get(name) and language=='plpgsql' and volatility=='v' and not leakproof)
    require(all(c.execute('SELECT to_regprocedure(%s) IS NOT NULL', (fn,)).fetchone()[0] for fn in FUNCTIONS))

    # ACLs can name only the intended grantees and owners, without grant options.
    for table in TABLES:
        grants = TABLE_GRANTS[table]
        acl = c.execute("SELECT a.grantee::regrole::text,a.privilege_type,a.is_grantable FROM pg_class r CROSS JOIN LATERAL aclexplode(coalesce(r.relacl,acldefault('r',r.relowner))) a WHERE r.oid=%s::regclass", ('api_usage.'+table,)).fetchall()
        expected = {(actor,p,False) for p in PRIVILEGES}
        expected |= {('proptech_usage_'+role,p,False) for role,permissions in grants.items() for p in permissions}
        require(set(acl)==expected)
        for role in ROLES:
            for privilege in PRIVILEGES:
                actual = c.execute('SELECT has_table_privilege(%s,%s,%s)',(role,'api_usage.'+table,privilege)).fetchone()[0]
                require(actual == (privilege in grants.get(role.removeprefix('proptech_usage_'),set())))
    for fn, grantee in zip(FUNCTIONS, ('proptech_usage_guard','proptech_usage_writer')):
        acl = c.execute("SELECT a.grantee::regrole::text,a.privilege_type,a.is_grantable FROM pg_proc p CROSS JOIN LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a WHERE p.oid=%s::regprocedure",(fn,)).fetchall()
        require(set(acl)=={('proptech_usage_executor','EXECUTE',False),(grantee,'EXECUTE',False)})
    for schema, expected in (
        ('api_usage', {(actor,'USAGE',False),(actor,'CREATE',False),*((r,'USAGE',False) for r in ROLES)}),
        ('api_usage_bootstrap', {(actor,'USAGE',False),(actor,'CREATE',False)}),
    ):
        acl = c.execute("SELECT a.grantee::regrole::text,a.privilege_type,a.is_grantable FROM pg_namespace n CROSS JOIN LATERAL aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a WHERE n.nspname=%s",(schema,)).fetchall()
        require(set(acl)==expected)
    require(not c.execute('SELECT EXISTS(SELECT 1 FROM pg_default_acl)').fetchone()[0])
    history = c.execute('SELECT migration_id,checksum,bootstrap_version,actor FROM api_usage_bootstrap.history').fetchall()
    require(history==[(MIGRATION_ID,CHECKSUM,1,actor)])
    require(c.execute("SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid='api_usage_bootstrap.history'::regclass").fetchone()==(actor,))
    require(not c.execute("SELECT EXISTS(SELECT 1 FROM pg_class r CROSS JOIN LATERAL aclexplode(coalesce(r.relacl,acldefault('r',r.relowner))) a WHERE r.oid='api_usage_bootstrap.history'::regclass AND a.grantee<>r.relowner)").fetchone()[0])

    # PG17 automatically grants the creator ADMIN-only membership, by the
    # bootstrap superuser. It is not SET or inherited authority. Self-grants
    # used at the seams must be absent; do not try to revoke another grantor.
    rows = c.execute("SELECT r.rolname,m.rolname,a.admin_option,a.inherit_option,a.set_option FROM pg_auth_members a JOIN pg_roles r ON r.oid=a.roleid JOIN pg_roles m ON m.oid=a.member WHERE r.rolname=ANY(%s) OR m.rolname=ANY(%s)", (list(names),list(names))).fetchall()
    for granted, member, admin, inherit, can_set in rows:
        if member==actor and granted in names:
            require((admin,inherit,can_set)==(True,False,False))
        else:
            require(runtime and member==RUNTIME and granted in ('proptech_usage_guard','proptech_usage_writer') and (admin,inherit,can_set)==(False,True,False))
    require(c.execute("SELECT pg_has_role(%s,'proptech_usage_executor','SET'),pg_has_role(%s,'proptech_usage_executor','USAGE')", (actor,actor)).fetchone()==(False,False))
    for role in names:
        require(not c.execute("SELECT has_schema_privilege(%s,'api_usage','CREATE') OR has_schema_privilege(%s,'api_usage_bootstrap','USAGE') OR has_database_privilege(%s,current_database(),'CREATE')",(role,role,role)).fetchone()[0])
    # Test effective request-role privileges too, including inherited access.
    browser = c.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated','service_role','vnext_api')").fetchall()
    for (role,) in browser:
        require(not c.execute("SELECT has_schema_privilege(%s,'api_usage','USAGE') OR has_schema_privilege(%s,'api_usage','CREATE')",(role,role)).fetchone()[0])
        require(not any(c.execute('SELECT has_function_privilege(%s,%s,\'EXECUTE\')',(role,fn)).fetchone()[0] for fn in FUNCTIONS))
        for table in TABLES:
            require(not c.execute("SELECT has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER,MAINTAIN')",(role,'api_usage.'+table)).fetchone()[0])
    if runtime:
        rows = c.execute('SELECT r.rolname,a.admin_option,a.inherit_option,a.set_option FROM pg_auth_members a JOIN pg_roles r ON r.oid=a.roleid WHERE a.member=%s::regrole ORDER BY r.rolname',(RUNTIME,)).fetchall()
        require(rows==[('proptech_usage_guard',False,True,False),('proptech_usage_writer',False,True,False)])
        require(not c.execute("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspowner=%s::regrole) OR EXISTS(SELECT 1 FROM pg_class WHERE relowner=%s::regrole) OR EXISTS(SELECT 1 FROM pg_proc WHERE proowner=%s::regrole) OR EXISTS(SELECT 1 FROM pg_database WHERE datname=current_database() AND datdba=%s::regrole)",(RUNTIME,)*4).fetchone()[0])
