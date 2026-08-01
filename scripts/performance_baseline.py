"""Report reproducible static performance measurements from a local build."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_route_budgets import measure as measure_routes


def report(root: Path = Path(".")) -> dict[str, object]:
    static = root / "frontend_next/.next/static"
    result = measure_routes(static)
    return {"schema_version": "performance-baseline-v1", "status": result["status"], "python": platform.python_version(), "platform": platform.platform(), "build_mode": "next-production-if-present", "route_static_measurement": result, "network": "not measured", "browser_web_vitals": "not measured"}


if __name__ == "__main__":
    print(json.dumps(report(), ensure_ascii=True, sort_keys=True))
