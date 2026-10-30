#!/usr/bin/env python3
"""Image-local, opt-in bounded imagery smoke. Never installs or activates anything."""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import ssl
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _adapter(provider, year):
    from services.imagery_providers import NLSCOrthophotoAdapter, CSRSRSpotAdapter
    return NLSCOrthophotoAdapter() if provider == "nlsc_photo2" else CSRSRSpotAdapter(year=year, noncommercial_use=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("nlsc_photo2", "csrsr_spot"), default="nlsc_photo2")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--accept-noncommercial", action="store_true")
    parser.add_argument("--allow-network", action="store_true", help="One bounded on-demand reference fetch; no imagery is printed or retained")
    args = parser.parse_args(argv)
    result = {
        "status": "PREPARED_NOT_NETWORK_VERIFIED", "provider": args.provider,
        "python_version": platform.python_version(), "openssl_version": ssl.OPENSSL_VERSION,
        "provider_activated": False, "credential_values_returned": False,
        "normal_ca_validation": True, "persistent_imagery_written": False, "provider_calls": 0,
    }
    if not args.allow_network:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    if args.provider == "csrsr_spot" and not args.accept_noncommercial:
        result.update(status="REFUSED", reason_code="licensing_not_accepted")
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 1
    try:
        from services.imagery_reference import ImageryQuery, ImageryProviderError
        from services.provider_cost_metrics import PROVIDER_COST_METRICS
        before = PROVIDER_COST_METRICS.snapshot().get(("satellite", "physical_calls"), 0)
        reference = _adapter(args.provider, args.year).fetch(ImageryQuery(
            latitude=25.035570879000026, longitude=121.4525876531026,
            deadline=time.monotonic() + 8.0,
        ))
        result.update(status="PASS", source_type=reference.source_type,
                      output_bytes=len(reference.image_bytes), vintage=reference.vintage,
                      observation_date=reference.observation_date)
    except Exception as error:
        from services.imagery_reference import ImageryProviderError
        result.update(status="UNAVAILABLE", reason_code=error.reason_code if isinstance(error, ImageryProviderError) else "provider_error")
    finally:
        # Metrics count all HTTP boundaries, including capabilities/NoData/error.
        from services.provider_cost_metrics import PROVIDER_COST_METRICS
        result["provider_calls"] = PROVIDER_COST_METRICS.snapshot().get(("satellite", "physical_calls"), 0) - before
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
