"""Strict address accuracy benchmark v2 — NO oracle leakage.

Key rules:
- NEVER use expected_* fields to construct provider query
- Input is sent exactly as-is (road_section cases with no city = bare input)
- Scoring uses expected_* ONLY for post-resolution verification
- UNVERIFIABLE_ACCEPTED: provider accepted but component cannot be verified
- Section must be exact (四段 ≠ 三段)
- House number must match for full_address cases
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

def norm(text: str) -> str:
    """Normalize: NFKC, 台→臺, strip."""
    return unicodedata.normalize("NFKC", str(text or "")).replace("台", "臺").strip()


_SECTION_RE = re.compile(r"(.*?(?:大道|路|街))((?:一|二|三|四|五|六|七|八|九|十)段)")
_HOUSE_RE = re.compile(r"(\d+)號")
_ROAD_RE = re.compile(r"([^\s縣市區鄉鎮]{1,16}(?:大道|路|街)(?:(?:一|二|三|四|五|六|七|八|九|十)段)?)")


def parse_road_and_section(road: str) -> tuple[str, str, str]:
    """Returns (full_road_with_section, base_road, section)."""
    n = norm(road)
    m = _SECTION_RE.match(n)
    if m:
        return n, m.group(1), m.group(2)
    return n, n, ""


def extract_house(text: str) -> str:
    m = _HOUSE_RE.search(str(text or ""))
    return m.group(1) if m else ""


def extract_road_from_text(text: str) -> str:
    """Extract road+section from formatted address text."""
    n = norm(text)
    m = _ROAD_RE.search(n)
    return m.group(1) if m else ""


# ─── Strict Classification ──────────────────────────────────────────────────

def strict_classify(case: dict, acceptance: dict | None, found: dict | None) -> tuple[str, str]:
    """
    Returns (classification, reason).
    Classifications: EXACT_CORRECT, SAFE_REFUSAL, WRONG_ACCEPTED, UNVERIFIABLE_ACCEPTED
    """
    # Not accepted → safe refusal
    if not acceptance or not acceptance.get("accepted_for_analysis"):
        quality = acceptance.get("match_quality", "NO_RESULT") if acceptance else "NO_RESULT"
        return "SAFE_REFUSAL", quality

    # Accepted by product. Now verify every expected component strictly.
    resolved_addr = norm(acceptance.get("normalized_address", ""))
    resolved_city = norm(found.get("city", "") if found else "")
    resolved_district = norm(found.get("district", "") if found else "")
    resolved_road_raw = norm(found.get("road", "") if found else "")
    # Also try to extract road from formatted address
    resolved_road_from_addr = extract_road_from_text(resolved_addr)
    resolved_road = resolved_road_raw or resolved_road_from_addr

    expected_city = norm(case.get("expected_city", ""))
    expected_district = norm(case.get("expected_district", ""))
    expected_road = norm(case.get("expected_road", ""))

    failures = []
    unverifiable = []

    # CITY — only verify if INPUT contains city
    input_text = norm(case.get("input", ""))
    if expected_city and expected_city in input_text:
        if resolved_city:
            if expected_city != resolved_city:
                failures.append(f"city:{expected_city}!={resolved_city}")
        else:
            # Try to find city in formatted address
            if expected_city in resolved_addr:
                pass  # Verifiable from address text
            else:
                unverifiable.append(f"city_unverifiable")

    # DISTRICT — only verify if INPUT contains district
    if expected_district and expected_district in input_text:
        if resolved_district:
            if expected_district != resolved_district:
                failures.append(f"district:{expected_district}!={resolved_district}")
        else:
            if expected_district in resolved_addr:
                pass
            else:
                unverifiable.append(f"district_unverifiable")

    # ROAD + SECTION
    if expected_road:
        exp_full, exp_base, exp_section = parse_road_and_section(expected_road)
        res_full, res_base, res_section = parse_road_and_section(resolved_road)

        if res_base:
            # Road base comparison
            if exp_base != res_base:
                failures.append(f"road:{exp_base}!={res_base}")
            else:
                # Section comparison
                if exp_section:
                    if res_section:
                        if exp_section != res_section:
                            failures.append(f"section:{exp_section}!={res_section}")
                    else:
                        # Expected section but resolved has none → NOT exact
                        # Check if section appears in formatted address
                        if exp_full in resolved_addr:
                            pass  # Found in formatted address
                        else:
                            unverifiable.append(f"section_missing:{exp_section}")
        else:
            # No road extracted from resolution
            if exp_full in resolved_addr or exp_base in resolved_addr:
                pass
            else:
                unverifiable.append(f"road_unverifiable:{expected_road}")

    # HOUSE NUMBER (for full_address cases)
    input_house = extract_house(case.get("input", ""))
    if input_house:
        resolved_house = extract_house(resolved_addr)
        if resolved_house:
            if input_house != resolved_house:
                failures.append(f"house:{input_house}!={resolved_house}")
        else:
            # Provider returned road-level but input had house number
            # This is UNVERIFIABLE for building-level exactness
            unverifiable.append(f"house_unverifiable:{input_house}")

    if failures:
        return "WRONG_ACCEPTED", "; ".join(failures)
    if unverifiable:
        return "UNVERIFIABLE_ACCEPTED", "; ".join(unverifiable)
    return "EXACT_CORRECT", ""


# ─── Main ───────────────────────────────────────────────────────────────────

def run_benchmark():
    benchmark_path = os.path.join(os.path.dirname(__file__), "..", "frontend_next", "e2e", "address-accuracy-benchmark.frozen.json")
    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark = json.load(f)

    valid_cases = benchmark["valid_cases"]
    adversarial_cases = benchmark["adversarial_cases"]

    print("=" * 100)
    print("STRICT ADDRESS BENCHMARK v2 — NO ORACLE LEAKAGE")
    print("=" * 100)

    rows = []
    for case in valid_cases:
        # B: NO ORACLE LEAKAGE — send input exactly as-is
        query = case["input"]
        time.sleep(0.3)

        try:
            found = search_location(query)
            acceptance = found.get("geocoding_acceptance")
            classification, reason = strict_classify(case, acceptance, found)

            rows.append({
                "id": case["id"],
                "input": query,
                "category": case.get("category", ""),
                "resolved_address": acceptance.get("normalized_address", "") if acceptance else "",
                "resolved_city": found.get("city", ""),
                "resolved_district": found.get("district", ""),
                "resolved_road": found.get("road", ""),
                "source": found.get("source", ""),
                "match_quality": acceptance.get("match_quality", "") if acceptance else "NO_RESULT",
                "accepted": acceptance.get("accepted_for_analysis", False) if acceptance else False,
                "classification": classification,
                "reason": reason,
            })
        except Exception as e:
            rows.append({
                "id": case["id"],
                "input": query,
                "category": case.get("category", ""),
                "resolved_address": "",
                "resolved_city": "",
                "resolved_district": "",
                "resolved_road": "",
                "source": "error",
                "match_quality": "ERROR",
                "accepted": False,
                "classification": "SAFE_REFUSAL",
                "reason": str(e)[:60],
            })

    # Print per-case table
    print(f"\n{'ID':<5} {'CAT':<14} {'CLASS':<22} {'SRC':<10} {'QUALITY':<14} {'REASON'}")
    print("-" * 100)
    for r in rows:
        sym = {"EXACT_CORRECT": "+", "SAFE_REFUSAL": ".", "WRONG_ACCEPTED": "X", "UNVERIFIABLE_ACCEPTED": "?"}[r["classification"]]
        print(f"{sym}{r['id']:<4} {r['category']:<14} {r['classification']:<22} {r['source']:<10} {r['match_quality']:<14} {r['reason'][:50]}")

    # Compute stats
    full_addr = [r for r in rows if r["category"] == "full_address"]
    road_sect = [r for r in rows if r["category"] == "road_section"]

    total = len(rows)
    exact = sum(1 for r in rows if r["classification"] == "EXACT_CORRECT")
    safe = sum(1 for r in rows if r["classification"] == "SAFE_REFUSAL")
    wrong = sum(1 for r in rows if r["classification"] == "WRONG_ACCEPTED")
    unverifiable = sum(1 for r in rows if r["classification"] == "UNVERIFIABLE_ACCEPTED")

    fa_total = len(full_addr)
    fa_exact = sum(1 for r in full_addr if r["classification"] == "EXACT_CORRECT")
    fa_safe = sum(1 for r in full_addr if r["classification"] == "SAFE_REFUSAL")
    rs_total = len(road_sect)
    rs_exact = sum(1 for r in road_sect if r["classification"] == "EXACT_CORRECT")
    rs_safe = sum(1 for r in road_sect if r["classification"] == "SAFE_REFUSAL")

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
    print(f"\n{'='*100}")
    print(f"FULL_ADDRESS_TOTAL       = {fa_total}")
    print(f"FULL_ADDRESS_EXACT       = {fa_exact}")
    print(f"FULL_ADDRESS_SAFE_REFUSAL= {fa_safe}")
    print(f"FULL_ADDRESS_ACCURACY    = {fa_exact/fa_total:.1%}" if fa_total else "N/A")
    print(f"ROAD_SECTION_TOTAL       = {rs_total}")
    print(f"ROAD_SECTION_EXACT       = {rs_exact}")
    print(f"ROAD_SECTION_SAFE_REFUSAL= {rs_safe}")
    print(f"VALID_TOTAL              = {total}")
    print(f"EXACT_CORRECT            = {exact}")
    print(f"SAFE_REFUSAL             = {safe}")
    print(f"WRONG_ACCEPTED           = {wrong}")
    print(f"UNVERIFIABLE_ACCEPTED    = {unverifiable}")
    print(f"OVERALL_ACCURACY         = {exact/total:.1%}" if total else "N/A")
    print(f"SAFETY_REJECTED          = {adv_rejected}/10")
    print(f"\nSAFE_REFUSAL_CASES:")
    for r in rows:
        if r["classification"] == "SAFE_REFUSAL":
            print(f"  {r['id']} | {r['match_quality']} | {r['reason'][:60]}")
    print(f"\nUNVERIFIABLE_CASES:")
    for r in rows:
        if r["classification"] == "UNVERIFIABLE_ACCEPTED":
            print(f"  {r['id']} | {r['reason']}")

    gate_pass = exact/total >= 0.80 and fa_exact/fa_total >= 0.90 and wrong == 0 and unverifiable == 0 and adv_rejected == 10
    gate = "PASS" if gate_pass else "FAIL"
    print(f"\nGATE = {gate}")
    print(f"{'='*100}")

    print(f"\n[RESULT] total={total} exact={exact} safe={safe} wrong={wrong} unverifiable={unverifiable} accuracy={exact/total:.3f} fa_total={fa_total} fa_exact={fa_exact} fa_accuracy={fa_exact/fa_total:.3f} rs_total={rs_total} rs_exact={rs_exact} safety={adv_rejected}/10 gate={gate}")


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    run_benchmark()
