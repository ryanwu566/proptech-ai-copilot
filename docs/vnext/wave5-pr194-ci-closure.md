# PR #194 browser CI closure — 2026-10-17

Published base: `9a47f7d270483a73315dfed399f2fe3ff008eb58` on
`feat/documents-citation-evidence-v1`. The working tree was clean and origin's
feature ref matched that SHA. This closure appends one normal commit; no rebase,
amendment of published commits, force-push, merge, deployment or migration.

## Contract findings

The tenth h2 is **來源引用** (English: **Source references**), rendered by
`ReportCitationReferences` after the nine numbered report sections. It is an
intentional Wave 5 peer section under the report h1, not a duplicate or an
accessibility hierarchy defect. The commercial UI test now asserts the ordered
names of the nine existing sections and this citation register instead of the
stale magic count of nine. Production heading markup remains unchanged.

The original citation register reused the screen provenance grid in print:
11 definition pairs, 8px row gaps, 1rem vertical margins, and a reference-list
`break-inside: avoid`. The first definition list measured 305.27px high even
before A4 line wrapping. This inflated each complete reference and amplified
page breaks; mobile's single-column rule also applied unless explicitly
overridden. The standard fixture has 22 real citation records. All six original
PDFs (Chromium/Chrome at 1440, 1024 and 390) reproduced **29 pages**.

The fix scopes compact typography and flow to printed citation registers:
9pt text at 1.35 line height; inline, bold term labels with visible separators;
normal wrapping; 1mm definition-list spacing and 2mm spacing between records.
Each complete record still avoids splitting where it fits on a page. All fields,
full identifiers, URLs, limitations, dates and source labels remain rendered.
The existing 15mm A4 margins, report body, screen layout, citation identities,
graph/model and provider behavior remain unchanged.

A browser-only style probe reduced the same report to **20 pages**, retaining
all 22 IDs and without clipped PDF text. A rasterized reference page was inspected
for readability. Final results from the built application are recorded below.

## Regression protection

The original PDF byte-size and **at most 20 pages** assertions remain intact.
No retries, timeout, fixture content or acceptance ceiling was relaxed. The
existing CI-installed PyMuPDF auditor now also checks actual A4 dimensions, no
clipped text, and that every citation ID and every rendered provenance value is
present in extracted PDF text. Reference entries must match the fixture's real
evidence graph with no duplicate IDs; each resolves for Case A and fails for
Case B. Existing zero-provider and Save/Reopen checks continue afterward.
Every reference entry and definition field must also remain visible under print
media, including ancestor visibility/opacity checks, so shared PDF strings cannot
mask a hidden record.
Each PDF run attaches a page-count/reference/geometry audit for inspection.

## Validation checklist

- [x] Reproduce all 12 reported failures on the published build in both browsers,
      all three widths, retries=0: six stale-heading and six 29-page failures.
- [x] Confirm tenth heading and measure pagination root cause with real PDFs.
- [x] Implement print-only layout change and semantic heading assertion.
- [x] Run both complete affected specs first, Chromium and Chrome, retries=0.
- [x] Then run Wave 5, Saved Case/Compare/Report and Grounded Copilot regressions.
- [x] Run typecheck, lint, build and fresh route/global budgets.
- [x] Finish independent read-only review, append one normal commit and verify
      clean tree and unchanged published parent/ref.

## Verification results

| Check | Result |
| --- | --- |
| Original failing groups, both browsers / three widths, retries=0 | All 12 failures reproduced; all six original PDFs were 29 pages |
| Complete affected specs, Chromium, retries=0 | 41 passed |
| Complete affected specs, Chrome, retries=0 | 41 passed; 82 total across both browsers, no failures/skips/retries, one uninterrupted 6.2-minute run |
| Final actual A4 PDFs | 20 pages in both browsers at 1440, 1024 and 390px; all six passed full provenance and geometry audits |
| Wave 5 / Saved Case / Compare / Report / Grounded Copilot regressions | 39 passed per browser, 78 total, no failures/skips/retries; one uninterrupted 4.0-minute run after the affected specs |
| Native focused model tests | 32 document/case/report tests, 19 Grounded Copilot tests and 9 Saved Case repository tests passed |
| `npm --prefix frontend_next run typecheck` | Passed after final test changes |
| `npm --prefix frontend_next run lint` | Passed; zero errors, 23 unchanged warnings outside this diff |
| `npm --prefix frontend_next run build:e2e` | Passed; Turbopack, TypeScript and static generation |
| Route budgets | All 17 routes and coverage passed after fresh production-browser measurement |
| Global assets | 3,324,007 / 8,000,000 static bytes; largest JS 602,295 / 900,000 bytes; total JS unchanged at 3,146,161 bytes |
| Independent read-only review | No remaining Critical, Important or actionable Minor findings after adding per-record print visibility checks |

Affected-spec command (from `frontend_next`):

```text
node e2e/run-e2e.cjs e2e/commercial-uiux.spec.ts e2e/final-production-acceptance.spec.ts --project=chromium --project=chrome --workers=1 --retries=0 --max-failures=1 --output=../.tmp/pr194-affected
```

The original-failure reproduction used those same two files and browser/retry
settings, restricted to `--grep 'commercial screens fit|saved Taipei transit fixture'`,
with artifacts under `.tmp/pr194-before`. No timeout override was passed.

Subsequent browser-regression command (from `frontend_next`):

```text
node e2e/run-e2e.cjs e2e/document-evidence.spec.ts e2e/commercial-overview-save.spec.ts e2e/commercial-compare-report.spec.ts e2e/grounded-property-copilot.spec.ts --project=chromium --project=chrome --workers=1 --retries=0 --max-failures=1 --output=../.tmp/pr194-regressions
```

Native checks: `npm --prefix frontend_next run test:documents`, then
`node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test frontend_next/lib/workspace/grounded-copilot.test.ts frontend_next/lib/workspace/case-repository.test.ts`.
No backend or migration changes required expanding into unrelated Python suites;
the actual PDF audits use the existing CI-pinned PyMuPDF dependency.

The updated fixture checks all 22 reference entries and all their provenance
fields. Its Save/Reopen and zero-provider assertions run after actual PDF audits.
Fresh references and PDF content remain saved snapshots, not live evidence.
The production report's DOM, heading hierarchy and evidence model are unchanged.
PDF identifiers wrap without truncation and no record is hidden for pagination.
A final built-application reference page was rasterized and visually inspected.

Route measurement used the unchanged official helper in groups of 6, 6 and 5
routes, preserving its deadlines, provider blocking and two cold samples each at
390px and 1440px. Receipts were combined only after the build fingerprint matched,
then checked with unchanged route/global budgets. No threshold was raised.

Artifacts are ignored local files: `.tmp/pr194-before`, `.tmp/pr194-affected`,
`.tmp/pr194-route-budgets.json`, and the print probe/raster files under `.tmp`.
The actual PDF audit JSON is stored next to each PDF and attached to the browser
result. GitHub CI itself has not been rerun by this local, unpushed follow-up.

## Files and local disposition

Four changed files:

- `frontend_next/components/evidence/document-evidence.module.css`
- `frontend_next/e2e/commercial-uiux.spec.ts`
- `frontend_next/e2e/final-production-acceptance.spec.ts`
- `docs/vnext/wave5-pr194-ci-closure.md`

The final follow-up commit is a direct child of published `9a47f7d`, with subject
`fix: align evidence report print contracts`; its SHA is supplied in the handoff
rather than embedded in its own content. Final verification checks one commit
ahead of the unchanged origin feature ref, the exact four-file diff and a clean
working tree. No migration, workflow bypass, history rewrite or automatic push
is included. Safe to publish this follow-up normally: **YES**.
