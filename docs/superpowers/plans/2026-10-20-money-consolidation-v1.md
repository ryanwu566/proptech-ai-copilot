# Money consolidation v1

Implement the supplied buyer workflow in the existing `/cases/[caseId]/finance` route.

1. Add focused regression tests for saved manual prices, non-default assumptions, explicit unknowns, and asking/offer cash and mortgage projections. Reuse the existing scenario equation; keep finance snapshot and Report/Compare contracts.
2. Arrange the page as Money summary → cash needed → monthly/holding → transaction/tax verification → offer scenarios. Use existing design components, localized copy, and compact rows instead of wide tables.
3. Keep the existing loan and holding endpoints. Offer previews run locally. Preserve price provenance, calculation time, saved assumptions, identity checks, and stale-result boundaries. Unknown closing costs remain excluded from a labelled cash subtotal.
4. Add browser coverage for the four locales, saved scenario reopening, provider boundaries, and 390/430 layouts. Initially defer execution during the shared test-slot restriction. The user subsequently freed the slot: run only focused Money browser tests with bundled Chromium, headless, one worker and zero retries, including saved-scenario Report/Compare projections.
5. Run focused unit and Report/Compare regression tests, typecheck, focused lint, and inspect the final diff. Create one local implementation commit, without pushing. Record the final browser results and readiness in `docs/qa/money-consolidation-v1.md`.
