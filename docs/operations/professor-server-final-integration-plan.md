# Professor Server final local integration plan

Goal: complete the user's phased local integration specification on baseline
9cc40d645757af4513d9afdf0c008939cc489a77 without public deployment.

Architecture: retain the current FastAPI/PostgreSQL services. Reuse artifact
validation for explicit read-only local data sources; preserve R2 defaults.
Reconcile raw PLVR special-note evidence against actual serving facts and add
exclusions only for unambiguous matches. Preserve original transactions.

Constraints: never touch /dev/sda; never modify X9 source; never print secrets;
no push, merge, public ingress, paid providers, destructive database operations,
or filling the accepted CWA 1897–1989 gap. Preserve the existing frontend change.
The user has explicitly requested autonomous implementation and one final commit.

- [ ] Snapshot sanitized host state and create timestamped backup evidence.
- [ ] Switch NLSC mount to verified server copy, test NLSC → RIS.
- [ ] Inventory copied datasets with hashes, schemas, provenance and versions.
- [ ] Test local WRA/GSMMA reads, checksum failures, malformed data, traversal,
      no network and match/no-match; implement in existing runtimes and verify.
- [ ] Inspect ARDSWC/liquefaction/CWA; enable only proven compatible contracts.
- [ ] Test and implement strong-fact PLVR reconciliation with UNIQUE_MATCH,
      MULTIPLE_MATCH and NO_MATCH; fail closed for evidence conflicts.
- [ ] Add serving exclusions and apply to all database serving queries; verify
      known row retention and exclusion, demo and future official separation.
- [ ] Reconcile aggregate/coverage metadata through a reviewed transaction.
- [ ] Run role/TLS/port checks and reverse-proxy API contract acceptance.
- [ ] Run focused then broader backend and selfhost tests, review changes.
- [ ] Write handoff and machine-readable acceptance; one local commit only if
      intentional changes pass; leave existing user edit unstaged.

Review focus: local missing files must never fall back to network; symlink escapes
and version/path traversal must fail; historical revisions and duplicate facts
must not create automatic exclusions; empty market groups must disappear from
serving aggregates; absent privilege or host access is a blocker, not a PASS.

Initial state: current host sudo cache expired; Docker socket and copied data
are inaccessible to the current account. Loopback API health/readiness passed.


## Execution result

Repository implementation and tests are complete for local WRA/GSMMA artifact
transport, passive diagnostics and inventory/probe tooling. Full suite: 4,260
passed / 149 skipped with pinned Node and venv PATH. Independent review completed;
security findings addressed. Source reference inventory and artifact/schema
validation completed without source writes. API probes completed.

Server phases remain externally blocked: sudo authorization unavailable, Docker
socket denied, server-copy/protected env/backup paths unreadable. No host mount,
container or database modification occurred. The existing PLVR defect is still
reproduced; reconciliation classifications and coverage repair are not fabricated.
See professor-server-final-handoff.md and reports/professor-final-integration/.
