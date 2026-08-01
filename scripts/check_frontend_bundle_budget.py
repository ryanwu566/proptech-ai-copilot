"""Check the built frontend's static asset budget without reading secrets."""

from __future__ import annotations

import json
import sys
from pathlib import Path


TOTAL_BUDGET_BYTES = 8_000_000
LARGEST_CHUNK_BUDGET_BYTES = 900_000


def measure(root: Path = Path("frontend_next/.next/static")) -> dict[str, int | str]:
    if not root.exists():
        return {"status": "not_run", "reason": "frontend_build_missing"}
    files = [path for path in root.rglob("*") if path.is_file()]
    total = sum(path.stat().st_size for path in files)
    javascript = [path for path in files if path.suffix == ".js"]
    largest = max((path.stat().st_size for path in javascript), default=0)
    status = "pass" if total <= TOTAL_BUDGET_BYTES and largest <= LARGEST_CHUNK_BUDGET_BYTES else "fail"
    return {"status": status, "total_static_bytes": total, "initial_javascript_bytes": sum(path.stat().st_size for path in javascript), "largest_client_chunk_bytes": largest, "total_budget_bytes": TOTAL_BUDGET_BYTES, "largest_chunk_budget_bytes": LARGEST_CHUNK_BUDGET_BYTES}


def main() -> int:
    result = measure()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
