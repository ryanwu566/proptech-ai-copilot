"""Audit 6 failed full-address cases: capture Google raw structured components."""
import sys, time, json
sys.path.insert(0, ".")
import httpx, os

KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
assert KEY, "GOOGLE_MAPS_API_KEY required"

CASES = [
    ("V09", "臺北市大安區和平東路二段106號"),
    ("V11", "臺北市信義區信義路五段7號"),
    ("V19", "臺中市西屯區臺灣大道三段99號"),
    ("V22", "臺南市中西區中山路1號"),
    ("V24", "高雄市前鎮區中山二路260號"),
    ("V28", "基隆市中正區信一路181號"),
]

from services.geocoding_acceptance import evaluate_geocoding_acceptance

for case_id, query in CASES:
    time.sleep(0.4)
    resp = httpx.get("https://maps.googleapis.com/maps/api/geocode/json",
        params={"address": query, "language": "zh-TW", "region": "tw", "key": KEY}, timeout=8)
    data = resp.json()
    results = data.get("results", [])
    print(f"\n{'='*80}")
    print(f"CASE: {case_id}")
    print(f"INPUT: {query}")
    print(f"RESULT_COUNT: {len(results)}")
    
    for idx, r in enumerate(results[:5]):
        geo = r.get("geometry", {})
        comps = r.get("address_components", [])
        print(f"\n  --- Result [{idx}] ---")
        print(f"  TYPES: {r.get('types', [])}")
        print(f"  FORMATTED: {r.get('formatted_address', '')}")
        print(f"  LOCATION_TYPE: {geo.get('location_type', '')}")
        print(f"  PARTIAL_MATCH: {r.get('partial_match', False)}")
        
        city = district = route = street_number = locality = ""
        sublocalities = []
        for c in comps:
            types = c.get("types", [])
            name = c.get("long_name", "")
            if "administrative_area_level_1" in types: city = name
            if "administrative_area_level_2" in types: district = name
            if "administrative_area_level_3" in types: district = district or name
            if "locality" in types: locality = name
            if "route" in types: route = name
            if "street_number" in types: street_number = name
            if any(t.startswith("sublocality") for t in types): sublocalities.append(name)
        
        print(f"  CITY: {city}")
        print(f"  DISTRICT: {district}")
        print(f"  LOCALITY: {locality}")
        print(f"  SUBLOCALITIES: {sublocalities}")
        print(f"  ROUTE: {route}")
        print(f"  STREET_NUMBER: {street_number}")
        
        # Run acceptance on this candidate
        region = {"city": city, "district": district, "road": route,
                  "center": geo.get("location", {}), "formatted_address": r.get("formatted_address", ""),
                  "geocoding_metadata": {"provider_types": r.get("types", []),
                      "location_type": geo.get("location_type", ""),
                      "partial_match": r.get("partial_match", False),
                      "route": route, "street_number": street_number}}
        acc = evaluate_geocoding_acceptance(query, region, "google_geocoding")
        print(f"  ACCEPTANCE: {acc['match_quality']} accepted={acc['accepted_for_analysis']}")
        print(f"  REASONS: {acc['mismatch_reasons']}")
