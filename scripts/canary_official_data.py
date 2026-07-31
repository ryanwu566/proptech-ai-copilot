"""Explicit opt-in canary for the verified public NLSC OGC endpoint.

This command is never called by tests, builds, or the application.  It reads a
bounded capabilities document and reports only status and schema validity.
"""

from __future__ import annotations

import argparse
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen


VERIFIED_ENDPOINTS = {
    "nlsc_base_map": "https://wmts.nlsc.gov.tw/wmts",
}
MAX_BYTES = 1_000_000


def run_canary(provider_id: str, *, http_get=urlopen) -> dict[str, object]:
    base_url = VERIFIED_ENDPOINTS[provider_id]
    query = urlencode({"SERVICE": "WMTS", "REQUEST": "GetCapabilities", "VERSION": "1.0.0"})
    request = Request(f"{base_url}?{query}", headers={"Accept": "application/xml"})
    with http_get(request, timeout=20) as response:
        body = response.read(MAX_BYTES + 1)
        content_type = response.headers.get("Content-Type", "")
        truncated = len(body) > MAX_BYTES
        schema_valid = not truncated and bool(re.search(rb"<(?:\w+:)?Capabilities\b", body)) and b"WMTS" in body
        return {
            "provider_id": provider_id,
            "status": "available" if response.status == 200 and schema_valid else "unavailable",
            "http_status": response.status,
            "content_type_present": bool(content_type),
            "schema_status": "valid" if schema_valid else "invalid_or_unavailable",
            "response_bytes_bounded": not truncated,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Explicit NLSC official-source canary")
    parser.add_argument("--provider-id", choices=sorted(VERIFIED_ENDPOINTS), required=True)
    parser.add_argument("--allow-network", action="store_true", help="required to make the live canary call")
    args = parser.parse_args()
    if not args.allow_network:
        print({"provider_id": args.provider_id, "status": "not_run", "reason": "explicit_opt_in_required"})
        return 0
    result = run_canary(args.provider_id)
    print({key: result[key] for key in ("provider_id", "status", "http_status", "content_type_present", "schema_status", "response_bytes_bounded")})
    return 0 if result["status"] == "available" else 1


if __name__ == "__main__":
    raise SystemExit(main())
