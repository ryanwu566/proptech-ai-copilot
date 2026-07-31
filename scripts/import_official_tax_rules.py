"""Validate a versioned official TaxOracle rule snapshot offline."""

from __future__ import annotations

import argparse
import json

from services.official_tax_rules import ingest_tax_rule_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an official tax-rule JSON snapshot")
    parser.add_argument("--input", required=True, help="local operator-provided JSON path")
    parser.add_argument("--apply", action="store_true", help="reserved explicit flag; no database mutation is performed")
    args = parser.parse_args()
    print(json.dumps(ingest_tax_rule_snapshot(args.input, dry_run=not args.apply), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
