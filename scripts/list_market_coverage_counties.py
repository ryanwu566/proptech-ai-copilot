"""Print canonical county names for the market coverage workflow.

The workflow needs only county labels for bounded reconciliation calls. This
helper reads the existing tracked frontend registry artifact and emits one
county per line. It intentionally does not print tracebacks or file contents.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_SOURCE = ROOT / "frontend_next" / "lib" / "taiwan-admin-areas.ts"
COUNTY_PATTERN = re.compile(r'county:\s*"([^"]+)"')


def main() -> int:
    try:
        text = REGISTRY_SOURCE.read_text(encoding="utf-8")
        counties = _unique_counties(text)
    except Exception:
        counties = []
    if not counties:
        print("CANONICAL_REGISTRY_UNAVAILABLE", file=sys.stderr)
        return 1
    for county in counties:
        print(county)
    return 0


def _unique_counties(text: str) -> list[str]:
    counties: list[str] = []
    seen: set[str] = set()
    for match in COUNTY_PATTERN.finditer(text):
        county = match.group(1).strip()
        if county and county not in seen:
            counties.append(county)
            seen.add(county)
    return counties


if __name__ == "__main__":
    raise SystemExit(main())
