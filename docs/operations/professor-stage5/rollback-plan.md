# Backup and rollback plan

No public changes were applied, so **no rollback is currently required**. A
future controlled installer must write a concrete, root-protected receipt before
activation. This document is a prepared procedure, not an invented backup.

Receipt under `/var/backups/proptech-selfhost/stage5-ingress/<UTC>-<random>/`:

- Previous/next exact Git source, API/proxy image IDs and labels, project/file
  order, Compose model digest and sanitized delta; do not dump secret values.
- Backup every `/etc` file/unit/symlink before replacement. Record absent paths
  so rollback removes only files created by this apply. Backups with possible
  credentials stay root-only0600 in0700 directories; never copy them to Git/tmp.
- Preserve original host nginx configuration, TLS-only service/timer enablement,
  existing listeners, firewall policy snapshot and unrelated administration rules.
- Current API/proxy container IDs, existing volume identities, read-only local
  GIS binds and credential-file metadata. Preserve volumes even on failure.
- Existing ML PID/source/UID/model fingerprint, loopback launch mode and exact
  non-secret startup configuration. Do not include environment dumps.
- Protected ACME certificate/account state and deploy-hook prior version; no CA
  rotation, existing PostgreSQL TLS replacement or credential rotation.
- Approved router/DNS changes and named operator rollback owner. Agent cannot
  undo router/DNS implicitly or alter other hosted environments.

Safe rollback sequence after a failed future activation:

1. Close only the newly admitted public ingress path if needed, preserving
   management and existing host nginx80. Stop/disable only newly installed edge
   and monitoring units. Never flush rules or stop PostgreSQL.
2. Restore exact prior API/proxy Compose configuration and images, recreate only
   those consumers with no-deps/no-build. Keep all datasets, secrets and DB volumes.
3. Stop the newly installed ML socket/service only if its handover occurred;
   restore the exact prior loopback companion launch from the protected receipt.
   Never kill unrelated processes or train/rewrite artifacts during rollback.
4. Restore only changed `/etc` files/symlinks and previous unit states. Run nginx
   syntax validation before reloading the existing service. Keep protected backup
   and ACME evidence for diagnosis; never delete original data or shared config.
5. Operator restores only the approved DNS/forwarding entries if they changed.
6. Recheck local health/readiness, accepted GIS/Market/Valuation/Trend/Finder/ML,
   auth denial/ownership, private DB and loopback8080/8081. Record fixed statuses.

Never `docker compose down -v`, delete/recreate volumes, DROP/TRUNCATE, delete
transactions, change Supabase users, touch/dev/sda or mutate X9. Do not roll back
accepted Stage1–4 migrations or authority approvals as part of ingress rollback.
