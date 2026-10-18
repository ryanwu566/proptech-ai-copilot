# Wave 1 certification closure v1

Acceptance date: 2026-10-18 (Asia/Taipei). Attempt: `20261018T135930Z-2206b957`.

**Original Wave 1 local integration: FAIL.** **Closure: PASS.** **Hosted production: NO_GO.**

This is a new, bounded acceptance attempt under the approved closure criteria. It does not replace the original full-suite or browser failures, and does not claim a fresh complete-suite pass.

## Original evidence preservation

Before source edits, 74 existing evidence files (including 12 XML artifacts) were SHA-256 fingerprinted and copied under this attempt. Every original and preserved copy was rechecked unchanged. The JSON companion enumerates all original paths, sizes, hashes and preserved paths.

| Original record | SHA-256 |
| --- | --- |
| `docs/wave1/wave1-integration-gate-v1.md` | `da395d9aa165cefc14720d656c96d305476c8be110b5264662c1dc4b860d3b0b` |
| `docs/wave1/wave1-integration-gate-v1.json` | `230821d316571ad33e1ff63c94b7f767082b4403b9a52ed2b7dd9ac2e2f1fadb` |
| `artifacts/wave1-integration-gate-v1/all.log` | `13048559cc53c61d439df1457b3a2941598043ae96826060f1e9dc22775e8855` |
| `artifacts/wave1-integration-gate-v1/browser.log` | `3fc3e94e334daccb7d6bb674ec7f5f9c8580aaf122abea02fee11ee36399176d` |

New artifacts: `artifacts/wave1-certification-closure-v1/20261018T135930Z-2206b957`. Original Markdown/JSON remain historical FAIL records; their old git/cleanup observations describe that original attempt. Referenced historical screenshot/video attachments were already absent when this closure began.

## Scope and fresh results

Exactly three test-local subprocess calls now set child `PYTHONIOENCODING=utf-8` and reader `text=True`, `encoding="utf-8"`, `errors="strict"`. All original functional assertions were compared by AST and retained unchanged. They parse or inspect decoded stdout, so empty/discarded output cannot satisfy them. No CLI or application encoding behavior changed.

The new temporary launcher removes inherited `PYTHONIOENCODING` and `PYTHONUTF8`; it adds no blanket replacement. The original launcher is untouched for forensic context. The Windows pytest parent uses native CP950; only the three CLI boundaries have explicit UTF-8 contracts.

| Fresh check | Result |
| --- | --- |
| Encoding tests | 3 passed, 0 failed, 0 skipped |
| Configured test-only E2E build | Exit 0 |
| Complete active/suspended browser cases | 2 passed, 0 failed, 0 skipped |
| Full Python rerun | NO |
| Original and preserved evidence integrity | Unchanged |
| Cleanup | MANUAL CLEANUP REQUIRED; stopped, no PID/listener/reparse point |

Each browser case records only spawn/exit state, PID, elapsed phases, poll counts, connection categories, HTTP statuses and assertion-completion flags. Backend stderr is streamed through an allowlist; raw stderr, session bodies, JWTs, cookies and Authorization values are not retained. The helper only adds opt-in startup phase events; fixture API/auth behavior is unchanged. Windows cleanup terminates only the owned backend tree, including a venv launcher child.

Both backend processes exited during intentional fixture cleanup after assertions completed; neither exit was premature. Their recorded helper exit codes are distinct from the successful browser runner exit status.

The 15-second readiness deadline remains unchanged. A manual trace covers only the empty browser context during startup and stops before credential-bearing browser operations; readiness requests use a separate untraced API context. Full automatic tracing is disabled. Screenshots/video/error context are retained on first failure, with a unique output directory. Credential-bearing transport operations replace raw Playwright errors with fixed operation/category errors, without preserving the original message or cause. New text and trace payloads were scanned for credential-shaped data without printing matches.

| Account | Readiness (ms) | Polls | Navigation | Complete assertions |
| --- | --- | --- | --- | --- |
| active | 14218 | 17 | True | True |
| suspended | 8082 | 11 | True | True |

Both case results must include readiness, navigation, account display, direct authorization, no page errors, and the suspended forgery/reload checks where applicable. A readiness-only diagnostic cannot satisfy this closure. Historical browser underlying cause remains UNKNOWN even if this attempt passes. Three quiet-host observations precede the build and the browser run; process queries exclude installed Chrome.

## Reused evidence

| Check | Execution | Original result |
| --- | --- | --- |
| Real PostgreSQL Wave 1 | REUSED FROM ORIGINAL ATTEMPT | 140 distinct real SQL cases passed |
| Focused Wave 1 | REUSED FROM ORIGINAL ATTEMPT | 388 passed; one ledger skip separately proved on PostgreSQL |
| Cross-wave models | REUSED FROM ORIGINAL ATTEMPT | 318 passed |
| Worker pool | REUSED FROM ORIGINAL ATTEMPT | 26 passed, once within original complete suite |
| Production build | REUSED FROM ORIGINAL ATTEMPT | Passed |
| Route/global budgets | REUSED FROM ORIGINAL ATTEMPT | All 24 routes and global limits passed; unchanged ceilings |
| Security/performance | REUSED FROM ORIGINAL ATTEMPT | Passed |

No production build, SQL pack, focused/model/worker pack, budget measurement or security/performance gate was repeated. A configured E2E rebuild was necessary because the previous production artifact lacked fixture API/Auth configuration. The new changes are test-local; no shared runtime subprocess utility or production encoding contract changed, so a new full Python run is neither required nor authorized. The original complete-suite result remains 4,123 passed / 3 failed / 151 skipped / 4 warnings in 516.58 seconds.

## Cleanup and hosted boundary

The sole remaining stopped directory is `.tmp/wave1-gate/pg-eb77cffd58b3`. `pg_ctl status` reports stopped, `postmaster.pid` is absent, original port 55520 has no listener, and the exact root/descendants have no reparse points. Prior automatic deletion review remains binding; no deletion or bypass was attempted. **MANUAL CLEANUP REQUIRED** is an explicitly permitted closure disposition under the approved criteria, and supplies no evidence of database functional failure. Manual removal cannot alter the original FAIL verdict.

Hosted production remains NO_GO with the same separately documented infrastructure/configuration/runtime/recovery evidence gaps. No hosted, provider, production-database, Render or Supabase action was performed. Installed Chrome was not inspected or controlled.

## Git and disposition

Current main was re-fetched and remained `4a17ddb91f4b7d3e5a106759ba71175619347419`; the branch was 0 behind / 0 ahead before the conditional certification commit. The two original runtime security fixes and all original regression coverage remain. Closure adds only the three encoding test contracts, three browser test/helper diagnostic files and these two new records. Temporary scripts and raw acceptance artifacts stay ignored.

A fresh read-only final review identified two Important issues in the new test/evidence path. Both were addressed before the browser attempt: safe categorized transport errors prevent bearer call logs reaching reporters, and PASS now requires zero exit status for encoding, build and browser execution. A real loopback API negative control reproduced raw placeholder disclosure, and the safe boundary rejected disclosure without launching a browser. Verdict-expression checks reject each nonzero execution status even with otherwise passing testcase counts. Diagnostic persistence is protected by unconditional fixture cleanup. No residual Critical/Important source finding remains from that review.

A single local certification/source commit is authorized only after closure PASS, evidence consistency and final review. No push, merge or deployment is authorized. Its resulting SHA and final clean-tree status are reported separately to avoid a self-referential commit hash in this record.
