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
