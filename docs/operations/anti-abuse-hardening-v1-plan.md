# Anti-abuse hardening implementation plan

Goal: implement the user's anti-abuse specification in the existing isolated worktree, with one final commit and no deployment, push, merge, production traffic, or credential changes.

Architecture: reuse `FixedWindowRateLimiter` for independent capability request policies and process-wide physical-operation reservations. Keep peer identity from ASGI transport only. Bound provider work after cache/coalescing selection; retain permits for the actual operation lifetime. Use ASGI byte accounting before parsing for streaming bodies.

Execution: inline using test-driven development. The supplied request is the authoritative specification. Per-task commits and further authorization handoffs are superseded by the user's instruction to implement and create exactly one commit.

- [x] 1. Add deterministic admission, configuration, concurrency, body-size and identity tests; observe failure; implement shared guards and request middleware. Modify map routes to use the same limiter architecture with independent policies and fail-closed errors.
- [x] 2. Guard Geocoding, Places, Routes, Satellite and terrain physical work after reuse decisions. Preserve physical-call metrics, caches and partial evidence. Test rejection, cache hits, failure, timeout and cancellation recovery with mocks.
- [x] 3. Bound text, categories, geometry and alternate inputs; document threat model, endpoint inventory, policy/configuration table, ingress limitations and owner acceptance actions.
- [x] 4. Run focused and full backend tests, frontend units, both local browser projects, npm checks and existing local gates. Obtain an independent security review and fix Critical/Important findings with regression tests.
- [x] 5. Record validation and remaining operational blockers; prepare and verify the bounded diff. Create the single requested commit and confirm clean status in the final handoff.

Review focus: forwarded header spoofing; equivalent URL forms; chunked/malformed bodies before parsing; cached or coalesced operations under exhaustion; cancellation while synchronous provider work still runs; saturation across independent adapters and capabilities; partial evidence under a guard rejection; honest multi-worker/global-budget limits.

Execution evidence and review dispositions are recorded in `anti-abuse-hardening-v1-validation.md`. Commit identity and the post-commit clean-worktree check are reported in the final handoff, avoiding a self-referencing commit hash in a committed document.
