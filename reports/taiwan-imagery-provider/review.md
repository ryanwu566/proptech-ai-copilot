# Whole-branch independent review

Spec verdict: APPROVED for local implementation, with the two nonblocking consistency issues below.

Quality verdict: APPROVED. No Critical or Important findings identified.

Security verdict: APPROVED for the reviewed code scope. This is not runtime activation acceptance.

Reviewed the plan, progress ledger, complete supplied branch diff including new files, prior task reviews, current affected implementation/tests, and supporting cache, admission, metrics and immutable migration 021 code. No implementation edits, test reruns, live provider/network calls, credential reads, runtime changes, commits or subagents were performed. Only this requested review report was written. Reported test/typecheck results were treated as supplied evidence. The controller subsequently reported expanded affected-source ESLint passing with zero errors, typecheck passing, and seven frontend tests passing; the two browser files were ignored by repository lint configuration and the browser suite was not run.

The request contract remains latitude/longitude only. PHOTO2 is the default, fixed 512px EPSG:3857 WMS reference with unknown capture vintage and nullable cloud/window metadata. CSRSR requires explicit noncommercial admission and an exact official capabilities-confirmed annual layer; the adapter and URL allowlist enforce 1996–2025. Taiwan paths do not resolve the EE manager or ADC. Frontend requests remain manual, maintain coordinate/controller race guards, and keep images in component memory without risk-score or Saved Case changes.

Transport retains exact HTTPS authorities/paths, normal certificate validation, no redirects or environment proxies, raw-byte/MIME/encoding checks, safe XML parsing, bounded tile and decoded-image dimensions, and NoData rejection. Shared absolute deadlines cancel awaited HTTP I/O. One physical executor slot is acquired without queueing and released only by the actual future's completion callback, so caller timeout/cancellation cannot admit a second physical worker. Single-flight retains no completed Taiwan result. Synthetic deadline tests cover stalled headers/body; this review does not claim real DNS/TLS behavior was exercised.

Usage labels stay exact in API/process-local records and physical calls are counted at each HTTP boundary. SQL serialization alone maps PHOTO2 to `nlsc` and CSRSR to `unknown`, both accepted by migration 021; source rows are copied before mapping, retries remain transactional/idempotent, and sequential UPSERT execution accommodates alias collisions. Durable summary metadata explicitly discloses the aliases and documentation discloses loss of exclusive CSRSR breakdown. No schema migration or EE misattribution was introduced.

The unavailable Docker socket and prior host TLS rejection are honestly documented external validation limitations, not evidence of a code defect requiring weaker TLS. Candidate-image normal TLS/image smoke remains necessary before separately authorized activation. The current acceptance report does not claim that smoke passed.

## Optional Minor findings

1. **Align configuration year validation with the fixed adapter range.** `services/provider_config_contract.py:74` and `services/satellite_reference.py:257` accept years through the current/check year, so 2026 is reported configured today and reaches operation admission, while `CSRSRSpotAdapter.fetch` correctly rejects it before HTTP. Use the same fixed 1996–2025 bounds in these checks and add a service/config-status boundary assertion. This is nonblocking because production adapter and transport fail closed and cannot request an unsupported year.

2. **Successful PHOTO2 retrievals update the failure timestamp.** `services/provider_observability.py:30` excludes `limited` from success. Since valid PHOTO2 imagery deliberately returns `limited / vintage_unknown`, the new route observation records `last_failure` and never advances `last_success` for this provider. Recognize this specific successful limited result without treating every limited response as success, and verify its timestamps. API availability/provenance and physical-call accounting remain correct; the issue is passive status history.

## Final fix-wave re-review

Both earlier Minor findings are **ADDRESSED**.

1. **Year bounds: ADDRESSED.** Lightweight shared constants fix the supported interval at 1996–2025 in configuration reporting, service admission, and adapter validation. The service additionally preserves its check-date future-year rejection. Calendar rollover cannot expand support; invalid configurations return before the generator is invoked. Regression cases cover out-of-range years and an injected earlier check date.

2. **PHOTO2 history: ADDRESSED.** The observation path passes only an image-presence boolean into the registry. Only satellite/NLSC PHOTO2 with `limited`, `vintage_unknown`, and a nonempty image string receives the special success treatment. Status and unknown freshness remain unchanged, no image is retained, prior failure/success timestamps survive the opposite outcome, and other providers retain their previous behavior. Added regressions cover image absence, empty images, error/timeout outcomes, and another provider's limited result.

Final Spec / Quality / Security verdict: **APPROVED for local implementation**. No new Critical, Important, or Minor findings identified in this fix wave. Runtime activation remains outside this approval and still requires the documented candidate-image TLS/image validation.

Scope: read `final-fix-report.md` and the complete `final-fix-review.diff`; accepted the reported 65 passing focused tests and clean diff check without rerunning them. No live calls, implementation edits, or other work were performed; only this requested review appendix was added. This appendix supersedes the unresolved status of the two optional findings above.
