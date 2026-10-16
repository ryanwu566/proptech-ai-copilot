# Grounded Property Copilot v1

User-authorized scope: implement Wave 3 in the supplied worktree, one local commit,
no push/deploy, no migrations (including 022/023). Base verified by fetching
origin/main: 59631992e03c05ff01e67fb691710c738fcc6d1b.

## Design

Use the existing browser-local Saved Case workspace and pure CaseEvidenceModel.
There is no active production model provider: services/llm_service.py is an offline
template. Add no network or model dependency. The assembler accepts exactly one
workspace plus validated, case-bound Scenario Lab and Decision Room snapshots.
Evidence strings are data, never instructions. Citations are case-scoped internal
evidence references. Unknown, failed, stale, limited and conflicting observations
remain explicit. Saved observations are never described as live.

Keep authority in deterministic code. A future responder may select only known
evidence IDs within an established topic; it cannot supply claims, URLs, prices,
status, instructions or prose. Reject malformed/foreign outputs and regenerate a
fail-closed answer. Bind requests, follow-ups and displayed conversations to the
case, identity and evidence revision; discard stale responses.

## Implementation sequence

1. Write failing isolation, grounding, citation, missing/conflict, follow-up,
   stale-response, injection and model-output contract tests.
2. Implement a pure context assembler, deterministic topic selection, bounded
   answer contract, model selection validator and stale-response controller.
   Reuse the Scenario Lab context and Decision Room repository validation.
3. Add a lazy Copilot conversation on case routes, localized for zh-TW/en/ja/ko.
   Show saved/live state, context, sources, used evidence, missing evidence,
   limitations and safe follow-ups. Link to existing evidence screens; refresh
   requires their explicit user action and existing provider safeguards.
4. Browser-test all four widths and locales in Chromium and Chrome, retries=0.
   Cover reopen, locale changes, case switch, citations, Compare/Report and
   performance. Run existing workspace unit and Saved Case/Compare/Report E2E
   regressions, typecheck, lint, build.
5. Request a fresh-context independent grounding/security review, address material
   findings with regression coverage, record acceptance evidence and commit once.

## Budgets

Context assembly: 100 iterations below 1000 CPU ms on the local test machine (wall
time is recorded separately because concurrent worktree builds share this host). Context
payload under 128 KiB for standard fixtures; no whole storage tokens or histories
in provider payloads. Copilot interaction below 2 seconds in browser; no horizontal
overflow at 390/430/1024/1440. No added dependencies or provider requests.

## Execution record

- Existing linked worktree verified; no additional worktree required.
- User's implementation instruction authorizes execution of this concrete brief;
  single-commit requirement overrides skill intermediate-commit guidance.
- Grounding tests: 13 initial RED cases, then GREEN; bounded arithmetic and
  foreign-validator fallback added, followed by two review regression cases.
- Independent fresh-context grounding/security review: no critical findings;
  two important findings reproduced RED then fixed: single-topic asking-price
  conflicts now retain both observations, and identity conflicts invalidate POI
  and secondary transit observations. Generated Scenario labels and limitations
  are localized. Reviewer limitations: static UI review and Node reproductions;
  browser validation is performed by the implementer.
- Grounding suite: 17/17 passed. 100 assemblies: 235 CPU ms / 3456 wall ms during
  concurrent host builds. Full regression and browser results recorded in the
  acceptance report after final verification.
- Added a failing stale/foreign future-provider payload test, then guarded payload
  construction before serialization. Refreshed suite: 209/209, including 18/18
  grounding cases. Latest budget: 155 CPU ms / 593.5 wall ms for 100 assemblies.
- Typecheck passed; ESLint exit 0 with 23 warnings in untouched files. Standard
  Turbopack production E2E build passed (compile, TypeScript, static generation).
  Exact-lockfile local dependency hardlinks avoided concurrent install contention;
  package/lock/config files remain unchanged.
- Extended injection coverage to a literal saved commute destination. A final RED
  minimization case found the existing scenario parser tolerates additional JSON
  keys; context revision binding now serializes only validated calculation inputs.
  Refreshed native suite: 210/210, including 19 grounding/security cases. Latest
  benchmark: 63 CPU ms / 83 elapsed ms for 100 assemblies; payload below 128 KiB.
- Final source rebuild passed with Turbopack, TypeScript and static generation.
  Fresh standalone typecheck exit 0 and final lint exit 0 (same 23 existing warnings).
  Pilot Copilot browser suite: 16/16 on Chromium + Chrome, retries=0. Combined
  200-case final regression run remains pending in the acceptance report.
- Combined browser run: 151 passed before an existing Chrome Decision Room
  multi-tab workflow hit its file-level 60-second deadline (overriding CLI 120 s).
  The file now preserves its 60-second default while honoring a longer explicit
  project timeout. Follow-up exposed a test synchronization gap: it did not await
  the remote save or activate the receiving tab before checking its storage event.
  Added readiness/save/foreground waits, following the neighboring test's pattern;
  all conflict, data preservation, same-document and isolation assertions remain.
  Remaining 49 Chrome cases are being verified with retries=0. Application code
  and the two-second response budget are unchanged by these harness corrections.
- Final browser coverage complete: 200 unique cases, 100 per browser. Aggregated
  initial 151 passes plus targeted remaining cases after legacy harness corrections;
  all runs retries=0. Explicit foreground actor/save waits also fixed inactive-page
  native-lock/input scheduling in legacy tests. Fixed lock/task cases passed in
  both browsers; corrected asking-price case passed Chrome (36.1 s) and Chromium
  (16.5 s). Final remaining-45 run and standalone typecheck exited 0. No assertions,
  lock semantics, source data or application behavior were weakened.
- Final audit: origin/main advanced two non-overlapping operations commits during
  execution; verified start base is retained for the requested local-only handoff.
  No database migration, package/lock/config change, push or deployment.
