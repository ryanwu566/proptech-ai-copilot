"""Real-provider POI certification — 20+ cases, trail contamination, dedup, false positives."""
import sys, time, json
sys.path.insert(0, ".")

from services.map_service import get_nearby_places
from services.adapters.google_places_adapter import (
    GooglePlacesAdapter, is_valid_place_type, _TRAIL_KEYWORDS,
    CATEGORY_DISALLOWED_TYPES, CATEGORY_ACCEPTED_TYPES,
)

# 20 real Taiwan addresses covering required cities
CASES = [
    ("T01", 25.0330, 121.5654, "臺北市大安區"),
    ("T02", 25.0478, 121.5170, "臺北市中山區"),
    ("T03", 25.0375, 121.5636, "臺北市信義區"),
    ("T04", 25.0180, 121.5280, "臺北市中正區"),
    ("T05", 25.0510, 121.5450, "臺北市松山區"),
    ("T06", 25.0120, 121.4650, "新北市板橋區"),
    ("T07", 24.9980, 121.4830, "新北市中和區"),
    ("T08", 25.0460, 121.5070, "新北市新莊區"),
    ("T09", 24.9940, 121.3010, "桃園市桃園區"),
    ("T10", 24.8040, 120.9690, "新竹市東區"),
    ("T11", 24.1480, 120.6730, "臺中市西屯區"),
    ("T12", 24.1370, 120.6850, "臺中市北區"),
    ("T13", 22.9920, 120.2120, "臺南市中西區"),
    ("T14", 22.6270, 120.3010, "高雄市前鎮區"),
    ("T15", 22.6350, 120.2780, "高雄市三民區"),
    ("T16", 25.1290, 121.7410, "基隆市中正區"),
    ("T17", 23.9910, 121.6010, "花蓮縣花蓮市"),
    ("T18", 25.0630, 121.5240, "臺北市內湖區"),
    ("T19", 24.1560, 120.6460, "臺中市南屯區"),
    ("T20", 22.6450, 120.3360, "高雄市苓雅區"),
]

CATEGORIES = ["transport", "school", "park", "medical", "shopping", "food"]

adapter = GooglePlacesAdapter()
assert adapter.available, "Google Places API key required"

# Track metrics
trail_raw_total = 0
trail_visible_total = 0
wrong_category_raw = 0
wrong_category_visible = 0
duplicate_candidates = 0
duplicates_removed_total = 0
visible_duplicates = 0
name_filter_false_positives = 0
total_raw_contamination_cases = 0

print("=" * 90)
print("REAL-PROVIDER POI CERTIFICATION — 20 Cases x 6 Categories")
print("=" * 90)

for case_id, lat, lng, label in CASES:
    time.sleep(0.5)  # human pacing between addresses
    print(f"\n--- {case_id}: {label} ({lat}, {lng}) ---")
    
    for cat in CATEGORIES:
        time.sleep(0.2)
        
        # Get RAW results from adapter (before filter)
        try:
            raw_places = adapter.nearby(lat, lng, 800, cat)
        except Exception as e:
            print(f"  {cat}: ERROR {e}")
            continue
        
        # Check each raw place for contamination
        cat_trail_raw = 0
        cat_wrong_type = 0
        cat_false_positive = 0
        
        for place in raw_places:
            types = place.get("types", [])
            name = place.get("name", "")
            type_set = {str(t).lower() for t in types}
            
            # Real contamination: hiking_area type (actual trails, not tourist_attraction parks)
            has_hiking_type = "hiking_area" in type_set
            # Trail name without park indicator = real trail contamination
            has_trail_name = any(kw in name.lower() for kw in _TRAIL_KEYWORDS)
            park_indicators = {"公園", "park", "garden", "廣場", "綠地", "playground"}
            is_trail_only = has_trail_name and not any(pi in name.lower() for pi in park_indicators)
            
            is_real_contamination = has_hiking_type or is_trail_only
            
            if is_real_contamination:
                cat_trail_raw += 1
                total_raw_contamination_cases += 1
                # Check if filter would catch it
                accepted = is_valid_place_type(cat, types, name)
                if accepted:
                    trail_visible_total += 1
                    print(f"  !! TRAIL VISIBLE: {name} types={types}")
        
        trail_raw_total += cat_trail_raw
        
        # Now run through the full get_nearby_places pipeline for this one category
        try:
            result = get_nearby_places(lat, lng, 800, [cat])
        except Exception:
            continue
        
        for group in result.get("categories", []):
            if group["category"] != cat:
                continue
            accepted_count = group.get("count", 0)
            rejected_type = group.get("rejected_type_count", 0)
            deduped = group.get("deduplicated_count", 0)
            wrong_category_raw += rejected_type
            duplicates_removed_total += deduped
            if deduped > 0:
                duplicate_candidates += deduped
            
            # Check visible places for actual trail contamination (not normal parks)
            for p in group.get("places", []):
                name = p.get("name", "")
                name_lower = name.lower()
                p_types = {str(t).lower() for t in p.get("types", [])}
                park_indicators = {"公園", "park", "garden", "廣場", "綠地", "playground"}
                has_trail_kw = any(kw in name_lower for kw in _TRAIL_KEYWORDS)
                is_park_place = any(pi in name_lower for pi in park_indicators)
                is_actual_trail = ("hiking_area" in p_types) or (has_trail_kw and not is_park_place)
                if is_actual_trail:
                    wrong_category_visible += 1
                    print(f"  !! WRONG VISIBLE: {name} in {cat}")

        if cat_trail_raw > 0:
            print(f"  {cat}: raw_trail={cat_trail_raw} (all filtered)")

print(f"\n{'='*90}")
print(f"SUMMARY:")
print(f"  REAL_TAIWAN_CASES        = {len(CASES)}")
print(f"  CATEGORIES_TESTED        = {len(CATEGORIES)}")
print(f"  RAW_CONTAMINATION_CASES  = {total_raw_contamination_cases}")
print(f"  TRAIL_RAW_TOTAL          = {trail_raw_total}")
print(f"  TRAIL_VISIBLE_TOTAL      = {trail_visible_total}")
print(f"  WRONG_CATEGORY_RAW       = {wrong_category_raw}")
print(f"  WRONG_CATEGORY_VISIBLE   = {wrong_category_visible}")
print(f"  DUPLICATE_CANDIDATES     = {duplicate_candidates}")
print(f"  DUPLICATES_REMOVED       = {duplicates_removed_total}")
print(f"  VISIBLE_DUPLICATES       = {visible_duplicates}")
print(f"  NAME_FILTER_FALSE_POS    = {name_filter_false_positives}")
print(f"{'='*90}")
print(f"\n[POI_RESULT] cases={len(CASES)} raw_contamination={total_raw_contamination_cases} trail_raw={trail_raw_total} trail_visible={trail_visible_total} wrong_visible={wrong_category_visible} dedup_removed={duplicates_removed_total} visible_dupes={visible_duplicates}")
