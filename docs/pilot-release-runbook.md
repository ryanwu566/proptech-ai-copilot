# Closed Pilot Release Runbook v1

## Purpose and boundaries

This runbook collects real, privacy-safe evidence about the closed pilot. It
does not create customer, revenue, accuracy, time-saving, or professional
endorsement claims. Empty evidence remains empty. TaxOracle, valuation, loan,
terrain, market, comparison, and viewing-decision rules are unchanged.

## Pilot setup

1. Configure `PILOT_EVIDENCE_DB_PATH` and the server-side `PILOT_ADMIN_TOKEN`.
2. Create a campaign through the protected administration boundary; never put
   the campaign code in frontend source, a URL, or a public asset.
3. Confirm administration is disabled when the admin variable is absent.
4. Give a participant the campaign identifier and code through a private channel.

## Consent and moderation

Show the separate participation, interaction-metric, written-feedback,
follow-up-contact, and anonymous-publication choices. Participation can continue
without publication permission. Explain that browser narration is explicit,
does not upload audio, and does not store transcripts. Do not collect addresses,
prices, coordinates, client records, secrets, or provider payloads.

## Pilot task

Use the three catalog tasks: tax and holding-cost preparation, one supporting
evidence review, and an explicit assistive-narration task. Record task events,
not property values. Active timing uses visibility and bounded activity seconds;
do not call it time saved.

## Feedback and review

Ask the bounded clarity, trust, usefulness, reuse, alternative-tool,
decision-maker, privacy, integration, and optional willingness-to-pay questions.
Limit free text and review it before any publication. Professional reviews are
versioned, private by default, and never displayed as public approval without
qualification verification and publication approval.

## Evidence verification and export

Administrators review provenance, verification, and publication status before
export. Public evidence is aggregate-only and excludes test fixtures. Show a
numerator and denominator for distributions. For a small sample show:
`Exploratory evidence — sample size is too small for a general conclusion.`
The JSON, CSV, and printable HTML exports contain methodology, exclusions,
limitations, product version, and retention notes, but no identity, contact,
raw case facts, quotation, coordinates, SQL, or secrets.

## Retention and deletion

Contact data is separate from analytical evidence. A participant can request a
privacy-safe export and run a deletion dry-run before deleting their own session.
The deletion response reports affected record counts. Test fixtures are marked
and excluded from production aggregates. Do not promise deletion behavior that
the deployed database has not enabled.

## Release checklist and rollback

- migrations applied and rollback guidance reviewed;
- database and public aggregate health checked;
- administration remains disabled until configured;
- fixture isolation and publication revocation tested;
- rate limits, payload bounds, and idempotency tested;
- four locales, keyboard navigation, mobile widths, console/page errors tested;
- privacy policy and terms reviewed;
- bundle budget and existing product suites pass.

Rollback means deploy the previous application version and follow the database
operator's reviewed additive-migration rollback plan. Do not delete evidence
tables without a retention decision.

## Human work remaining

Recruit real participants, obtain consent, verify professional qualifications,
review evidence, approve quotations, and decide whether any aggregate is fit
for publication. Until then the public Evidence Center must state zero completed
pilot sessions, zero paying customers, willingness to pay not validated,
professional review pending, and no publishable testimonials.

## Exact local release-candidate commands

Run these commands from the repository root. They use a disposable local
database for migration checks and do not contact production services:

```powershell
python scripts/validate_pilot_environment.py
python scripts/validate_pilot_evidence_migration.py
python -m pytest -q tests/test_pilot_observability.py tests/test_pilot_environment.py tests/test_pilot_migration_validation.py tests/test_pilot_api.py tests/test_pilot_evidence.py
npm.cmd --prefix frontend_next run build
python scripts/check_frontend_bundle_budget.py
npm.cmd --prefix frontend_next run build:e2e
Set-Location frontend_next
node e2e/run-e2e.cjs e2e/pilot-evidence.spec.ts --project=chromium
node e2e/run-e2e.cjs e2e/pilot-evidence.spec.ts --project=chrome
Set-Location ..
python scripts/pilot_release_quality_gate.py --execute
```

The browser suite covers rejected access, the participant workflow, the
publication-consent boundary, four locale entry smoke, and 360/390/430 pixel
overflow checks. The production gate reports `pass`, `failed`, and `not_run`
separately; a required browser or build check that was not run is not a pass.

## Environment activation and rollback

1. Run `python scripts/validate_pilot_environment.py` before enabling a pilot.
2. Configure `PILOT_EVIDENCE_DB_PATH`, `PILOT_ADMIN_TOKEN`, and
   `PILOT_REVIEW_TOKEN` only in the server runtime secret store.
3. Run the migration validator against a disposable database, then apply the
   additive migration through the reviewed database operator process.
4. Create a campaign with the protected admin API and disable it with the
   same boundary after the pilot window.
5. Export aggregate evidence only after review and publication approval.
6. For a participant request, run the deletion dry-run, confirm the bounded
   counts, then delete that participant session. Repeat requests return the
   existing unavailable state rather than targeting another participant.
7. Revoke publication before any re-review or incident response when evidence
   must be withdrawn. A revoked record is not eligible for public output.
8. Rotate the admin and review tokens in the server secret store, then rerun
   the readiness command. Never place them in the browser, bundle, URL, or
   issue text.
9. To roll back the application, deploy the previous release and keep the
   additive evidence tables intact until the retention decision is approved.
   Disable the pilot administration boundary during rollback. Do not delete
   tables as an application rollback step.
10. After recovery, rerun the environment, migration, browser, and bundle
    checks, confirm fixtures remain excluded, and check professional-review
    rule/product versions for stale status before re-enabling access.
