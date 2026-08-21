"""Real-provider backend API certification — 15 cases through /location/insight.
Calls the same endpoint the browser calls. Records exact structured results.
"""
import sys, time, json, re, unicodedata
sys.path.insert(0, ".")
import httpx

API = "http://127.0.0.1:8000"

CASES = [
    {"id": "V01", "input": "臺北市大安區忠孝東路四段45號", "exp_city": "臺北市", "exp_district": "大安區", "exp_road": "忠孝東路四段", "exp_house": "45"},
    {"id": "V03", "input": "臺北市中山區南京東路三段12號", "exp_city": "臺北市", "exp_district": "中山區", "exp_road": "南京東路三段", "exp_house": "12"},
    {"id": "V05", "input": "臺北市松山區民生東路五段88號", "exp_city": "臺北市", "exp_district": "松山區", "exp_road": "民生東路五段", "exp_house": "88"},
    {"id": "V07", "input": "臺北市中山區中山北路二段65號", "exp_city": "臺北市", "exp_district": "中山區", "exp_road": "中山北路二段", "exp_house": "65"},
    {"id": "V11", "input": "臺北市信義區信義路五段7號", "exp_city": "臺北市", "exp_district": "信義區", "exp_road": "信義路五段", "exp_house": "7"},
    {"id": "V13", "input": "新北市板橋區文化路一段266號", "exp_city": "新北市", "exp_district": "板橋區", "exp_road": "文化路一段", "exp_house": "266"},
    {"id": "V14", "input": "新北市中和區中和路390號", "exp_city": "新北市", "exp_district": "中和區", "exp_road": "中和路", "exp_house": "390"},
    {"id": "V17", "input": "桃園市桃園區中正路77號", "exp_city": "桃園市", "exp_district": "桃園區", "exp_road": "中正路", "exp_house": "77"},
    {"id": "V19", "input": "臺中市西屯區臺灣大道三段99號", "exp_city": "臺中市", "exp_district": "西屯區", "exp_road": "臺灣大道三段", "exp_house": "99"},
    {"id": "V20", "input": "臺中市北區三民路三段129號", "exp_city": "臺中市", "exp_district": "北區", "exp_road": "三民路三段", "exp_house": "129"},
    {"id": "V22", "input": "臺南市中西區中山路1號", "exp_city": "臺南市", "exp_district": "中西區", "exp_road": "中山路", "exp_house": "1"},
    {"id": "V24", "input": "高雄市前鎮區中山二路260號", "exp_city": "高雄市", "exp_district": "前鎮區", "exp_road": "中山二路", "exp_house": "260"},
    {"id": "V27", "input": "新竹市東區光復路二段101號", "exp_city": "新竹市", "exp_district": "東區", "exp_road": "光復路二段", "exp_house": "101"},
    {"id": "V28", "input": "基隆市中正區信一路181號", "exp_city": "基隆市", "exp_district": "中正區", "exp_road": "信一路", "exp_house": "181"},
    {"id": "V29", "input": "花蓮縣花蓮市中山路230號", "exp_city": "花蓮縣", "exp_district": "花蓮市", "exp_road": "中山路", "exp_house": "230"},
]

def norm(t):
    return unicodedata.normalize("NFKC", str(t or "")).replace("台", "臺").strip()

def classify(case, result):
    """Classify using actual backend response fields."""
    acc = result.get("geocoding_acceptance")
    if not acc:
        return "ERROR", "no_acceptance_field"
    if not acc.get("accepted_for_analysis"):
        return "SAFE_REFUSAL", acc.get("match_quality", "UNKNOWN")

    # Product accepted — verify identity components
    resolved = result.get("resolved_location") or {}
    addr_label = norm(resolved.get("address_label", ""))
    resolved_addr = norm(acc.get("normalized_address", ""))

    failures = []
    # We trust the product's acceptance gate. If it accepted, verify expected components are present.
    exp_road = norm(case["exp_road"])
    if exp_road and exp_road not in resolved_addr and exp_road not in addr_label:
        # Check road base without section
        road_base = re.sub(r"(一|二|三|四|五|六|七|八|九|十)段$", "", exp_road)
        if road_base not in resolved_addr and road_base not in addr_label:
            failures.append(f"road_missing:{exp_road}")

    exp_house = case.get("exp_house", "")
    if exp_house:
        if f"{exp_house}號" not in resolved_addr and f"No. {exp_house}" not in resolved_addr and f"No.{exp_house}" not in resolved_addr:
            # Check if house number exists with alternate formatting
            if exp_house + "号" not in resolved_addr:
                failures.append(f"house_unverified:{exp_house}")

    if failures:
        return "WRONG_ACCEPTED", "; ".join(failures)
    return "EXACT", ""

print("=" * 80)
print("REAL-PROVIDER API CERTIFICATION — 15 cases via /location/insight")
print("=" * 80)

results = []
for case in CASES:
    time.sleep(0.5)  # Human pacing
    body = {"address": case["input"], "city": case["exp_city"], "district": case["exp_district"],
            "road": "", "radius_m": 800}
    try:
        r = httpx.post(f"{API}/location/insight", json=body, timeout=15)
        data = r.json()
        acc = data.get("geocoding_acceptance") or {}
        resolved = data.get("resolved_location") or {}
        classification, reason = classify(case, data)
        results.append({
            "id": case["id"],
            "input": case["input"],
            "resolved_addr": norm(acc.get("normalized_address", "")),
            "match_quality": acc.get("match_quality", "N/A"),
            "accepted": acc.get("accepted_for_analysis", False),
            "classification": classification,
            "reason": reason,
        })
        sym = {"EXACT": "+", "SAFE_REFUSAL": ".", "WRONG_ACCEPTED": "X", "ERROR": "!"}[classification]
        print(f"  {sym} {case['id']} | {classification:<14} | {acc.get('match_quality','N/A'):<20} | {case['input'][:25]}")
    except Exception as e:
        results.append({"id": case["id"], "input": case["input"], "classification": "ERROR", "reason": str(e)[:40]})
        print(f"  ! {case['id']} | ERROR          | {str(e)[:40]}")

# Summary
total = len(results)
exact = sum(1 for r in results if r["classification"] == "EXACT")
safe = sum(1 for r in results if r["classification"] == "SAFE_REFUSAL")
wrong = sum(1 for r in results if r["classification"] == "WRONG_ACCEPTED")
errors = sum(1 for r in results if r["classification"] == "ERROR")

print(f"\n{'='*80}")
print(f"REAL_UI_TOTAL            = {total}")
print(f"REAL_UI_EXACT            = {exact}")
print(f"REAL_UI_SAFE_REFUSAL     = {safe}")
print(f"REAL_UI_WRONG_ACCEPTED   = {wrong}")
print(f"REAL_UI_ERRORS           = {errors}")
print(f"REAL_UI_IDENTITY_ACCURACY= {exact/total:.1%}")
print(f"{'='*80}")
print(f"\n[REAL_UI_RESULT] total={total} exact={exact} safe={safe} wrong={wrong} errors={errors} accuracy={exact/total:.3f}")
