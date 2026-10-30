# Individual provider admission after required credential migration

**Preparation only. No functional provider request is run by migration.**
All listed backend credentials are required in protected server storage even
when the capability is disabled or its adapter is not ready. A storage PASS is
not permission to mount keys into the active API or enable a paid provider.

For every row, first require the complete storage receipt, minimal proposed
consumer-only mounts, no credentials in ENV/image/Git/log/response, supported
adapter contract, approved identity/API restrictions and a bounded cost/quota
budget. Keep exact timeouts/retry bounds and allowlisted endpoints. Use protected
operator inputs; no key/token in a shell argument or agent request. Prepare a
separate reviewed activation/rollback change for only that provider. Migration
itself never changes flags, recreates services or retargets production callers.

| Provider | Functional admission test to prepare | Honest failure / rollback boundary |
|---|---|---|
| Google server geocoding | One approved deterministic coordinate/address fixture; server restriction and quota proof; known-match and zero-result contract, request/timeout budget | Denied/empty/error remain explicit; restore disabled guard and remove only the newly admitted consumer mount through reviewed recreation |
| Google Places | Same canonical server key, independently approved Places API/billing restriction; one bounded known fixture and zero-result response; fields/count/time limits | No mocked success or fabricated POIs; storage PASS does not prove Places authorization |
| Google Routes | Independently approved Routes quota/cost; one fixed origin/destination/mode fixture, duration/distance contract and unavailable response | No traffic/freshness claim beyond provider response; no automatic retry/fallback to paid calls |
| Earth Engine | Approved service identity and registered project/IAM/API access; existing bounded Sentinel-2 worker contract; fixed geometry/window, no-scene and auth/timeout tests | Preserve reference-only semantics, zero export/background work; no invented portable metadata ADC or automatic key creation |
| TGOS | Canonical app-ID/key and accepted endpoint contract; one approved normalized fixture plus no-match/denied/malformed tests, strict call count | No fallback through unreviewed legacy aliases; unavailable remains unavailable |
| TDX | Bounded token exchange and one controlled snapshot fetch after approval; protected producer identity; persistent producer/API loader adapter and freshness/provenance required | Existing in-memory refresh is not a standalone persistent local job; never enable a public refresh route or paid Routes implicitly |
| R2 | Approved read-only scope to an exact immutable manifest/key; bounded HEAD/GET/hash/no-match/denied checks; no bucket-wide listing/write | Local NLSC/WRA remain local; remote artifact mismatch fails closed; uploader/writer acceptance separate |
| OpenAI | Current service is template-only; first review an actual bounded adapter, token/output/cost limits, privacy contract and disabled default; then one explicitly approved request and denied/timeout tests | A stored key does not implement an LLM provider or permit a paid test; activation blocked until adapter and budget acceptance |
| Supabase verification | Preserve accepted public issuer/audience/JWKS and identities; malformed/expired auth denial and real user/session/profile/Saved Cases ownership E2E | No service-role/signing secret, password migration or auth bypass; existing users preserved |
| Database/HMAC/session | Preserve current principals/TLS/SELECT-only serving separation and stable secret identities; focused core/user/usage contracts | No new passwords, broad role grants, provisioning, serving-table mutation or initializer mounts in API |

Every provider remains `NOT_RUN / NOT_ADMITTED` for functional activation until
its own approved test runs. Store browser public keys/config only on the frontend;
do not use a backend server key as a browser shortcut. Current legacy deployment
aliases, alternate unproven provider/DB identities and cloud callers remain in
the names-only retirement inventory until their authority/consumer proof exists.
Never fabricate a credential for an account that has not been established.

Acceptance receipts must state provider, exact image/config/mount identity,
restriction/quota approval, test request count and safe status/counters only,
auth/error behavior, secret scan scope and rollback result. Public HTTPS/Vercel
cutover and cloud retirement remain separate gates owned by their workstreams.
