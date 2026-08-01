"""Operator CLI for the official PLVR file pipeline.

The CLI does not accept credentials or database URLs on the command line. The
default commands are discovery/configuration checks; imports require an
explicit operator-approved staging path and remain outside the frontend tree.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.official_plvr_market_pipeline import (
    DISCOVERY_STATUSES,
    aggregate_transactions,
    load_source_registry,
    normalize_rows,
    parse_csv_rows,
    safe_release_evidence,
)


def discover(registry_path: Path) -> dict[str, object]:
    try:
        sources = load_source_registry(registry_path)
    except (OSError, ValueError):
        return {"status": "configuration_required", "source_count": 0}
    enabled = [source for source in sources if source.enabled]
    if not enabled:
        return {"status": "configuration_required", "source_count": 0}
    return {
        "status": "configuration_required",
        "source_count": len(enabled),
        "message": "Operator must resolve and validate the current official release before download.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded official PLVR market pipeline")
    parser.add_argument("command", choices=("discover", "validate", "status", "verify"))
    parser.add_argument("--registry", type=Path, default=ROOT / "config" / "official-market-sources.json")
    parser.add_argument("--input", type=Path, default=None, help="Operator staging CSV path outside the repository")
    parser.add_argument("--source-id", default=None)
    parser.add_argument("--release-id", default=None)
    parser.add_argument("--source-updated-at", default=None)
    args = parser.parse_args()
    if args.command == "validate":
        if not args.input or not args.source_id or not args.release_id:
            result = {"status": "configuration_required", "message": "Validation requires an operator staging path and release metadata."}
        else:
            try:
                transactions, summary = normalize_rows(parse_csv_rows(args.input), source_id=args.source_id, release_id=args.release_id)
                aggregates = aggregate_transactions(transactions, source_name="Official PLVR OpenData", source_release_id=args.release_id, source_updated_at=args.source_updated_at)
                result = {"status": "validated", "aggregate_count": len(aggregates), **safe_release_evidence(source_id=args.source_id, release_id=args.release_id, schema_version=None, archive_sha256=None, input_rows=summary.input_rows, accepted_rows=summary.accepted_rows, quarantined_rows=summary.quarantined_rows, source_updated_at=args.source_updated_at)}
            except (OSError, ValueError):
                result = {"status": "validation_failed", "message": "The staged release did not pass bounded validation."}
    else:
        result = discover(args.registry) if args.command == "discover" else {
        "status": "configuration_required",
        "message": "No production release is claimed without operator data launch.",
        }
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result["status"] in DISCOVERY_STATUSES or result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
