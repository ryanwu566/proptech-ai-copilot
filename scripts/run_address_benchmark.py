"""Run frozen address accuracy benchmark against real geocoding providers.

Usage: python scripts/run_address_benchmark.py
"""
import json
import os
import sys
import time

sys.path.insert(0, ".")

from services.geocoding_acceptance import evaluate_geocoding_acceptance
from services.map_service import search_location


def classify_result(case, acceptance):
    """Classify a benchmark result as EXACT_CORRECT, SAFE_REFUSAL, or WRONG_ACCEPTED."""
    if not acceptance:
        return "SAFE_REFUSAL"
    
    if not acceptance.get("accepted_for_analysis"):
        return "SAFE_REFUSAL"
    
    # Check if accepted result matches expected
    resolved_address = acceptance.get("normalized_address", "")
    expected_road = case["expected_road"]
    
    # Normalize for comparison
    resolved_lower = resolved_address.replace("台", "臺").lower()
    expected_road_lower = expected_road.replace("台", "臺").lower()
    
    # Check road identity
    if expected_road_lower in resolved_lower:
        return "EXACT_CORRECT"
    
    # Check if the resolved road contains the expected road name (section-tolerant)
    road_base = expected_road_lower.rstrip("一二三四五六七八九段")
    if road_base and road_base in resolved_lower:
        # Check it's not the opposite direction
        if "東" in expected_road_lower and "西" in resolved_lower and "東" not in resolved_lower:
            return "WRONG_ACCEPTED"
        if "西" in expected_road_lower and "東" in resolved_lower and "西" not in resolved_lower:
            return "WRONG_ACCEPTED"
        if "南" in expected_road_lower and "北" in resolved_lower and "南" not in resolved_lower:
            return "WRONG_ACCEPTED"
        if "北" in expected_road_lower and "南" in resolved_lower and "北" not in resolved_lower:
            return "WRONG_ACCEPTED"
        return "EXACT_CORRECT"
    
    # Road not found in resolved — this is WRONG_ACCEPTED
    return "WRONG_ACCEPTED"


def run_benchmark():
    benchmark_path = os.path.join(os.path.dirname(__file__), "..", "frontend_next", "e2e", "address-accuracy-benchmark.frozen.json")
    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark = json.load(f)
    
    valid_cases = benchmark["valid_cases"]
    adversarial_cases = benchmark["adversarial_cases"]
    
    results = []
    print(f"\n{'='*70}")
    print(f"ADDRESS ACCURACY BENCHMARK — REAL PROVIDER")
    print(f"{'='*70}")
    print(f"Valid cases: {len(valid_cases)}")
    print(f"Adversarial cases: {len(adversarial_cases)}")
    print(f"{'='*70}\n")
    
    # Run valid cases
    print("VALID CASES:")
    print("-" * 70)
    exact_correct = 0
    safe_refusal = 0
    wrong_accepted = 0
    
    for case in valid_cases:
        input_addr = case["input"]
        time.sleep(0.3)  # Rate limiting
        
        try:
            found = search_location(input_addr)
            acceptance = found.get("geocoding_acceptance")
            classification = classify_result(case, acceptance)
            
            resolved = acceptance.get("normalized_address", "") if acceptance else "N/A"
            match_quality = acceptance.get("match_quality", "N/A") if acceptance else "N/A"
            accepted = acceptance.get("accepted_for_analysis", False) if acceptance else False
            source = found.get("source", "unknown")
            
            if classification == "EXACT_CORRECT":
                exact_correct += 1
                status = "✓"
            elif classification == "SAFE_REFUSAL":
                safe_refusal += 1
                status = "◌"
            else:
                wrong_accepted += 1
                status = "✗"
            
            results.append({
                "id": case["id"],
                "input": input_addr,
                "resolved": resolved,
                "source": source,
                "match_quality": match_quality,
                "accepted": accepted,
                "classification": classification,
            })
            
            print(f"  {status} {case['id']} | {classification:15s} | {source:18s} | {input_addr[:30]}")
            if classification == "WRONG_ACCEPTED":
                print(f"    CRITICAL: resolved={resolved}")
        except Exception as e:
            safe_refusal += 1
            results.append({
                "id": case["id"],
                "input": input_addr,
                "resolved": "ERROR",
                "source": "error",
                "match_quality": "ERROR",
                "accepted": False,
                "classification": "SAFE_REFUSAL",
            })
            print(f"  ◌ {case['id']} | SAFE_REFUSAL     | error              | {input_addr[:30]} [{e}]")
    
    valid_total = len(valid_cases)
    accuracy = exact_correct / valid_total if valid_total > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"VALID RESULTS:")
    print(f"  TOTAL:          {valid_total}")
    print(f"  EXACT_CORRECT:  {exact_correct}")
    print(f"  SAFE_REFUSAL:   {safe_refusal}")
    print(f"  WRONG_ACCEPTED: {wrong_accepted}")
    print(f"  ACCURACY:       {accuracy:.1%}")
    print(f"{'='*70}")
    
    # Run adversarial cases
    print(f"\nADVERSARIAL CASES (using evaluate_geocoding_acceptance directly):")
    print("-" * 70)
    safety_total = len(adversarial_cases)
    safety_rejected = 0
    
    for case in adversarial_cases:
        input_addr = case["input"]
        resolved_road = case.get("resolved_road", "")
        resolved_district = case.get("resolved_district", "大安區")
        resolved_city = case.get("resolved_city", "臺北市")
        
        region = {
            "city": resolved_city,
            "district": resolved_district,
            "road": resolved_road,
            "center": {"lat": 25.04, "lng": 121.53},
            "formatted_address": f"{resolved_city}{resolved_district}{resolved_road}",
        }
        
        acceptance = evaluate_geocoding_acceptance(input_addr, region, "google_geocoding")
        rejected = not acceptance["accepted_for_analysis"]
        
        if rejected:
            safety_rejected += 1
            print(f"  ✓ {case['id']} | REJECTED | {case['reason']:25s} | {input_addr[:25]} → {resolved_road}")
        else:
            print(f"  ✗ {case['id']} | ACCEPTED | {case['reason']:25s} | {input_addr[:25]} → {resolved_road}")
            print(f"    CRITICAL: Should have been rejected!")
    
    safety_accuracy = safety_rejected / safety_total if safety_total > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"ADVERSARIAL RESULTS:")
    print(f"  TOTAL:    {safety_total}")
    print(f"  REJECTED: {safety_rejected}")
    print(f"  ACCURACY: {safety_accuracy:.0%}")
    print(f"{'='*70}")
    
    print(f"\n{'='*70}")
    print(f"FINAL SUMMARY:")
    print(f"  VALID_ADDRESS_ACCURACY:       {accuracy:.1%} (threshold >= 80%)")
    print(f"  VALID_WRONG_ACCEPTED:         {wrong_accepted} (threshold = 0)")
    print(f"  SAFETY_REJECTION_ACCURACY:    {safety_accuracy:.0%} (threshold = 100%)")
    gate = "PASS" if accuracy >= 0.80 and wrong_accepted == 0 and safety_accuracy == 1.0 else "FAIL"
    print(f"  BENCHMARK_GATE:               {gate}")
    print(f"{'='*70}")
    
    return {
        "valid_total": valid_total,
        "exact_correct": exact_correct,
        "safe_refusal": safe_refusal,
        "wrong_accepted": wrong_accepted,
        "accuracy": accuracy,
        "safety_total": safety_total,
        "safety_rejected": safety_rejected,
        "safety_accuracy": safety_accuracy,
        "gate": gate,
        "results": results,
    }


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    result = run_benchmark()
    # ASCII-safe final line for parsing
    print(f"\n[BENCHMARK_RESULT] valid_total={result['valid_total']} exact_correct={result['exact_correct']} safe_refusal={result['safe_refusal']} wrong_accepted={result['wrong_accepted']} accuracy={result['accuracy']:.3f} safety_total={result['safety_total']} safety_rejected={result['safety_rejected']} safety_accuracy={result['safety_accuracy']:.3f} gate={result['gate']}")
