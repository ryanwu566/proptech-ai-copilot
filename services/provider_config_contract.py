"""Capability-specific configuration checks; never probe or return values."""

from __future__ import annotations

import re
from collections.abc import Mapping
from urllib.parse import urlsplit

R2 = ("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT", "R2_BUCKET", "R2_REGION")
REQUIREMENTS = {
    "geocoding": ("GOOGLE_MAPS_API_KEY",),
    "routes": ("GOOGLE_MAPS_API_KEY",),
    "places": ("GOOGLE_MAPS_API_KEY",),
    "maps": ("NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY",),
    "street-view": ("NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY",),
    "valuation": ("VALUATION_DATABASE_URL", "VALUATION_DEMO_MODE", "PLVR_DATA_BACKEND"),
    "finder": ("VALUATION_DATABASE_URL", "VALUATION_DEMO_MODE"),
    "trend": ("VALUATION_DATABASE_URL", "VALUATION_DEMO_MODE"),
    "market": ("VALUATION_DATABASE_URL",),
    "plvr": ("PLVR_UPDATE_DATABASE_URL", "PLVR_UPDATE_ENVIRONMENT"),
    "wra": R2,
    "gsmma": (*R2, "GSMMA_GEOLOGICAL_SENSITIVITY_DATASET_VERSION"),
    "ardswc": (),
    "ardswc-landslide": (),
    "ardswc-debris-flow": (),
    "liquefaction": (),
    "tdx": ("TDX_CLIENT_ID", "TDX_CLIENT_SECRET", "COMMUTE_REFRESH_TOKEN"),
    "ris": ("DATABASE_URL", "NLSC_VILLAGE_BOUNDARY_ARTIFACT_SHA256", "NLSC_VILLAGE_BOUNDARY_SOURCE_VINTAGE"),
    "nlsc": ("NLSC_GATEWAY_BASE_URL", "NLSC_GATEWAY_CLIENT_TOKEN"),
    "satellite": ("EARTH_ENGINE_SATELLITE_REFERENCE_V1", "EARTH_ENGINE_PROJECT"),
    "hosted": ("FRONTEND_PRODUCTION_URL", "BACKEND_PRODUCTION_URL", "EXPECTED_FRONTEND_COMMIT_SHA", "EXPECTED_BACKEND_COMMIT_SHA"),
    "active-fault": (),
    "tax-legal": (),
}
SOURCES = {"geocoding": "google_geocoding", "routes": "google_routes", "places": "google_places", "valuation": "blue_or_green", "finder": "blue", "trend": "blue", "market": "blue", "plvr": "official_plvr_opendata", "wra": "WRA", "gsmma": "GSMMA", "ardswc": "ARDSWC", "liquefaction": "GeologyCloud", "tdx": "TDX", "ris": "RIS_ODRP014", "nlsc": "NLSC_gateway", "satellite": "Sentinel-2", "maps": "Google_Maps", "street-view": "Google_Street_View", "hosted": "deployed_release", "active-fault": "official_manual_verification", "tax-legal": "professional_manual_verification"}
SOURCES.update({"ardswc-landslide": "ARDSWC", "ardswc-debris-flow": "ARDSWC"})


def valid_sha(value: str) -> bool:
    return re.fullmatch(r"[0-9a-fA-F]{40}", value) is not None


def exact_version(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value)) and value.lower() not in {"latest", "current", "unknown", "unconfigured"}


def _url(value: str, *, postgres: bool = False) -> bool:
    try:
        url = urlsplit(value)
        if postgres:
            return url.scheme in {"postgres", "postgresql"} and bool(url.hostname) and bool(url.path.strip("/"))
        return url.scheme == "https" and bool(url.hostname) and not url.username and not url.password and not url.query and not url.fragment and url.hostname not in {"localhost", "127.0.0.1", "::1"}
    except ValueError:
        return False


def configuration_status(capability: str, environ: Mapping[str, str]) -> dict[str, str]:
    if capability not in REQUIREMENTS:
        raise ValueError("unsupported capability")
    names = list(REQUIREMENTS[capability])
    if capability == "valuation" and environ.get("PLVR_DATA_BACKEND", "blue").strip().lower() == "green":
        names.append("COMPACT_GREEN_DATABASE_URL")
    if capability == "ris":
        names.append("NLSC_VILLAGE_BOUNDARY_ARTIFACT_PATH" if environ.get("NLSC_VILLAGE_BOUNDARY_ARTIFACT_PATH") else "NLSC_VILLAGE_BOUNDARY_R2_KEY")
        if "NLSC_VILLAGE_BOUNDARY_R2_KEY" in names:
            names.extend(R2)
    result = {}
    for name in names:
        value = str(environ.get(name, "")).strip()
        status = "present" if value else "missing"
        if value:
            valid = True
            if name.endswith("DATABASE_URL"):
                valid = _url(value, postgres=True)
            elif name.endswith("COMMIT_SHA") or name.endswith("ARTIFACT_SHA256"):
                valid = valid_sha(value) if name.endswith("COMMIT_SHA") else re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None
            elif name.endswith("DATASET_VERSION"):
                valid = exact_version(value)
            elif name == "VALUATION_DEMO_MODE":
                valid = value.lower() == "false"
            elif name == "PLVR_DATA_BACKEND":
                valid = value.lower() in {"blue", "green"}
            elif name == "PLVR_UPDATE_ENVIRONMENT":
                valid = value == "production-market-import"
            elif name == "EARTH_ENGINE_SATELLITE_REFERENCE_V1":
                valid = value.lower() == "true"
            elif name.endswith("URL") or name == "R2_ENDPOINT":
                valid = _url(value)
            elif "TOKEN" in name:
                valid = len(value) >= 32 and not any(char.isspace() for char in value)
            if not valid:
                status = "invalid-contract"
        result[name] = status
    if capability == "nlsc":
        from services.production_config import nlsc_gateway_configuration_status
        if nlsc_gateway_configuration_status(environ, production_like=True) == "configured":
            result = {name: "present" for name in REQUIREMENTS[capability]}
        else:
            for name in REQUIREMENTS[capability]:
                if str(environ.get(name, "")).strip():
                    result[name] = "invalid-contract"
    return result
