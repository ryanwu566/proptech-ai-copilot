# VNext API Database Role Provisioning

Status: Stage 1 Slice 2 deployment boundary; no live credential provisioned

Migration `013_vnext_workspace_case_foundation.sql` defines `vnext_api` as a direct-login
PostgreSQL request role with `NOSUPERUSER`, `NOBYPASSRLS`, `NOINHERIT`, no DDL authority,
and only the grants required by the VNext repositories. The migration deliberately assigns
no password. Therefore the role cannot authenticate after schema application alone.

Credential provisioning is a separate deployment operation. An authorized operator must
generate a secret outside the repository, set it through the managed database's approved
secret channel, and expose only a connection string authenticating directly as `vnext_api`
to the FastAPI runtime:

```text
VNEXT_DATABASE_URL=postgresql://vnext_api:<secret>@<approved-host>/<database>
```

The secret must not be placed in SQL migrations, source control, frontend variables,
browser storage, logs, screenshots, or API responses. The application intentionally does
not fall back from `VNEXT_DATABASE_URL` to the legacy `DATABASE_URL`, because that legacy
credential may own tables or bypass RLS.

Deployment acceptance must connect using `VNEXT_DATABASE_URL` and verify:

```sql
select current_user;
select rolsuper, rolbypassrls
from pg_roles
where rolname = current_user;
```

`current_user` must be `vnext_api`; both flags must be false; the role must not own either
VNext schema or any VNext tenant table. Normal request handling must never connect as
`postgres` or `service_role`, and must not use `SET ROLE` from an owner connection.

Migration/DDL credentials remain operator-only. Rotation changes the externally managed
credential and `VNEXT_DATABASE_URL`; it does not edit migration 013 or grant RLS bypass.
