# Preparation that does not require WAN

All plans below are prepared; none has been applied. Router status does not block
source/configuration audit or these reviews. It does block later direct public
acceptance. **The system is not waiting only for router/WAN.**

The final [provider/job adoption and retirement matrices](adoption-retirement-matrix.md)
separate current local evidence from public caller migration. New optional
maintenance implementations are later admission/retirement work; they are not
silently made mandatory to start the accepted limited local profile. All actual
deployed credential, IAM/caller and protected host evidence gaps remain open.

| Workstream | Prepared/tested material | Remaining evidence/action independent of WAN |
|---|---|---|
| Provider names/config | Full dependency JSON/CSV; four indexed env examples projected to names only | Actual Cloud Run/Render/Vercel/GitHub secret-name inventories; optional store metadata where inaccessible |
| Credentials | Six accepted API files and DB-only mounts hash-verified; safe conditional install/recovery procedures | No current-profile install needed; any future provider needs explicit admission and restrictions/quotas |
| Retirement | Per-service dependency graph and exact CI refresh references | Resolve unique remote caller/data/ADC/IAM dependencies and local maintenance-job disposition; retire nothing |
| Nginx | Existing80 preserved; dedicated TLS-only service; fixed127.0.0.1:8080 upstream; private ML socket bridge | Actual root Compose merge and UID/socket metadata review; no service install/recreation yet |
| TLS | Domain and verified-tool public-IP alternatives, separate ACME staging/prod stores, validated reload/timers | Choose owned identity; approve/install verified ACME tooling; stage/renew/validate trusted production chain after separate network gate |
| Firewall | Interface-scoped80/443 only, private DB/8080/8081/Docker, admin preservation and rollback procedure | Effective root rules/forwarding review and console/management recovery; no change authorized |
| Boot | Explicit credential/TLS/Docker/ML/proxy ordering and before-login acceptance | Identify trusted persistent DB TLS restoration source, restore procedure and immutable ML source/runtime dependencies |
| Rollback | Exact protected snapshot/backup/consumer-only restore requirements | Capture concrete root receipt immediately before a separately approved apply; no invented backup or rollback needed now |
| Vercel | Exact-origin policy, Preview->Production checklist and public API base-name contract | Actual origin/env-scope/CSP review; no production change; later authenticated browser E2E |

## Host evidence gate

The existing operator-only `--host-audit` is read-only: secret file metadata,
selected Docker mount/port/name metadata, fixed nonsecret guard comparisons,
firewall summary and service state. It does not return credential values or
install anything. One already reviewed command, **not ingress apply**:

```bash
sudo python3 -B /home/andy/.codex/worktrees/7d59/proptech-ai-copilot/scripts/ops/professor_stage5.py --host-audit
```

The agent has not run this command or attempted sudo. A sanitized receipt can
resolve accessible host metadata, but does not by itself prove complete firewall
policy, a TLS backup's correctness or cloud credential presence. No direct Docker
socket access is required merely to duplicate accepted Stage4A evidence.

## TLS / reboot prerequisites

`/run/proptech-selfhost/secrets` and `/run/proptech-selfhost/tls` are volatile.
Stage2/4 staging restores credentials, not trusted PostgreSQL TLS. Preserve the
current CA/server identity and exact private key permissions; do not generate
replacement keys to make boot pass. The trusted persistent restoration source
is still unverified. Before a boot installer is released, the operator must
identify that protected source, validate public certificate identities and
private key pairing internally without exposing keys, and approve the exact
restore/ordering plan. Never copy keys into Git or evidence.

Docker restart policy is insufficient if bind files are absent. Do not add a
global Docker dependency that disrupts unrelated services. Keep original volumes,
verify staged material first and start only reviewed project consumers. No
database reinitialization, volume recreation or `down -v` is permitted. ML must
move from its current interactive scope to the prepared fixed-source service,
through an explicitly verified PID/source handover; never broad-kill Python.

Reboot is a later explicit operator action. Acceptance must run before login,
verify trusted local TLS, all accepted API/GIS/ML/auth contracts, original volume
identities, disabled paid providers/market_ops and private listeners, then repeat
outside-LAN browser acceptance. No reboot has occurred during preparation.

## Release sequence once prerequisites are proved

1. Close root and cloud metadata gaps; reconcile the approved production profile.
2. Obtain WAN/control and owned HTTPS identity evidence; approve exact network
   changes separately. No tunnel or managed backend fallback.
3. Release/review a concrete fail-closed installer against the actual merged
   Compose model, staged artifacts, protected backups and exact rollback receipt.
4. Operator-controlled host apply and local acceptance; only then approved direct
   HTTPS admission and outside-LAN checks. Keep8080/8081/5432 private.
5. Vercel Preview E2E, approved Production cutover and E2E; keep rollback.
6. Approved reboot/renewal acceptance and zero unique old-cloud dependencies;
   only then consider separately approved Cloud Run/Render retirement.

No prerequisite can be satisfied by editing a readiness boolean or treating a
repository reference as a deployed credential. All current plans retain
`ingress_apply_allowed=false` and no public apply command.
