# Production Release Evidence

Generate evidence from local/CI/preview/production separately. Every field
must be marked `generated`, `ci_verified`, `preview_verified`,
`production_verified`, or `pending`; pending is not a success claim.

## Safe evidence fields

- release ID and commit identifier;
- declared API and schema versions;
- test/build/gate result categories;
- migration table/index/foreign-key verification categories;
- backup checkpoint category, without provider identifiers that are private;
- smoke check categories and unresolved owner actions;
- source-status category;
- bundle/dependency budget categories;
- rollback checkpoint status.

Never include secrets, database URLs, cookies, raw headers, customer records,
provider payloads, addresses, coordinates, or private domains unless an owner
has explicitly approved a separate restricted record.

Hosted evidence is `pending` until the URLs are reached and the corresponding
non-destructive checks pass. This repository does not claim monitoring,
backups, TLS, source availability, or deployment success without evidence.

## Final Production Acceptance v2 closure inputs

`scripts/collect_production_closure.py` collects a bounded local identity,
configuration, artifact/provider inventory and sanitized runtime audit snapshot.
It makes no provider calls. `generate_release_evidence.py --closure-json <path>`
adds a revalidated `closure_acceptance` projection in evidence schema v2 while
retaining the existing v1 interface when no closure input is supplied.

Missing, malformed, speculative deployed receipts and local fixture results
remain blockers. The projection never sets product GO. See
`operations/production-identity-provider-closure-v1.md` for exact commands,
immutable backend build injection, evidence scopes and required owner actions.
