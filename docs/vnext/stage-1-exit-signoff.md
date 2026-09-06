# Stage 1 Exit Signoff

Date: 2026-09-06

Branch: `vnext-stage-1-property-identity`

Stage 1 code gate: **GO**

Production rollout gate: **BLOCKED**

Live JWT compatibility: **UNVERIFIED**

This signoff covers the additive Stage 1 property-identity implementation through Slice 9. It is a code and local-test conclusion, not authorization to merge, apply migrations to a live database, provision live roles, or enable a production feature flag.

## Commit lineage

| Slice | Commit |
| --- | --- |
| 1 | `6250519cfcce4341a0b6e7c20d57bcf8ab8b721e` |
| 2 | `29fbfa6d2295e3d91626568c76533cff5096e74c` |
| 2 hermetic/RLS closure | `f7cb024ace8e56fbbb7b43653902ceba23ea4237` |
| 3 | `c29b40ed91fa42626b21e1a7c6994ee8d9c03278` |
| 4 | `f7603367f5ae7ef128bc0142a78d3736e6f07c55` |
| 5 | `7138b673e72fa3c5a7c1d8d5dadc2c7c6cb54cee` |
| 6 | `32e7f960bb89c9a8809c9637e662988290e62cdd` |
| 7 | `91a45eca4c695aa2db701e9afde60cbe17350c08` |
| 8 | `d4c006a0204acfbc866cc717e9f3898218e75a7f` |
| 9 | `SELF` - the commit containing this signoff; its immutable SHA is recorded in the Slice 9 closure report because a commit cannot contain its own hash. |

## Migration boundary

Slice 9 adds no migration. Migrations `001` through `017` and the registry are unchanged; `018` remains the next safe sequence.

| Migration | Frozen SHA-256 |
| --- | --- |
| `013_vnext_workspace_case_foundation.sql` | `322c66295975a612d03b39d46c2fdb4fdb0a7e4be6212ae3f4488fee4ce73952` |
| `014_vnext_property_graph_evidence_foundation.sql` | `0b465671d513a4b182af8c56e784e8a7e161ed019e6218934ce30625cde7dacd` |
| `015_vnext_identity_resolution_candidates.sql` | `b87b582e013d3733fe8db179681489fcc950ea6998b7c23552b0fa88a044361f` |
| `016_vnext_identity_confirmation_case_links.sql` | `b0f5ae9694fbb6dcb64d467aa9338778b3c83e7d0da3c5bbab9f710dbebd3636` |
| `017_vnext_legacy_saved_case_import.sql` | `0753b222597d7e0d6cbc618a17bc1d07d047a0d499318936c29880a119182efa` |

The static validator passed with 18 registry entries and 13 production-runner migrations. The production-runner dry-run returned ready with next sequence `018`. A local disposable PostgreSQL 17 rehearsal proved clean application, existing production prefix to Stage 1, the `016` to `017` boundary, repeat execution, exact ledger checksums, foreign keys, FORCE RLS, ownership/grants, trigger `search_path`, and the restricted `vnext_api` role.

## Validation evidence

These results are separate test selections and intentionally overlap; they must not be summed:

| Gate | Result |
| --- | --- |
| Focused Slice 9/OpenAPI/auth/frontend contract | 44 passed |
| Frontend session/DTO mutation harness | 31 passed |
| Slice 1-8 VNext regression selection | 294 passed |
| Existing SavedCase compatibility selection | 11 passed |
| Terrain safety selection | 72 passed |
| Complete frontend static/component selection | 240 passed |
| Full backend with synthetic hosted-looking DB variables | 1,730 passed, 14 skipped, 1 deprecation warning |
| Real disposable PostgreSQL migration/RLS/concurrency suite | 9 passed |
| Focused VNext identity Playwright | 24 passed |
| Complete Chromium and Chrome Playwright regression | 530 passed in 21.1 minutes, zero retries in the accepted run |
| Frontend TypeScript | passed |
| Frontend lint | 0 errors, 27 pre-existing warnings |
| Frontend production build | passed |
| Production bundle secret scan | passed, zero requested-pattern matches |
| `git diff --check` | passed before signoff finalization |

An earlier default-concurrency Playwright attempt was not accepted as a pass: it retained 19 resource-timeout failures after configured retries. Without a source change, the required one-worker rerun passed all 530 tests with no retry. This is classified as runner-resource instability rather than a Slice 9 product regression, but the failed attempt is recorded here rather than hidden.

The 14 skips in the full hermetic backend run were declared external/optional gates. The nine Stage 1 PostgreSQL tests were then executed separately against a fresh local database named `vnext_rls_test_slice9_20260906`; skipped PostgreSQL tests were not counted as pass.

## Architecture and security conclusions

- `PropertyEntity`, `Case`, candidate, evidence, and relation concepts remain distinct. Confidence, rank, provider output, AI output, legacy import, and Case attachment do not confer identity confirmation.
- Only explicit owner/admin human confirmation can produce a confirmed identity relation. Demo/test sources, incomplete coverage, evidence-free candidates, unsupported candidate states, and active blocking conflicts fail closed.
- Confirmation and Case attachment remain separate commands. No destructive merge exists.
- Unknown, unavailable, limited, partial, stale, conflicting, unverified, and no-match states remain distinct through persistence, API DTOs, frontend parsing, and presentation.
- SavedCase v1 storage behavior remains unchanged. Import is explicit-consent, copy-only, `legacy_unverified`, and cannot create a PropertyEntity, resolution, confirmation, or CasePropertyLink.
- All six command routes retain scoped idempotency. Real PostgreSQL races proved at most one terminal confirmation/rejection, one same-version Case transition, no duplicate consequential replay effect, and scoped legacy-import duplicate protection.
- Failure-injection and real-database tests preserve atomic rollback for confirmation, Case attachment, and legacy import. Candidates, attempts, conflicts, evidence, decisions, links, import records, and audits remain protected history.
- FastAPI remains the BFF. Browser code sends only a Supabase access token to FastAPI and has no direct VNext tenant-table path. The request principal is derived from verified JWT `sub`, active workspace membership, and server-side role policy; forged identity headers/query fields are rejected.
- The normal database principal remains non-owner `vnext_api` with `NOSUPERUSER`, `NOBYPASSRLS`, `NOINHERIT`, and FORCE RLS on all 19 VNext tables.
- OpenAPI contains exactly the 12 approved Stage 1 operations, bearer security on each, bounded `Idempotency-Key` on each command, and one allowlisted structured error envelope. No debug, auto-confirm, auto-merge, confidence-attach, provider-bypass, or admin-shortcut route exists.

## Auth assumptions and live blocker

The narrow browser adapter was checked against the Supabase session contract: the standard `sb-<project-ref>-auth-token` storage key, top-level stored session payload, JWT expiry, refresh endpoint, refresh-token rotation, signed-out/replaced session guards, corrupt storage, timeout/failure, malformed responses, same-realm single-flight, and cross-tab storage replacement checks. Only publishable keys or legacy `anon` keys are accepted in the browser; privileged keys and token logging are absent. A custom/non-standard Supabase hostname requires an explicitly configured compatible storage key.

Backend tests cover RS256 and ES256, issuer/audience enforcement, current/rotated `kid` selection, unknown-key failure, expiry, UUID subject mapping, and privileged-token rejection. A read-only public JWKS observation confirmed an ES256/P-256 public-key shape that this backend supports, but it was not proof of the actual deployment's issuer, audience, active signing key, or real access-token claims. Therefore:

> **LIVE JWT COMPATIBILITY: UNVERIFIED**

Production rollout remains blocked until an operator verifies the actual deployment project URL, issuer, audience, JWKS/key rotation, and a real signed user access token against the backend without logging token material. The implementation assumptions align with the Supabase documentation for [API keys](https://supabase.com/docs/guides/getting-started/api-keys), [sessions](https://supabase.com/docs/guides/auth/sessions), and [signing keys](https://supabase.com/docs/guides/auth/signing-keys), but documentation compatibility is not live-environment proof.

## Feature flags, rollback, and prerequisites

Checked-in defaults remain:

```text
FEATURE_IDENTITY_V1=false
FEATURE_LEGACY_CASE_IMPORT_V1=false
```

Rollback is feature flags OFF. It is not destructive DDL reversal: additive durable records and immutable history remain intact. No rollback `DROP` SQL is supplied.

Production prerequisites remain outside this code gate:

1. Verify live JWT issuer/audience/key/token compatibility.
2. Approve and execute the migration runbook with operator credentials; do not expose the private schemas through the Supabase Data API.
3. Provision and verify the restricted live `vnext_api` principal and application connection separately from owner/operator credentials.
4. Perform live tenant/RLS smoke checks with controlled test identities and audit review.
5. Enable flags only through an approved staged rollout after all preceding checks pass.

## Scope statement

No live Supabase mutation, live migration, Auth change, signing-key change, user/workspace creation, production flag enablement, Migration `018`, provider expansion, automatic merge, Terrain change, title/listing/CRM work, AI identity decision, Hero integration, main merge, or deletion of `HISTORY-001` was performed. The separate Hero/user worktree was not edited.
