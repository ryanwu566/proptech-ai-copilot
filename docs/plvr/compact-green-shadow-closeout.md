# Compact GREEN Shadow A/B Closeout

Date: 2026-08-18
Run ID: 20260818-052034
Branch: bench/valuation-blue-green-shadow-prep

## Summary

| Metric       | Value |
|--------------|-------|
| Total cases  | 36    |
| EXPECTED     | 34    |
| REVIEW       | 2     |
| FAIL         | 0     |

**Verdict: STRUCTURAL GO — HUMAN REVIEW REQUIRED**

No production cutover performed.

## Generation Lineage

| Field              | Value                                  |
|--------------------|----------------------------------------|
| generation_key     | 1                                      |
| generation_id      | official-plvr-green-18203c6347cd       |
| source             | official_plvr_opendata                 |
| canonical_status   | 1                                      |
| publishable        | 1                                      |
| market_source_name | Official PLVR OpenData aggregate       |

All relevant source artifacts have verified `source_artifact_sha256`.

## Latency

| Side  | Layer   | Median    | P95        |
|-------|---------|-----------|------------|
| BLUE  | service | 6532.7 ms | 15939.1 ms |
| GREEN | service | 6206.7 ms | 8470.1 ms  |

GREEN P95 is ~47% lower than BLUE P95.

## Estimate Delta Distribution (absolute %)

| Stat   | Value  |
|--------|--------|
| median | 2.62%  |
| p95    | 22.76% |
| max    | 45.52% |

## Accepted REVIEW Cases

### 1. yilan-luodong-zhongzheng (delta −45.52%)

- BLUE: road level, 4 comparables, estimate 1305.0, confidence 65
- GREEN: road level, 5 comparables, estimate 711.0, confidence 79
- Cause: GREEN has 2 additional official same-road transactions (artifact keys 8) not present in BLUE
- Road parity: MATCHED=4, BLUE_ONLY=0, GREEN_ONLY=2
- Classification: **Accepted semantic divergence** — additional verified official data changed comparable selection

### 2. changhua-yuanlin-dayong (delta −22.76%)

- BLUE: district level, 10 comparables, estimate 639.6, confidence 60
- GREEN: road level, 3 comparables, estimate 494.0, confidence 49
- Cause: GREEN has 3 same-road official rows (BLUE only has 1), triggering road-level threshold (≥3)
- Road parity: MATCHED=1, BLUE_ONLY=0, GREEN_ONLY=2
- Classification: **Accepted semantic divergence** — more complete road coverage triggered intended level promotion

### Common Pattern

Both REVIEW cases have BLUE_ONLY=0. No BLUE transactions are missing from GREEN.
The divergence is caused by GREEN having additional official data that changes comparable selection scope.

## Hard Failure Resolution

The single initial hard failure (`pingtung-pingtung-ziyou`) was caused by
`price_range.low > price_range.mid` when the weighted estimate fell below
unweighted P25. Fixed in PR #104 (`min(p25, mid)` / `max(p75, mid)` for public range bounds).

Post-fix rerun confirmed: CLASS=EXPECTED, delta=+10.29%, provenance valid.

## Production Safety

- Database writes: 0
- Supabase modified: NO
- Render modified: NO
- Production PLVR_DATA_BACKEND changed: NO
- Production cutover: NO
