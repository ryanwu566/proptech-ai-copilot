# Final Production Acceptance v2

**Controlled Beta verdict: NO-GO.** Acceptance recorded 2026-10-11T13:16:41.130232+08:00 (Asia/Taipei).

The release identity, official-data/provider, fleet cost/security, production recovery, and real acquired-case journey gates are not closed. Local implementation and synthetic browser passes cannot compensate. No product feature, assertion, timeout, skip policy, dependency lock, security rule, or budget was changed. Exactly one documentation/evidence commit is authorized; no push, merge, deploy, cloud mutation, provider-account change or production database write was performed.

The categorical evidence is `final-production-acceptance-v2-evidence.json`; detailed observations, commands/counts, failure history and hashed local artifacts are in `final-production-acceptance-v2-validation.json`. Both reuse existing v1 schemas and the current evidence generator/guardrail evaluator; v2 identifies this acceptance iteration, not a competing framework. Suggested filenames follow the request. Retained operator artifacts are under ignored `.local/acceptance-v2/`.

## Requested forty-point report

| # | Acceptance item | Result |
| --- | --- | --- |
| 1 | Frozen candidate | c9ab5f61a45f7f704326af66cb0bea02740b9927 |
| 2 | Frontend deployed SHA | c9ab5f61a45f7f704326af66cb0bea02740b9927; SHA PASS, complete identity BLOCKED (environment/release unconfigured) |
| 3 | Backend deployed SHA | c9ab5f61a45f7f704326af66cb0bea02740b9927; build-bound SHA PASS, identity coherence BLOCKED (runtime mismatch) |
| 4 | Frontend/backend compatibility | BLOCKED; SHA parity PASS, backend api-contract-v1/schema-007 declarations compatible; frontend release contract absent |
| 5 | Backend health/readiness | PASS observation: ok, ready, production, database available, durable yes |
| 6 | Runtime configuration | 10 backend categorical items PASS; overall BLOCKED; frontend, hosts, enforcement, maintenance, kill-switch actual state and applied ledger unverified |
| 7 | Provider acceptance matrix | 23 authoritative capabilities; no production provider accepted; matrix below |
| 8 | Artifact acceptance matrix | 13 authoritative artifacts; hosted activation/date/checksum/coverage unverified; matrix below |
| 9 | Global security/cost | BLOCKED: 15 external controls; application/instance fixtures do not prove fleet/account controls |
| 10 | Migration status | 20 registered, 15 managed, latest 019, next 020; static/native PostgreSQL 17 E2E PASS, production ledger BLOCKED |
| 11 | Backup status | Synthetic custom archive integrity PASS (359,664 bytes); production backup/retention/offsite BLOCKED |
| 12 | Restore status | Native PostgreSQL 17 synthetic row/ledger/RLS inventory equality PASS, cleanup PASS; production restore/ACL/artifact recovery BLOCKED |
| 13 | Rollback status | BLOCKED: candidate→first-parent immutable/API/schema checks pass, frontend consumer tree differs and accepted artifact map missing; no hosted rollback |
| 14 | Homepage journey | Homepage/address entry PASS; realistic acquired case→full real-provider journey BLOCKED |
| 15 | Guided Case Simulation | PASS hosted: seven stages × four locales × three widths = 84 cells; Back/Next/restart/exit/Escape/focus/reduced motion; zero provider attempts and unchanged storage |
| 16 | Market/Comparable Explanation | Saved synthetic rendering PASS: 10 selected, 3 excluded, deterministic/context distinction, unknown parking, straight-line label, frozen reference; valuations unchanged; real acquisition NOT_TESTED |
| 17 | Location/Commute | Saved synthetic rendering PASS with blocked map tiles; live providers NOT_TESTED; 1024px English overflow FAIL |
| 18 | Risk | Saved synthetic unknown/no-match limitations PASS; official layers/coverage NOT_TESTED |
| 19 | Finance | Saved synthetic 55,111 TWD/month preserved; missing affordability/costs disclosed; real-provider finance journey NOT_TESTED |
| 20 | Evidence Checklist | PASS browser-local: not_checked/pending/reviewed/recheck, persistence/isolation/stale review; manual review not official verification |
| 21 | Save/Reopen | PASS deployed browser-local save/card reopening; hosted durable customer-case persistence NOT_TESTED |
| 22 | 2-case Compare | PASS deployed synthetic snapshots, distinct case state and finance, unchanged storage, zero provider attempts |
| 23 | Report | PASS frozen synthetic snapshot/history/provenance; all-locale trust/UI acceptance FAIL; real acquired case report NOT_TESTED |
| 24 | A4 PDF | Two actual deployed-renderer PDFs: 18 A4 pages each, zero out-of-page text spans and empty pages; sources/unknowns/finance/manual disclaimers present; legacy locale issue and printed next-step link text remain |
| 25 | 390/1024/1440 | 390/1440 bounded overflow probes PASS; 1024 English Location FAIL at scrollWidth 1035 |
| 26 | zh-TW/en/ja/ko | Demo and Comparable localization PASS; legacy headings/copy FAIL in en/ja/ko (21/32 settled 1440px heading cells) |
| 27 | Accessibility | Sampled keyboard focus/labels/reduced motion and Demo dismissal PASS; manual screen-reader and full WCAG NOT_TESTED |
| 28 | Zero-provider journeys | Demo/Save/Reopen/Compare/Report/Checklist/Comparable expansion: zero attempted provider requests in bounded hosted runs; no hidden backend telemetry available |
| 29 | Bundle/headroom | Local production: 2,974,397 bytes; 25,603 headroom; largest JS 597,609. Hosted observed lower bound 2,322,925; complete inventory NOT_VERIFIED |
| 30 | Full Python result | 3,615 passed, 32 skipped, 1 warning; supplemental 59 passed with 30 original skips closed, 2 historical state integrations unexecuted; do not sum duplicate tests |
| 31 | Frontend result | 270/270 deterministic, 0 skipped; typecheck/build PASS; lint 0 errors/23 warnings; production audits 0 vulnerabilities, dev exception valid until 2026-11-04 |
| 32 | Browser result | Local Chrome 71 passed/0 failed/0 skipped, no retries. Hosted initial 102 probes: 100 PASS/2 FAIL; corrected invariants 5/5; settled locale/responsive failures retained separately |
| 33 | Production blockers | Identity metadata; unaccepted providers/artifacts; fleet/quota/spend/paging proof; applied schema/hosted recovery; real acquired/persisted user journey; locale/overflow; complete hosted asset inventory |
| 34 | External owner actions | Release, database, provider/data, ingress/reliability, billing, incident and product owners: actions below |
| 35 | Independent review | Initial read-only review agrees NO-GO; final artifact review recorded in validation JSON before commit |
| 36 | Controlled Beta verdict | NO-GO |
| 37 | Exact reason | Non-compensable release identity, trust/data, security/cost, operational recovery and real journey gates remain blocked; local passes cannot compensate |
| 38 | Safe to open acceptance PR? | YES for evidence/documentation review only; no PR opened or pushed |
| 39 | Safe to merge acceptance evidence? | YES after normal review; does not authorize beta, deployment or merge; no merge performed |
| 40 | Certifies Paid SaaS? | NO; no separate commercial-operation acceptance supplied |

## Freeze and exact release logic

The initial worktree was clean on `release/final-production-acceptance-v2`. HEAD, local origin/main and read-only `git ls-remote origin refs/heads/main` matched `c9ab5f61a45f7f704326af66cb0bea02740b9927`. Commit message: `Merge pull request #175 from ryanwu566/feat/comparable-explanation-v1`. A later check at 2026-10-11T13:05:19.107557+08:00 still matched. The evidence commit is separate from this frozen product candidate and is not deployment proof. Main must not silently replace the candidate.

Frontend `/release-version` returned HTTP 200, 160 bytes, exact 40-character candidate SHA, but `environment=unconfigured` and `release_version=unconfigured`. The SHA observation passes; complete frontend identity is BLOCKED. Backend `/release-version` returned HTTP 200, 2,012 bytes, exact candidate SHA, UTC build timestamp `2026-10-11T04:29:10.830194+00:00`, build ID `sha256:76ff6169f494327ec12de7aecc2fed1c10398655c415fc2c7fb9e7b34f27c8f1`, `identity_source=render-checkout`, `identity_status=PASS`, and `runtime_sha_matches_build=false`. The immutable build reports this candidate; there is no evidence that its binary is an older SHA. The disagreement is an explicitly failing runtime claim, so full identity is BLOCKED rather than treating health or the `identity_status` label as acceptance.

Backend release version `release-2026-10-10-c2ddf18` is an observed runtime label, not an independently supplied intended release contract. Its older date/short suffix is not proof of binary staleness. The hosted smoke used that observed value explicitly as its expected label to test coherence; it remains unconfigured on the frontend. Existing acceptance policy requires both exact candidate SHAs and matching production release/environment metadata. No approved independent-component compatibility exception was supplied.

`/compatibility` returns api-contract-v1/schema-007 and compatible. Repository code generates this declaration; `/release-version` explicitly marks schema compatibility declared. Neither proves an applied ledger, a release-bound frontend consumer contract, or provider provenance. `/source-status` describes canonical pilot records, empty until real records; it is not a PLVR/risk/provider health endpoint.

The ten backend runtime configuration categories report PASS: database, session-secret presence, CORS, public base URL, release/API/schema versions, production mode/readiness and backend public origin. CORS preflight and passive security-header checks pass. Safe projections do not prove actual API_ALLOWED_HOSTS values, trusted forwarding, ingress denial, maintenance/kill switches, secret rotation/IAM, frontend build config or the live schema ledger. These remain unverified; secrets were not printed.

## Provider matrix

This matrix comes from all 23 `services/provider_config_contract.py:REQUIREMENTS` entries, including TGOS and PLVR updates beyond the legacy scorecard's provider gates. Each capability has repository code/offline contract coverage. No production capability is accepted merely by this fact. Collector process configuration categories are separate from hosted configuration. No direct upstream provider check or expensive Satellite generation was attempted.

| Capability | Configured | Authorized / reachable / hosted contract / fresh | Production acceptance |
| --- | --- | --- | --- |
| active-fault | NOT_TESTED | NOT_APPLICABLE for automated verification; manual only | BLOCKED |
| ardswc | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| ardswc-debris-flow | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| ardswc-landslide | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| finder | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| geocoding | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| gsmma | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| liquefaction | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| maps | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| market | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| nlsc | UNAVAILABLE | NOT_TESTED in each dimension | BLOCKED |
| places | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| plvr | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| ris | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| routes | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| satellite | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| street-view | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| tax-legal | NOT_TESTED | NOT_APPLICABLE for automated verification; manual only | BLOCKED |
| tdx | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| tgos | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| trend | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| valuation | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |
| wra | NOT_TESTED | NOT_TESTED in each dimension | BLOCKED |

NLSC gateway unavailability is specifically reported by hosted health. Public ARDSWC/liquefaction paths requiring no credentials still need live contract/coverage/freshness evidence. Maps/Street View display is not numeric NLSC terrain proof. BLUE Market/Finder/Trend do not inherit GREEN Valuation availability. Active-fault/tax-legal automation is not applicable; professional/manual verification remains required. Satellite is not accepted or assumed safely disabled without runtime proof.

## Artifact matrix

All 13 current authoritative `services/production_artifact_registry.py:REGISTRY` entries are included. No accepted remote manifest/artifact bytes, immutable source release, deployed activation or geographic fixtures were supplied. Processor version/current-only files do not establish publication history or PIT validity.

| Artifact | Storage | Local presence | Hosted acceptance |
| --- | --- | --- | --- |
| wra-flood | r2 | UNKNOWN | BLOCKED; activation/source date/checksum/coverage NOT_TESTED |
| gsmma-sensitivity | r2 | UNKNOWN | BLOCKED; activation/source date/checksum/coverage NOT_TESTED |
| ardswc-landslide | remote_mvt | UNKNOWN | BLOCKED; activation/source date/checksum/coverage NOT_TESTED |
| ardswc-debris-flow | remote_mvt | UNKNOWN | BLOCKED; activation/source date/checksum/coverage NOT_TESTED |
| gsmma-liquefaction | remote_api | UNKNOWN | BLOCKED; activation/source date/checksum/coverage NOT_TESTED |
| nlsc-village-boundary | local_or_r2 | UNKNOWN | BLOCKED; activation/source date/checksum/coverage NOT_TESTED |
| nlsc-terrain | remote_gateway | UNKNOWN | BLOCKED; activation/source date/checksum/coverage NOT_TESTED |
| ris-population | database | UNKNOWN | BLOCKED; activation/source date/checksum/coverage NOT_TESTED |
| plvr-blue | database | UNKNOWN | BLOCKED; activation/source date/checksum/coverage NOT_TESTED |
| plvr-green | database | UNKNOWN | BLOCKED; activation/source date/checksum/coverage NOT_TESTED |
| tdx-mrt | process_memory | UNKNOWN | BLOCKED; activation/source date/checksum/coverage NOT_TESTED |
| road-display | local | PRESENT | BLOCKED; activation/source date/checksum/coverage NOT_TESTED |
| road-source | local | PRESENT | BLOCKED; activation/source date/checksum/coverage NOT_TESTED |

Local road-display presence/schema is bounded repository proof. Road-source presence is checked separately; missing or unverified items are retained. Local checksums are not assertions about deployed bytes.

## Guardrails and recovery

Application/instance-level anti-abuse, endpoint limits, concurrency, operation reservations, safe errors, cancellation, body bounds, provider budgets and kill-switch code have local fixture coverage. `SharedAdmission` is a future Protocol; `local_only` is the sole implemented mode. Local counters never become fleet protection.

All 15 owner controls remain BLOCKED: trusted ingress/direct-backend bypass, cross-instance reservations, edge/WAF, Google server quota, Google browser restrictions/quota, Earth Engine quota, other metered-provider inventory, billing alerts, enforced global currency ceiling, kill-switch rollout, monitoring/alert delivery, production backup, production restore, hosted rollback and incident escalation. Health readiness and CORS do not attest to those controls. No cloud exports or delivered paging/billing receipts were supplied.

The migration registry validates 20 entries, 15 managed migrations, latest sequence 019 and next 020. A fresh owned native PostgreSQL 17 cluster on an ephemeral loopback port applied the current 15 managed migrations, exercised the transactional validator and selected current RLS/integration tests, and restored a synthetic custom archive. Canary rows, ordered ledger checksums and RLS inventory matched; the archive hash and cleanup are recorded in validation. This was separate from the PostgreSQL 16 Docker runner, which failed at local image inspection because its daemon was unavailable. PostgreSQL 17 proof is not PostgreSQL 16 or hosted recovery proof. The 59 supplemental tests cover 30 initially skipped tests; two historical Phase 2E/2F target/state integrations remain unexecuted. Counts overlap the full suite and are not added together.

Production backup integrity, age/retention/offsite coverage, restore access/RPO/RTO, production-role/ACL restore and artifact recovery remain BLOCKED. No production backup was read or restored. Historical committed drills are explicitly old synthetic/offline records, not fresh proof for this release.

The fresh immutable rollback checker compared the frozen candidate with first parent `0b2e74a87adfc0f0bac57d30afedff7955233d61`. Immutable/API/schema checks passed, but the frontend consumer tree differs and no accepted artifact inventory exists. It correctly returned BLOCKED. No same-SHA self-check, fabricated artifact checksum, traffic switch or hosted rehearsal was used as rollback proof.

## Deployed journey, browser evidence and limitations

Fresh disposable Chrome contexts loaded the actual deployed site and entered a realistic address. Provider acquisition/case creation was not invoked: those logical requests may fan out into multiple billable operations and accepted credentials/budget/provenance were not supplied. The complete real-provider journey and hosted durable case persistence are BLOCKED. Browser-local saving is a distinct product capability and was actually exercised.

The Demo was tested on the deployed frontend with browser-local storage canaries. Seven stages, animated input/case creation, market/location/commute/risk/finance/checklist/report reveal, all locales/widths, semantic stage preservation on locale switches, Back/Next/restart/exit, Escape, initiating-button focus restoration and reduced motion passed. No case storage change or provider attempt was observed.

Saved-case rendering used two explicitly synthetic browser-local records from existing fixtures, not mocked HTTP provider responses. No synthetic provider result was fulfilled over the network. The Taipei valuation fixture retained its own geographic context; unrelated Taichung market data was removed rather than relabeled. The feature checks validate deployed rendering only, not upstream authorization, official freshness or true property identity.

Comparable Explanation showed ten selected and three bounded excluded examples, actual deterministic ranking/weighting/window rules, context-only floor/parking, unknown parking, approximate straight-line distance and frozen UTC references. Ranking is not confidence, no AI-similarity inference is added, and complete valuation storage remained unchanged after expansion. Checklist states persisted and remained isolated across cases; changed underlying risk evidence resulted in recheck. Report snapshots remained frozen when storage changed, preserving manual history without turning unknowns into safety/official verification. Compare kept two cases isolated and finance values visible.

Each zero-provider operation had zero automatic provider attempts: Demo, Save, Reopen, Compare, Report, Checklist and Comparable expansion. Network interception allowed only read-only frontend assets/pages/RSC traffic; provider, analysis and mutation requests were blocked and counted rather than fulfilled. Location/Risk attempted OpenStreetMap display tiles, which were stopped before transmission and are explicitly not reported as zero-provider journeys. Server-internal telemetry was not available; this is bounded client observation plus source/local fixtures, not fleet traffic attestation.

The initial hosted matrix performed 102 probes: 100 passed and two failed. One was a real 1024px English Location overflow; the other used an English checklist selector on a Chinese legacy surface. A corrected independent invariant run passed all five workflow checks. A subsequent stale-review wording mismatch was resolved by asserting the actual semantic recheck state, with no product assertion changed. Settled English followup found 15/18 legacy heading samples in Chinese; the 1440px four-locale matrix found 21/32 heading cells failed. Demo and Comparable copy switch, while Market/Overview/Location/Risk/Finance/Compare/Report retain legacy Chinese UI in en/ja/ko. The 1024px Location overflow reproduced after language settled (1,035px scroll width). No failure was labeled flaky, and these product defects were not repaired in this lane.

Both actual hosted-renderer PDFs contain 18 A4 pages (594.96 × 841.92 pt), zero out-of-page text spans and no empty pages. All pages were inspected as contact sheets; representative first-page, risk, finance and source/manual-summary evidence was inspected at readable scale. Finance 55,111 TWD/month, sources, unknowns, comparable limitations and manual-review/official-verification distinctions remain visible. Navigation/export/save controls are hidden, but next-step work-area hyperlinks are still printed as action text; all-locale PDF acceptance fails with the legacy-copy issue. These are synthetic reports, not accepted real-property reports. Binary hashes and paths bind the inspected artifacts.

Hosted accessibility coverage is bounded: reachable controls, visible labels, semantic text, Demo dismissal/focus restoration, reduced motion and a 2px visible keyboard focus sample. Local existing browser fixtures expand these checks. Manual screen-reader/full WCAG and alternate browser-engine audits were not performed.

## Gates, performance and failure accounting

Full Python: 3,615 passed, 32 skipped, 1 warning in 389.64s. PostgreSQL supplemental: 59 passed, 0 skipped, 1 warning in 125.04s. Deterministic frontend: 270 passed, 0 skipped across 45 files. Selected current acceptance Chrome suite: 71 passed, 0 failed/0 skipped, no retries. Typecheck/build pass; lint has zero errors and 23 existing warnings. The release-quality wrapper's documented skip flags avoid repeating the separately completed full Python/build runs; its nine static contracts pass and its standalone test/build fields remain not_run, without rewriting them as PASS. Security/performance, production operations, migration static/pilot contracts, repository hygiene and route/bundle gates passed locally.

Python runtime manifest resolution audited 68 dependencies with zero vulnerabilities. This Windows/Python 3.13 resolution does not certify the unlocked deployed Python 3.12/Linux inventory. Production npm audit has zero findings. Full npm audit reports six high/two moderate affected development nodes; existing GHSA-vfj7-8cjw-p6xm exception passed with the actual `npm explain braces` chain and expires 2026-11-04. No dependencies or exception policy were changed. Tool versions differ from repository declarations and are recorded explicitly.

The production build measured 2,974,397 bytes, with largest JavaScript 597,609 bytes and 25,603 bytes remaining under the unchanged 3,000,000-byte homepage ceiling. Route budgets passed. The generic 8,000,000-byte asset gate alone is not sufficient. Hosted browser asset reads measured a lower bound only; the complete deployed asset inventory remains unverified. E2E builds use separate fixture flags and never replace this recorded production-build result.

Hosted passive smoke sent its existing bounded 13 requests and returned BLOCKED. It failed frontend environment/version, backend build/runtime identity and the raw-homepage offline keyword check. The final item cannot establish whether a lazy Demo/competition disclosure is absent: Guided Demo disclosure was independently exercised and passed, while the separate competition flow remains NOT_TESTED. The raw failure is retained as BLOCKING_UNKNOWN rather than being changed to PASS or asserted to be a missing Demo disclosure.

ML Targets A/B remain BLOCKED, historical publication proofs/PIT-valid/approved training cohort remain zero, and ML-B may not begin. No ML valuation, CatBoost result, prediction interval, AI confidence or official fair-value capability is accepted. This run sampled visible deployed claims and the explicit Comparable limitations; it is not a full content-corpus certification.

## Owner actions and review boundary

| Owner role | Required action before reacceptance |
| --- | --- |
| Release owner | Supply intended release label/environment; correct frontend build metadata and backend runtime/build disagreement through a separately authorized change; freeze resulting actual candidate and collect fresh endpoint proof. |
| Database owner | Read and review the actual applied checksum ledger through an approved safe projection; supply offsite/retention/backup integrity and disposable/staging production-backup restore validation, role/ACL compatibility and RPO/RTO proof. |
| Provider/data owner | Supply exact deployed source/artifact versions/checksums/publication dates/coverage and accepted fixtures; authorize bounded physical provider checks and evidence for necessary capabilities, with optional capabilities correctly blocked/disabled. |
| Ingress/reliability owner | Prove ingress/header/allowed-host/direct-bypass handling, fleet reservations or bounded deployment topology, WAF/body/bot coverage, protected monitoring and delivered alerts. |
| Billing/provider owner | Supply effective quotas/restrictions covering every consumer/project, tested alert delivery and enforceable global spend/shutdown controls. |
| Incident/release owner | Prove fleet kill-switch rollout/recovery, immutable compatible hosted rollback and privately assigned primary/backup paging authority. |
| Product/QA owner | Address hardcoded legacy locales and the reproducible Location overflow in a separate product lane; perform a bounded real acquired-case/persistence/report journey after safety/provider gates close. |

Independent review checked false GO, identity/runtime disagreement, all registry entries, static schema declarations, local/fleet separation, old recovery provenance, ML boundaries and the strict ceiling. Final artifact findings and resolution are in validation. The acceptance commit contains only four documentation/evidence files. Acceptance evidence is safe to review and merge as evidence after normal review; it does not authorize Controlled Beta or Paid SaaS. No PR was opened, no push/merge/deploy occurred, and no production mutation was authorized.
