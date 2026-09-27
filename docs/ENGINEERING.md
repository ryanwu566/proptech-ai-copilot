# Engineering and Validation

This document summarizes the engineering practices that are most relevant to reviewers. Detailed deployment, migration, release, and recovery procedures remain in their focused runbooks.

## Engineering principles

### Preserve uncertainty

The system models `available`, `limited`, `no_data`, `unavailable`, `error`, `not_assessed`, and `unknown` states explicitly. This prevents missing data from being rendered as a favorable result. Market and valuation paths can fail closed; terrain layers remain independently inspectable; decision summaries cannot treat unassessed terrain as an all-clear.

### Keep calculations deterministic

Loan amortization, holding-cost estimates, TaxOracle evaluation, market statistics, and valuation contracts are deterministic. Explanations are downstream of structured results. The current “AI explanation” is a stable template and cannot modify eligibility, risk scores, or legal conclusions.

### Isolate providers

Google, TGOS, TDX, PLVR, NLSC, ARDSWC, WRA, GeologyCloud, RIS, and Earth Engine behavior is separated into services, adapters, or providers. Domain code consumes normalized contracts rather than provider payloads. Credentials remain server-side except for intentionally public, restricted browser-map configuration.

### Separate online serving from data engineering

National downloads, archive validation, geometry processing, reconciliation, migration, and read-model refresh run through scripts or protected workflows. Web startup does not fetch raw PLVR, RIS, or WRA datasets. This reduces startup risk and makes data lineage reviewable.

## Reliability and trust boundaries

### Market and valuation

The official market path validates source identity, periods, row shape, duplicates, coverage, and freshness. Production property search accepts official PLVR origins. Normal valuation provider selection returns an unavailable provider when official persistence is absent; sample results require an explicit demo mode. Valuation result contracts identify origin and actionability so the frontend can avoid presenting sample or insufficient evidence as official.

### Terrain and spatial evidence

Terrain providers return layer-specific status and source metadata. The frontend safety gate uses completeness as well as hazard level. A low signal from one layer cannot erase unavailable layers. Parcel raster context, user-uploaded geometry, and official parcel identity are kept as different concepts.

### Property identity and evidence

VNext models provider observations, resolution candidates, human decisions, property/entity materialization, graph edges, evidence lineage, conflicts, and case attachment. Identity confirmation is a state transition rather than an implicit geocoder side effect. The current production engine has no accepted provider, which is a deliberate fail-closed boundary.

## Persistence and migrations

PostgreSQL migrations are registered with checksums and validated before application. The migration set covers transaction data, market read models, pilot evidence, VNext workspaces/property graphs, identity resolution, parcel sets, and demographics.

Important practices include:

- append/alter migrations rather than destructive history rewriting;
- a schema migration ledger and checksum validation;
- production-safe statement splitting, including dollar-quoted SQL;
- rehearsal and verification scripts for critical migrations;
- separate application roles and forced RLS for VNext data;
- dry-run and explicit confirmation for imports, pruning, repair, and cutover work;
- backup, restore, rollback, and disaster-recovery documentation.

## Security and privacy

The FastAPI boundary implements explicit CORS origins, origin enforcement for writes, bounded request bodies, safe error responses, correlation identifiers, maintenance mode, security headers, and production startup checks. Metrics labels are bounded to registered route templates to avoid leaking arbitrary paths.

Authenticated VNext routes reject client-supplied identity overrides and resolve workspace membership on the server. JWT validation, role checks, constrained database principals, deny-by-default RLS, and tenant-isolation tests provide defense in depth. These foundations do not remove the need for production acceptance and operational ownership.

The consumer path minimizes browser persistence. Saved cases are capped, detailed transaction rows are removed, trusted valuation summaries are compacted, precise resolved locations and POIs are cleared, and session state is separated from durable browser state. Pilot evidence has consent, export, review, publication/revocation, and deletion boundaries.

## Observability and production readiness

The backend separates liveness, readiness, compatibility, release version, source status, and health. It attaches correlation IDs, emits privacy-safe observations, supports maintenance mode, and exposes bounded Prometheus-format metrics behind configuration.

Production configuration checks report categories such as configured, malformed, or unavailable without printing secret values. Production-like startup requires a durable database, signing secret, allowed origins, and a public base URL. Optional providers can remain unavailable without preventing unrelated routes from starting.

The frontend constrains its Content Security Policy from validated HTTPS origins and blocks unsafe production API fallbacks. Error, not-found, and global-error surfaces avoid exposing stack data and provide accessible recovery controls.

## Testing strategy

At the rebased `7f442f8` baseline on 2026-09-27, the repository had 273 tracked Python test modules and 38 Playwright specifications, plus test fixtures, Playwright support files, Node tests, and build-time contracts. These counts are a dated inventory, not a permanent project metric.

### Python and service tests

Pytest covers services, routes, providers, data import, migrations, Postgres behavior, privacy, configuration, security, and release scripts. Database tests contain safety guards so production-like URLs are not used accidentally.

### Frontend contract tests

Python and Node tests inspect frontend state contracts, localized copy, trusted-evidence transfer, browser storage, accessibility, CSP origins, map behavior, decision summaries, and route budgets. These fast tests catch cross-language contract drift without requiring every check to start a browser.

### Browser acceptance

Playwright specifications cover guided journeys, hosted smoke checks, localization, property identity, professional workspace behavior, geospatial evidence, market workflows, Google Maps integration, privacy, accessibility, and real-provider configurations. Some require explicit environment setup and are not treated as hermetic unit tests.

### Release gates

`scripts/release_quality_gate.py` combines the full Python suite, frontend build, and repository contracts for registry integrity, market/valuation trust boundaries, property-case evidence, privacy, deployment, error recovery, and accessibility. Additional scripts cover production smoke, operations readiness, security/performance, release certification, migration validation, and provider canaries.

The 2026-09-27 audit baseline passed the full Python release gate and the Next.js production build after `npm ci` installed the lockfile dependencies.

## Continuous integration and operations

GitHub workflows cover release quality, security/performance, hosted smoke, official-market import, market Postgres E2E, production release operations, coverage reconciliation, commute refresh, authenticated identity smoke, and market read-model refresh.

Workflows and runbooks preserve a separation between:

- hermetic checks that read tracked source only;
- database integration tests with disposable/safe configuration;
- protected operator actions;
- live provider or hosted acceptance requiring explicit credentials and approval.

This separation makes a green local contract test meaningful without misrepresenting it as proof that every external system is live.

## Local development

From the repository root:

```powershell
python -m pip install -r requirements.txt
cd frontend_next
npm ci
cd ..
```

Start the backend and frontend in separate terminals:

```powershell
.\scripts\start_backend.ps1
.\scripts\start_frontend.ps1
```

Then open `http://localhost:3000`.

Useful validation commands:

```powershell
python scripts/release_quality_gate.py --skip-frontend-build
npm --prefix frontend_next run build
python scripts/check_repository_hygiene.py
```

Provider-backed, Postgres, hosted, and Playwright tests may require additional documented environment configuration. Do not copy production secrets into local files or command output.

## What the engineering evidence demonstrates

The repository demonstrates more than feature breadth. Its strongest engineering characteristics are:

- status-aware data integration rather than optimistic fallback;
- deterministic decision logic separated from explanation;
- spatial/provider normalization and explicit provenance;
- durable data and migration discipline;
- tenant/security foundations for a professional evolution path;
- production readiness and recovery contracts;
- tests that cover trust boundaries, not only successful UI paths.

The limitations are equally important: several provider and VNext paths are conditional, the consumer/professional systems are not yet unified, and repository tests cannot substitute for source authorization, live coverage, or user outcome research.
