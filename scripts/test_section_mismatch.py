"""Test section mismatch detection."""
import sys
sys.path.insert(0, ".")
from services.geocoding_acceptance import evaluate_geocoding_acceptance

# 四段 resolved as 三段 — should REJECT
r = evaluate_geocoding_acceptance(
    "臺北市大安區忠孝東路四段45號",
    {"city": "臺北市", "district": "大安區", "road": "忠孝東路三段",
     "center": {"lat": 25.04, "lng": 121.55},
     "formatted_address": "臺北市大安區忠孝東路三段45號"},
    "google"
)
print(f"section 4→3: quality={r['match_quality']} accepted={r['accepted_for_analysis']} reasons={r['mismatch_reasons']}")
assert not r["accepted_for_analysis"], "Should reject section mismatch"

# 四段 resolved as 四段 — should ACCEPT
r2 = evaluate_geocoding_acceptance(
    "臺北市大安區忠孝東路四段45號",
    {"city": "臺北市", "district": "大安區", "road": "忠孝東路四段",
     "center": {"lat": 25.04, "lng": 121.55},
     "formatted_address": "臺北市大安區忠孝東路四段45號"},
    "google"
)
print(f"section 4→4: quality={r2['match_quality']} accepted={r2['accepted_for_analysis']} reasons={r2['mismatch_reasons']}")
assert r2["accepted_for_analysis"], "Should accept matching section"

print("\nSection identity guard: PASS")
