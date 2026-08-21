"""RAW Google Places capture — targeted hillside/trail cases.
Captures HTTP response BEFORE product filtering to prove real contamination evidence.
"""
import sys, time, os, math
sys.path.insert(0, ".")
import httpx

KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
assert KEY, "GOOGLE_MAPS_API_KEY required"

PLACES_URL = "https://places.googleapis.com/v1/places:searchNearby"
FIELD_MASK = "places.id,places.displayName,places.types,places.location,places.formattedAddress"

# Targeted hillside / mountain-adjacent Taiwan coordinates
# where hiking_area / trail results are more likely
TARGETED_CASES = [
    ("H01", 25.0190, 121.5870, "臺北市信義區虎山"),       # 虎山步道 area
    ("H02", 25.0840, 121.5590, "臺北市士林區陽明山"),     # 陽明山 trails
    ("H03", 25.0280, 121.6150, "臺北市南港區"),           # near 南港山
    ("H04", 24.9560, 121.5380, "新北市新店區碧潭"),       # hiking area
    ("H05", 25.1350, 121.5050, "新北市北投區"),           # near 陽明山/北投
    ("H06", 24.7860, 121.0070, "新竹縣尖石鄉"),          # mountain area
    ("H07", 24.1700, 120.7100, "臺中市北屯區大坑"),       # 大坑步道 area
    ("H08", 22.6500, 120.3800, "高雄市鼓山區壽山"),       # 壽山步道
]

from services.adapters.google_places_adapter import (
    is_valid_place_type, _TRAIL_KEYWORDS, CATEGORY_TYPES
)

raw_contamination_results = []
name_filter_rejections = []
false_positives = []

print("=" * 90)
print("RAW GOOGLE PLACES CAPTURE — TARGETED TRAIL/HILLSIDE CASES")
print("=" * 90)

client = httpx.Client(timeout=8)

for case_id, lat, lng, label in TARGETED_CASES:
    print(f"\n--- {case_id}: {label} ({lat}, {lng}) ---")
    time.sleep(0.5)

    # Query park category (most likely to see trails)
    payload = {
        "includedTypes": CATEGORY_TYPES["park"],
        "maxResultCount": 10,
        "languageCode": "zh-TW",
        "rankPreference": "DISTANCE",
        "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": 1000.0}},
    }
    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": KEY, "X-Goog-FieldMask": FIELD_MASK}

    try:
        resp = client.post(PLACES_URL, json=payload, headers=headers)
        resp.raise_for_status()
        raw_places = resp.json().get("places", [])
    except Exception as e:
        print(f"  ERROR: {e}")
        continue

    for place in raw_places:
        name = place.get("displayName", {}).get("text", "")
        types = place.get("types", [])
        place_id = place.get("id", "")
        type_set = {str(t).lower() for t in types}

        # Check for real contamination indicators
        has_hiking_type = "hiking_area" in type_set
        has_trail_name = any(kw in name.lower() for kw in _TRAIL_KEYWORDS)
        park_indicators = {"公園", "park", "garden", "廣場", "綠地", "playground"}
        is_trail_only = has_trail_name and not any(pi in name.lower() for pi in park_indicators)

        is_contamination = has_hiking_type or is_trail_only

        # Product filter decision
        product_accepted = is_valid_place_type("park", types, name)
        rejection_reason = ""
        if not product_accepted:
            if has_hiking_type:
                rejection_reason = "hiking_area_type"
            elif is_trail_only:
                rejection_reason = "trail_name_only"
            else:
                rejection_reason = "other"

        if is_contamination:
            raw_contamination_results.append({
                "case": case_id, "name": name, "types": types,
                "is_trail_only": is_trail_only, "has_hiking_type": has_hiking_type,
                "product_accepted": product_accepted, "rejection_reason": rejection_reason,
            })
            sym = "REJECTED" if not product_accepted else "!! ACCEPTED"
            print(f"  {sym}: {name} | types={types[:4]} | hiking={has_hiking_type} trail_name={is_trail_only}")

        # Track name filter rejections for false-positive analysis
        if has_trail_name and not product_accepted:
            is_legit_rejection = is_trail_only or has_hiking_type
            name_filter_rejections.append({
                "name": name, "types": types, "category": "park",
                "reason": rejection_reason, "legitimate": is_legit_rejection,
            })
            if not is_legit_rejection:
                false_positives.append({"name": name, "types": types})

client.close()

print(f"\n{'='*90}")
print(f"RAW CONTAMINATION RESULTS:")
print(f"  TARGETED_CASES_EXECUTED    = {len(TARGETED_CASES)}")
print(f"  RAW_CONTAMINATION_RESULTS  = {len(raw_contamination_results)}")
accepted_contamination = [r for r in raw_contamination_results if r["product_accepted"]]
rejected_contamination = [r for r in raw_contamination_results if not r["product_accepted"]]
print(f"  PRODUCT_REJECTED           = {len(rejected_contamination)}")
print(f"  PRODUCT_ACCEPTED (LEAK)    = {len(accepted_contamination)}")
print(f"\nNAME FILTER ANALYSIS:")
print(f"  NAME_FILTER_REJECTIONS     = {len(name_filter_rejections)}")
print(f"  CONFIRMED_FALSE_POSITIVES  = {len(false_positives)}")
for fp in false_positives:
    print(f"    FALSE_POS: {fp['name']} types={fp['types']}")
print(f"\nTRAIL_VISIBLE_UI = {len(accepted_contamination)}")
print(f"{'='*90}")

print(f"\n[RAW_RESULT] targeted={len(TARGETED_CASES)} contamination={len(raw_contamination_results)} rejected={len(rejected_contamination)} leaked={len(accepted_contamination)} false_pos={len(false_positives)}")
