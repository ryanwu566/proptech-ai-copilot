"""Restore a local SQLite backup only after an explicit operator confirmation."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def restore(source: Path, destination: Path, *, mode: str = "local", confirm: bool = False) -> dict[str, str]:
    if mode != "local":
        return {"status": "blocked", "reason": "managed_postgres_restore_runbook_required"}
    if not confirm or not source.is_file() or source.resolve() == destination.resolve():
        return {"status": "blocked", "reason": "explicit_local_restore_confirmation_required"}
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
    parser.add_argument("--confirm-local-restore", action="store_true")
    args = parser.parse_args()
    result = restore(args.source, args.destination, mode=args.mode, confirm=args.confirm_local_restore)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
