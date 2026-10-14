"""Real SQL proof on the existing explicitly disposable VNext test contract."""
import os
from pathlib import Path
from uuid import UUID

import pytest
from scripts.disposable_postgres_auth import bootstrap_disposable_supabase_auth
from scripts.validate_postgres_migration import _statements
from services.postgres_runtime import connect

URL = os.getenv("VNEXT_RLS_POSTGRES_URL", "")
pytestmark = [pytest.mark.external_database, pytest.mark.skipif(
    not URL or os.getenv("VNEXT_RLS_POSTGRES_DISPOSABLE") != "1", reason="requires explicit disposable PostgreSQL")]
ROOT = Path(__file__).resolve().parents[1]
USER = UUID("11111111-1111-4111-8111-111111111111")
OTHER = UUID("22222222-2222-4222-8222-222222222222")


def test_real_account_grants_isolation_and_suspension_rls():
    with connect(URL) as connection:
        assert connection.execute("select current_database()").fetchone()[0].startswith("vnext_rls_test")
        try:
            connection.execute("drop schema if exists vnext_private cascade")
            connection.execute("drop schema if exists vnext_core cascade")
            connection.execute("drop schema if exists auth cascade")
            bootstrap_disposable_supabase_auth(connection)
            for filename in ["013_vnext_workspace_case_foundation.sql", "020_consumer_account_foundation.sql"]:
                for statement in _statements(ROOT / "database/migrations" / filename):
                    connection.execute(statement)
            connection.execute("insert into auth.users(id) values (%s),(%s)", (USER, OTHER))
            connection.execute("insert into vnext_core.workspaces(workspace_id, workspace_type, display_name, created_by_user_id, personal_owner_user_id) values (%s, 'personal', 'Fixture', %s, %s)", (USER, USER, USER))
            connection.execute("insert into vnext_core.workspace_members(workspace_id,user_id,role,status,joined_at) values (%s,%s,'owner','active',clock_timestamp())", (USER, USER))
            connection.execute("set local role vnext_api")
            connection.execute("select set_config('request.jwt.claim.sub',%s,true)", (str(USER),))
            connection.execute("insert into vnext_private.consumer_accounts(user_id) values (%s) on conflict do nothing", (USER,))
            row = connection.execute("select user_id,status,platform_role from vnext_private.consumer_accounts").fetchone()
            assert row == (USER, "active", "consumer")
            assert connection.execute("select user_id from vnext_private.consumer_accounts where user_id=%s", (OTHER,)).fetchone() is None
            assert connection.execute("select workspace_id from vnext_core.workspaces").fetchone() is not None
            connection.execute("insert into vnext_core.cases(workspace_id,purpose,title,created_by_user_id) values (%s,'buy_due_diligence','Fixture',%s)", (USER, USER))
            assert connection.execute("select case_id from vnext_core.cases").fetchone() is not None
            for sql, values in [
                ("update vnext_private.consumer_accounts set platform_role='platform_admin'", ()),
                ("insert into vnext_private.consumer_accounts(user_id,platform_role) values (%s,'platform_admin')", (USER,)),
                ("insert into vnext_private.consumer_accounts(user_id) values (%s)", (OTHER,)),
            ]:
                with pytest.raises(Exception):
                    with connection.transaction():
                        connection.execute(sql, values)
            connection.execute("reset role")
            connection.execute("update vnext_private.consumer_accounts set status='suspended',updated_at=clock_timestamp() where user_id=%s", (USER,))
            connection.execute("set local role vnext_api")
            # Conflict insert cannot reset a suspended account.
            connection.execute("insert into vnext_private.consumer_accounts(user_id) values (%s) on conflict do nothing", (USER,))
            assert connection.execute("select status from vnext_private.consumer_accounts").fetchone()[0] == "suspended"
            assert connection.execute("select workspace_id from vnext_core.workspace_members").fetchall() == []
            assert connection.execute("select workspace_id from vnext_core.workspaces").fetchall() == []
            assert connection.execute("select case_id from vnext_core.cases").fetchall() == []
            with pytest.raises(Exception):
                with connection.transaction():
                    connection.execute("insert into vnext_core.cases(workspace_id,purpose,title,created_by_user_id) values (%s,'buy_due_diligence','Denied',%s)", (USER, USER))
        finally:
            connection.rollback()
