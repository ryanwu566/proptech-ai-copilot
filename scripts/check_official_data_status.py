"""Print safe, metadata-only official source status."""

from __future__ import annotations

import argparse
import json

from services.official_data_registry import public_source_status
from services.official_tax_rules import tax_source_status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", choices=("terrain", "tax", "all"), default="all")
    args = parser.parse_args()
    payload = {}
    if args.domain in {"terrain", "all"}:
        payload["terrain"] = public_source_status("terrain")
    if args.domain in {"tax", "all"}:
        payload["tax"] = tax_source_status()
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
