# PLVR Shadow Cutover Runbook Draft

## Status

`DESIGN ONLY - DO NOT EXECUTE AGAINST PRODUCTION`

This draft describes a future execution sequence. Every mutation step is a
STOP point requiring the independent approval named below. Phase 2D provides
no approval and executes no database or deployment operation.

## Roles

- Data owner: owns clean manifest and lineage acceptance.
- Database owner: owns additive schema and capacity review.
- Application owner: owns generation-aware valuation and Market Insight readers.
- Release owner: owns Render/Vercel contract alignment and observation window.
- Incident owner: owns rollback authority and remains present through switch.
- Audit owner: owns evidence retention and any later legacy retirement.

## Before any production work

1. Run the pure-data plan validator locally.
2. Rehearse the full plan on a disposable PostgreSQL 16 database with production
   schema shape but no production rows or credentials.
3. Prove generation-aware readers select the same generation for transaction,
   aggregate, coverage, and status queries.
4. Prove rollback pointer restoration and all failure injections.
5. Confirm backend contract/version compatibility. Vercel must not select the
   generation and no frontend deployment is needed merely to move the pointer.

## STOP A: schema objects

Approval: `A_CREATE_PRODUCTION_SCHEMA_OBJECTS`

Before approval, do not create generation tables, indexes, constraints, or the
active pointer. Required evidence includes a reviewed forward migration,
PostgreSQL integration tests, schema rollback behavior, lock analysis, capacity
estimate, and migration-ledger compatibility.

After approval in a future phase, create only additive objects. Do not alter,
rename, truncate, or drop the legacy transaction or aggregate tables. Verify
that no anonymous or browser role can access private generation tables.

## STOP B: candidate transaction load

Approval: `B_WRITE_AUTHORITATIVE_ROWS`

Freeze the candidate generation ID, source manifest SHA, artifact hashes,
normalizer and dedupe versions, expected period range, and accepted count.
Register the generation inactive. Load in bounded checkpointed batches using
the source-row idempotency key. On duplicate or manifest mismatch, roll back the
batch and stop; do not overwrite.

After loading, verify:

- loaded and distinct identities match the approved manifest baseline
- canonical invalid geography is zero
- publishable future rows are zero
- every accepted row has complete lineage
- authoritative duplicate identity count is zero
- candidate remains inactive

## STOP C: candidate aggregates

Approval: `C_BUILD_CANDIDATE_AGGREGATES`

Build aggregates and coverage only from publishable rows in the inactive
candidate generation. Do not copy live aggregate rows. Verify transaction and
aggregate generation IDs, period ceiling, metrics, freshness, manifest link,
and expected scope count. Failure keeps the generation inactive.

## Shadow verification

No mutation approval is required for read-only verification.

1. Label current reads `LIVE_BLUE` and candidate reads `CANDIDATE_GREEN`.
2. Run deterministic Market Insight summary/history, valuation, coverage,
   status/catalog, and seven golden-region fixtures.
3. Classify every difference as expected correction, added coverage, duplicate
   removal, future exclusion, unexpected value delta, unexpected missing data,
   or unexpected schema error.
4. Block the switch for any unexpected class, material unexplained scope, or
   failed hard gate.
5. Confirm no candidate result is user-facing.

## Rollback rehearsal before switch

Record the current active generation as the rollback pointer. Rehearse pointer
restoration in a non-production environment and verify transaction, aggregate,
coverage, status, and golden-region behavior. Confirm caches include generation
ID and no process uses session-level generation state.

## STOP D: production read switch

Approval: `D_SWITCH_PRODUCTION_READERS`

Required before approval:

- all hard gates pass
- shadow comparison has no unexpected class
- rollback rehearsal passes
- active and candidate generations are observable
- Render runs generation-aware backend readers
- frontend/backend contracts are compatible
- incident owner and rollback authority are present

The last point of no user-visible change is completion of this approval. In a
future approved execution, lock the single active-pointer row, verify it still
matches the recorded blue generation, record the rollback pointer, change it to
the validated green generation, verify transaction and aggregate bindings, and
commit once.

`FIRST_USER_VISIBLE_CHANGE` and `CUTOVER_COMMIT_POINT` are the commit of that
single pointer transaction.

## Immediate acceptance

Immediately after commit, verify:

- active generation and candidate generation match
- transaction and aggregate generation IDs match
- health and safe status endpoints succeed
- canonical invalid, future publishable, and lineage-missing counts are zero
- seven golden regions pass
- Market Insight does not return unexpected zero or unavailable results
- valuation retains official evidence states where evidence is sufficient
- rollback remains available

Do not wait for a long observation window to respond to a hard failure.

## Rollback

Hard triggers include health or SQL failure, schema mismatch, mixed generation,
unexpected zero results, golden-region failure, material unexplained deltas,
valuation evidence loss, coverage regression, or future leakage.

Restore the recorded blue generation ID in one pointer transaction. Verify the
committed pointer, then health, status, Market Insight, valuation, and golden
regions. Invalidate only generation-keyed bounded application caches if needed.
Keep the failed candidate intact and inactive for forensic analysis.

Target pointer reversal and verification: under five minutes. Rollback never
requires bulk row restoration.

## STOP E: legacy retirement or deletion

Approval: `E_RETIRE_OR_DELETE_LEGACY_GENERATIONS`

Phase 2D policy: `PROHIBITED`.

No legacy retirement or deletion belongs in the cutover execution. It requires
a separate later change after the observation period, backup and retention
review, audit evidence preservation, and deletion-specific authorization.

## Failure handling

The complete machine-readable failure matrix is
`artifacts/plvr_cutover_failure_matrix.json`. Every pre-switch candidate failure
leaves live blue untouched. Every post-switch integrity failure triggers pointer
rollback. If rollback itself fails, affected data surfaces enter a fail-closed
maintenance state and the incident owner follows a separately reviewed
break-glass procedure.
