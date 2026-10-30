# Stage5 credential audit closure and conditional network plan

> **For agentic workers:** Use superpowers:executing-plans inline and one independent security review before the local commit.

**Goal:** Finish all accessible credential/configuration audit scopes and prepare exact router evidence and conditional HTTPS decisions.

**Architecture:** Extend the existing names-only auditor with an explicit dependency matrix and accepted receipt validation. Preserve unknown live cloud scopes. A pure router evidence validator produces conditional plans but never permits apply.

**Tech Stack:** Python standard library; existing accepted Stage2/4A manifests/receipts; focused pytest; no host changes.

**Spec:** Latest Stage5 continuation instructions and `2026-10-30-professor-direct-ingress-design.md`.

## Constraints and review focus

- No secrets/actual envfile values, runtime changes, sudo, router/firewall changes, frontend edits, cloud mutations or push.
- Current core credential presence must come from exact accepted metadata, never inference from optional files or docs.
- Missing, inaccessible, unsafe and previously verified are different states. Unknown must not become missing or present.
- Cloud configuration references and declared sync=false keys do not prove deployed credential presence.
- Required current-profile secrets and optional paid providers remain separate; no automatic activation/retirement.
- Router WAN equality is not inbound proof. CGNAT/shared address and private upstream NAT are different cases.

### Task1 — dependency matrix and evidence

- [x] Add failing tests for name extraction, required matrix fields, six accepted credentials, unknown/unsafe metadata, missing-required classification and absent cloud scopes.
- [x] Implement `services/professor_credential_audit.py` and extend the existing audit CLI without adding any apply operation.
- [x] Generate matrix/evidence with names only; include configuration manifests, source, Compose/CI/docs and skipped private scopes. Verify Supabase public metadata only.
- [x] Document operator-only names collection and conditional credential installation/adoption; do not execute it.

### Task2 — router and conditional HTTPS

- [x] Add failing tests for null WAN, equal/unequal WAN, shared/private NAT, explicit reservation/upstream metadata, and forbidden forwards.
- [x] Implement pure router evidence/conditional-plan logic and an unfilled metadata template.
- [x] Publish router checklist and conditional direct/CGNAT HTTPS plans with no apply command.

### Task3 — verification and handoff

- [x] Run focused audit/network tests and AST/static checks; no fullsuite or activation.
- [x] Independent security review; fix material findings and reconcile acceptance honestly.
- [x] Update Stage5 evidence/runbooks and one local commit; preserve main/frontend/history worktrees.

Live Cloud Run/Render/Vercel and CI control-plane inventories are genuine external
dependencies if no authenticated metadata channel exists. The report must remain
incomplete rather than turn repository declarations into deployed-state proof.

## Continuation: finish accessible scopes without WAN

- [x] Audit the four tracked env examples through a Git names-only projection;
  never return/materialize assignment values or open host envfiles.
- [x] Generate per-workflow secret/config references and a concrete Cloud Run /
  Render dependency inventory, including Render maintenance jobs that must not
  be pointed at the public edge.
- [x] Record current connector capabilities and sanitized GitHub metadata;
  repository-read access must not imply secrets-inventory access.
- [x] Complete a no-WAN preparation checklist for TLS, firewall, boot, rollback,
  Preview/Production cutover and local controlled maintenance.
- [x] Focused regressions, static checks, independent review, current evidence
  and a local-only commit. Keep non-WAN external blockers explicit.

Verified preparation scope:332env/config identifiers plus9file contracts;
83credential/public/legacy subset identifiers. All six current API secrets and
DB-only admin mounts validated through accepted hash-bound metadata. No confirmed
required secret missing. Four live cloud/CI scopes remain externally unverified,
so complete audit NO and production-critical migration PARTIAL. Router decision
evidence pending; conditional HTTPS plan prepared; no apply released. Tests93
initial focused and51final changed-module tests pass; no fullsuite. Independent
review found no remaining critical/important issue after regressions.

No-WAN continuation:333identifiers+9file contracts;4indexed examples projected
to names without RHS;10workflow references and exact3Render maintenance jobs
inventoried. GitHub reader verified main9cc40d6 and sampled CI metadata, but its
secret APIs are unsupported. Four deployed names inventories remain unknown.
Focused55PASS; source/static review PASS; no fullsuite, root or runtime apply.
Unknown keys remain unadmitted. No service/credential retirement is approved.
Remaining blockers include cloud/host/TLS recovery and controlled maintenance,
not only WAN. Local-only commit; no push.

## Final adoption and retirement matrix continuation

- [x] Record whether new names-only deployment receipts or metadata readers exist;
  request only paths to sanitized exports when external facts remain blocked.
- [x] Specify A/B/C workflow decisions, interim status, exact local credential,
  service/job/data/capability mapping and implementation gaps. Preserve manual
  cadence; never create a timer or run a privileged refresh just for a matrix.
- [x] Generate Cloud Run/Render dependency/replacement/migrated/tested/retirement
  matrices. Distinguish accepted local replacement evidence from public cutover.
- [x] Focused matrix/guardrail tests and independent review, then current evidence
  and a local-only commit. No new privileged installation if none is required now.

Final adoption continuation:11provider mappings and22retirement rows prepared;
allretirementNO. TargetsA for3jobs, currentC definitionsunchanged, localbootstrap
substep notcarriedforward. Commute memory-only and legacyaggregate replacement
write gaps documented; no new role/timer/adapter installation claimed. Named
GIS/ML evidence required; real authorized user-flow testing staysNO. Public
frontend release9cc40d6 containsCloudRunorigin reference;50/1490CIruns notnonuse
proof. Focused33PASS and final11evidenceguardsPASS; no fullsuite. No new names
exports/access supplied, so fullcloud inventories remainexternallyblocked.
