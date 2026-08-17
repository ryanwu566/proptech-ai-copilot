-- Migration: 011_add_plvr_compact_green_schema.sql
-- Purpose: Create the Compact GREEN PLVR schema for the free-plan deployment.
-- Source: Extracted from verified local model_b (Round 2 benchmark, FINAL GO).
--
-- This migration is SCHEMA ONLY. It does not load business data.
-- It does not modify any existing tables, schemas, or data.
-- It is safe for a new empty GREEN project database.
--
-- Period encoding: (year - 2000) * 12 + month - 1
-- Example: 2026-07 = 318
--
-- Expected final dataset after load:
--   facts = 517195, evidence = 517195, aggregates = 9606
--   total storage ~ 344 MiB
--
-- Generation ID: official-plvr-green-18203c6347cd
-- Dataset SHA256: 2ee0cf968d769a9dd8261031f3f13f6d7c5fcb4c0c33316a22120070806cef57

BEGIN;

CREATE SCHEMA IF NOT EXISTS compact_green;

-- ============================================================
-- DICTIONARY TABLES
-- ============================================================

CREATE TABLE compact_green.compact_generations (
    generation_key          integer     NOT NULL PRIMARY KEY,
    dataset_key             text        NOT NULL,
    generation_id           text        NOT NULL,
    source_manifest_sha256  bytea       NOT NULL,
    dataset_sha256          bytea       NOT NULL,
    source                  text        NOT NULL,
    canonical_status        integer     NOT NULL,
    publishable             integer     NOT NULL,
    market_source_name      text        NOT NULL,
    aggregation_method      text        NOT NULL,
    aggregate_built_at      text        NOT NULL
);

CREATE TABLE compact_green.compact_artifacts (
    artifact_key            integer     NOT NULL PRIMARY KEY,
    artifact_id             text        NOT NULL,
    source_artifact_sha256  bytea       NOT NULL
);

CREATE TABLE compact_green.compact_geographies (
    geographic_unit_id      integer     NOT NULL PRIMARY KEY,
    city                    text        NOT NULL,
    district                text        NOT NULL,
    geographic_unit_kind    integer     NOT NULL
);

CREATE TABLE compact_green.compact_roads (
    road_id                 integer     NOT NULL PRIMARY KEY,
    geographic_unit_id      integer     NOT NULL,
    road                    text        NOT NULL
);

CREATE TABLE compact_green.compact_building_types (
    building_type_id        integer     NOT NULL PRIMARY KEY,
    building_type           text        NOT NULL
);

-- ============================================================
-- FACT TABLE (hot-path optimized, includes address_text)
-- ============================================================

CREATE TABLE compact_green.compact_transaction_facts (
    transaction_id          integer     NOT NULL PRIMARY KEY,
    generation_key          integer     NOT NULL,
    geographic_unit_id      integer     NOT NULL,
    period_code             integer     NOT NULL,
    road_id                 integer     NOT NULL,
    building_type_id        integer     NOT NULL,
    area_ping               real        NOT NULL,
    building_age_years      real        NOT NULL,
    floor                   integer     NOT NULL,
    total_floor             integer,
    unit_price_per_ping     real        NOT NULL,
    total_price             real        NOT NULL,
    address_text            text        NOT NULL
);

-- ============================================================
-- EVIDENCE TABLE (lineage, identity, dedupe, fact verification)
-- ============================================================

CREATE TABLE compact_green.compact_transaction_evidence (
    transaction_id          integer     NOT NULL PRIMARY KEY,
    source_row_hash         bytea       NOT NULL,
    source_identity_kind    integer     NOT NULL,
    source_identity_hash    bytea       NOT NULL,
    artifact_key            integer     NOT NULL,
    official_transaction_id text        NOT NULL,
    official_transfer_id    text        NOT NULL,
    business_dedupe_key     bytea       NOT NULL,
    production_fact_hash    bytea       NOT NULL,
    address_text            text        NOT NULL
);

-- ============================================================
-- MARKET AGGREGATES
-- ============================================================

CREATE TABLE compact_green.compact_market_aggregates (
    generation_key          integer     NOT NULL,
    geographic_unit_id      integer     NOT NULL,
    period_code             integer     NOT NULL,
    average_unit_price      real,
    transaction_count       integer     NOT NULL,
    record_count            integer     NOT NULL,
    coverage_status         integer     NOT NULL,
    data_status             integer     NOT NULL
);

-- ============================================================
-- DICTIONARY INDEXES (unique constraints)
-- ============================================================

CREATE UNIQUE INDEX uq_compact_generation_id
    ON compact_green.compact_generations (generation_id);

CREATE UNIQUE INDEX uq_compact_artifact_id
    ON compact_green.compact_artifacts (artifact_id);

CREATE UNIQUE INDEX uq_compact_artifact_sha
    ON compact_green.compact_artifacts (source_artifact_sha256);

CREATE UNIQUE INDEX uq_compact_geography
    ON compact_green.compact_geographies (city, district, geographic_unit_kind);

CREATE UNIQUE INDEX uq_compact_road
    ON compact_green.compact_roads (geographic_unit_id, road);

CREATE UNIQUE INDEX uq_compact_building_type
    ON compact_green.compact_building_types (building_type);

-- ============================================================
-- FACT INDEXES (hot-path performance)
-- ============================================================

-- Primary scan index for region+period queries and recent-district
CREATE INDEX idx_compact_fact_region_period
    ON compact_green.compact_transaction_facts
    (generation_key, geographic_unit_id, period_code DESC, transaction_id);

-- Covering index for city_district_period aggregate (Index Only Scan, 0 heap fetches)
CREATE INDEX idx_compact_fact_geo_period_cover
    ON compact_green.compact_transaction_facts
    (generation_key, geographic_unit_id, period_code)
    INCLUDE (unit_price_per_ping, total_price);

-- ============================================================
-- EVIDENCE INDEXES (lineage verification)
-- ============================================================

CREATE UNIQUE INDEX uq_compact_source_row_hash
    ON compact_green.compact_transaction_evidence (source_row_hash);

CREATE UNIQUE INDEX uq_compact_source_identity
    ON compact_green.compact_transaction_evidence (source_identity_hash);

CREATE UNIQUE INDEX uq_compact_business_dedupe
    ON compact_green.compact_transaction_evidence (business_dedupe_key);

-- ============================================================
-- AGGREGATE INDEX
-- ============================================================

CREATE UNIQUE INDEX uq_compact_aggregate_key
    ON compact_green.compact_market_aggregates
    (generation_key, geographic_unit_id, period_code);

COMMIT;
