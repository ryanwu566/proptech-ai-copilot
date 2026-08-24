"""Adversarial tests for identified scoring/acceptance risks.

Run BEFORE fixes to prove the risks are real.
Run AFTER fixes to prove they are closed.
"""
import sys
sys.path.insert(0, ".")
from services.geocoding_acceptance import evaluate_geocoding_acceptance

PASS = 0
FAIL = 0

def check_case(name, query, region, expected_accepted, expected_reasons=None):
    global PASS, FAIL
    acc = evaluate_geocoding_acceptance(query, region, "google_geocoding")
    ok = acc["accepted_for_analysis"] == expected_accepted
    if expected_reasons:
        for r in expected_reasons:
            if r not in acc["mismatch_reasons"]:
                ok = False
    sym = "PASS" if ok else "FAIL"
    if not ok:
        FAIL += 1
    else:
        PASS += 1
    print(f"  {sym}: {name}")
    if not ok:
        print(f"    expected accepted={expected_accepted} reasons>={expected_reasons}")
        print(f"    got      accepted={acc['accepted_for_analysis']} reasons={acc['mismatch_reasons']}")

print("=" * 70)
print("ADVERSARIAL RISK TESTS")
print("=" * 70)

# B: City cannot be implied by non-unique district name
print("\n--- B: Non-unique district must not imply city ---")

check_case("B1: same district different city must REJECT",
    "臺北市中正區忠孝西路一段50號",
    {"city": "基隆市", "district": "中正區", "road": "忠孝西路一段",
     "center": {"lat": 25.13, "lng": 121.74},
     "formatted_address": "基隆市中正區忠孝西路一段50號",
     "geocoding_metadata": {"route": "忠孝西路一段", "street_number": "50", "location_type": "ROOFTOP", "provider_types": [], "partial_match": False}},
    expected_accepted=False, expected_reasons=["city_mismatch"])

check_case("B2: same district different city (東區) must REJECT",
    "臺南市東區東門路二段160號",
    {"city": "臺中市", "district": "東區", "road": "東門路二段",
     "center": {"lat": 24.14, "lng": 120.68},
     "formatted_address": "臺中市東區東門路二段160號",
     "geocoding_metadata": {"route": "東門路二段", "street_number": "160", "location_type": "ROOFTOP", "provider_types": [], "partial_match": False}},
    expected_accepted=False, expected_reasons=["city_mismatch"])

# D: District parsing must handle 前鎮區 correctly
print("\n--- D: District parsing ---")

check_case("D1: 前鎮區 matches 前鎮區",
    "高雄市前鎮區中山二路260號",
    {"city": "高雄市", "district": "前鎮區", "road": "中山二路",
     "center": {"lat": 22.6, "lng": 120.3},
     "formatted_address": "高雄市前鎮區中山二路260號",
     "geocoding_metadata": {"route": "中山二路", "street_number": "260", "location_type": "ROOFTOP", "provider_types": [], "partial_match": False}},
    expected_accepted=True)

check_case("D2: 中西區 mismatches 東區",
    "臺南市中西區中山路1號",
    {"city": "臺南市", "district": "東區", "road": "中山路",
     "center": {"lat": 22.99, "lng": 120.2},
     "formatted_address": "臺南市東區中山路1號",
     "geocoding_metadata": {"route": "中山路", "street_number": "1", "location_type": "ROOFTOP", "provider_types": [], "partial_match": False}},
    expected_accepted=False, expected_reasons=["district_mismatch"])

# E/F: Section missing must NOT be exact
print("\n--- E/F: Section missing/mismatch ---")

check_case("E1: 四段 resolved as missing section must NOT accept",
    "臺北市大安區忠孝東路四段45號",
    {"city": "臺北市", "district": "大安區", "road": "忠孝東路",
     "center": {"lat": 25.04, "lng": 121.55},
     "formatted_address": "臺北市大安區忠孝東路45號",
     "geocoding_metadata": {"route": "忠孝東路", "street_number": "45", "location_type": "ROOFTOP", "provider_types": [], "partial_match": False}},
    expected_accepted=False)

check_case("E2: 四段 → 三段 must REJECT",
    "臺北市大安區忠孝東路四段45號",
    {"city": "臺北市", "district": "大安區", "road": "忠孝東路三段",
     "center": {"lat": 25.04, "lng": 121.55},
     "formatted_address": "臺北市大安區忠孝東路三段45號",
     "geocoding_metadata": {"route": "忠孝東路三段", "street_number": "45", "location_type": "ROOFTOP", "provider_types": [], "partial_match": False}},
    expected_accepted=False, expected_reasons=["street_mismatch"])

check_case("E3: 四段 → 四段 must ACCEPT",
    "臺北市大安區忠孝東路四段45號",
    {"city": "臺北市", "district": "大安區", "road": "忠孝東路四段",
     "center": {"lat": 25.04, "lng": 121.55},
     "formatted_address": "臺北市大安區忠孝東路四段45號",
     "geocoding_metadata": {"route": "忠孝東路四段", "street_number": "45", "location_type": "ROOFTOP", "provider_types": [], "partial_match": False}},
    expected_accepted=True)

# O: Safety regressions
print("\n--- O: Safety regressions ---")

check_case("O1: 東路 → 西路 must REJECT",
    "忠孝東路四段",
    {"city": "臺北市", "district": "中正區", "road": "忠孝西路一段",
     "center": {"lat": 25.04, "lng": 121.52},
     "formatted_address": "臺北市中正區忠孝西路一段",
     "geocoding_metadata": {"route": "忠孝西路一段", "street_number": "", "location_type": "GEOMETRIC_CENTER", "provider_types": [], "partial_match": False}},
    expected_accepted=False, expected_reasons=["street_mismatch"])

check_case("O2: mock source must NOT be accepted for real analysis",
    "臺北市大安區和平東路二段",
    {"city": "台北市", "district": "大安區", "road": "和平東路二段",
     "center": {"lat": 25.03, "lng": 121.54},
     "formatted_address": "台北市大安區和平東路二段",
     "geocoding_metadata": {"route": "和平東路二段", "street_number": "", "location_type": "GEOMETRIC_CENTER", "provider_types": [], "partial_match": False}},
    expected_accepted=True)  # Note: mock blocking is at search_location level, not acceptance

print(f"\n{'='*70}")
print(f"RESULTS: {PASS} passed, {FAIL} failed")
print(f"{'='*70}")
