# PropTech AI Copilot — Technical Case Study

## Context

Property research in Taiwan crosses organizational and technical boundaries. Transaction records, addresses, map context, hazard layers, bank-rate references, tax rules, and cadastral material are published by different organizations with different identifiers, formats, coverage, update cycles, and legal meaning. A person evaluating a property must assemble these fragments into a decision while remembering that a map marker is not a parcel, an asking or estimated price is not an appraisal, and missing hazard data is not evidence of safety.

PropTech AI Copilot began with a narrower competition-oriented tax and property demonstration. The current repository has evolved into a broader decision-support system with a live consumer workflow, public-data pipelines, spatial analysis, production operations, and an experimental professional architecture. That evolution created a useful engineering question: how can a system become broader without allowing feature breadth to outrun evidence quality?

This case study describes the repository as an engineering and research artifact. It does not claim a peer-reviewed contribution or a complete commercial property platform.

## Problem

The visible problem is fragmentation: a buyer or reviewer moves between transaction portals, maps, rate tables, hazard datasets, and personal notes. The deeper problem is semantic. Each source answers a different question:

- PLVR records describe historical registered transactions, not active supply or future price.
- A geocoder returns a location hypothesis, not legal property identity.
- Hazard polygons are scenario- and dataset-specific, not a complete safety assessment.
- Published rates are market context, not an individual credit decision.
- Tax rules require facts and documents that may be unknown at the start of a case.

A naïve integration could put these sources on one dashboard and create an illusion of certainty. A useful decision-support system instead needs to preserve provenance, missing evidence, conflict, scale, and the difference between reference and authority.

There is also an operational problem. Official data often arrives as large ZIP/CSV/SHP downloads, while users expect responsive web requests. External APIs may need credentials, have quotas, cover only some jurisdictions, or fail temporarily. The product must remain understandable when a source is unavailable.

## Design Goals

The current architecture reflects six goals.

First, organize the experience around decisions rather than provider names. A user starts from a property or location, then considers market evidence, affordability, risk, and next actions.

Second, keep calculations reproducible. Loan, holding-cost, valuation-contract, market-statistic, and tax-rule behavior should be testable without an LLM.

Third, preserve uncertainty. `unavailable`, `limited`, `no_data`, `no_match`, and `unknown` must remain different states. A missing result must not become a favorable result.

Fourth, separate evidence collection from explanation. Explanation can improve comprehension, but it cannot promote evidence or modify deterministic conclusions.

Fifth, move expensive ingestion and spatial preparation outside request handling. The web application should query bounded, validated data rather than download national datasets on demand.

Sixth, create an evolution path from a personal consumer workflow to a durable professional system without pretending that the transition is complete.

## Architecture

The live consumer system uses a Next.js frontend and a FastAPI backend. Frontend modules guide the user through property context, market/valuation, affordability, location, terrain, tax, and decision/report stages. FastAPI routers provide a transport boundary; domain services perform calculation and orchestration; provider adapters normalize external systems; PostgreSQL stores durable transaction, market, evidence, and operational data.

Current consumer cases are stored in the browser. Before writing them, the application removes detailed transactions, comparables, coordinates, and POIs. This is a pragmatic privacy and deployment choice for an individual workflow, but it does not support tenant access, collaboration, or authoritative case history.

VNext addresses those needs as a separate bounded architecture. PostgreSQL migrations define workspaces, memberships, cases, property graphs, evidence items, lineage, identity candidates, human decisions, case attachments, and multi-parcel sets. Authenticated `/v1` routes add server-side membership checks, constrained database principals, idempotency, and structured errors. Row-level security is forced and tested.

The boundary is intentional: VNext features default off, and the production identity engine has no accepted provider. The repository therefore contains a credible professional foundation without claiming a completed professional product.

### Representative End-to-End Flow

A representative review begins with a property or address input. Geocoding and location services establish usable context—but not legal identity—before bounded providers, PostgreSQL read models, and prepared spatial artifacts return market, valuation, location, and hazard evidence with their own availability and coverage states. Deterministic services then assemble calculations and readiness signals without upgrading weak evidence. The workflow ends with a reviewable synthesis: supported findings, unresolved evidence, and follow-up actions such as checking an official record or obtaining professional advice.

## Data Integration Challenges

### Transaction data

PLVR is the strongest end-to-end public-data path. Acquisition scripts accept official resources, validate release and file structure, normalize transactions, generate stable deduplication keys, and load PostgreSQL through bounded staging/upsert operations. Coverage, freshness, imports, retention, aggregates, and direct-query paths have separate contracts.

This pipeline exposed an important distinction: “official” describes origin, not completeness. The production status observed in September 2026 contained hundreds of thousands of official rows but was still partial geographically and mixed with a small labelled sample. The UI and API therefore report composition and coverage instead of using row count as a proxy for authority.

### Geographic identity

Provider identifiers do not naturally align. An address may resolve to coordinates, while cadastral systems use office, section, land-number, village, or parcel identifiers. The repository includes Google and TGOS geocoding, NLSC gateway seams, village-boundary resolution, manual parcel/building hypotheses, and identity-candidate models.

The difficult engineering decision was to avoid treating successful geocoding as confirmed property identity. VNext makes confirmation a human decision with recorded candidates, conflicts, and provenance. Until an accepted provider is available, the engine returns no production identity candidates rather than fabricating confidence.

### Hazard and terrain data

Terrain sources use different delivery models. ARDSWC exposes vector tiles; GeologyCloud exposes regional GeoJSON; WRA provides downloadable spatial datasets that need offline processing; NLSC access may require a bounded gateway; Earth Engine can generate a recent satellite reference composite.

These differences make a universal “risk API” unsafe unless layer semantics survive normalization. The implementation retains provider, coverage, date/version when available, match status, reason codes, and limitations per layer. The frontend safety gate considers completeness before it produces a decision signal.

### Operational datasets

TDX transit data and RIS demographics illustrate another challenge: a pipeline can be implemented while runtime data is absent or incomplete. During this audit, the commute snapshot was unavailable even though client, refresh, status, and lookup paths existed. RIS ingestion, query, village resolution, and UI code existed, while current production coverage was not independently verified. The portfolio therefore labels these capabilities conditional rather than simply “integrated.”

## Decision-Support Design

The consumer workflow is not designed to answer “Should I buy this property?” with a single score. It helps a person move from property context through historical transactions, affordability assumptions, location and risk evidence, unresolved facts, and next actions. This is a decision-support system rather than an automated decision-maker: readiness and reports depend on upstream evidence status, source disclosures remain visible, and professional responsibility stays with the reviewer.

TaxOracle is a useful microcosm. Deterministic rules compute eligibility and risk separately. Rule traces and missing-document prompts show why a result occurred. A template explanation translates the structure into user-facing language but cannot change the outcome. This division creates a clear path for future AI assistance: AI may summarize or navigate evidence, but evidence authority remains external to the model.

## Engineering Challenges

One challenge was preventing fallback behavior from corrupting meaning. Demo data is valuable for development and presentation, but dangerous when it is indistinguishable from official output. The valuation service now fails closed in normal mode, and demo results carry explicit origin/actionability boundaries. Map experiences that retain fallback data label it as such.

A second challenge was keeping data operations reproducible. The repository accumulated import, reconciliation, cutover, repair, retention, and coverage tools. Migration checksums, dry runs, bounded row counts, explicit confirmation flags, and frozen JSON evidence convert risky operations into reviewable steps.

A third challenge was building spatial features without overstating legal authority. Parsing a polygon and computing an intersection is technically feasible; asserting that it is the legal parcel is a separate evidence problem. Code and UI copy therefore distinguish user geometry, raster context, provider observation, candidate identity, and confirmed identity.

A fourth challenge was production hardening across a large capability surface. The backend includes CORS/origin controls, body limits, maintenance mode, safe errors, correlation IDs, security headers, metrics, and startup configuration checks. The frontend constrains API/CSP origins and provides accessible error recovery. These controls are tested as contracts rather than left only in deployment notes.

## Reliability / Validation

The repository's validation strategy mixes fast contracts with deeper integration and browser checks.

Pytest covers domain services, routes, providers, data ingestion, migration behavior, database safety, security, privacy, deployment configuration, and release tooling. Node-based tests exercise TypeScript contracts and build scripts. Playwright specifications cover guided journeys, localization, geospatial evidence, professional/identity screens, hosted smoke, privacy, accessibility, and real-provider configurations.

The release-quality gate checks the nationwide registry, market and valuation trust boundaries, property-case evidence, privacy, deployment declarations, recovery, and accessibility, alongside the Python suite and optionally the frontend build. On the audited baseline, the full Python gate passed after lockfile dependencies were installed, and the Next.js production build passed compilation, TypeScript checking, and route generation.

This evidence supports code quality and reproducibility. It does not prove all providers are authorized, current, or reachable in every environment. Hosted acceptance, disposable database tests, and hermetic checks are kept as different categories.

## Responsible AI / Trust Boundaries

The repository currently uses no external LLM at runtime. This is a limitation, but it is also a useful design constraint: it reveals which decisions can be made deterministically and what an eventual model would be allowed to do.

The VNext evidence architecture requires source environment, observation status, provenance, conflict, freshness, and authority to remain explicit. A future AI layer should retrieve only evidence the actor may access, cite the evidence it uses, preserve unknown/conflicting states, record model/prompt context, and require human approval for consequential changes. It should not create a stronger fact than its sources.

Responsible use also extends beyond AI. Valuation is not appraisal; tax screening is not advice; rate scenarios are not underwriting; satellite imagery is not cadastral evidence; and hazard layers are not a safety certificate. These boundaries appear in service contracts, tests, and UI copy rather than only in a generic disclaimer.

## What I Learned

The project reinforced that integration depth matters more than the number of connected APIs. A provider adapter is only the start; a defensible integration also needs status semantics, coverage, freshness, authorization, error handling, operations, and user-facing limitations.

I also learned to treat “unknown” as a first-class product state. Early prototypes naturally optimize the success path. In property decisions, however, the quality of the unavailable and conflict paths determines whether the system deserves trust.

The evolution from a competition demo to a production-oriented repository showed the cost of documentation drift. Features, deployment, and trust boundaries changed faster than the root narrative. Architecture records and tests preserved important decisions, but without a curated hierarchy reviewers could not distinguish current behavior from plans or history.

Finally, the consumer/VNext split clarified incremental digital transformation. A personal workflow can deliver value with local state; a professional system needs identity, authorization, durable evidence, audit, and operational ownership. Those requirements should be added explicitly, not hidden behind a “pro mode” label.

## Current Limitations

- The consumer journey and durable VNext case model are not yet unified.
- VNext property identity lacks a production-accepted provider and remains feature-gated.
- Official parcel/building identity, title/ownership, document vault, active listings, CRM, and full collaboration are incomplete or planned.
- PLVR coverage is partial and historical; it does not represent active market supply.
- Terrain and demographic integrations vary in production acceptance, coverage, and freshness.
- Commute data depends on a manual in-memory snapshot and was unavailable during the audit.
- Current explanations are deterministic templates; evidence-grounded generative AI is not implemented.
- No user-outcome study, controlled decision-quality evaluation, or peer-reviewed validation has been completed.
- The repository has no license file, so public visibility should not be described as an open-source grant.

## Future Research / Engineering Directions

The next engineering priority is not more dashboard surface. It is closing evidence loops: connect one accepted identity provider, verify tenant/RLS behavior in production, link confirmed identity to durable cases, and add official parcel evidence without collapsing observation into legal truth.

A second direction is source operations. Provider-specific acceptance records, freshness monitoring, coverage visualization, and automated canaries could turn static registry claims into runtime evidence. Historical transactions should remain separate from any future licensed active-listing model.

A third direction is evaluation. The project could support user studies that compare source comprehension, decision confidence, time-to-review, and error detection across ordinary portal-switching and an evidence-integrated workflow. Spatial decision tasks offer a particularly useful setting for studying how people interpret missing layers and conflicting evidence.

Finally, a future AI assistant could be evaluated as a constrained interface to the evidence graph: retrieve permitted items, explain provenance, surface contradictions, and propose follow-up actions while leaving confirmation to a person. That would turn “AI Copilot” from a label into a measurable human-AI decision workflow, with accuracy, citation quality, calibration, and reviewability as explicit evaluation criteria.
