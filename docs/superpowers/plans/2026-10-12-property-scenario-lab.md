# Property Scenario Lab implementation

Spec: `docs/superpowers/specs/2026-10-12-property-scenario-lab-design.md`.

Global constraints: work in existing isolated worktree; exactly one final commit; no pushes/merges; no providers; preserve saved evidence and production valuation; no bundle budget changes. Execute inline. User's build instruction authorizes implementation; routine design approval handoffs and intermediate commits are superseded by session instructions.

1. Write finance/model tests first for mortgage parity, zero/small rates, down payment modes, partial costs, invalid inputs, holding duration and pure immutable calculations. Run failing tests, implement `lib/workspace/scenario-model.ts`, then run green tests and existing finance tests.
2. Add typed locale catalogue, scenario component, isolated explicit local draft/baseline persistence, route and entry links. Inputs consume `ScenarioInput`; outputs consume `ScenarioResult`; storage binds case+revision+identity+evidence context. Accepted commute consumes existing location handoff. Add browser acceptance tests before UI implementation and confirm missing feature fails.
3. Run typecheck, lint, production E2E build and unchanged bundle budget checks. Run browser matrix at 390/430/1024/1440 in all locales plus trust/persistence/error tests and existing finance/workspace checks. Inspect screenshots and fix concrete failures.
4. Review entire diff for unknown-as-zero deception, invalid/malformed storage, cross-case leakage, baseline immutability, provenance and unexpected requests. Record actual verification evidence in `docs/qa/property-scenario-lab-v1.md`. Commit all final changes once.

Review focus: blank vs explicit zero; principal/down payment boundaries; saved grace-period assumptions; derived overflow; incompatible commute; changed evidence context; blocked storage; small screen comparison and translations.
