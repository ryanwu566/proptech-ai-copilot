import os, sys
sys.path.insert(0, ".")
print("TGOS_APP_ID configured:", bool(os.getenv("TGOS_APP_ID", "")))
print("TGOS_API_KEY configured:", bool(os.getenv("TGOS_API_KEY", "")))
from services.adapters.tgos_geocoding_adapter import TgosGeocodingAdapter
t = TgosGeocodingAdapter()
print("TGOS available:", t.available)
if t.available:
    result = t.search("臺北市中正區中山南路7號", [])
    print("V08 test:", "resolved" if result else f"failed: {t.last_error}")
