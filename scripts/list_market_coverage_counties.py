"""Print canonical county names for the market coverage workflow.

The workflow needs only county labels for bounded reconciliation calls. This
helper reads the shared tracked JSON registry and emits one county per line. It
intentionally does not print diagnostic internals or file contents.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_SOURCE = ROOT / "frontend_next" / "lib" / "taiwan-admin-areas.json"


def main() -> int:
    try:
        payload = json.loads(REGISTRY_SOURCE.read_text(encoding="utf-8"))
        counties = _unique_counties(payload)
    except Exception:
        counties = []
    if not counties:
        print("CANONICAL_REGISTRY_UNAVAILABLE", file=sys.stderr)
        return 1
    for county in counties:
        print(county)
    return 0


def _unique_counties(payload: dict[str, Any]) -> list[str]:
    areas = payload.get("areas")
    if not isinstance(areas, list):
        return []
    counties: list[str] = []
    seen: set[str] = set()
    for area in areas:
        if not isinstance(area, dict):
            continue
        county = str(area.get("county") or "").strip()
        districts = area.get("districts")
        if county and isinstance(districts, list) and districts and county not in seen:
            counties.append(county)
            seen.add(county)
    return counties


if __name__ == "__main__":
    raise SystemExit(main())
