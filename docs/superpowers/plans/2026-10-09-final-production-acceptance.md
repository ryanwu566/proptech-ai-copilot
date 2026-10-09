# Final Production Acceptance Implementation Plan

> Execution: native implementation in the supplied isolated worktree; fresh independent reviewer before the single final commit.

**Goal:** Extend existing release tooling and execute bounded acceptance without promoting local fixtures to production proof.

**Architecture:** Reuse production_smoke, provider_acceptance, generate_release_evidence and the existing browser runner. Keep the frozen candidate distinct from acceptance-tooling changes and from each deployed artifact.

**Spec:** Owner's Final Production Acceptance brief supplied 2026-10-09.

## Constraints

- Candidate: 95018f6fc2a366656cb798414dc54860d009e536; branch release/final-production-acceptance-v1.
- No push, merge, deployment, production database changes, secret changes, billing/quota changes, live provider traffic or Satellite generation.
- Exactly one commit after executable local gates pass; keep existing budgets and gates.
- Unknown evidence cannot pass; official import time and transaction freshness are separate.

## Tasks

- [x] Extend scripts/production_smoke.py with required expected identity, semantic health checks, bounded requests and refusal of redirected targets. Test mismatched/missing identity and malformed responses before implementation.
- [x] Extend scripts/provider_acceptance.py with explicit environment and one-request budget for live opt-in. Make scripts/certify_real_provider.py a safe entrypoint to that existing bounded workflow; remove import-time traffic.
- [x] Extend scripts/generate_release_evidence.py with bounded categorical gate records, deployment identity and fail-closed readiness aggregation. Test missing gates, false PASS, duplicate gates and unsafe metadata.
- [x] Extend browser acceptance with all eight views at 1440/1024/390, keyboard/labels/reduced motion, isolated saved cases and actual A4 PDF artifacts. Reuse existing trust, Compare and cost tests.
- [x] Execute Python/frontend suites, both browsers, build/lint/typecheck, release/security/operations/budget gates and dependency audits. Inspect PDFs and record hashes, page geometry and privacy-safe results.
- [x] Assemble docs/operations/final-production-acceptance-v1.md and JSON scorecards with exact owner steps; fresh review and corrections; verify staged diff; one commit, then clean-status check.

## Review focus

Missing deployed identity, valid-looking empty health objects, cross-origin redirects carrying smoke tokens, local fixtures mistaken for deployed official data, and manually asserted PASS without prerequisite evidence must fail closed.
