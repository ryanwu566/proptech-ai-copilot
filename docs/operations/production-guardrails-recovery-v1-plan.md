# Production guardrails and recovery plan

Date: 2026-10-09 (Asia/Taipei). Starting SHA:
`b4eb441a8ccf90965102f0646006dc4b0e145491`.

The user's supplied A–I specification is the design authority. Work stays in
this worktree on `ops/production-guardrails-recovery-v1`. Exactly one final
commit; no production mutation, push, merge, deployment, credential rotation,
DNS/WAF/billing changes or hosted load tests.

1. Add failing regression tests for production host/origin admission, missing
   host configuration, unsupported distributed modes and excessive cost
   overrides. Implement an ASGI ingress boundary inside existing CORS and
   telemetry, and validate before lifespan starts provider workers. Keep
   transport peers; never derive IPs from forwarding headers. PostgreSQL exists
   but no reviewed atomic limiter schema/role exists; implement a shared-control
   interface and reject enabling an unavailable driver.
2. Add failing tests for absent, expired, wrong-release, mismatched, unbounded
   or forged owner evidence. Implement a strict acceptance contract with
   exact facts, owner roles and file digests. Extend release evidence and the
   existing operations gate; repository contract PASS never implies external
   acceptance or production GO. No network calls in the default verifier.
3. Test backup metadata and rollback incompatibility failures first. Add an
   opt-in PostgreSQL rehearsal that owns an isolated container, pins a locally
   present image ID, publishes no ports, dumps only synthetic local data,
   restores into a fresh database and validates rows/constraints/checksums.
   It accepts no hosted restore URL or external dump. Add a read-only Git
   rollback verifier comparing immutable frontend/backend SHAs, migration
   checksums, API contracts and artifact digests. No down migrations.
4. Document topology, provider/edge expectations, monitoring thresholds,
   retention/offsite expectations and incident escalation. Generate bounded
   release evidence with all missing owner controls BLOCKED.
5. Run focused and full Python tests, existing security/operations/budget/
   hygiene gates, local provider-free smoke and disposable recovery. Request
   an independent read-only review, fix Critical/Important findings, record
   limitations and changed files, then create the single final commit.

Dependencies: ingress uses existing local policies; release evidence consumes
the guardrail evaluator; operations gate consumes the evidence contract;
rollback consumes the existing migration registry. No database schema change
or frontend behavior change is planned. Frontend build is needed to populate
existing route/bundle gate measurements, not to claim hosted verification.

## Latest-main integration execution plan (2026-10-10 Asia/Taipei)

Authority: the user's nine-phase PR #173 integration request. All work stays
in this already isolated worktree; one amended Lane E commit, no push, merge,
deployment or production/cloud mutation. Baseline must remain
`8469c1f22b64a0e03be03a0099c59a8483d9e0c8`.

- [x] Fetch, verify baseline/clean worktree, preserve `726b66c` on
  `backup/production-guardrails-recovery-pre-latest-main`, reset/cherry-pick.
- [x] Semantically combine `scripts/generate_release_evidence.py` parameters
  and CLI paths for #170 acceptance, #172 closure and Lane E proof validation.
- [x] Reconcile acceptance regression fixtures with both required controls;
  verify complete guardrail proof cannot bypass blocked provider closure.
- [x] Inspect original GitHub migration job logs and its failing stage; characterize
  and fix the readiness contract in `scripts/postgres_recovery_drill.py`; retain
  historical-cause uncertainty in the implementation report.
  Preserve isolation, ownership cleanup, existing timeout and migration checks.
- [x] Run disposable PostgreSQL rollback validation, managed production runner
  fresh/repeat/prefix/checksum-drift E2E, market lifecycle and restore validation.
  Derive authoritative migration inventory from the unchanged registry.
- [x] Run focused identity/provider/ingress/abuse/recovery/hosted/ML regressions,
  full Python suite, required frontend/build/audit/budget and repository gates.
- [x] Obtain independent read-only review of the full main-to-feature diff;
  resolve Critical/Important findings with regression evidence.
- [x] Update this existing implementation report and bounded validation record;
  amend the single feature commit, verify clean status and `0 1` topology.

Review focus: missing deployed proof must block closure, all guardrail owner
proof must remain required, restore must use only owned local resources,
migrations must retain ordering/checksums/repeatability, ML conclusions and
the 3,000,000-byte frontend ceiling must remain unchanged. Browser tour suites
are excluded only if frontend source is unchanged against this baseline.
