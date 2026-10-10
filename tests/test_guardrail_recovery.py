from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_backup_integrity_rejects_empty_corrupt_and_oversized_archives(tmp_path):
    from scripts.backup_integrity import describe_backup, verify_backup
    archive = tmp_path / "local.dump"
    archive.write_bytes(b"PGDMPsynthetic-fixture")
    metadata = describe_backup(archive, scope="disposable", release_commit="a" * 40, postgres_major=16)
    assert metadata["sha256"] == hashlib.sha256(b"PGDMPsynthetic-fixture").hexdigest()
    assert verify_backup(archive, metadata) == "PASS"
    archive.write_bytes(b"PGDMPcorrupted-fixture")
    assert verify_backup(archive, metadata) == "FAIL"
    archive.write_bytes(b"")
    with pytest.raises(ValueError):
        describe_backup(archive, scope="disposable", release_commit="a" * 40, postgres_major=16)
    archive.write_bytes(b"PGDMP" + b"x" * 100)
    with pytest.raises(ValueError):
        describe_backup(archive, scope="disposable", release_commit="a" * 40, postgres_major=16, max_bytes=50)


def test_metadata_output_cannot_overwrite_a_hardlinked_archive(tmp_path):
    archive = tmp_path / "source.dump"
    archive.write_bytes(b"PGDMPsynthetic-fixture")
    alias = tmp_path / "metadata.json"
    os.link(archive, alias)
    result = subprocess.run([sys.executable, "scripts/backup_integrity.py", "--archive", str(archive), "--scope", "disposable", "--release-commit", "a" * 40, "--postgres-major", "16", "--output", str(alias)], capture_output=True, text=True)
    assert result.returncode == 1
    assert archive.read_bytes() == b"PGDMPsynthetic-fixture"


def test_recovery_never_runs_without_disposable_opt_in():
    from scripts.postgres_recovery_drill import rehearse
    assert rehearse(execute=False)["state"] == "BLOCKED"


def test_recovery_rejects_remote_docker_daemon_before_creating_resources(monkeypatch):
    from scripts.postgres_recovery_drill import local_docker_endpoint
    for endpoint in ("tcp://production.example.com:2376", "ssh://production.example.com", "npipe:////remote/pipe/docker"):
        monkeypatch.setenv("DOCKER_HOST", endpoint)
        with pytest.raises(ValueError):
            local_docker_endpoint()


def test_recovery_waits_for_final_server_instead_of_initdb_socket(monkeypatch):
    """Official image initialization accepts Unix sockets before its restart."""
    from scripts import postgres_recovery_drill as drill

    class FinalServerSelected(Exception):
        pass

    phase = {"probes": 0}
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    monkeypatch.setattr(drill.time, "sleep", lambda _: None)

    def command(args, **kwargs):
        if "image" in args:
            return ("sha256:" + "a" * 64).encode()
        if "create" in args:
            return ("b" * 64).encode()
        if "psql" in args:
            if phase["probes"] < 2:
                raise RuntimeError("temporary_server_shutdown")
            raise FinalServerSelected
        return b""

    def probe(args, **kwargs):
        phase["probes"] += 1
        # The first phase accepts sockets; only the final phase accepts TCP.
        temporary_socket = "-h" not in args
        return subprocess.CompletedProcess(args, 0 if temporary_socket or phase["probes"] >= 2 else 2)

    monkeypatch.setattr(drill, "_run", command)
    monkeypatch.setattr(drill.subprocess, "run", probe)
    with pytest.raises(FinalServerSelected):
        drill.rehearse(execute=True)


def test_recovery_unready_server_stays_bounded_and_cleans_owned_container(monkeypatch):
    from scripts import postgres_recovery_drill as drill
    probes = []
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    monkeypatch.setattr(drill.time, "sleep", lambda _: None)

    def command(args, **kwargs):
        if "image" in args:
            return ("sha256:" + "a" * 64).encode()
        if "create" in args:
            return ("b" * 64).encode()
        if "psql" in args:
            pytest.fail("unready server must never receive SQL")
        return b""

    def unready(args, **kwargs):
        probes.append(args)
        return subprocess.CompletedProcess(args, 2)

    monkeypatch.setattr(drill, "_run", command)
    monkeypatch.setattr(drill.subprocess, "run", unready)
    result = drill.rehearse(execute=True)
    assert result["state"] == "FAIL"
    assert result["failed_stage"] == "database_ready"
    assert result["cleanup"] == "PASS"
    assert len(probes) == 30


def test_rollback_rejects_mutable_refs_missing_artifacts_and_contract_changes():
    from scripts.verify_rollback import compatibility
    base = {"frontend_sha": "a" * 40, "backend_sha": "b" * 40, "api_contract": "api-contract-v1", "migration_registry_sha256": "c" * 64,
            "artifacts": {"synthetic": "d" * 64}, "frontend_tree": "e" * 40}
    assert compatibility(base, dict(base))["state"] == "PASS"
    for mutation in ({"frontend_sha": "main"}, {"backend_sha": "latest"}, {"artifacts": {}}, {"api_contract": "api-contract-v2"}, {"migration_registry_sha256": "e" * 64}, {"artifacts": {"synthetic": "f" * 64}}, {"frontend_tree": "f" * 40}, {"frontend_tree": None}):
        assert compatibility(base, dict(base, **mutation))["state"] != "PASS"


def test_cloud_run_export_does_not_equate_ingress_settings_with_waf_or_origin_proof():
    from scripts.verify_cloud_run_guardrails import inspect_export
    insecure = {"metadata": {"annotations": {"run.googleapis.com/ingress": "all"}}, "spec": {"template": {"spec": {"containers": [{"command": ["uvicorn"], "args": ["--proxy-headers"]}]}}}}
    result = inspect_export(insecure)
    assert result["checks"]["restricted_ingress"] == "FAIL"
    assert result["controls"]["edge_waf"] == "BLOCKED"
    assert result["controls"]["trusted_ingress"] == "BLOCKED"


def test_historical_registry_rejects_duplicates_missing_inventory_and_bad_order():
    from scripts.migration_registry import load_registry, parse_registry, MigrationRegistryError
    import json
    payload = json.loads(Path("database/migration_registry.json").read_text())
    assert len(parse_registry(payload, verify_files=False)) == len(load_registry())
    duplicated = dict(payload, migrations=[*payload["migrations"], payload["migrations"][0]])
    with pytest.raises(MigrationRegistryError):
        parse_registry(duplicated, verify_files=False)
