"""Bounded operator command: verify, normalize, accept one reviewed PLVR release."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plvr_provider_update import UpdateBlocked, prepare_release, import_release


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--city", action="append", required=True)
    parser.add_argument("--since", required=True)
    parser.add_argument("--until", required=True)
    parser.add_argument("--as-of-date", type=date.fromisoformat)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--import", dest="write", action="store_true")
    parser.add_argument("--fixture-db", type=Path, help="Disposable SQLite fixture destination only")
    parser.add_argument("--max-bytes", type=int, default=256 * 1024 * 1024)
    parser.add_argument("--max-rows", type=int, default=100_000)
    parser.add_argument("--max-seconds", type=int, default=240)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        database_url = None
        if args.write and not args.fixture_db:
            database_url = os.getenv("PLVR_UPDATE_DATABASE_URL", "").strip()
            if os.getenv("PLVR_UPDATE_ENVIRONMENT", "") != "production-market-import" or not database_url:
                raise UpdateBlocked("configuration_required")
            if not database_url.startswith(("postgres://", "postgresql://")):
                raise UpdateBlocked("database_contract_invalid")
        prepared = prepare_release(args.manifest, args.artifact_id, cities=args.city, since=args.since,
            until=args.until, as_of=args.as_of_date, max_bytes=args.max_bytes, max_rows=args.max_rows,
            max_seconds=args.max_seconds)
        result = import_release(prepared, fixture_db=args.fixture_db, database_url=database_url) if args.write else prepared.report
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    except UpdateBlocked as error:
        print(json.dumps({"capability": "plvr_update", "status": "blocked", "reason_code": error.reason_code, "exclusion_reasons": error.exclusion_reasons, "retention_applied": False}))
        return 2
    except Exception:
        # Exceptions can contain credentials, raw addresses, paths or provider payloads.
        print(json.dumps({"capability": "plvr_update", "status": "blocked", "reason_code": "update_failed", "retention_applied": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
