# Work commercial re-evaluation rubric V2

Research date: 2026-10-10, Asia/Taipei. Baseline: `c2ddf1890897f44659b91079a563691fe337295e`. This replaces the old commercial maturity/UI score. **No score is awarded in this research.** The next ChatGPT Work evaluation must test the actual deployed successor release.

The evaluator needs the actual frontend/backend origins, frozen SHA/version/environment, accepted source/artifact manifest and redacted owner acceptance evidence. Missing evidence stays missing. Repository files, schemas, fixture screenshots, templates and an “AI” label earn no points by themselves. A public frontend SHA alone does not establish matching backend/data identity. See [current acceptance](../operations/final-production-acceptance-v1.md) and [guardrails owner contract](../operations/production-guardrails-recovery-v1.md).

| Dimension | Points | Deployed task / evidence required for full credit |
| --- | ---: | --- |
| Core user journey | 7 | Establish a property, query explicitly, understand evidence and missing items, save, reopen, compare and report without dead ends or lost inputs. |
| Decision transparency | 7 | Explain active asking/estimate/manual price basis, calculation assumptions, scope and limits; show no overall purchase/safety score or buy/no-buy verdict. |
| Evidence trust | 10 | Source/date/version/coverage distinguish official records, provider observations, user statements and demo; demonstrate unknown, unavailable, no-match, stale and numeric zero independently. |
| Market / valuation usability | 7 | Inspect actual supported transactions, comparables and inclusion/exclusion explanations; regional medians distinct from property valuation; display sample/period limits and missing data. |
| Risk / location usefulness | 5 | Answer a real location question with accepted source evidence; maps/POI/routes useful; hazard no-match is not safety and imagery is not legal identity. |
| Finance usefulness | 5 | Reproduce mortgage/holding calculation under saved assumptions, change rate/down payment, identify unknown acquisition/renovation costs and avoid false lender approval. |
| Case workflow | 6 | Save/reopen/switch cases and manual checks, detect changed identity/evidence and storage errors; show local scope, export/deletion and unsaved state clearly. |
| Compare | 5 | Compare 2–4 cases; mobile two-at-a-time; detect mismatched route/period/POI/finance assumptions and avoid ranking/missing-as-zero. |
| Report | 5 | Generate readable A4 report from frozen snapshot with sources, limits and manual marks; newer snapshot does not silently overwrite; inspect long text and pagination. |
| Onboarding | 3 | Complete and restart contextual tour in all four locales, skip safely, distinguish simulation from real evidence and retain no unintended provider activity. |
| Accessibility | 3 | Complete critical tasks by keyboard; focus, labels, status announcements, contrast and reduced motion work; test with one assistive technology where available. |
| Mobile | 4 | Complete core task at 390px and 430px without document overflow, trapped navigation, clipped monetary values or inaccessible controls; use an actual touch device if available. |
| Performance | 4 | Measure deployed cold/warm core journey and saved-case operations; unchanged build/route budgets pass on exact release; no expensive provider prefetch or hidden route refresh. |
| Production reliability | 6 | Independent FE/BE identity and health plus managed backup/restore/rollback evidence, outage behavior and delivered monitoring; local drills alone cannot earn hosted-recovery credit. |
| Security / cost control | 6 | Owner evidence for bypass-resistant ingress, actual fleet controls, effective provider quotas and emergency switches; data/tenant isolation and privacy/export boundaries verified where enabled. |
| Accounts / collaboration | 4 | Actual account recovery, cross-device sync, conflict handling, shared read-only report roles/expiry/revocation and unauthorized-access rejection; no credit for gated schemas. |
| AI usefulness | 4 | If enabled, answer evidence-backed why/difference/missing/next-check questions with exact citations and calibrated refusal; if absent, zero AI points while deterministic explanation earns its relevant other dimensions. |
| Competitive parity | 3 | Complete benchmark-supported shortlist, continuity, scenario and shared-review tasks; no reward for adding a broad listing portal or unauthorized feed. |
| Differentiation | 3 | Demonstrate provenance, explicit uncertainty, manual verification and consistent snapshot/cost semantics together in one decision task; assess user benefit, not novelty labels. |
| Commercial readiness | 3 | Demonstrated pilot task outcomes, staffed support/escalation, consent/deletion, measured provider cost/unit economics and functioning lawful billing/entitlements if offered. |
| **Total** | **100** | Evidence coverage and blockers reported separately from points. |

For each dimension use `0`, `0.25`, `0.5`, `0.75` or `1.0` times its weight. Zero means absent, fails, or no observed evidence; 0.25 means a fragment succeeds with material blockers; 0.5 means the normal task succeeds with significant limitation; 0.75 means normal and one adverse path succeed with a minor known limitation; 1.0 requires normal, relevant adverse and repeated/switching paths plus the evidence above. The evaluator must write the concrete result and limitation for each fraction. “Not tested” earns zero provisional points and remains explicitly NOT TESTED, rather than a conclusion that the feature does not exist. Report tested-weight coverage and the provisional score; do not normalize away untested weight.

Provider-free local save/compare/report should be observed in a bounded network trace when tooling allows. In the absence of trace access, report cost behavior NOT VERIFIED and use release-bound engineering/owner evidence for that part of scoring; do not infer zero requests from a quiet screen. This research authorizes no provider calls, load tests or infrastructure changes. Later evaluation uses only its explicitly approved budget and test contract.

| Score | Interpretation, only if hard gates pass |
| --- | --- |
| <60 | Prototype / NO-GO for commercial release |
| 60–74 | Advanced research product |
| 75–84 | Controlled Beta candidate |
| 85–91 | Advisor / commercial pilot candidate |
| 92–100 | Strong early paid SaaS candidate |

These bands preserve the requested thresholds. They are decision aids, not market forecasts. A high score cannot compensate for a failed gate. A limited anonymous, browser-local Controlled Beta can pass without accounts if the limitation fits the cohort and is disclosed. Advisor access can initially use explicit customer-controlled PDF sharing; claiming hosted collaboration requires its own permission evidence. Paid SaaS requires actual durable account/entitlement, billing, support and sustainable operating cost proof.

Non-compensable gates:

1. Exact deployed release identity, accepted official source/artifact coverage for advertised capabilities, and fresh full regression/hosted acceptance. Demo or user records cannot masquerade as official production evidence.
2. No fabricated fact, price, comparable, identity, hazard, confidence interval or safety/buy verdict. Unknown and limited coverage survive Overview, Compare, Report and any AI response.
3. Effective global security/provider cost/emergency controls for the actual topology and all credential consumers; no assertion that process limits or alert-only billing budgets cap spend.
4. Managed-data recovery/rollback and named incident/support owners, plus consent/export/deletion and authorization isolation for any stored/shared personal documents.
5. Exact-release performance/bundle evidence. New features cannot waive the existing 3,000,000-byte aggregate budget. No unresolved critical/high security issue outside an explicitly applicable, evidenced exception.
6. ML remains excluded until its independent source/temporal/cohort approval; Target A/B BLOCKED, PIT-valid=0, approved cohort=0. A commercial score cannot approve ML-B.

Suggested deployed session pack:

1. Ordinary supported Taiwan address: follow intake → Market → Location → Risk → Finance → checklist → Save/Reopen → Compare → A4 report. Record source date and actual release identity.
2. Incomplete and unsupported address: explain all missing evidence; ensure unavailable POI is not zero and no-match hazard is not safety.
3. Two cases with different destinations, scope/period and financing: demonstrate comparison warnings and manual, user-controlled priorities.
4. Change case identity/evidence after a reviewed checklist: old marks require recheck; switch cases with an unsaved draft without contaminating the other case.
5. New/blocked browser storage and stale concurrent save: explicit failure/reload; no false “saved” feedback. Demonstrate lost-browser limits and delete/export.
6. Frozen report followed by a newer saved case: explicit newer-snapshot notice, no silent recomputation; inspect a long-address/long-source A4 PDF visually.
7. Keyboard, reduced motion and 390/430/1024/1440px; tour locale switches zh-TW/en/ja/ko; complete actual touch-device task if available.
8. If AI is enabled, ask “Why more expensive?”, “Different from Case B?”, “What is missing?”, then a unsupported price/hazard/buy question and malicious document instruction. Require cited supported answers, refusal and no new fact creation.
9. If sharing/accounts enabled, second device and unauthorized/expired/revoked viewer; real conflict/account recovery and deletion. Never test against real customer private cases.
10. Review redacted managed recovery, owner controls and support/billing evidence; a live browser session cannot independently prove every infrastructure property.

The result should include release/time, tested weight, points by dimension, scenario outcomes, screenshots/PDF observations, source/owner evidence references, hard-gate verdicts and a prioritized defect list. **Do not reuse an old score or score this repository as if it were the deployed site.**
