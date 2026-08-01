"""Create a local SQLite backup for pilot evidence recovery drills.

Production Postgres backups belong to the managed provider and are not
performed by this script.  The command is intentionally local-only.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def backup(source: Path, destination: Path, *, mode: str = "local") -> dict[str, str]:
    if mode != "local":
        return {"status": "blocked", "reason": "managed_postgres_backup_required"}
    if source.resolve() == destination.resolve() or not source.is_file():
        return {"status": "blocked", "reason": "invalid_local_backup_scope"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as destination_connection:
        source_connection.backup(destination_connection)
        integrity = destination_connection.execute("PRAGMA integrity_check").fetchone()[0]
    return {"status": "pass" if integrity == "ok" else "fail", "integrity": integrity}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--mode", choices=("local", "production"), default="local")
    args = parser.parse_args()
    result = backup(args.source, args.destination, mode=args.mode)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
