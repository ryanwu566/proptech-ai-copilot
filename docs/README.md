# PropTech AI Copilot Documentation

This is the curated documentation index for the current repository. It separates active product truth from experimental architecture, specialist operations records, and historical material.

Status labels:

- **ACTIVE** — current source of truth or maintained operating guidance.
- **REFERENCE** — useful technical evidence; narrower or more dated than an active overview.
- **EXPERIMENTAL** — implemented foundation or design whose production workflow is incomplete or feature-gated.
- **DRAFT** — proposed or approval-dependent procedure; do not treat as current operations.
- **ARCHIVED** — historical context only.

## Start here

| Document | Status | Purpose |
| --- | --- | --- |
| [Project README](../README.md) | **ACTIVE** | English-first product, architecture, evidence, and local-start overview |
| [Traditional Chinese README](../README.zh-TW.md) | **ACTIVE** | Idiomatic Traditional Chinese counterpart |
| [System architecture](ARCHITECTURE.md) | **ACTIVE** | Current consumer, backend, data, VNext, and deployment boundaries |
| [Data sources](DATA_SOURCES.md) | **ACTIVE** | Provider-by-provider integration, coverage, and trust status |
| [Engineering and validation](ENGINEERING.md) | **ACTIVE** | Reliability, security, testing, migrations, and operations evidence |
| [Technical case study](PORTFOLIO_CASE_STUDY.md) | **ACTIVE** | Deeper admissions/interview narrative and lessons learned |

## Product & Architecture

### Current product

- [Product capability surface](product-capability-surface-v1.md) — **REFERENCE** — detailed user-facing capability and trust-state inventory.
- [Property Case Decision System](property-case-decision-system-v1.md) — **ACTIVE** — current browser-local case, readiness, comparison, and report boundaries.
- [Evidence verification checklist V1](evidence-verification-checklist-v1.md) — **REFERENCE** — implemented manual-review workflow, browser persistence/invalidation contract, and dated validation evidence.
- [Experience architecture audit](experience-architecture-v3-audit.md) — **REFERENCE** — journey, navigation, accessibility, privacy, and release-surface analysis.
- [Frontend design brief](../frontend_next/DESIGN_BRIEF.md) — **REFERENCE** — package-level interaction and visual guidance.

### Professional VNext foundation

- [VNext architecture overview](vnext/architecture-overview-v1.md) — **EXPERIMENTAL** — bounded contexts, dependency direction, feature gates, migrations, and test strategy.
- [Property identity architecture](vnext/property-identity-architecture-v1.md) — **EXPERIMENTAL** — candidates, human confirmation, graph relations, merge/split boundaries.
- [VNext API contract](vnext/api-contract-v1.md) — **EXPERIMENTAL** — authenticated `/v1` resource, error, idempotency, and audit conventions.
- [Property identity UI slice](vnext/property-identity-ui-slice1.md) — **EXPERIMENTAL** — isolated identity workflow and acceptance boundary.
- [Multi-parcel GIS case set](vnext/multiparcel-gis-case-set-v1.md) — **EXPERIMENTAL** — durable case parcel-set model and controls.
- [Legacy case migration](vnext/legacy-case-migration-v1.md) — **EXPERIMENTAL** — copy-only import with `legacy_unverified` semantics.
- [Stage 0 architecture signoff](vnext/stage-0-architecture-signoff.md) — **REFERENCE** — architecture-stage decision record, not production acceptance.
- [Stage 1 exit signoff](vnext/stage-1-exit-signoff.md) — **REFERENCE** — code-gate status and remaining production blockers.

## Data & Integrations

### Market and valuation

- [Taiwan Market Data Foundation](market-data-foundation-v1.md) — **ACTIVE** — aggregate contract and fail-closed data policy.
- [Official PLVR data pipeline](official-plvr-data-pipeline.md) — **ACTIVE** — controlled acquisition, validation, and publication stages.
- [Nationwide Market Read Model](nationwide-market-read-model-v1.md) — **ACTIVE** — read model, coverage, and protected refresh contract; “nationwide” is the model target, not proof of complete live coverage.
- [Market insight methodology](market-insight-methodology.md) — **ACTIVE** — median-first statistics, sample sufficiency, and comparable boundaries.
- [Valuation public-service architecture](valuation_public_service_architecture.md) — **REFERENCE** — provider architecture and public-service boundary.
- [Valuation trust boundary](valuation_trust_boundary.md) — **ACTIVE** — official/demo origin, actionability, and unavailable-state rules.
- [PLVR market aggregate bridge](plvr-market-aggregate-bridge-v1.md) — **REFERENCE** — read-only connection between valuation data and aggregates.

### Spatial, terrain, and public data

- [Terrain and disaster-risk public-source audit](terrain-disaster-risk-public-source-audit-v1.md) — **REFERENCE** — official source access and feasibility findings.
- [Terrain and disaster-risk audit](terrain-disaster-risk-audit-v1.md) — **REFERENCE** — earlier capability/trust audit; check current code and `DATA_SOURCES.md` for newer WRA/GeologyCloud status.
- [Satellite reference evidence](satellite-reference-evidence-v1.md) — **EXPERIMENTAL** — bounded Sentinel-2/Earth Engine contract.
- [NLSC requested-service matrix](nlsc-requested-service-integration-matrix-v1.md) — **REFERENCE** — service-by-service feasibility, not production approval.
- [NLSC TILE_001 test seam](nlsc-tile001-test-seam-v1.md) — **EXPERIMENTAL** — bounded integration/test boundary.
- [NLSC LUI_002 planning slice](nlsc-lui002-planning-slice-v1.md) — **DRAFT** — explicit no-go for production enablement pending authorization and acceptance.
- [Taiwan statutory planning source matrix](vnext/taiwan-statutory-planning-source-matrix-v1.md) — **REFERENCE** — jurisdiction/source analysis.
- [Taipei planning source audit](vnext/taipei-planning-read-v1-source-audit.md) — **REFERENCE** — manual-reference limits and owner prerequisites.

### Source setup and specialist data operations

- [Official data provider setup](official-data-provider-setup.md) — **ACTIVE** — credential and provider boundaries without secret values.
- [Market coverage operations](market-coverage-operations.md) — **ACTIVE** — registry, audit, direct-query, and rollout controls.
- [PLVR historical import guide](plvr_historical_import_guide.md) — **ACTIVE** — controlled offline import and dry-run workflow.
- [PLVR data freshness operations](plvr_data_freshness_operations.md) — **ACTIVE** — freshness and database-availability handling.
- [PLVR retention policy](plvr_retention_policy.md) — **ACTIVE** — rolling retention and guarded deletion.
- [Commute snapshot operations](commute-snapshot-operations-v1.md) — **ACTIVE** — protected manual refresh and memory-only limitation.

## Engineering & Operations

### Deployment and environment

- [Hosted production launch](hosted-production-launch.md) — **ACTIVE** — hosted release architecture, owner actions, and truth boundaries.
- [Hosted environment setup](hosted-environment-setup.md) — **ACTIVE** — frontend/backend variables, origins, cookies, and maintenance mode.
- [Production backend deployment](production-backend-deployment-v1.md) — **REFERENCE** — repository deployment contract; current Cloud Run status remains a dated runtime observation.
- [Environment matrix](environment-matrix.md) — **ACTIVE** — development, preview, and production configuration requirements.
- [Deployment guide](deployment_guide.md) — **REFERENCE** — broader deployment notes; use active hosted documents for current gates.

### Migration, continuity, and recovery

- [Hosted migration runbook](hosted-migration-runbook.md) — **ACTIVE** — registry, verification, and checkpoint procedure.
- [Hosted rollback runbook](hosted-rollback-runbook.md) — **ACTIVE** — frontend, backend, schema, and outage recovery.
- [Backup and restore](backup-restore.md) — **ACTIVE** — safe local procedure and production boundary.
- [Disaster recovery](disaster-recovery.md) — **ACTIVE** — recovery roles and evidence requirements.
- [Security operations](security-operations.md) — **ACTIVE** — operational security checks and incident boundaries.

### Specialist PLVR records

The `plvr/` directory and the root-level `plvr-*` documents preserve compact-green contracts, reconciliation, repair, cutover, and residual-cohort evidence. They are **REFERENCE** engineering records, not onboarding material. Start with [compact-green production runbook](plvr/compact-green-production-runbook.md) only when operating that path. Several phase-specific documents are archive candidates after operational-owner review.

## Security / Privacy / Trust

- [Privacy and storage inventory](privacy_and_storage_inventory.md) — **ACTIVE** — browser persistence, sensitive fields, sharing, and export limits.
- [Security and performance release](security-performance-release.md) — **ACTIVE** — threat model, controls, budgets, and release gate.
- [Market data security](market-data-security.md) — **ACTIVE** — archives, CSVs, privacy, and import boundary.
- [Property Case trusted evidence](property_case_trusted_evidence.md) — **ACTIVE** — evidence transfer and report rules.
- [VNext evidence architecture](vnext/evidence-architecture-v1.md) — **EXPERIMENTAL** — provenance, conflicts, freshness, lineage, and future AI boundaries.
- [VNext workspace and security architecture](vnext/workspace-security-architecture-v1.md) — **EXPERIMENTAL** — tenant roles, RLS, private storage, audit, and PostGIS target.
- [VNext API database role provisioning](vnext/vnext-api-database-role-provisioning.md) — **ACTIVE / SPECIALIST** — constrained database principal setup and acceptance.
- [Supabase emergency RLS remediation](security/supabase-emergency-rls-remediation-2026-08.md) — **REFERENCE** — dated incident/remediation evidence; not general setup guidance.
- [Title/document/ownership foundation](vnext/title-document-ownership-foundation-v1.md) — **DRAFT** — sensitive future architecture, not an implemented product claim.

## Testing & Validation

- [Release Candidate Operations](release_candidate_operations.md) — **ACTIVE** — hermetic release gate and protected checks.
- [Production Acceptance Checklist](production_acceptance_checklist.md) — **ACTIVE** — manual hosted, responsive, accessibility, privacy, and recovery acceptance.
- [Release certification checklist](release/certification-checklist.md) — **ACTIVE** — certification evidence and stop conditions.
- [Production release evidence](production-release-evidence.md) — **ACTIVE** — non-secret evidence fields and pending-state semantics.
- [Property Case Workspace smoke test](property-case-workspace-smoke-test.md) — **ACTIVE** — executable workspace stability expectations.
- [Visual data storytelling production acceptance](visual_data_storytelling_production_acceptance.md) — **REFERENCE** — evidence-disclosure and visual-state acceptance.
- [Pilot release runbook](pilot-release-runbook.md) — **ACTIVE** — consent, evidence, review, export, deletion, and release operations.
- [Release signoff template](release_signoff_template.md) — **REFERENCE** — controlled decision-record template.

Test source remains authoritative for executable expectations: Python tests are under `tests/`, Playwright specifications under `frontend_next/e2e/`, and CI definitions under `.github/workflows/`.

## Research / Design Rationale

- [Technical case study](PORTFOLIO_CASE_STUDY.md) — **ACTIVE** — problem framing, design decisions, learning, limitations, and research directions.
- [September 2026 product rebaseline](proptech7-current-product-rebaseline-2026-09.md) — **REFERENCE** — rigorous stage and product-debt assessment at a dated commit.
- [iTaiwan deep-workflow audit](itaiwan-proptech-deep-workflow-audit-v1.md) — **REFERENCE** — competitive workflow and feasibility analysis; target architecture, not current product truth.
- [Experience architecture phases 5–8](experience-architecture-v3-phases5-8.md) — **REFERENCE** — multilingual, speech, and release-design rationale.
- [Customer interview pack](customer-interview-pack.md) — **REFERENCE** — neutral pilot questions; not completed user research.
- [Professional review pack](professional-review-pack.md) — **REFERENCE** — review scope and non-endorsement checklist.
- [Active-listing observation pilot](vnext/active-listing-observation-pilot-v1.md) — **DRAFT** — future licensed-source pilot boundary.

Design specifications and implementation plans under `docs/superpowers/` are **REFERENCE work records**. They explain intended slices and decisions but do not supersede current code, tests, or this index.

## Historical / Archived Material

- [Archive policy and index](archive/README.md) — **ARCHIVED** — entry point for superseded audits, old implementation phases, release scripts, and examples.
- [Competition release](competition-release.md) — **HISTORICAL / ARCHIVE CANDIDATE** — competition-era positioning; not current product identity.
- [Competition evidence pack](competition-evidence-pack.md) — **HISTORICAL / ARCHIVE CANDIDATE** — preserved reproducibility evidence for the former judging flow.
- [Legacy feature inventory](archive/audits/legacy_feature_inventory.md) — **ARCHIVED** — earlier implementation inventory.
- [Map feature inventory](archive/audits/map_feature_inventory.md) — **ARCHIVED** — historical map audit.
- [Project gap analysis](archive/audits/project_gap_analysis.md) — **ARCHIVED** — superseded gap assessment.
- [Demo script, final checklist, and screenshot plan](archive/release-history/) — **ARCHIVED** — former competition/demo presentation material.

No historical file was deleted or moved by the portfolio documentation pass. Any future archive move requires explicit owner review.
