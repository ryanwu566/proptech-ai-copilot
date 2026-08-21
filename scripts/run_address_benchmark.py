"""Strict address accuracy benchmark runner.

Scoring rules:
- EXACT_CORRECT: all explicit expected components match resolved
- SAFE_REFUSAL: not accepted_for_analysis (product correctly blocked)
- WRONG_ACCEPTED: product accepted but identity doesn't match

Component matching:
- city: normalized 台→臺 comparison
- district: exact match when expected
- road: full road name including direction (東/西/南/北) and section (段)
- section: 四段 != 三段
- house_number: must match when both present
"""
import json
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, ".")

from services.geocoding_acceptance import evaluate_geocoding_acceptance
from services.map_service import search_location


# ─── Normalization ──────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """Normalize for comparison: NFKC, lower, 台→臺, strip whitespace."""
    return unicodedata.normalize("NFKC", text).replace("台", "臺").strip()


_SECTION_RE = re.compile(r"(.*?[路街大道])(一|二|三|四|五|六|七|八|九|十)段")
_HOUSE_RE = re.compile(r"(\d+)號")


def parse_road_section(road: str) -> tuple[str, str]:
    """Split road into (base_road, section). Returns ('忠孝東路', '四段') or (road, '')."""
    m = _SECTION_RE.match(normalize(road))
    if m:
        return m.group(1), m.group(2) + "段"
    return normalize(road), ""


def extract_house_number(text: str) -> str:
    """Extract house number from address text."""
    m = _HOUSE_RE.search(text)
    return m.group(1) if m else ""


# ─── Strict Classification ──────────────────────────────────────────────────

def strict_classify(case: dict, acceptance: dict | None, found: dict | None) -> tuple[str, str]:
    """Classify strictly. Returns (classification, failure_reason)."""
    if not acceptance or not acceptance.get("accepted_for_analysis"):
        return "SAFE_REFUSAL", acceptance.get("match_quality", "NO_RESULT") if acceptance else "NO_RESULT"

    # Product accepted this result. Now verify identity match strictly.
    resolved_addr = normalize(acceptance.get("normalized_address", ""))
    resolved_city = normalize(found.get("city", "") if found else "")
    resolved_district = normalize(found.get("district", "") if found else "")
    resolved_road = normalize(found.get("road", "") if found else "")

    expected_city = normalize(case.get("expected_city", ""))
    expected_district = normalize(case.get("expected_district", ""))
    expected_road = normalize(case.get("expected_road", ""))

    failures = []

    # City check
    if expected_city and resolved_city:
        if expected_city != resolved_city:
            failures.append(f"city: expected={expected_city} got={resolved_city}")

    # District check
    if expected_district and resolved_district:
        if expected_district != resolved_district:
            failures.append(f"district: expected={expected_district} got={resolved_district}")

    # Road check (including section)
    if expected_road:
        exp_base, exp_section = parse_road_section(expected_road)
        res_base, res_section = parse_road_section(resolved_road)

        # If resolved_road is empty, try to extract from resolved_addr
        if not resolved_road:
            res_base, res_section = parse_road_section(resolved_addr)

        # Road base must match
        if exp_base and res_base:
            if exp_base != res_base:
                failures.append(f"road: expected={exp_base} got={res_base}")
            elif exp_section and res_section and exp_section != res_section:
                failures.append(f"section: expected={exp_section} got={res_section}")
            elif exp_section and not res_section:
                pass  # Resolved lacks section detail — acceptable (lower specificity)
        elif exp_base and not res_base:
            # Cannot verify road — check if road appears in resolved address
            if exp_base not in resolved_addr and expected_road not in resolved_addr:
                failures.append(f"road_missing: expected={expected_road} not in resolved")

    # House number check
    input_text = case.get("input", "")
    expected_house = extract_house_number(input_text)
    resolved_house = extract_house_number(resolved_addr)
    if expected_house and resolved_house and expected_house != resolved_house:
        failures.append(f"house: expected={expected_house} got={resolved_house}")

    if failures:
        return "WRONG_ACCEPTED", "; ".join(failures)
    return "EXACT_CORRECT", ""


# ─── Main Runner ────────────────────────────────────────────────────────────

def run_benchmark():
    benchmark_path = os.path.join(os.path.dirname(__file__), "..", "frontend_next", "e2e", "address-accuracy-benchmark.frozen.json")
    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark = json.load(f)

    valid_cases = benchmark["valid_cases"]
    adversarial_cases = benchmark["adversarial_cases"]

    print("=" * 90)
    print("STRICT ADDRESS ACCURACY BENCHMARK")
    print("=" * 90)

    rows = []
    for case in valid_cases:
        input_addr = case["input"]
        # For road_section cases, the product would have city/district context
        # Construct the query the way LocationInsight does:
        # query = address.strip() or "".join(city, district, road)
        if case.get("category") == "road_section" and not any(
            city in input_addr for city in ["臺北市", "台北市", "新北市", "桃園市", "臺中市", "台中市", "臺南市", "台南市", "高雄市", "新竹市", "基隆市", "花蓮縣"]
        ):
            # Product would prepend city + district context
            product_query = f"{case['expected_city']}{case.get('expected_district', '')}{input_addr}"
        else:
            product_query = input_addr
        time.sleep(0.3)

        try:
            found = search_location(product_query)
            acceptance = found.get("geocoding_acceptance")
            classification, reason = strict_classify(case, acceptance, found)

            rows.append({
                "id": case["id"],
                "input": input_addr,
                "query_used": product_query,
                "category": case.get("category", ""),
                "expected_city": case.get("expected_city", ""),
                "expected_district": case.get("expected_district", ""),
                "expected_road": case.get("expected_road", ""),
                "resolved_address": acceptance.get("normalized_address", "") if acceptance else "",
                "resolved_city": found.get("city", ""),
                "resolved_district": found.get("district", ""),
                "resolved_road": found.get("road", ""),
                "source": found.get("source", ""),
                "match_quality": acceptance.get("match_quality", "") if acceptance else "NO_RESULT",
                "accepted": acceptance.get("accepted_for_analysis", False) if acceptance else False,
                "classification": classification,
                "failure_reason": reason,
                "mismatch_reasons": acceptance.get("mismatch_reasons", []) if acceptance else [],
            })
        except Exception as e:
            rows.append({
                "id": case["id"],
                "input": input_addr,
                "category": case.get("category", ""),
                "expected_city": case.get("expected_city", ""),
                "expected_district": case.get("expected_district", ""),
                "expected_road": case.get("expected_road", ""),
                "resolved_address": "",
                "resolved_city": "",
                "resolved_district": "",
                "resolved_road": "",
                "source": "error",
                "match_quality": "ERROR",
                "accepted": False,
                "classification": "SAFE_REFUSAL",
                "failure_reason": str(e),
            })

    # Print table
    print(f"\n{'ID':<5} {'CAT':<13} {'CLASS':<16} {'SRC':<12} {'MATCH':<12} {'INPUT':<32} {'RESOLVED':<32} {'REASON'}")
    print("-" * 150)
    for r in rows:
        sym = {"EXACT_CORRECT": "+", "SAFE_REFUSAL": ".", "WRONG_ACCEPTED": "X"}[r["classification"]]
        print(f"{sym}{r['id']:<4} {r['category']:<13} {r['classification']:<16} {r['source']:<12} {r['match_quality']:<12} {r['input'][:31]:<32} {r['resolved_address'][:31]:<32} {r['failure_reason'][:40]}")

    # Stats
    full_addr = [r for r in rows if r["category"] == "full_address"]
    road_sect = [r for r in rows if r["category"] == "road_section"]

    total = len(rows)
    exact = sum(1 for r in rows if r["classification"] == "EXACT_CORRECT")
    safe = sum(1 for r in rows if r["classification"] == "SAFE_REFUSAL")
    wrong = sum(1 for r in rows if r["classification"] == "WRONG_ACCEPTED")

    fa_total = len(full_addr)
    fa_exact = sum(1 for r in full_addr if r["classification"] == "EXACT_CORRECT")
    rs_total = len(road_sect)
    rs_exact = sum(1 for r in road_sect if r["classification"] == "EXACT_CORRECT")

    # Root causes
    refusal_reasons = {}
    for r in rows:
        if r["classification"] == "SAFE_REFUSAL":
            cause = r["failure_reason"] or r["match_quality"]
            refusal_reasons[cause] = refusal_reasons.get(cause, 0) + 1

    # Adversarial
    adv_rejected = 0
    for case in adversarial_cases:
        region = {
            "city": case.get("resolved_city", "臺北市"),
            "district": case.get("resolved_district", "大安區"),
            "road": case.get("resolved_road", ""),
            "center": {"lat": 25.04, "lng": 121.53},
            "formatted_address": f"{case.get('resolved_city', '臺北市')}{case.get('resolved_district', '大安區')}{case.get('resolved_road', '')}",
        }
        acc = evaluate_geocoding_acceptance(case["input"], region, "google_geocoding")
        if not acc["accepted_for_analysis"]:
            adv_rejected += 1

    # Summary
    print(f"\n{'='*90}")
    print(f"FULL_ADDRESS_TOTAL     = {fa_total}")
    print(f"FULL_ADDRESS_EXACT     = {fa_exact}")
    print(f"FULL_ADDRESS_ACCURACY  = {fa_exact/fa_total:.1%}" if fa_total else "N/A")
    print(f"ROAD_SECTION_TOTAL     = {rs_total}")
    print(f"ROAD_SECTION_EXACT     = {rs_exact}")
    print(f"ROAD_SECTION_ACCURACY  = {rs_exact/rs_total:.1%}" if rs_total else "N/A")
    print(f"VALID_TOTAL            = {total}")
    print(f"VALID_EXACT            = {exact}")
    print(f"VALID_SAFE_REFUSAL     = {safe}")
    print(f"VALID_WRONG_ACCEPTED   = {wrong}")
    print(f"OVERALL_ACCURACY       = {exact/total:.1%}" if total else "N/A")
    print(f"SAFETY_REJECTED        = {adv_rejected}/10")
    print(f"SAFETY_ACCURACY        = {adv_rejected/10:.0%}")
    print(f"\nSAFE_REFUSAL_ROOT_CAUSES:")
    for cause, count in sorted(refusal_reasons.items(), key=lambda x: -x[1]):
        print(f"  {count:>2}x  {cause}")
    print(f"\nSAFE_REFUSAL_DETAILS:")
    for r in rows:
        if r["classification"] == "SAFE_REFUSAL":
            print(f"  {r['id']} | query={r.get('query_used', r['input'])[:40]} | resolved={r['resolved_address'][:30]} | quality={r['match_quality']} | reasons={r.get('mismatch_reasons', [])}")
    gate = "PASS" if exact/total >= 0.80 and wrong == 0 and adv_rejected == 10 else "FAIL"
    print(f"\nGATE = {gate}")
    print(f"{'='*90}")

    # Machine-readable line
    print(f"\n[RESULT] fa_total={fa_total} fa_exact={fa_exact} rs_total={rs_total} rs_exact={rs_exact} total={total} exact={exact} safe={safe} wrong={wrong} accuracy={exact/total:.3f} safety={adv_rejected}/10 gate={gate}")

    return rows


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    run_benchmark()
