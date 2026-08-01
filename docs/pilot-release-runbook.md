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
