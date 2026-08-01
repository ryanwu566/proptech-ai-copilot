# Backup and Restore

## What is backed up

The managed Postgres provider is the system of record for pilot sessions,
consents, profiles, contacts, events, feedback, professional reviews, and
TaxOracle history. Provider snapshots and point-in-time recovery should cover
those tables. Exported evidence packs require the same retention controls as
their source records.

Code, migrations, and static official-data artifacts are regenerated from the
repository and release artifacts; they are not substitutes for database
backups.

## Local drill

The local-only commands are:

```text
python scripts/backup_pilot_evidence.py --source <local-db> --destination <backup-db>
python scripts/restore_pilot_evidence.py --source <backup-db> --destination <restored-db> --confirm-local-restore
```

The scripts refuse production mode and emit only status and integrity
categories. They do not connect to hosted Postgres. A production restore uses
the managed provider snapshot or PITR process, followed by migration and
readiness verification.

## Retention and deletion

Participant deletion applies to the active database through the existing
scoped workflow. Backups may retain immutable historical pages until the
provider retention window expires; operators must document the window and any
legal hold rather than promise immediate erasure from every backup copy.
