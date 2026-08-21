import sys
sys.path.insert(0, ".")
from services.map_service import search_location
r = search_location("臺北市大安區忠孝東路四段45號")
print(f"matched={r['matched']} source={r['source']} road={r['road'][:20]}")
if r.get("geocoding_acceptance"):
    print(f"accepted={r['geocoding_acceptance']['accepted_for_analysis']}")
