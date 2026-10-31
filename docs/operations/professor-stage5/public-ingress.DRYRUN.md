# Public ingress change dry-run — NOT AN APPLY

Current result: BLOCKED_PLAN, exit2. No DNS/router/firewall/listener change,
certificate issuance, package install, container recreation, secret inode renewal,
database migration or ML restart has occurred. Plan is the checked-in
`config/professor-direct-ingress.plan.example.json`; identity and router WAN are
intentionally null. There is no executable public apply yet.

Proposed controlled changes after all gates and operator approvals:

| Surface | Exact intended delta | Current action |
|---|---|---|
| Router | Reserve192.168.200.215; forward TCP443 and HTTP-01 TCP80 only | None |
| DNS | Approved owned hostname A only, if domain chosen; no current AAAA | None |
| Packages | Approved/pinned Certbot with demonstrated required capabilities | None |
| Existing nginx | Add one named HTTP-01/redirect site; keep default80 | None |
| Public edge | Separate TLS-only nginx config/service on443 | None |
| TLS | Separate staging/prod persistent root-owned ACME dirs; trusted production chain | None |
| Renewal |12h timer, validated deploy/reload hook; no raw request logging | None |
| API environment | Exact host union + exact approved CORS list only | None |
| Inner reverse proxy | Read-only new nginx config and ML socket directory | None |
| ML lifecycle | Install reviewed source privately under/opt; same pinned model; socket/service | None |
| API containers | Recreate only api and reverse_proxy, --no-deps, after merge approval | None |
| Database containers/volumes | No delta, recreation or migration | None |
| Firewall | Interface-specific80/443 only after effective-rules/admin review | None |
| Boot | Verified persistent DB TLS recovery + Stage2/4 credential staging + fixed-source services | None |
| Monitoring | Trusted local TLS and bounded API/ML boolean checks | None |

The future installer must:

1. Capture image IDs, project labels, exact Compose file order, sanitized mount
   metadata, listeners, policy, active service state and protected `/etc` backups.
   Protected original configuration containing secrets stays root-only and out of Git.
2. Refuse changed ownership, unexpected listener/conflicting units, unsafe storage,
   credential-bearing env merges, new services or any database/volume delta.
3. Compare the actual merged model in memory against its exact prior model using
   `validate_compose_delta`; never print/store raw `compose config` or environment.
4. Render into root-owned staging paths; validate nginx, systemd, certificate,
   origin and resource limits. Require exact approved plan fingerprint.
5. Preserve existing host nginx80. Validate dedicated TLS-only service independently;
   do not require a production certificate merely to start HTTP-01.
6. Hand over only the verified ML companion PID/ports from its interactive scope,
   install same-source/model socket activation; never broad-kill Python processes.
7. Apply only the reviewed API/proxy override using the current full Compose file
   list, existing project `proptech-selfhost`, no-deps and no-build. Never run a
   general `up` or `down -v`, change DB roles/secrets or recreate database services.
8. Validate private API/ML/auth isolation immediately; only then admit public443.
9. Write a sanitized apply report and exact rollback receipt. Stop on any failure.

Missing gates are authoritative in
`reports/professor-stage5-ingress/public-ingress-dry-run.json`. Outside-LAN HTTPS
acceptance is a later result, not something a plan can prove before deployment.
No operator is instructed to edit flags to bypass these gates.
