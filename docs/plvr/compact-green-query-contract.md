# Compact GREEN Frozen Query Contract

## Schema

`compact_green`

## Generation

- ID: `official-plvr-green-18203c6347cd`
- generation_key: `1`

## Period Encoding

```
period_code = (year - 2000) * 12 + month - 1
```

| Period  | Code |
|---------|------|
| 2023-09 | 284  |
| 2026-07 | 318  |

## Required Application-Level Geography Cache

Before executing hot-path queries, the application MUST load and cache the
geography dictionary (323 entries for `geographic_unit_kind=1`):

```sql
SELECT geographic_unit_id, city, district
FROM compact_green.compact_geographies
WHERE geographic_unit_kind = 1;
```

This returns a static map of `(city, district) -> geographic_unit_id` for the
current generation. It must be loaded once per connection/session and reused
for all hot-path queries. It is 323 entries (~13 KB) and never changes within
a generation.

---

## Hot Path 1: city_district_period

**Purpose:** Aggregate statistics for a specific city/district/period.

**Application resolves:** `geographic_unit_id` from in-process cache.

**SQL:**

```sql
SELECT count(*), avg(unit_price_per_ping), sum(total_price)
FROM compact_green.compact_transaction_facts
WHERE generation_key = 1
  AND geographic_unit_id = $1
  AND period_code = $2;
```

**Parameters:**
- `$1`: geographic_unit_id (from cache)
- `$2`: period_code (encoded)

**Index used:** `idx_compact_fact_geo_period_cover` (Index Only Scan, 0 heap fetches)

**Verified performance:** B p95 ≤ A p95 (0.99x)

---

## Hot Path 2: recent_district_transactions

**Purpose:** Most recent 50 transactions for a district.

**Application resolves:** `geographic_unit_id` from in-process cache.

**SQL:**

```sql
SELECT f.period_code, f.geographic_unit_id, road.road, bt.building_type,
       f.area_ping, f.building_age_years, f.floor, f.total_floor,
       f.unit_price_per_ping, f.total_price, f.address_text
FROM compact_green.compact_transaction_facts f
JOIN compact_green.compact_roads road USING (road_id)
JOIN compact_green.compact_building_types bt USING (building_type_id)
WHERE f.generation_key = 1
  AND f.geographic_unit_id = $1
ORDER BY f.period_code DESC, f.transaction_id
LIMIT 50;
```

**Parameters:**
- `$1`: geographic_unit_id (from cache)

**Key design decisions:**
- `address_text` is read directly from `compact_transaction_facts` (denormalized)
- Evidence table is NOT joined for this user-facing query
- Evidence remains intact for lineage verification

**Index used:** `idx_compact_fact_region_period`

**Verified performance:** B p95 ≤ A p95 (0.97x)

---

## Hot Path 3: valuation_comparables

**Purpose:** Top 200 comparable transactions ranked by relevance.

**SQL:**

```sql
WITH target_ids AS (
    SELECT geo.geographic_unit_id, road.road_id, bt.building_type_id
    FROM compact_green.compact_geographies geo
    LEFT JOIN compact_green.compact_roads road
      ON road.geographic_unit_id = geo.geographic_unit_id AND road.road = $1
    LEFT JOIN compact_green.compact_building_types bt
      ON bt.building_type = $2
    WHERE geo.city = $3 AND geo.district = $4 AND geo.geographic_unit_kind = 1
), candidates AS MATERIALIZED (
    SELECT fact.*
    FROM compact_green.compact_transaction_facts fact, target_ids t
    WHERE fact.generation_key = 1
      AND fact.geographic_unit_id = t.geographic_unit_id
      AND fact.period_code <= $5
    ORDER BY
      CASE WHEN fact.road_id = t.road_id THEN 0 ELSE 1 END,
      CASE WHEN fact.building_type_id = t.building_type_id THEN 0 ELSE 1 END,
      abs(fact.area_ping - $6),
      abs(fact.building_age_years - $7),
      fact.period_code DESC,
      fact.transaction_id
    LIMIT 200
)
SELECT c.period_code, geo.city, geo.district,
       road.road, bt.building_type, c.area_ping,
       c.building_age_years, c.floor, c.total_floor,
       c.unit_price_per_ping, c.total_price, c.address_text
FROM candidates c
JOIN compact_green.compact_geographies geo USING (geographic_unit_id)
JOIN compact_green.compact_roads road USING (road_id)
JOIN compact_green.compact_building_types bt USING (building_type_id)
ORDER BY
  CASE WHEN road.road = $8 THEN 0 ELSE 1 END,
  CASE WHEN bt.building_type = $9 THEN 0 ELSE 1 END,
  abs(c.area_ping - $10),
  abs(c.building_age_years - $11),
  c.period_code DESC,
  c.transaction_id;
```

**Parameters:**
- `$1`, `$8`: road name
- `$2`, `$9`: building_type
- `$3`: city
- `$4`: district
- `$5`: period_code (maximum period, encoded)
- `$6`, `$10`: target area_ping
- `$7`, `$11`: target building_age_years

**Verified performance:** B p95 ≤ A p95 (0.63x — 37% faster than Model A)

---

## Ordering Equivalence

For this frozen generation:

```
ORDER BY transaction_id
```

is **semantically equivalent** to the historical:

```
ORDER BY source_identity
```

**Evidence:** Verified across all 517,195 rows. Zero out-of-order pairs when
comparing `transaction_id` sequence against `source_identity_hash` bytea
sequence. This is because `transaction_id` was assigned during the deterministic
load in `ORDER BY source_identity, source_row_hash`, and all identities share
the `official:` prefix making text ordering equal to bytea ordering.

This equivalence is guaranteed ONLY for the frozen generation
`official-plvr-green-18203c6347cd`. Future generations must re-verify.

---

## Lineage Verification Queries (non-hot-path)

These use the evidence table and are not performance-gated:

```sql
-- Source identity lookup
SELECT * FROM compact_green.compact_transaction_evidence
WHERE source_identity_hash = $1;

-- Source row lineage
SELECT * FROM compact_green.compact_transaction_evidence
WHERE source_row_hash = $1;

-- Business dedupe
SELECT * FROM compact_green.compact_transaction_evidence
WHERE business_dedupe_key = $1;
```

All bytea parameters use raw 32-byte values (not hex text).
