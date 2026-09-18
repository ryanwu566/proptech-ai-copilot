"""Minimal Supabase Auth contract for explicitly disposable PostgreSQL tests.

This bootstrap is for test and CI databases only. Production migrations must
continue to require the real ``auth.users`` table and ``auth.uid()`` function.
"""

from __future__ import annotations


def bootstrap_disposable_supabase_auth(connection) -> None:
    """Install only the Auth objects referenced by repository migrations/tests."""
    connection.execute("CREATE SCHEMA IF NOT EXISTS auth")
    connection.execute("CREATE TABLE IF NOT EXISTS auth.users (id uuid PRIMARY KEY)")
    auth_uid = connection.execute("SELECT to_regprocedure('auth.uid()')").fetchone()
    if auth_uid is None or auth_uid[0] is None:
        connection.execute(
            "CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE "
            "SET search_path = '' AS $$ SELECT COALESCE("
            "NULLIF(current_setting('request.jwt.claim.sub', true), ''), "
            "NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'"
            ")::uuid $$"
        )
