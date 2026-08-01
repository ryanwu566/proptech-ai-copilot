# Market data operations v1

Use `python scripts/plvr_market_pipeline.py discover` to validate the local
official source registry. Production import requires an operator-approved
staging location, a protected database secret, a release checkpoint, and a
successful dry-run. No credential belongs in a command line, repository, URL,
frontend bundle, or log.

Imports are single-writer operations. Raw archives are temporary server-side
artifacts with bounded retention. The active release is never deleted before a
new release passes integrity checks. Failed releases remain evidence and do
not replace the previous active release. Rollback reactivates a previously
validated aggregate release rather than re-normalizing raw data.

The scheduled workflow is conservative and runs only from `main`. It does not
claim that production has data until an operator has completed the data launch
and verified a hosted query.
