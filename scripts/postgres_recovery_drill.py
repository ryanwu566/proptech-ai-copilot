"""Explicit opt-in, isolated PostgreSQL rehearsal. No production URL/dump input.

Only a freshly owned network-disabled container can be removed. No host mount,
port publication, external dump, database URL or production credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.backup_integrity import describe_backup, verify_backup
from scripts.migration_registry import load_registry, production_migrations


def _run(args, *, data=None, timeout=120):
    result = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    if result.returncode:
        # Diagnostics remain on the exception for local debugging only; main
        # emits categorical stage/reason and never subprocess stdout/stderr.
        error = RuntimeError("disposable_command_failed")
        error.diagnostic = result.stderr
        raise error
    return result.stdout


def local_docker_endpoint():
    """Resolve then pin a local socket; never inherit a remote Docker context."""
    endpoint = os.getenv("DOCKER_HOST", "")
    if not endpoint:
        endpoint = _run(["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"], timeout=15).decode().strip()
    if not (endpoint.startswith("unix:///") or endpoint.startswith("npipe:////./pipe/")):
        raise ValueError("local_docker_socket_required")
    if any(ord(char) < 32 for char in endpoint):
        raise ValueError("invalid_docker_socket")
    return endpoint


def rehearse(*, execute=False, image="postgres:16"):
    result = {"schema_version": "postgres-recovery-drill-v1", "scope": "synthetic_disposable",
              "state": "BLOCKED", "reason": "disposable_opt_in_required", "production_connections": 0}
    if not execute:
        return result
    container = None
    docker_base = None
    name = None
    ownership = uuid.uuid4().hex
    stage = "daemon_locality"
    try:
        docker_base = ["docker", "--host", local_docker_endpoint()]
        stage = "image_inspect"
        # Inspect local image only: no pull, mutable image tags resolved BEFORE
        # creation; run by immutable ID. PostgreSQL major is verified separately.
        image_id = _run([*docker_base, "image", "inspect", image, "--format", "{{.Id}}"], timeout=15).decode().strip()
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", image_id):
            raise RuntimeError("invalid_disposable_image")
        name = "proptech-recovery-" + ownership
        stage = "container_create"
        created = _run([*docker_base, "create", "--pull=never", "--name", name,
                        "--label", "proptech.recovery.disposable=true", "--network=none",
                        "--label", "proptech.recovery.run=" + ownership,
                        "--memory=512m", "--cpus=1", "--pids-limit=128",
                        "--tmpfs", "/var/lib/postgresql/data:rw,size=256m",
                        "-e", "POSTGRES_HOST_AUTH_METHOD=trust", image_id], timeout=30).decode().strip()
        if not re.fullmatch(r"[a-f0-9]{64}", created):
            raise RuntimeError("invalid_disposable_container")
        container = created
        stage = "database_ready"
        _run([*docker_base, "start", container], timeout=30)
        for _ in range(30):
            # The official image starts a socket-only temporary server during
            # initdb, then stops it. TCP loopback becomes ready only when the
            # final server starts; no port is published from this container.
            ready = subprocess.run([*docker_base, "exec", container, "pg_isready", "-h", "127.0.0.1", "-U", "postgres"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            if ready.returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("disposable_start_timeout")
        def sql(database, text):
            return _run([*docker_base, "exec", "-i", container, "psql", "-X", "-h", "127.0.0.1", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", database, "-At"], data=text.encode())
        version = int(sql("postgres", "SHOW server_version_num;").decode().strip()) // 10000
        if version != 16:
            raise RuntimeError("unsupported_disposable_major")
        sql("postgres", "CREATE DATABASE recovery_source; CREATE DATABASE recovery_restored;")
        stage = "managed_migrations"
        bootstrap = """CREATE SCHEMA auth;
CREATE TABLE auth.users (id uuid PRIMARY KEY);
CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE SET search_path='' AS $$ SELECT NULL::uuid $$;
"""
        registrations = load_registry()
        migration_sql = "\n".join(path.read_text(encoding="utf-8") for path in production_migrations(registrations))
        sql("recovery_source", bootstrap + migration_sql)
        stage = "synthetic_seed"
        # Synthetic rows, FK, check constraint, sequence and immutable ledger.
        sql("recovery_source", """CREATE TABLE recovery_canary_parent(id serial PRIMARY KEY, value text NOT NULL);
CREATE TABLE recovery_canary_child(id integer PRIMARY KEY, parent_id integer REFERENCES recovery_canary_parent(id), units integer CHECK(units > 0));
INSERT INTO recovery_canary_parent(value) VALUES ('synthetic-alpha'), ('synthetic-beta');
INSERT INTO recovery_canary_child VALUES (1,1,2),(2,2,3);
""")
        for registration in registrations:
            if registration.execution_policy == "production_runner":
                sql("recovery_source", f"INSERT INTO schema_migration_ledger(migration_id,schema_version,checksum) VALUES ('{registration.logical_id}','disposable-drill','{registration.sha256}');")
        validation_sql = """SELECT id,value FROM recovery_canary_parent ORDER BY id;
SELECT id,parent_id,units FROM recovery_canary_child ORDER BY id;
SELECT migration_id,checksum FROM schema_migration_ledger ORDER BY migration_id;
SELECT schemaname,tablename,rowsecurity FROM pg_tables WHERE schemaname IN ('public','vnext_core','vnext_private') ORDER BY schemaname,tablename;
SELECT n.nspname,c.relname,k.conname,k.contype,k.convalidated,k.condeferrable,k.condeferred,k.conkey,k.confkey,k.confupdtype,k.confdeltype
FROM pg_constraint k JOIN pg_namespace n ON n.oid=k.connamespace LEFT JOIN pg_class c ON c.oid=k.conrelid
WHERE n.nspname IN ('public','vnext_core','vnext_private') ORDER BY n.nspname,c.relname,k.conname;
SELECT last_value FROM recovery_canary_parent_id_seq;
"""
        before = sql("recovery_source", validation_sql)
        stage = "backup_creation"
        dump = _run([*docker_base, "exec", container, "pg_dump", "-U", "postgres", "--format=custom", "--dbname=recovery_source"])
        with tempfile.TemporaryDirectory(prefix="proptech-recovery-") as directory:
            archive = Path(directory) / "synthetic.dump"
            archive.write_bytes(dump)
            commit = _run(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).decode().strip()
            metadata = describe_backup(archive, scope="disposable", release_commit=commit, postgres_major=version)
            if verify_backup(archive, metadata) != "PASS":
                raise RuntimeError("backup_integrity_failed")
            _run([*docker_base, "exec", "-i", container, "pg_restore", "--list"], data=dump)
            stage = "restore"
            started = time.monotonic()
            _run([*docker_base, "exec", "-i", container, "pg_restore", "-U", "postgres", "--exit-on-error", "--single-transaction", "--no-owner", "--no-privileges", "--dbname=recovery_restored"], data=dump)
            elapsed = round(time.monotonic() - started, 3)
            stage = "post_restore_validation"
            if sql("recovery_restored", validation_sql) != before:
                raise RuntimeError("restored_validation_failed")
            # Prove restored FK/check enforce rejection and connection recovers.
            for invalid in ("INSERT INTO recovery_canary_child VALUES(3,999,1);", "INSERT INTO recovery_canary_child VALUES(3,1,0);"):
                try:
                    sql("recovery_restored", invalid)
                except RuntimeError:
                    pass
                else:
                    raise RuntimeError("restored_constraint_failed")
            if sql("recovery_restored", "SELECT count(*) FROM recovery_canary_child;").strip() != b"2":
                raise RuntimeError("restored_rows_failed")
        result.update(state="PASS", reason="synthetic_restore_verified", image_id=image_id,
                      postgres_major=version, managed_migrations=len(production_migrations(registrations)),
                      backup_sha256=metadata["sha256"], backup_bytes=len(dump), restore_seconds=elapsed,
                      row_constraint_ledger_validation="PASS", validation_sha256=hashlib.sha256(before).hexdigest(),
                      constraint_validation_scope="inventory_and_synthetic_fk_check_rejection",
                      production_backup="BLOCKED", production_restore="BLOCKED", production_acl_role_restore="NOT_TESTED")
        result["daemon_scope"] = "local_socket"
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        result.update(state="FAIL", reason="disposable_rehearsal_failed", failed_stage=stage)
    finally:
        if container is None and name and docker_base:
            # Creation may succeed before a CLI timeout. Recover only the
            # exact random name with the run-specific ownership label.
            try:
                found = _run([*docker_base, "inspect", name, "--format", '{{.Id}} {{index .Config.Labels "proptech.recovery.run"}}'], timeout=15).decode().strip().split()
                if len(found) == 2 and re.fullmatch(r"[a-f0-9]{64}", found[0]) and found[1] == ownership:
                    container = found[0]
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                result["cleanup"] = "UNKNOWN"
        if container:
            # This exact ID was returned by our successful creation; never
            # remove a caller-supplied name or enumerate any other containers.
            try:
                _run([*docker_base, "rm", "--force", "--volumes", container], timeout=30)
                result["cleanup"] = "PASS"
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                result.update(state="FAIL", cleanup="FAIL", reason="owned_container_cleanup_required")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-disposable", action="store_true")
    parser.add_argument("--local-image", default="postgres:16")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = rehearse(execute=args.execute_disposable, image=args.local_image)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["state"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
