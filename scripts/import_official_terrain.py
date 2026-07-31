"""Validate a manually downloaded official Terrain snapshot.

Dry-run is the default.  This command does not download data or mutate a
database; it prints only a safe validation summary.
"""

from __future__ import annotations

import argparse
import json

from services.official_terrain_data import ingest_terrain_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an official Terrain GeoJSON snapshot")
    parser.add_argument("--input", required=True, help="local operator-provided GeoJSON path")
    parser.add_argument("--provider-id", required=True)
    parser.add_argument("--apply", action="store_true", help="reserved explicit flag; no database mutation is performed")
    args = parser.parse_args()
    print(json.dumps(ingest_terrain_snapshot(args.input, args.provider_id, dry_run=not args.apply), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
