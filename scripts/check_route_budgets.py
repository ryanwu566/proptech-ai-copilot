"""Enforce measured route assets and the unchanged global static/JS limits."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analyze_next_bundle import SUPPORTED_ROUTES, analyze
from scripts.check_frontend_bundle_budget import measure as measure_global

BASELINE_PATH = ROOT / "docs/performance-budget-v2-baseline.json"
BASELINE = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
ROUTE_BUDGETS = BASELINE["route_budgets"]


def route_limit(budget: dict[str, object]) -> int:
    baseline = int(budget["baseline_client_bytes"])
    return baseline + min((baseline * int(budget["headroom_percent"]) + 99) // 100,
                          int(budget["headroom_cap_bytes"]))


def measure(root: Path = ROOT / "frontend_next/.next") -> dict[str, object]:
    build_root = root.parent if root.name == "static" else root
    global_budget = measure_global(build_root / "static")
    analysis = analyze(build_root)
    routes = {}
    coverage_ok = True
    for route in SUPPORTED_ROUTES:
        budget = ROUTE_BUDGETS[route]
        entry = dict(analysis["routes"].get(route, {"status": analysis["status"], "client_bytes": None, "client_files": []}))
        entry.update(baseline_client_bytes=budget["baseline_client_bytes"],
                     client_budget_bytes=route_limit(budget),
                     headroom_percent=budget["headroom_percent"], headroom_cap_bytes=budget["headroom_cap_bytes"])
        if entry["status"] == "measured":
            entry["status"] = "pass" if entry["client_bytes"] <= entry["client_budget_bytes"] else "fail"
        elif entry["status"] == "route_not_present" and budget["required"]:
            coverage_ok = False
        routes[route] = entry
    passed = (analysis["status"] == "pass" and global_budget["status"] == "pass" and coverage_ok
              and all(entry["status"] in {"pass", "route_not_present"} for entry in routes.values()))
    return {"schema_version": "route-budgets-v2", "status": "pass" if passed else "fail",
            "attribution_status": analysis["status"], "coverage_status": "pass" if coverage_ok else "fail",
            "global_budget": global_budget, "routes": routes,
            "total_static_bytes": global_budget.get("total_static_bytes"),
            "largest_client_chunk_bytes": global_budget.get("largest_client_chunk_bytes")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT / "frontend_next/.next")
    args = parser.parse_args()
    result = measure(args.root)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
