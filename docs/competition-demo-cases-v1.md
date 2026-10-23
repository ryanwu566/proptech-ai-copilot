# Competition demo cases A/B (v1)

Home → **查看完整範例案件 / View complete example cases** installs two local demonstration
snapshots and opens Demo A's real Overview. Every surface (Overview, Market, Location, Risk,
Money, Decision Room, Report, Compare, Case Pulse, Command Palette) is the production component
reading saved evidence; there is no separate demo UI.

## Provenance

- Data lives in `frontend_next/lib/workspace/demo-cases.ts`, built on the current saved-case,
  finance-evidence, terrain-reference and Decision Room schemas (same shape as the approved
  `e9` test fixture). Unit tests pass both snapshots through the real normalizers and adapters.
- All values are illustrative and dated `DEMO_SNAPSHOT_DATE` (2026-10-01). Addresses are road-level.
  Market summaries, risk notices and the asking-price note carry "示範快照" text, and every demo
  route shows a localized disclosure (`DemoCaseNotice`): demonstration snapshot, example data,
  not a live query, not official evidence; unknown stays unknown; no match ≠ safe; no ranking,
  winner or purchase advice.
- Valuation stays unavailable (never fabricated). Some risk layers are deliberately unavailable /
  limited so UNKNOWN states are visible.
- Installing or opening demos makes **zero** provider/API calls; basemap tiles follow existing rules.

| | Demo A — 新北市板橋區文化路一段 | Demo B — 臺北市文山區木柵路三段 |
|---|---|---|
| Asking | 1,680 萬 · 28 坪 · 22 yrs · elevator | 1,980 萬 · 30 坪 · 38 yrs · walk-up |
| Market (district median) | 53.6 萬/坪, 132 samples | 62.4 萬/坪, 61 samples |
| Commute to 臺北車站 | 24 min transit · 府中 BL 640 m | 41 min transit · 木柵 BR 420 m |
| Risk | flood + liquefaction recorded; landslide/debris no match; geo-sensitivity unknown | landslide recorded; flood/liquefaction no match; debris unknown; geo limited |
| Money | 20% down, 2.185%, 30 yr, income 15 萬 assessed | 30% down, 2-yr grace, income not provided (unassessed) |
| Decision Room | 6 actions (verification/question/task; open, in progress, blocked, done) | 3 actions |

## Storage and reset

- Reserved IDs `proptech-demo-a` / `proptech-demo-b`; real cases use random IDs, so they never collide.
- **Ensure (Home CTA):** installs only missing demos (with their seeded Decision Room) under the
  shared saved-case lock and validated writer. Existing demos — including the viewer's edits — are
  left untouched; repeated clicks never duplicate. Real cases keep their exact stored objects.
- **Restore (button in the demo disclosure):** resets both demos and their Decision Rooms to the
  snapshot. Never touches other cases.
- **Deleted demo:** the next CTA click reinstalls it.
- **Capacity:** if the 10-case limit cannot fit the missing demos, nothing is written or evicted and
  Home shows a bounded message with a link to case management.

Tests: `lib/workspace/demo-cases.test.ts`, `e2e/competition-demo-cases.spec.ts`.
