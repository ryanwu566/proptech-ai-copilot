#!/usr/bin/env bash
# Runs only on a new PGDATA volume. No passwords in argv or generated SQL files.
set -Eeuo pipefail
if [[ "${RESTORE_MODE:-0}" == "1" ]]; then
  echo 'Restore mode: no application actors or databases initialized.'
  exit 0
fi
case "${SELFHOST_DATABASE_KIND:?required}" in
  app)
    export DB_ACTOR_PASSWORD="$(cat /run/secrets/app_runtime_password)"
    psql --username postgres --dbname postgres --no-psqlrc --set ON_ERROR_STOP=1 <<'SQL'
\getenv runtime_password DB_ACTOR_PASSWORD
CREATE ROLE app_migration NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE app_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'runtime_password';
CREATE DATABASE proptech_app OWNER app_migration;
REVOKE ALL ON DATABASE proptech_app FROM PUBLIC;
GRANT CONNECT ON DATABASE proptech_app TO app_runtime;
SQL
    psql --username postgres --dbname proptech_app --no-psqlrc --set ON_ERROR_STOP=1 <<'SQL'
REVOKE ALL ON SCHEMA public FROM PUBLIC;
SQL
    ;;
  usage)
    export DB_ACTOR_PASSWORD="$(cat /run/secrets/usage_migration_password)"
    psql --username postgres --dbname postgres --no-psqlrc --set ON_ERROR_STOP=1 <<'SQL'
\getenv migration_password DB_ACTOR_PASSWORD
CREATE ROLE usage_migration LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB CREATEROLE NOREPLICATION PASSWORD :'migration_password';
CREATE DATABASE proptech_api_usage OWNER usage_migration;
REVOKE ALL ON DATABASE proptech_api_usage FROM PUBLIC;
GRANT CONNECT ON DATABASE proptech_api_usage TO usage_migration;
SQL
    # Bootstrap grants runtime CONNECT later; migration actor owns public schema
    # through pg_database_owner and has all rights required for immutable 021.
    ;;
  *) echo 'Invalid database kind.' >&2; exit 1 ;;
esac
unset DB_ACTOR_PASSWORD
