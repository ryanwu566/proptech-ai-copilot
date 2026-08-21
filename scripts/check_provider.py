"""Check geocoding provider availability for benchmark."""
import os
import sys
sys.path.insert(0, ".")

key = os.getenv("GOOGLE_MAPS_API_KEY", "")
print(f"GOOGLE_MAPS_API_KEY configured: {bool(key)}")
print(f"Key length: {len(key)}")

# Check if the adapter reports as available
from services.adapters.geocoding_adapter import GoogleGeocodingAdapter
adapter = GoogleGeocodingAdapter()
print(f"GoogleGeocodingAdapter.available: {adapter.available}")

# Check TGOS
tgos_key = os.getenv("TGOS_API_KEY", "")
print(f"TGOS_API_KEY configured: {bool(tgos_key)}")
