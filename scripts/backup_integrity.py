"""Inspect custom-format backup integrity metadata; never connect or restore."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

MAX_BACKUP_BYTES = 4 * 1024**3


def describe_backup(path: Path, *, scope: str, release_commit: str, postgres_major: int,
                    max_bytes: int = MAX_BACKUP_BYTES):
    if scope not in {"disposable", "staging", "production"} or not re.fullmatch(r"[a-f0-9]{40}", release_commit) or not 14 <= postgres_major <= 20:
        raise ValueError("invalid_backup_metadata")
    size = path.stat().st_size
    if not 5 < size <= max_bytes or path.is_symlink():
        raise ValueError("invalid_backup_archive")
    digest = hashlib.sha256()
    with path.open("rb") as archive:
        if archive.read(5) != b"PGDMP":
            raise ValueError("invalid_backup_format")
        archive.seek(0)
        for chunk in iter(lambda: archive.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"schema_version": "postgres-backup-integrity-v1", "scope": scope,
            "release_commit": release_commit, "postgres_major": postgres_major,
            "observed_at": datetime.now(UTC).isoformat(), "format": "custom", "bytes": size,
            "sha256": digest.hexdigest(), "offsite": "UNKNOWN", "retention": "UNKNOWN",
            "restore": "NOT_RUN", "archive_parse": "NOT_RUN"}


def verify_backup(path: Path, metadata: dict) -> str:
    try:
        observed = describe_backup(path, scope=metadata["scope"], release_commit=metadata["release_commit"], postgres_major=metadata["postgres_major"])
        return "PASS" if all(observed[key] == metadata[key] for key in ("schema_version", "format", "bytes", "sha256")) else "FAIL"
    except (KeyError, TypeError, OSError, ValueError):
        return "FAIL"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--scope", required=True, choices=("disposable", "staging", "production"))
    parser.add_argument("--release-commit", required=True)
    parser.add_argument("--postgres-major", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = describe_backup(args.archive, scope=args.scope, release_commit=args.release_commit, postgres_major=args.postgres_major)
        # Never overwrite the inspected backup with its metadata.
        if args.output.resolve() == args.archive.resolve() or args.output.exists():
            raise ValueError("invalid_backup_output")
        with args.output.open("x", encoding="utf-8") as output:
            output.write(json.dumps(result, indent=2) + "\n")
    except (OSError, ValueError):
        print("BACKUP_METADATA=FAIL")
        return 1
    print("BACKUP_METADATA=PASS; OFFSITE=UNKNOWN; RESTORE=NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
