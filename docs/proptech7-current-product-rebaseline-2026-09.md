# PropTech7 Current Product Rebaseline — 2026-09

Status: evidence-backed repository audit

Audit date: 2026-09-19

Audit branch: `audit/proptech7-product-rebaseline`

Base reviewed: `origin/main` at `9e5eaa4d4a42fec15f0652299c9ea0d93e9168fb`

## 1. Decision and scope

**Final product target decision: NO-GO.** The repository supports a credible, bounded competition demonstration and a useful consumer decision-support flow. It does not yet support a claim of consumer decision-product completeness, Professional VNext platform completeness, or production-mature official-data coverage.

The four readiness lanes must remain separate:

| Readiness lane | Rebaseline | Evidence-backed conclusion |
| --- | --- | --- |
| Competition demo readiness | `SUBSTANTIAL` | A guided property, location, risk, market, valuation, affordability, decision and HTML-report experience exists. Demo/sample/mock behavior is visibly labelled in many paths, and core calculations are deterministic. This is sufficient for a controlled demonstration, not parity with iTaiwan's professional workflow. See `frontend_next/lib/guided-journey.ts:3-48`, `frontend_next/components/immersive-viewing-workspace.tsx:84-129`, and `services/llm_service.py:18-32`. |
| Consumer Decision Product | `PARTIAL` | The consumer journey has meaningful breadth, conservative unknown handling, local save/compare and reports. Its case state is browser-local, several providers are conditional or mock-backed, official parcel/building identity is not joined into the journey, and active listings/title/documents are absent. See `frontend_next/lib/case-storage.ts:10-13,65-90,124-145`, `frontend_next/app/page.tsx:172-176,248-251`, and `services/parcel_geometry.py:31-38,78-101`. |
| Professional VNext Platform | `FOUNDATION` | Workspace membership, cases, property graph, evidence, identity resolution/confirmation and RLS foundations are real. The feature is off by default, the production identity engine has no accepted provider, live JWT rollout is unverified, and the Hero does not enter a professional shell. See `database/migrations/013_vnext_workspace_case_foundation.sql:57-395`, `database/migrations/014_vnext_property_graph_evidence_foundation.sql:8-730`, `backend/api/v1/property_identity.py:521-531`, and `docs/vnext/stage-1-exit-signoff.md:7-13,83-110`. |
| Production infrastructure maturity | `PARTIAL` | The code has backend-only credentials, safe failure contracts, forced RLS, bounded clients, migrations and operator routes. The repository cannot prove hosted configuration, source authorization, loaded coverage, real-provider acceptance, durable TDX refresh, or live Supabase JWT/RLS behavior. See `docs/vnext/data-source-registry-v1.md:50-66`, `docs/production-backend-deployment-v1.md:45-51`, `docs/commute-snapshot-operations-v1.md:59-65`, and `docs/vnext/stage-1-exit-signoff.md:83-91`. |

No percentages are used. The audit uses these states:

- `NOT_STARTED`: no target runtime workflow or accepted implementation evidence.
- `FOUNDATION`: contracts, schema, safety controls, manual/test seams, or isolated UI exist, but the target user workflow is not operational.
- `PARTIAL`: a bounded end-to-end subset works, with material provider, coverage, workflow, security-validation, or operations gaps.
- `SUBSTANTIAL`: most bounded stage behavior and acceptance controls exist; remaining gaps prevent closure, usually production validation or limited target scope.
- `CLOSED`: the stage's defined exit gate is met with repository evidence. Closure does not imply the whole product or its production deployment is complete.

## 2. Evidence basis and audit rules

The audit read the following authoritative inputs in full:

- `docs/itaiwan-proptech-deep-workflow-audit-v1.md`
- `docs/vnext/stage-0-architecture-signoff.md`
- `docs/vnext/architecture-overview-v1.md`
- `docs/vnext/property-identity-architecture-v1.md`
- `docs/vnext/evidence-architecture-v1.md`
- `docs/vnext/workspace-security-architecture-v1.md`
- `docs/vnext/data-source-registry-v1.md`

The target is not inferred from marketing language alone. The authoritative audit defines the professional progression from intake through identity, GIS, building/planning, market/listings, title/documents, CRM/team, evidence-grounded AI and professional workspace (`docs/itaiwan-proptech-deep-workflow-audit-v1.md:74-90,244-350,790-945`). It also explicitly distinguishes the current competition-oriented product from the VNext target (`docs/itaiwan-proptech-deep-workflow-audit-v1.md:1292-1299`).

Repository evidence rules used here:

1. A registered source is not an integrated source. The registry says registration is not production approval (`docs/vnext/data-source-registry-v1.md:3-19`).
2. An adapter is not proof of successful hosted calls, current coverage, legal authorization, or operational ownership.
3. A mock, sample, manual hypothesis, point marker or user upload is not official identity, official parcel geometry or official building resolution.
4. Schema and API foundations do not equal a user-complete workflow.
5. A local browser case is not a durable, tenant-secured professional case.
6. A deterministic template explanation is not native evidence-grounded AI.
7. Absence findings were checked against the runtime router inventory (`backend/api_main.py:21-38,186-203`), VNext migration table inventory (`database/migrations/013_vnext_workspace_case_foundation.sql:57-247`, `database/migrations/014_vnext_property_graph_evidence_foundation.sql:8-645`, `database/migrations/015_vnext_identity_resolution_candidates.sql:12-363`, `database/migrations/016_vnext_identity_confirmation_case_links.sql:25-565`, `database/migrations/017_vnext_legacy_saved_case_import.sql:6-166`), and runtime filename/symbol searches. No listing, title, ownership, document vault, CRM, zoning or redevelopment runtime module/API was found.

## 3. Gate 1 — Hero promise versus reality

The Hero promises unified location, valuation, risk, market and decision analysis plus public/verified sources, evidence traceability and multi-source intelligence (`frontend_next/components/hero-intro.tsx:8-21`; translated product copy at `frontend_next/lib/experience-i18n.ts:28-48,179-185`). The guided journey itself contains five steps—property, location, price, affordability and decision (`frontend_next/lib/guided-journey.ts:3-48`).

| Promise | Frontend promise | Backend reality | Provider/data reality | Production reality | Biggest missing piece |
| --- | --- | --- | --- | --- | --- |
| Property | The journey begins with property criteria and an address/property profile; the Hero calls it an integrated initial due-diligence flow (`frontend_next/lib/experience-i18n.ts:28-49,179-183`). | Consumer search and inputs exist. A separate VNext route supports resolution candidates, explicit human confirmation, a durable case and resolution attachment (`backend/api/v1/property_identity.py:1176-1367`; `frontend_next/app/vnext/property-identity/page.tsx:1-7`). | The VNext engine is instantiated with no providers because no identity source is production accepted (`backend/api/v1/property_identity.py:529-531`). Manual parcel/building hypotheses do not fix this. | VNext identity is feature-flagged off by default (`services/vnext/feature_flags.py:10-32`); production rollout and live JWT/RLS remain unverified (`docs/vnext/stage-1-exit-signoff.md:7-13,83-110`). | Put one authorized, accepted identity provider into the engine and connect confirmed identity/durable cases to the main journey. |
| Location | Location Intelligence and nearby context are presented as core analysis (`frontend_next/components/hero-intro.tsx:8-14`; `frontend_next/lib/experience-i18n.ts:181-183`). | Address resolution, map search, nearby places, commute and route enrichment exist (`services/location_resolver.py:205-234`; `services/map_service.py:74-174,243-324`; `services/commute_routing_service.py:151-228`). | Trusted address resolution uses TGOS then Google and no mock; the general map flow uses Google, TGOS, then bundled mock. Places can fall back to normalized mock results (`services/location_resolver.py:205-234`; `services/map_service.py:74-132,249-323`). | Credential presence can enable calls, but the repository does not prove hosted reachability, quota/terms acceptance or real-provider coverage. TDX is an in-memory, manually refreshed MRT snapshot (`docs/commute-snapshot-operations-v1.md:3-5,59-65`). | Production acceptance evidence for TGOS/Google/TDX plus durable transit coverage and clear separation of live versus demo outputs. |
| Risk | The Hero promises Risk Evidence, and the journey includes terrain/location risk (`frontend_next/components/hero-intro.tsx:8-14`; `frontend_next/lib/experience-i18n.ts:180-184`). | Terrain aggregation, parcel context, risk summary and a safety gate exist. Incomplete terrain evidence cannot become an unrestricted green signal (`frontend_next/lib/terrain-safety-gate.ts:4-16,39-80`; `frontend_next/lib/risk-summary.ts:50-95,200-211`). | ARDSWC has a bounded official MVT adapter; NLSC terrain is available only through an optional gateway; WRA flood and geology/liquefaction/fault providers always return unavailable (`services/terrain_risk_providers/ardswc_slope_hazard_provider.py:1-4,95-227`; `services/terrain_risk_providers/nlsc_terrain_provider.py:1-5,22-60`; `services/terrain_risk_providers/wra_flood_provider.py:10-25`; `services/terrain_risk_providers/geologycloud_provider.py:10-25`). | Live ARDSWC/NLSC calls, coverage, freshness and authorization are not proven. The NLSC config check validates syntax, not Taiwan residency or NLSC approval (`docs/production-backend-deployment-v1.md:45-51`). | Accepted nationwide hazard sources—especially flood, geology, liquefaction and faults—with versioned coverage/freshness evidence. |
| Market | The Hero promises Market Intelligence and the price step combines market and comparable evidence (`frontend_next/components/hero-intro.tsx:8-14`; `frontend_next/lib/guided-journey.ts:29-35`). | Official PLVR ingestion, Postgres aggregates, market queries, coverage/freshness states, protected refresh and safe-unavailable responses exist (`services/official_plvr_market_pipeline.py:214-441,790-885`; `backend/api/routes_market.py:161-239,468-509`). | Only official PLVR rows qualify for production property search; absence or query failure returns no data/unavailable (`services/property_search_service.py:17-41,94-102`). | The repository does not prove a currently populated production database, successful latest release import or accepted geographic coverage. The VNext registry remains `prototype_partial` (`docs/vnext/data-source-registry-v1.md:25`). | Recorded live release, freshness and geographic coverage acceptance; then add licensed active listings without conflating them with transactions. |
| Valuation | The Hero promises a valuation range and evidence-backed price check (`frontend_next/components/hero-intro.tsx:8-14`; `frontend_next/lib/experience-i18n.ts:47-48,183-184`). | A Postgres provider queries comparable transactions and validates official results. Normal provider selection fails closed; sample data requires explicit demo mode (`services/valuation_service.py:135-159,176-286`; `services/valuation_providers/postgres_provider.py:25-99,204-369`). | Official results require `official_plvr_opendata`; the provider records composition and coverage. Demo results are marked non-actionable (`services/valuation_service.py:306-341,368-417`). | Runtime database availability, current import, nationwide scope and hosted latency are not proven by source code. It is not a formal appraisal (`frontend_next/lib/experience-i18n.ts:179-185`). | Production coverage/freshness proof and a confirmed-property join so comparable selection is not anchored only by user-entered location attributes. |
| Affordability | The journey promises loan, holding-cost and tax references, explicitly not approval or formal tax advice (`frontend_next/lib/experience-i18n.ts:49-95,183-185`). | Deterministic loan amortization and holding-cost calculations exist (`services/loan_calculator_service.py:11-58,62-114`; `services/holding_cost_service.py:11-88`). TaxOracle is deterministic, opt-in for persistence, and attaches a rule trace (`services/tax_service.py:15-22`). | Central-bank mortgage/bank-rate paths can fall back to mock (`services/mortgage_rate_service.py:21-57,122-132`; `services/bank_rate_service.py:71-90,107-139`). Tax compatibility metadata explicitly does not claim official rates, and source status is `not_checked` (`services/official_tax_rules.py:55-79,97-109,169-173`). | No bank underwriting, actual offer, verified borrower data, current official jurisdiction rule pack or production financial integration is proven. | Versioned official tax/rate acceptance and a durable scenario model tied to a confirmed case, while keeping lending approval out of scope. |
| Decision | The journey culminates in a viewing decision, readiness, risks and next actions (`frontend_next/lib/experience-i18n.ts:49-95`; `frontend_next/components/immersive-viewing-workspace.tsx:84-129`). | Client-side synthesis aggregates location, terrain, valuation, finance and tax; missing terrain blocks an all-clear. Manual review notes and readiness checks exist (`frontend_next/lib/risk-summary.ts:50-103`; `frontend_next/lib/property-case.ts:157-163,190-294`). | The decision inherits each upstream provider's limitations. No independent decision provider exists, which is appropriate; however, evidence is split between consumer state and VNext ledgers. | Decisions are not durably versioned in a tenant-secured professional case, assigned for review, approved, or audited as a workflow outcome. | A durable decision record with reviewer, rationale, evidence snapshot, unknowns, status transitions and audit history. |
| Workspace | The Hero offers “view analysis progress”; the page also renders a “Property Decision Workspace” (`frontend_next/lib/experience-i18n.ts:179-185`; `frontend_next/components/immersive-viewing-workspace.tsx:125-132`). | The Hero's workspace action opens a consumer journey/workspace, not `/workspace/{caseId}`; VNext has workspaces/cases only through a separate identity screen (`frontend_next/app/page.tsx:172-176,248-251`; `frontend_next/app/vnext/property-identity/page.tsx:1-7`). | Consumer saves are capped at ten browser-local cases, with compacted evidence (`frontend_next/lib/case-storage.ts:10-13,65-90,124-145`). VNext has durable RLS-backed workspace/case schema (`database/migrations/013_vnext_workspace_case_foundation.sql:57-195,386-462`). | The VNext signoff explicitly excludes Hero integration and production enablement (`docs/vnext/stage-1-exit-signoff.md:93-114`). | The Professional Workspace shell: durable case route, map/table canvas, tasks/activity/documents/team and role-aware navigation. |
| Multi-source | The trust strip claims Multi-Source Intelligence and Public & Verified Sources (`frontend_next/components/hero-intro.tsx:16-21`). | Multiple adapters and source labels exist across geocoding, places, routing, PLVR and terrain. | Sources have different readiness: some live-optional, some demo fallback, some metadata-only, some always unavailable. The VNext registry says no source becomes accepted merely because code exists (`docs/vnext/data-source-registry-v1.md:3-19,23-35`). | No repository evidence proves the full provider set live, authorized, current and monitored together. Some consumer flows deliberately return mock fallback (`services/map_service.py:243-323`). | A runtime source-status/acceptance ledger that drives UI claims per fact, with mock/demo outputs excluded from verified-source language. |
| Evidence traceability | The Hero claims Evidence Traceability (`frontend_next/components/hero-intro.tsx:16-21`). | VNext implements immutable/versioned evidence, lineage, links and property graph with forced RLS (`database/migrations/014_vnext_property_graph_evidence_foundation.sql:127-730`). The isolated UI can inspect graph and evidence (`frontend_next/components/vnext-property-identity-workflow.tsx:321-335,485-489`). | Current VNext evidence comes from identity/test/manual/deterministic seams; the production identity engine has no accepted provider. Consumer exports can carry selected evidence but remain separate (`frontend_next/lib/valuation-share.ts:67-158`). | The evidence architecture says unknown and unavailable must remain explicit and AI may not elevate evidence (`docs/vnext/evidence-architecture-v1.md:85-105,230-259`). End-to-end production lineage across every consumer module is not present. | One evidence contract and durable ledger across identity, GIS, market, risk, finance, documents, decisions and future AI citations. |

**Gate 1 conclusion:** Hero capability wording is defensible only as a bounded decision-support/demo promise with the existing disclaimer. “Public & Verified Sources,” “Multi-Source Intelligence,” “Evidence Traceability,” and “Workspace” are broader than the production-proven reality unless the UI exposes per-result status and avoids implying all sources and all workflows are verified/live.

## 4. Gate 2 — Competitive workflow parity

| Workflow | Status | Current implementation and exact evidence | Parity gap |
| --- | --- | --- | --- |
| Intake | `PARTIAL` | Consumer forms and guided steps collect property, location, price and finance inputs (`frontend_next/lib/guided-journey.ts:3-48`; `frontend_next/components/property-case-command-center.tsx:417-603`). | No professional intake queue, assignment, source-document intake, duplicate detection or canonical identity-first handoff. |
| Property Identity | `SUBSTANTIAL` code foundation; production `PARTIAL` | Candidate resolution, conflict/confirmation decisions, property materialization and case attachment exist (`backend/api/v1/property_identity.py:1176-1367`; `database/migrations/015_vnext_identity_resolution_candidates.sql:12-363`; `database/migrations/016_vnext_identity_confirmation_case_links.sql:25-565`). | Engine provider tuple is empty, flags default off, live JWT/RLS is unverified, and the consumer Hero is not integrated (`backend/api/v1/property_identity.py:529-531`; `services/vnext/feature_flags.py:15-32`; `docs/vnext/stage-1-exit-signoff.md:83-114`). |
| Parcel / GIS | `FOUNDATION` | User GeoJSON/KML/Shapefile parsing, point fallback, spatial checks, LANDSECT raster context and manual VNext parcel hypotheses exist (`services/parcel_geometry.py:31-38,62-101,167-181,345-401`; `services/landsect_context.py:1-16`; `backend/api/v1/property_identity.py:1022-1048`). | Official parcel vector is disabled; no legal parcel ID/area, durable multi-parcel selection, map/table sync, PostGIS case layer or accepted NLSC parcel resolver (`backend/api/routes_parcel_geometry.py:24-31`). |
| Building | `FOUNDATION` | VNext accepts a manual building cadastral-number claim and creates user-provided evidence plus a proposed edge (`services/vnext/building_claim_command.py:31-32,66-97,145-151,238-289`; `backend/api/v1/property_identity.py:1083-1109`). | No authoritative source, provider candidates, permits/use/floor/unit facts, temporal validity, official confirmation or consumer workflow. |
| Planning / Zoning | `NOT_STARTED` | The source registry marks local planning data `not_integrated` (`docs/vnext/data-source-registry-v1.md:30`). No planning/zoning runtime route or module appears in `backend/api_main.py:21-38,186-203`. | Jurisdiction registry, zoning/land-use facts, effective dates, map overlays, evidence and manual-verification workflow. |
| Redevelopment | `NOT_STARTED` | Urban renewal data is `not_integrated` (`docs/vnext/data-source-registry-v1.md:31`). | Pilot jurisdiction, project/site identity, temporal status model, source rights, case overlay and evidence. |
| Historical Market | `SUBSTANTIAL` | Official PLVR pipeline, release metadata, normalized transactions, aggregates, comparables, coverage/freshness contracts and protected operations exist (`services/official_plvr_market_pipeline.py:214-441,790-885`; `backend/api/routes_market.py:161-239,468-591`). | Current production release, loaded coverage, freshness and operations are not demonstrated in-repo; VNext reuse terms remain owner-review required (`docs/vnext/data-source-registry-v1.md:25`). |
| Active Listings | `NOT_STARTED` | Registry status is `partner_required`, with licensed API/feed only and no scraping (`docs/vnext/data-source-registry-v1.md:34,47-48`). | Partner, contract, listing identity/history, relist/dedup/takedown, licensed media/contact handling and runtime adapter. |
| Title / Ownership | `NOT_STARTED` | Registry status is `partner_required` and highly sensitive (`docs/vnext/data-source-registry-v1.md:33`). Current parcel contracts explicitly do not determine ownership (`services/parcel_geometry.py:31-38`). | Legal basis, partner/procurement path, identity assurance, consent, signed delivery, retention, audit and restricted views. |
| Documents | `NOT_STARTED` for target vault | User parcel-geometry upload is request-scoped and not persisted (`backend/api/routes_parcel_geometry.py:24-31`); consumer tax/document fields are checklists, not document storage. The registry calls user upload `user_input_partial` (`docs/vnext/data-source-registry-v1.md:35`). | Private object storage, malware/type validation, document metadata, versioning, permissions, retention/deletion, audit and title-document workflow. |
| CRM | `NOT_STARTED` | No contact, lead, activity or follow-up runtime table/module/route exists in the VNext migrations or API router inventory. The target CRM is described only in the authoritative audit (`docs/itaiwan-proptech-deep-workflow-audit-v1.md:914-945`). | Contacts/leads, activities, tasks, follow-ups, consent, permissions, relationship to cases/properties and audit. |
| Team Collaboration | `FOUNDATION` | Workspaces, members, roles, cases, actor context and RLS exist (`database/migrations/013_vnext_workspace_case_foundation.sql:57-195,386-546`; `docs/vnext/workspace-security-architecture-v1.md:41-89,91-177`). | No invitations, assignments, comments, tasks, activity feed, review queue or professional team UI; live JWT/RLS remains unverified. |
| Valuation | `PARTIAL` | Official Postgres comparable selection, data status, confidence, validation and fail-closed responses exist (`services/valuation_service.py:135-286`; `services/valuation_providers/postgres_provider.py:49-99,204-369`). | Production dataset/coverage is not proved, identity is not canonical, and no professional valuation review/override/version workflow exists. |
| Finance / Affordability | `PARTIAL` | Deterministic loan and holding-cost calculations, sensitivity and burden signals exist (`services/loan_calculator_service.py:11-114`; `services/holding_cost_service.py:11-100`). | No lender/product eligibility, verified rates/borrower data, offer comparison, approval workflow or durable professional scenarios. |
| Tax | `PARTIAL` | Deterministic TaxOracle analysis and trace fields exist (`services/tax_service.py:15-22`; `services/official_tax_rules.py:97-109`). | The active compatibility catalog does not claim official rates and has `source_status: not_checked` (`services/official_tax_rules.py:55-79,169-173`); no jurisdiction-complete versioned official rule operation. |
| Terrain / Disaster | `PARTIAL` | ARDSWC MVT, optional NLSC terrain gateway, explicit unavailable WRA/geology layers and a frontend no-false-green safety gate exist (`services/terrain_risk_providers/ardswc_slope_hazard_provider.py:95-227`; `frontend_next/lib/terrain-safety-gate.ts:39-80`). | Flood, geology, liquefaction and active-fault sources are placeholders; official coverage/freshness/terms/live acceptance are open. |
| Evidence | `PARTIAL` | Strong immutable evidence, lineage/link, status, coverage, quality and license schema exists with forced RLS (`database/migrations/014_vnext_property_graph_evidence_foundation.sql:127-296,597-730`). | Only a bounded identity/manual slice writes to it; consumer modules and future documents/listings/planning are not unified in the ledger. |
| Decision | `PARTIAL` | Conservative consumer decision synthesis, readiness and manual notes exist (`frontend_next/lib/risk-summary.ts:50-103`; `frontend_next/lib/property-case.ts:157-163,223-294`; `frontend_next/components/property-case-command-center.tsx:601-603,795-843`). | No durable decision object, workflow ownership, reviewer/approval state, evidence snapshot or audited decision history. |
| Report | `PARTIAL` | Browser-generated valuation/decision HTML and a server TaxOracle HTML report exist (`frontend_next/lib/valuation-share.ts:125-158`; `services/report_service.py:1-24`). | No durable professional report artifact, template/version governance, case permissions, signed/frozen evidence pack or controlled sharing. |
| Compare | `PARTIAL` | Consumer cases can be saved locally and compared/readied, capped at ten (`frontend_next/lib/case-storage.ts:10-13,65-90`; `frontend_next/lib/property-case.ts:287-294`). | No server-side comparison set, canonical property identity, multi-user persistence, listing/parcel/building normalization or auditable scenario snapshots. |
| AI Copilot | `FOUNDATION` | The service produces a stable template explanation. Even with an API key it remains template mode and does not call an external model (`services/llm_service.py:18-32`). Deterministic decision/risk explanations are useful but are not generative AI. | Native evidence retrieval/citation, permission filtering, unknown/conflict preservation, prompt/model audit, evaluation and human approval. |
| Professional Workspace | `NOT_STARTED` | Current “pro mode” is a browser presentation preference (`frontend_next/lib/view-mode.ts:4-15`); the consumer workspace is session/local state (`frontend_next/components/immersive-viewing-workspace.tsx:32-55,96-132`). | No `/workspace/{caseId}` shell, map/table canvas, case queue, tasks/activity, documents, CRM/team, evidence rail or role-aware professional workflow (`docs/vnext/architecture-overview-v1.md:274-296`). |

**Gate 2 conclusion:** competitive parity is strongest in consumer calculation and historical-market reference work. The identity/evidence/security foundation is materially stronger than the original iTaiwan audit baseline, but the workflow remains discontinuous: the VNext identity screen is isolated, GIS is not official/durable, and the professional stages after identity are mostly foundation or not started.

## 5. Gate 3 — VNext stage rebaseline

| Stage | Status | Rebaseline evidence and closure condition |
| --- | --- | --- |
| Stage 0 — Architecture | `CLOSED` | The architecture signoff records `GO` and the required architecture/security contracts exist (`docs/vnext/stage-0-architecture-signoff.md:9-14`; `docs/vnext/architecture-overview-v1.md`; `docs/vnext/property-identity-architecture-v1.md`; `docs/vnext/evidence-architecture-v1.md`; `docs/vnext/workspace-security-architecture-v1.md`; `docs/vnext/data-source-registry-v1.md`). Open provider/deployment work belongs to later stages and does not reopen the architecture deliverable. |
| Stage 1 — Property Identity + Durable Case | `SUBSTANTIAL` | The code gate is `GO`: durable workspaces/cases, graph/evidence, candidate resolution, human confirmation, case attachment, auth code and RLS exist (`docs/vnext/stage-1-exit-signoff.md:7-13,30-81`; migrations 013–017). Not `CLOSED`: live Supabase JWT/RLS is unverified, flags default off, Hero integration was excluded, and the production engine has zero accepted providers (`docs/vnext/stage-1-exit-signoff.md:83-114`; `backend/api/v1/property_identity.py:529-531`). |
| Stage 2 — Parcel / GIS | `FOUNDATION` | Bounded user geometry, LANDSECT context, manual parcel hypotheses and a safe disabled NLSC vector seam exist (`services/parcel_geometry.py:31-38,78-101,345-401`; `services/landsect_context.py:1-16`; `backend/api/v1/property_identity.py:1022-1048`). Closure requires official parcel resolution/geometry, durable multi-parcel case selection and GIS workspace behavior. |
| Stage 3 — Building / Planning / Redevelopment | `FOUNDATION` | Manual building claims and manual parcel-building proposed relations exist (`backend/api/v1/property_identity.py:1083-1169`; `services/vnext/parcel_building_relation_command.py:1-9,114-142`). Building, planning and renewal sources remain `not_integrated` (`docs/vnext/data-source-registry-v1.md:30-32`). |
| Stage 4 — Market / Listings | `PARTIAL` | Historical PLVR pipeline/market/valuation capabilities are substantial (`services/official_plvr_market_pipeline.py:214-441,790-885`; `services/property_search_service.py:17-41`). Active listings are `partner_required` with no adapter (`docs/vnext/data-source-registry-v1.md:34`). Historical data alone cannot close a combined market/listings stage. |
| Stage 5 — Title / Documents | `NOT_STARTED` | No target title or document-vault runtime model/API exists. The partner path is unselected and user uploads are only partial/request-scoped (`docs/vnext/data-source-registry-v1.md:33,35`; `backend/api/routes_parcel_geometry.py:24-31`). |
| Stage 6 — CRM / Collaboration | `FOUNDATION` | Tenant workspaces, roles/memberships, cases and audit/RLS controls exist (`database/migrations/013_vnext_workspace_case_foundation.sql:57-247,386-546`). CRM, tasks, activity feed, invitations, assignment and collaboration UI do not. |
| Stage 7 — Evidence-grounded AI | `FOUNDATION` | The evidence/lineage model and safe AI boundary are defined and partially implemented (`database/migrations/014_vnext_property_graph_evidence_foundation.sql:127-296,597-730`; `docs/vnext/evidence-architecture-v1.md:230-259`). Runtime “AI” is template-only (`services/llm_service.py:18-32`), so no native evidence-grounded AI workflow exists. |
| Stage 8 — Professional Workspace | `NOT_STARTED` | The target shell is architecture only (`docs/vnext/architecture-overview-v1.md:274-296`). The current browser-local consumer workspace and view-mode toggle are not the professional shell (`frontend_next/components/immersive-viewing-workspace.tsx:32-55,96-132`; `frontend_next/lib/view-mode.ts:4-15`). |

## 6. Gate 4 — External data and API reality

`Production-callable` below means the code can make a bounded external call when configured. It does **not** mean the call is deployed, successful, authorized, current or accepted. `Production-live proven` and `officially authorized proven` require repository evidence; credentials or environment keys alone are insufficient.

| Source | Registered | Adapter / pipeline exists | Test-only / fallback-only / production-callable | Production-live proven | Officially authorized proven | Audit conclusion and evidence |
| --- | --- | --- | --- | --- | --- | --- |
| PLVR | Yes | Yes | Production-callable batch pipeline and Postgres query/read model; safe unavailable without DB | **No** | **No for VNext reuse** | Registry is `prototype_partial`; license/attribution, loaded release, coverage/freshness and VNext reuse remain owner actions (`docs/vnext/data-source-registry-v1.md:25`). The code enforces official HTTPS/hosts and release validation (`services/official_plvr_market_pipeline.py:214-441`), but code is not a live import record. |
| Google Geocoding | Not a VNext canonical registry row | Yes | Production-callable when backend key exists; general map path can fall back to mock | **No** | **No** | Adapter calls Google and returns `None` on missing key/failure (`services/adapters/geocoding_adapter.py:32-85`). The registry explicitly says Google is optional current integration, not an approved VNext identity source (`docs/vnext/data-source-registry-v1.md:39-41`). |
| Google Places | Not a VNext canonical registry row | Yes | Production-callable; normalized mock fallback in map flow | **No** | **No** | Key controls availability (`services/adapters/google_places_adapter.py:69-98`); map service falls back to bundled mock and marks it (`services/map_service.py:249-323`). No terms/quota/real-provider acceptance pack exists. |
| Google Routes | Not a VNext canonical registry row | Yes | Production-callable; deterministic mock only in dev/test or explicit demo opt-in | **No** | **No** | Live adapter fails closed (`services/adapters/routes_adapter.py:96-188`); routing service uses Google then gated mock and does not cache mock (`services/commute_routing_service.py:151-228`). |
| TGOS | Yes | Yes; plus VNext observation seam | Current trusted resolver is production-callable. VNext TGOS observation provider is explicitly test-environment-only | **No** | **No** | Credentials enable current calls (`services/adapters/tgos_geocoding_adapter.py:16-100`); registry is `prototype_partial` and terms/quota/acceptance remain open (`docs/vnext/data-source-registry-v1.md:26`). VNext seam states test-only and cannot confirm identity (`services/vnext/tgos_observation_provider.py:1-35,62-78,328-331`). |
| TDX | Yes | Yes | Production-callable only through protected manual refresh into memory | **No** | **No** | OAuth client and MRT endpoints exist (`services/tdx_mrt_client.py:12-91`), but the snapshot is memory-only and can disappear on restart (`services/commute_service.py:1-56`; `docs/commute-snapshot-operations-v1.md:59-65`). Registry is `prototype_partial` (`docs/vnext/data-source-registry-v1.md:28`). |
| ARDSWC | Yes | Yes | Production-callable official MVT when decoder/network are available; tested with injected HTTP/decoder | **No** | **No** | Four public MVT layers are bounded and normalized (`services/terrain_risk_providers/ardswc_slope_hazard_provider.py:1-4,25-29,95-227`). Registry remains `prototype_partial`; endpoint terms, version, coverage and real-provider acceptance are open (`docs/vnext/data-source-registry-v1.md:29`). |
| NLSC | Yes | Terrain gateway adapter and LANDSECT raster context; cadastral vector placeholder | Terrain gateway is production-callable when configured. LANDSECT is context only. Cadastral vector/official parcel resolution is fallback-only/disabled | **No** | **No** | Gateway supports only `/nlsc/terrain/point` and fails closed (`services/adapters/nlsc_gateway_adapter.py:18-29,56-93`). LANDSECT cannot identify a parcel (`services/landsect_context.py:10-16`). Cadastral provider is disabled until endpoint and authorization are proven (`services/parcel_geometry.py:78-101`). Config validates syntax only; Taiwan residency/application evidence is external and absent (`docs/production-backend-deployment-v1.md:45-51`). |
| NCDR | Metadata registry only | No runtime hazard adapter found | Manual-download metadata only | **No** | **No** | Official-data registry records manual download and `runtime_status: not_checked` (`services/official_data_registry.py:42-106`). It is not an integrated source. |
| WRA | Placeholder metadata/source URL | Unavailable provider only | Fallback-only: always explicit unavailable | **No** | **No** | Provider returns unavailable because no legally configured coordinate API exists (`services/terrain_risk_providers/wra_flood_provider.py:10-25`). VNext registry calls WRA an honest placeholder (`docs/vnext/data-source-registry-v1.md:42-44`). |
| Geology / fault / liquefaction | Placeholder metadata/source URL | One unavailable provider for three layers | Fallback-only: all three always explicit unavailable | **No** | **No** | Geological sensitivity, liquefaction and active fault all return unavailable (`services/terrain_risk_providers/geologycloud_provider.py:10-25`). No selected dataset, adapter contract, authorization or coverage acceptance exists. |

### NLSC requested-API finding

The repository does not contain an approved or implemented matrix of the requested NLSC APIs. It contains exactly three bounded NLSC-related shapes:

1. `LANDSECT` WMTS section-context metadata, explicitly not a parcel boundary, parcel ID, legal area or ownership source (`services/landsect_context.py:6-16`).
2. A disabled future cadastral-vector provider that requires a verified endpoint, authorization and resolver (`services/parcel_geometry.py:78-101`).
3. One Taiwan-gateway terrain operation, `POST /nlsc/terrain/point`, with offline contract tests and fail-closed normalization (`services/adapters/nlsc_gateway_adapter.py:18-29,56-93`; `tests/test_nlsc_gateway_adapter.py:1-28,49-180`).

Therefore:

- NLSC integration: `FOUNDATION`.
- NLSC production-live: not proven.
- NLSC official authorization: not proven.
- Official parcel resolution: not implemented.
- Official building resolution through NLSC: not implemented.
- Requested NLSC API coverage beyond the single terrain gateway contract: not evidenced in the repository.

## 7. Gate 5 — Top 12 product debts

1. **Production-grade Property Identity is not closed.** Stage 1 code is substantial, but the runtime engine has zero production-accepted providers, flags default off, live JWT/RLS is unverified, and Hero integration is absent (`backend/api/v1/property_identity.py:521-531`; `services/vnext/feature_flags.py:15-32`; `docs/vnext/stage-1-exit-signoff.md:83-114`).

2. **NLSC requested APIs and official parcel resolution are absent.** The repository has one terrain gateway method, LANDSECT context and a disabled cadastral-vector seam—not an accepted parcel ID/boundary service (`services/adapters/nlsc_gateway_adapter.py:18-29`; `services/landsect_context.py:10-16`; `services/parcel_geometry.py:78-101`). Exact dataset/API selection, authorization, terms, coverage, CRS/version and acceptance remain open (`docs/vnext/data-source-registry-v1.md:27`).

3. **Official building resolution is absent.** Current VNext building support is a user-provided manual claim with unknown coverage, unverified reference and proposed relation (`services/vnext/building_claim_command.py:31-32,66-97,145-151,238-289`). The building source is still `not_integrated` (`docs/vnext/data-source-registry-v1.md:32`).

4. **There is no durable multi-parcel GIS workspace.** Upload parsing and spatial checks are useful, but uploads are not persisted and official parcel geometry is disabled (`backend/api/routes_parcel_geometry.py:24-31`; `services/parcel_geometry.py:345-401`). There is no case layer, map/table selection, parcel set, versioned geometry or PostGIS workspace.

5. **Planning and zoning are not integrated.** The registry marks planning `not_integrated`, with jurisdiction, effective-date, licensing and coverage work unresolved (`docs/vnext/data-source-registry-v1.md:30`). No runtime module/route is in the application router inventory (`backend/api_main.py:21-38,186-203`).

6. **Redevelopment / urban-renewal intelligence is not integrated.** The registry marks it `not_integrated` and calls out fragmented project/status semantics over time (`docs/vnext/data-source-registry-v1.md:31`). There is no temporal project/site workflow.

7. **Current listings are absent.** PLVR transactions do not provide current inventory. Listings require a licensed partner and explicit relist/dedup/takedown/retention acceptance; URLs do not authorize scraping (`docs/vnext/data-source-registry-v1.md:34,47-48`).

8. **Title and document workflows are absent.** The title source is `partner_required` and highly sensitive; no legal basis, provider, vault, signed delivery or audit workflow exists (`docs/vnext/data-source-registry-v1.md:33`). User parcel upload is request-scoped, not a document system (`backend/api/routes_parcel_geometry.py:24-31`).

9. **Ownership is not resolved.** Parcel point/upload contracts explicitly disclaim ownership and legal boundary conclusions (`services/parcel_geometry.py:31-38`). No ownership entity, rights, effective-time, confidence, consent or restricted-access workflow exists.

10. **CRM and team collaboration are not a product workflow.** Workspaces, memberships, roles, cases and audit foundations exist (`database/migrations/013_vnext_workspace_case_foundation.sql:57-247`), but contacts, leads, tasks, activities, follow-ups, invitations, assignments, comments and team UI do not.

11. **Native evidence-grounded AI is absent.** The current LLM service always returns a template, even if an API key exists (`services/llm_service.py:18-32`). There is no retrieval across the evidence ledger, permission filtering, citations, conflict/unknown preservation, model/prompt audit or evaluation gate required by `docs/vnext/evidence-architecture-v1.md:230-259`.

12. **Professional Workspace is not implemented.** The current workspace is a browser-local consumer analysis surface, and “pro mode” is a display preference (`frontend_next/components/immersive-viewing-workspace.tsx:32-55,96-132`; `frontend_next/lib/view-mode.ts:4-15`). The target case route, map/table canvas, evidence rail, documents, tasks/activity, CRM/team and role-aware shell remain architecture (`docs/vnext/architecture-overview-v1.md:274-296`).

## 8. Gate 6 — Next six bounded implementation slices

These slices are in dependency order. They deliberately do not attempt all twelve debts at once.

### Slice 1 — Stage 1 live truth closure

- **User value:** a signed-in workspace member can create a durable case, resolve an address, explicitly confirm a candidate and reopen the same case with an auditable identity.
- **Bounded scope:** production-like Supabase JWT/RLS acceptance; migrations 013–017; default-off flag rollout; one approved identity observation provider; main-journey handoff to the confirmed case. Preserve human confirmation and no-match/unknown states.
- **Prerequisites:** owner-approved TGOS or alternative identity-source terms/quota/coverage pack; live test tenant; deployment secrets; rollback runbook.
- **Likely modules/files:** `services/vnext/auth.py`, `services/vnext/authorization.py`, `services/vnext/identity_resolution.py`, `services/vnext/tgos_observation_provider.py` or a new accepted provider, `backend/api/v1/property_identity.py`, `frontend_next/lib/vnext-auth-session.ts`, `frontend_next/lib/vnext-identity-client.ts`, `frontend_next/components/vnext-property-identity-workflow.tsx`, `frontend_next/app/page.tsx`, migrations/runbooks if defects are found.
- **Acceptance gate:** hosted real JWT tests prove tenant isolation and roles; one authorized provider produces candidate evidence; unresolved/conflict cases cannot be confirmed; flags support canary/rollback; Hero-to-durable-case path is exercised; provider, license, coverage and failure acceptance is recorded.
- **Explicitly excluded:** parcel polygons, buildings, listings, title, CRM and AI.

### Slice 2 — Official single-parcel NLSC resolution pilot

- **User value:** from a confirmed property/location, the user can retrieve candidate official parcel identity and geometry for one supported pilot area, see provenance/coverage/effective time, and confirm the parcel without mistaking it for ownership or survey certification.
- **Bounded scope:** select one exact NLSC cadastral dataset/API; complete application/authorization; implement one backend-only candidate resolver; normalize CRS/version; write VNext parcel evidence/reference/proposed relation; retain explicit human confirmation and no-match/multi-match states.
- **Prerequisites:** Slice 1; fixed Taiwan gateway evidence if required; NLSC approval/terms/attribution; test parcels and official expected results.
- **Likely modules/files:** `services/parcel_geometry.py`, `services/adapters/nlsc_gateway_adapter.py` or a new cadastral adapter, `services/vnext/parcel_evidence.py`, `services/vnext/parcel_hypothesis_command.py`, `services/vnext/identity_resolution.py`, `backend/api/v1/property_identity.py`, new source-registry/runbook updates and provider contract/real-provider tests.
- **Acceptance gate:** authorized real-provider cases cover exact, multi-match, no-match, stale/version and outage paths; official geometry never becomes ownership/legal-area evidence; all evidence fields and license status are populated; unsupported areas fail closed.
- **Explicitly excluded:** nationwide claims, multi-parcel editing, buildings, zoning, redevelopment and ownership.

### Slice 3 — Durable multi-parcel GIS case set

- **User value:** a professional can attach several parcel candidates to one durable case, select/deselect them on a synchronized map/table, preserve source/status, and reopen the set with the same geometry versions.
- **Bounded scope:** parcel-set and geometry-version persistence; PostGIS storage/indexes; official and user-provided geometry kept distinct; map/table selection; aggregate geometric area clearly separated from legal area; audit events.
- **Prerequisites:** Slice 2 parcel contract and at least one accepted official geometry source; workspace/case RLS verified by Slice 1.
- **Likely modules/files:** new VNext GIS migrations/repositories/services/routes, `backend/api/v1/property_identity.py` or a bounded GIS router, `frontend_next/components/map/*`, a new VNext case GIS component, `services/parcel_geometry.py`, evidence-link writers.
- **Acceptance gate:** RLS isolation; reopen/version/audit tests; map/table synchronization; multiple official/user geometries; geometry limits/CRS validation; no legal-area/ownership inference; deterministic handling of overlap and invalid shapes.
- **Explicitly excluded:** editing official boundaries, cadastral surveying, zoning calculations, documents and public sharing.

### Slice 4 — Official building candidate resolution pilot

- **User value:** within a confirmed parcel set, the user can review official/authorized building candidates, distinguish building from unit, and confirm parcel-building relationships with source and effective-time evidence.
- **Bounded scope:** one selected building source and pilot jurisdiction; building identifiers/basic attributes; candidate/conflict/no-match states; parcel-building proposed relation; explicit human confirmation; correction trail.
- **Prerequisites:** Slices 1–3; selected authoritative/partner building source and approved rights; building identity contract and test corpus.
- **Likely modules/files:** `services/vnext/building_claim.py`, `services/vnext/building_claim_command.py`, `services/vnext/parcel_building_relation_command.py`, new provider/normalizer/repository, `backend/api/v1/property_identity.py`, graph/evidence DTOs and VNext review UI.
- **Acceptance gate:** real-provider pilot cases cover one/many/no building; user claims cannot masquerade as official; parcel/building/unit identities stay separate; confirmed relation is evidence-bound and tenant-secured.
- **Explicitly excluded:** nationwide coverage, permit-document vault, valuation changes, zoning and redevelopment.

### Slice 5 — One-jurisdiction planning and redevelopment evidence

- **User value:** for confirmed parcels/buildings in one pilot jurisdiction, the user can see current planning/zoning observations and redevelopment project overlap/status with effective dates, source versions and manual-verification warnings.
- **Bounded scope:** at most one zoning/land-use dataset and one redevelopment dataset from one jurisdiction; read-only observations/overlays; temporal applicability; unknown/coverage states; evidence links; no legal interpretation.
- **Prerequisites:** Slices 2–4; jurisdiction/source registry; approved terms; known update cadence; correction/manual-verification route.
- **Likely modules/files:** new planning/redevelopment adapters and VNext services/routes, evidence schema writers, GIS overlay components, source registry and operations runbook.
- **Acceptance gate:** real-provider fixtures and acceptance cases prove in-area, out-of-area, no-record, stale/version-change and outage behavior; UI shows source/effective date/coverage; no definitive development-right or investment conclusion is generated.
- **Explicitly excluded:** additional municipalities, automated feasibility/yield, permit application, legal opinion and AI summary.

### Slice 6 — Licensed active-listing observation pilot

- **User value:** a case can compare recent closed transactions with current asking-price observations from one licensed feed, while clearly showing that partner inventory is incomplete and asking price is not transaction value.
- **Bounded scope:** one partner/feed; listing identity, status, observed timestamps, relist/dedup and takedown handling; case attachment; source/evidence display; bounded comparison to PLVR without blending the measures.
- **Prerequisites:** Slice 1 durable case/identity; partner contract; privacy/retention/redistribution decisions; listing identity contract and takedown runbook.
- **Likely modules/files:** new listing adapter/repository/migrations/routes, evidence writers, market/listing UI, `services/property_search_service.py` only through a separate listing boundary, case comparison/report updates.
- **Acceptance gate:** licensed real-feed acceptance; idempotent updates; relist/dedup/takedown tests; inventory-coverage disclosure; asking and transacted prices remain separate; no scraping path; RLS and retention tests pass.
- **Explicitly excluded:** multi-partner aggregation, public raw-feed export, seller CRM, title/ownership, automated outreach and AI recommendations.

After these six slices, title/documents, CRM/team workflow, evidence-grounded AI and the full Professional Workspace shell remain later stages. They should not be pulled forward before identity, parcel/building and source-rights foundations are production-credible.

## 9. Final rebaseline summary

| Item | Result |
| --- | --- |
| Consumer Decision Product | `PARTIAL` |
| Professional VNext Platform | `FOUNDATION` |
| Hero promise coverage | `PARTIAL` — broad demo/consumer coverage, not full production proof |
| Professional Workspace | `NOT_STARTED` |
| External official-data integration | `PARTIAL` — PLVR/ARDSWC and optional provider adapters exist; live authorization/coverage is not generally proven |
| NLSC integration | `FOUNDATION` — LANDSECT context + optional terrain gateway + disabled parcel-vector seam; not official parcel/building resolution |
| Stage 0 | `CLOSED` |
| Stage 1 | `SUBSTANTIAL` |
| Stage 2 | `FOUNDATION` |
| Stage 3 | `FOUNDATION` |
| Stage 4 | `PARTIAL` |
| Stage 5 | `NOT_STARTED` |
| Stage 6 | `FOUNDATION` |
| Stage 7 | `FOUNDATION` |
| Stage 8 | `NOT_STARTED` |

**GO / NO-GO:** `NO-GO` for representing the current repository as the complete PropTech7/iTaiwan-inspired consumer product, Professional VNext platform, production-mature official-data integration, or Professional Workspace. `GO` only for a controlled, disclaimer-led competition demonstration and for executing the six bounded slices above under their explicit acceptance gates.
