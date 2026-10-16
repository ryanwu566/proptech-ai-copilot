# Wave 4 implementation plan

The supplied Wave 4 brief is the design authority. Implement in the requested
worktree/branch, in this session, and produce one local commit. No migration,
registry edit, push, deployment, provider refresh, or delivery integration.

1. Add failing contract tests for immutable imports, Auth UUID ownership,
   owner/editor/viewer boundaries, atomic compare-and-swap, idempotent explicit
   import, unavailable persistence, bounded reads and transactional activity.
2. Implement `services/vnext/durable_cases.py` with strict request models and a
   principal-bound transactional repository protocol. Default repository raises
   maintenance with `persistence_pending`; the memory adapter exists only in tests.
   Register `/v1/saved-cases` separately from workspace `/v1/cases` contracts.
3. Add a provider-free monitoring policy and notification interfaces. Scheduled
   execution remains disabled until worker, quota integration and persistence exist.
4. Add a Cloud panel to the existing Saved Cases entry. Explicit preview and confirm
   read the original JSON, preserve local storage on every outcome, reject credentials
   rather than silently strip evidence, and never import from mount/auth callbacks.
   Cloud list/open are explicit reads; metadata, membership and preference writes
   require expected revision. In-flight results are discarded after account changes.
5. Add model/client/browser coverage for no automatic upload, immutable import,
   failed upload retention, provider-free reopen, conflict drafts, offline and logout.
   Run Python Auth/domain regressions, frontend unit regressions, browser tests,
   typecheck, lint and production build.
6. Write `docs/wave4/wave4-persistence-schema-proposal.md` covering tables, constraints,
   RLS, grants, indexes, atomic adapter requirements, schedule/notification gates and
   choosing the next migration after rebasing. Review diff and record verified results.
   Commit once: `feat: add monitoring and collaboration foundation v1`.

Review focus: old local evidence must bypass normalization; failed/unknown evidence
and authored notes must survive; no token or raw error persistence; stale versions
must never partially mutate membership/activity; late account responses must disappear.
