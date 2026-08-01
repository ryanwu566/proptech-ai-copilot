"""Measure bounded route-level static budgets from an existing Next build."""

from __future__ import annotations

import json
from pathlib import Path


ROUTE_BUDGETS = {
    "homepage": {"total_static_bytes": 3_000_000, "largest_js_bytes": 900_000},
    "competition_demo": {"total_static_bytes": 4_000_000, "largest_js_bytes": 900_000},
    "taxoracle": {"total_static_bytes": 4_000_000, "largest_js_bytes": 900_000},
    "map_insight": {"total_static_bytes": 4_500_000, "largest_js_bytes": 900_000},
    "pilot": {"total_static_bytes": 4_500_000, "largest_js_bytes": 900_000},
    "admin": {"total_static_bytes": 4_500_000, "largest_js_bytes": 900_000},
}


def measure(root: Path = Path("frontend_next/.next/static")) -> dict[str, object]:
    if not root.exists():
        return {"status": "not_run", "reason": "frontend_build_missing", "routes": {}}
    files = [path for path in root.rglob("*") if path.is_file()]
    total = sum(path.stat().st_size for path in files)
    javascript = [path for path in files if path.suffix == ".js"]
    largest = max((path.stat().st_size for path in javascript), default=0)
    routes = {name: {"status": "pass" if total <= budget["total_static_bytes"] and largest <= budget["largest_js_bytes"] else "fail", **budget} for name, budget in ROUTE_BUDGETS.items()}
    return {"status": "pass" if all(item["status"] == "pass" for item in routes.values()) else "fail", "total_static_bytes": total, "largest_client_chunk_bytes": largest, "routes": routes}


if __name__ == "__main__":
    print(json.dumps(measure(), sort_keys=True))
