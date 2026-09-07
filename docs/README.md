# PropTech AI Copilot Documentation

This is the authoritative documentation index. Active documents describe the
current repository contracts and operating procedures; historical material is
kept under `docs/archive/` and must not be used as current product guidance.

## Start here

- [Project README](../README.md) - project purpose, local commands, current capabilities, and high-level limitations.
- [Product capability surface](product-capability-surface-v1.md) - authoritative map of user-facing capabilities and their trust status.
- [Experience architecture audit](experience-architecture-v3-audit.md) - active journey, accessibility, privacy, and release-boundary audit.
- [Experience architecture phases 5-8](experience-architecture-v3-phases5-8.md) - multilingual runtime shell, native speech boundaries, voice allowlist, and release evidence.
- [Competition release](competition-release.md) - TaxOracle/Holding Cost MVP positioning, demo boundaries, and capability truth.
- [Competition evidence pack](competition-evidence-pack.md) - reproducible judge flow and non-fabricated validation record.
- [Pilot release runbook](pilot-release-runbook.md) - closed-pilot consent, evidence, review, export, deletion, and release operations.
- [Security and performance release](security-performance-release.md) - threat model, persistence boundary, security controls, performance budgets, and release gate.
- [Customer interview pack](customer-interview-pack.md) - neutral questions for collecting real pilot evidence.
- [Professional review pack](professional-review-pack.md) - versioned review scope and non-endorsement checklist.

## Architecture and development

- [iTaiwan deep workflow competitive audit](itaiwan-proptech-deep-workflow-audit-v1.md) - authoritative Stage 0 competitive workflow, architecture, data feasibility, and roadmap input.
- [VNext Stage 0 architecture signoff](vnext/stage-0-architecture-signoff.md) - current GO/NO-GO gate, review answers, owner blockers, and Stage 1 readiness.
- [VNext architecture overview](vnext/architecture-overview-v1.md) - bounded contexts, dependency direction, core models, modes, feature gates, migration and test strategy.
- [VNext property identity architecture](vnext/property-identity-architecture-v1.md) - resolution state machine, candidates, graph relations, confirmation, merge and split.
- [VNext evidence architecture](vnext/evidence-architecture-v1.md) - evidence/provider DTOs, status, freshness, lineage, conflict and AI boundaries.
- [VNext workspace and security architecture](vnext/workspace-security-architecture-v1.md) - tenant roles, RLS, server-only schemas, private Storage, audit and PostGIS.
- [VNext data-source registry](vnext/data-source-registry-v1.md) - access/license/coverage feasibility and owner actions; registration is not readiness.
- [VNext API contract](vnext/api-contract-v1.md) - future `/v1` resource, error, idempotency and audit conventions.
- [VNext API database role provisioning](vnext/vnext-api-database-role-provisioning.md) - separates the passwordless `vnext_api` role/grants migration from external deployment credential provisioning and acceptance.
- [VNext legacy case migration](vnext/legacy-case-migration-v1.md) - optional copy-only SavedCase v1 import and `legacy_unverified` boundary.
- [Valuation public-service architecture](valuation_public_service_architecture.md) - active PLVR-to-valuation architecture and operational boundaries.
- [Property Case Decision System](property-case-decision-system-v1.md) - current case model, readiness, comparison, and report boundaries.
- [Property Case Workspace smoke test](property-case-workspace-smoke-test.md) - executable expectations for case workspace stability.
- [Frontend design brief](../frontend_next/DESIGN_BRIEF.md) - package-local visual and interaction guidance.

## Data and contracts

- [Taiwan Market Data Foundation](market-data-foundation-v1.md) - minimum market aggregate contract and fail-closed data policy.
- [PLVR Market Aggregate Bridge](plvr-market-aggregate-bridge-v1.md) - read-only bridge from valuation data to market aggregates.
- [Nationwide Market Read Model](nationwide-market-read-model-v1.md) - read model, coverage, and protected refresh contract.
- [Market Coverage Operations](market-coverage-operations.md) - canonical registry, coverage audit, direct query, and rollout rules.
- [Valuation Trust Boundary](valuation_trust_boundary.md) - public valuation evidence and unavailable-state boundary.
- [Privacy and Storage Inventory](privacy_and_storage_inventory.md) - browser persistence, sensitive-field, sharing, and export limits.

## Product behavior and trust

- [Property Case Trusted Evidence](property_case_trusted_evidence.md) - trusted evidence transfer and case-output rules.
- [Terrain and Disaster Risk Audit](terrain-disaster-risk-audit-v1.md) - active reference-only terrain and disaster boundary audit.
- [Terrain capability matrix](terrain-disaster-risk-capability-matrix-v1.json) - machine-readable terrain capability and fail-closed contract.
- [Experience capability matrix](experience-architecture-v3-capability-matrix.json) - machine-readable experience, privacy, and release contract.

## Deployment and operations

- [Hosted production launch](hosted-production-launch.md) - authoritative hosted release architecture, owner actions, and truth boundaries.
- [Hosted environment setup](hosted-environment-setup.md) - frontend/backend variables, CORS, cookies, and maintenance contract.
- [Hosted migration runbook](hosted-migration-runbook.md) - PostgreSQL migration ledger, verification, and checkpoint procedure.
- [Hosted rollback runbook](hosted-rollback-runbook.md) - frontend/backend/schema/outage recovery boundaries.
- [Production release evidence](production-release-evidence.md) - non-secret evidence fields and pending-state semantics.
- [Hosted owner launch checklist](hosted-owner-launch-checklist.md) - exact preview/production handoff sequence and stop conditions.

- [Production backend deployment](production-backend-deployment-v1.md) - current Render and Vercel configuration contract; values remain deployment-managed.
- [Commute snapshot operations](commute-snapshot-operations-v1.md) - manual protected refresh procedure and memory-only limitation.
- [PLVR historical import guide](plvr_historical_import_guide.md) - controlled offline import and dry-run procedure.
- [PLVR data freshness operations](plvr_data_freshness_operations.md) - import freshness and database availability handling.
- [PLVR retention policy](plvr_retention_policy.md) - rolling retention and dry-run deletion safeguards.
- [Supabase/Postgres valuation setup](supabase_valuation_setup.md) - operator setup notes without repository credentials or runtime values.

## Release and active audits

- [Release Candidate Operations](release_candidate_operations.md) - hermetic release quality gate and its protected checks.
- [Production Acceptance Checklist](production_acceptance_checklist.md) - manual deployment, responsive, accessibility, privacy, and recovery acceptance.
- [Visual Data Storytelling Production Acceptance](visual_data_storytelling_production_acceptance.md) - current evidence-disclosure acceptance checklist.
- [Release Signoff Template](release_signoff_template.md) - controlled release decision record template.

## Historical archive

- [Archive policy and index](archive/README.md) - completed plans, old audits, demo material, and superseded examples.
# Official data setup

- [Official Terrain and Tax data provider setup](official-data-provider-setup.md)
# Official market data

- `official-plvr-data-pipeline.md`: secure official PLVR acquisition and publication phases.
- `market-insight-methodology.md`: median-first aggregates, sample sufficiency, and bounded comparables.
- `market-data-operations.md`: operator workflow, retention, rollback, and scheduling.
- `market-data-security.md`: archive, CSV, privacy, and import security boundaries.
- `market-data-production-launch.md`: fail-closed launch gate and owner actions.
