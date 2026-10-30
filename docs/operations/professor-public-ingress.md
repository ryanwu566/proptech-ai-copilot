# Professor direct public HTTPS — Stage 5 preparation

Status: **PARTIAL; no public apply is released**. Everything in this change is
preparation, non-privileged observation, or isolated testing. The API remains
private. No router, DNS, firewall, listener, certificate order, cloud deployment,
provider activation, database, volume, secret or running service was changed.

## Current network and runtime

| Item | Observed state |
|---|---|
| Server / LAN | andy-PN41; enp2s0; 192.168.200.215/24, DHCP |
| Default gateway | 192.168.200.1 |
| Public outbound IPv4 | 140.119.55.43, independently observed over HTTPS twice |
| Router WAN / control | Unknown; no authenticated management interface available |
| IPv6 | Link-local only; no global address or default route |
| Inbound reachability | PENDING; no outside-LAN acceptance |
| NAT | Private first hop, then public campus hops; CGNAT/double NAT unproven |
| Existing public listeners | Host nginx 1.28.3 on IPv4/IPv6 port80; port443 free |
| Private listeners | Docker reverse proxy 127.0.0.1:8080; ML 127.0.0.1:8081 |
| PostgreSQL / Docker API | No host5432/2375/2376 listener observed |
| Administration | Existing unrelated3322 listener; preserve its policy |
| Firewall | UFW active/enabled, configured default deny inbound; effective rules unreviewed |
| Certificate client | Neither Certbot nor Caddy installed |
| Backend hostname | No owned domain/subdomain established |

`PUBLIC_IP_OBSERVED` is **not** `INBOUND_REACHABILITY_CONFIRMED`. The two
observers see outbound NAT; neither proves an exclusive public WAN assignment,
router control, forwarding or inbound permission. The gateway's next hops
140.119.55.254,140.119.240.254,140.119.240.230 are supporting route observations
only. A WAN address in100.64.0.0/10 indicates shared-address CGNAT; an RFC1918 WAN
indicates another private routing/NAT boundary, not definitive ISP CGNAT.
See [RFC6598](https://www.rfc-editor.org/rfc/rfc6598).

**Single next network instruction:** ask the gateway/network administrator to
confirm the WAN assignment and inbound443 authority relative to140.119.55.43,
and reserve192.168.200.215 for this server. Do not forward ports yet. If CGNAT
prevents inbound IPv4, request ISP public/static IPv4, or separately assess
routable and safely firewallable IPv6. No tunnel is a fallback.

## Prepared architecture

```text
Browser -> Vercel Next.js (frontend only)
        -> direct Professor HTTPS :443
        -> dedicated TLS-only service using installed nginx
        -> 127.0.0.1:8080 (existing Docker reverse proxy)
             -> FastAPI -> private PostgreSQL + verified local GIS
             -> exact ML routes -> private Unix socket -> ML companion
```

Keep the installed nginx package and existing host service/default80 site.
Prepare a separate TLS-only `proptech-public-ingress.service`, with its own PID
and configuration, plus a named HTTP-01/redirect site in existing nginx. This
keeps ACME HTTP validation independent of a failed/expired public certificate.
It adds no proxy software/package dependency. Caddy would require another edge
daemon and conflict on80; its default IP/local certificates use a local CA,
which is insufficient for public browser trust.
See [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).

Every public edge upstream is exactly `http://127.0.0.1:8080`. No public8080,
8081, PostgreSQL, Docker API or proxy admin endpoint is introduced. The prepared
inner proxy exposes only GET `/valuation/ml/v1/status` and POST
`/valuation/ml/v1/estimate` over the private ML Unix socket. Other ML paths return
404. Those two paths also admit browser OPTIONS preflight; the companion uses
the same exact approved CORS origins, without cookie credentials. ML still reports observational estimates, honest support/limitations,
`is_actionable=false`, and no confidence probability. No model retraining or
inference semantics changed.

### TLS and identity decision

HTTPS strategy is **PENDING**. Do not substitute a Vercel, Cloud Run or Render
hostname, invent a domain, or use a self-signed production certificate.

For an operator-owned domain, establish DNS control first, then approve exactly
`A <owned-api-host> -> <controlled-public-IPv4>`. Do not publish AAAA on this host
while there is no admitted global IPv6 route/firewall. Certbot webroot HTTP-01
requires inbound80 both for issuance and subsequent renewals; the rest redirects
to canonical HTTPS. Unknown Host/SNI is denied. No DNS write is performed here.

For a controlled public IPv4, Let's Encrypt supports trusted IP certificates
with the160-hour shortlived profile. Its Certbot webroot IP path requires5.4+.
The renderer uses `--required-profile shortlived` to reject profile fallback;
tool installation/version, IP control, CA-chain/browser validation and automatic
renewal remain gates. This is not an assertion that existing tooling supports
IP certificates. See [Let's Encrypt IP support](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability/),
[Certbot webroot requirements](https://letsencrypt.org/2026/03/11/shorter-certs-certbot)
and [Certbot profile flags](https://eff-certbot.readthedocs.io/en/stable/using.html).

Use distinct ACME staging and production config/work/log directories. Staging
chain validation never counts as trusted production. Proposed production
storage `/etc/proptech-selfhost/acme` is root-owned0700; account/private keys0600;
challenge webroot `/var/lib/proptech-acme` contains challenge material only.
Neither ACME credentials nor TLS keys belong in API mounts, Git, images or Vercel.
Twice-daily renewal has a deploy hook validating trusted chain, exact identity,
at least24h remaining and nginx syntax before reload. Failure retains the current
configuration or refuses startup. The separate HTTP service remains available
to obtain a replacement. Test issuance/renewal/recovery before production use.

### Edge security and application configuration

Prepared defaults: TLS1.2/1.3, no early data/tickets, fixed canonical Host,
overwritten forwarding headers, no Forwarded header, one nginx worker,1MiB body
limit,10s headers/15s body/30s upstream timeouts,10req/s per-IP with burst20,
20connections per-IP. Admin/ops/metrics/docs/reviewer and refresh paths are
blocked. Access logs are off; raw nginx error logs go to `/dev/null` to avoid
credential-bearing request lines. Separate monitoring records only booleans,
never headers, bodies, tokens or query values. Authentication/profile/user
errors remain the established V1 contract.
See [nginx proxy](https://nginx.org/en/docs/http/ngx_http_proxy_module.html) and
[TLS](https://nginx.org/en/docs/http/ngx_http_ssl_module.html) documentation.

Keep FastAPI `proxy_headers=False` and the inner proxy's forwarding-header strip.
The canonical Host reaches API_ALLOWED_HOSTS; client-supplied forwarding values
do not determine auth or owner. Anonymous backend quotas currently aggregate at
the inner proxy; the edge adds per-peer limits. Real-IP propagation would need a
separate explicit trust-chain change. It is not enabled by this plan.

Prepared Compose overlay changes only API_ALLOWED_HOSTS/CORS_ALLOWED_ORIGINS and
the inner proxy's read-only config/Unix-socket mounts. `validate_compose_delta`
refuses image/secrets/network/global/DB changes. Preserve all existing exact API
hosts and add only the approved ingress name. Exact Vercel production origin:
`https://proptech-ai-copilot.vercel.app`. Preview origins require explicit review;
none is currently admitted. Optional local development origins must be explicit
localhost/127.0.0.1 ports3000/3001/5173. No wildcard CORS or wildcard Vercel suffix.

Supabase remains identity authority, public issuer
`https://flyhsjcynreuofbcdxod.supabase.co/auth/v1`, audience`authenticated`.
Professor PostgreSQL remains application-data authority. Browser V1 mutations
use bearer JWT with credentials omitted; no ambient-cookie auth is introduced.
Do not add cookie-based authorization or weaken Origin/ownership checks. Legacy
pilot cookie/security settings remain unchanged; their privileged routes are
blocked at the edge. See [auth contract](../contracts/auth-user-api-v1.md).

## Tooling, evidence and operator gates

Stage5 continuation adds an expanded credential/configuration audit and an
observation-only router decision checklist. See the current
[credential matrix](provider-credential-matrix.md),
[names-only evidence collection](professor-stage5/credential-evidence-collection.md),
[router/CGNAT checklist](professor-stage5/router-cgnat-checklist.md), and
[conditional HTTPS plan](professor-stage5/conditional-https-plan.md).
No required secret is evidenced missing for the accepted current profile. Live
Cloud Run/Render/Vercel/GitHub Actions inventories are still unverified, so the
complete provider audit and production-critical migration remain incomplete.

`--dependency-matrix` adds configuration consumers, locations, production
requirements, migration and retirement states to the initial credential-only
audit. `--router-plan` validates operator-visible metadata without contacting or
changing a router. Both remain preparation-only, with no apply operation.

The later no-WAN continuation audits four indexed env examples through an
assignment-prefix-only Git projection; Python receives names, never RHS values.
Actual host envfiles and key files are not opened. `--retirement-inventory`
records tracked regular workflow/Render declarations without following symlinks
or running any job. See [dependency inventory](professor-stage5/retirement-dependency-inventory.md)
and [remaining no-WAN gates](professor-stage5/no-wan-preparation.md).

- `scripts/ops/professor_stage5.py --network-audit`: non-privileged diagnostics.
- `--matrix`: deterministic repository credential-name inventory.
- `--plan config/professor-direct-ingress.plan.example.json`: blocked dry-run;
  exit2 is expected. No image build, certificate order or file installation.
- `--host-audit`: operator-root **read-only** metadata audit, no activation.
  It writes a sanitized `/tmp/professor-stage5-host-*/diagnosis.json` receipt.
  Credential files are stat'ed only; values and environment values are not exported.

One reviewed optional command for that metadata audit (not public apply):

```bash
sudo python3 -B /home/andy/.codex/worktrees/7d59/proptech-ai-copilot/scripts/ops/professor_stage5.py --host-audit
```

The agent has not run that command. Docker socket access is unavailable without
privilege; active container/mount/DB separation facts are inherited explicitly
from accepted Stage4A evidence, not claimed as a fresh Docker inspection. Actual
root Compose merge and effective firewall review are still required. Synthetic
Compose5.6.1 merges and pure delta validators are tested without secret values.

There is deliberately **no `--apply` and no public operator apply command**.
WAN ownership, hostname/IP ownership, effective firewall, ACME tooling and trusted
TLS recovery across reboot are unproved. Readiness cannot be fabricated by editing
plan booleans: even complete inputs remain preparation until a separate reviewed
controlled installer is released against real evidence.

Evidence: [acceptance](../../reports/professor-stage5-ingress/acceptance.json),
[network](../../reports/professor-stage5-ingress/network-audit.json),
[dry-run](../../reports/professor-stage5-ingress/public-ingress-dry-run.json),
[credential matrix](provider-credential-matrix.md). Accepted prior host evidence:
`/var/backups/proptech-selfhost/stage4a-activation/20261030T040052Z-8cd21b4e0da2`;
sanitized copy `/tmp/professor-stage4a-activation-dpf5uno4`.

## Operational plans

- [Exact change dry-run](professor-stage5/public-ingress.DRYRUN.md)
- [Firewall/router](professor-stage5/firewall-plan.md)
- [Reboot and ordering](professor-stage5/reboot-plan.md)
- [Backup/rollback](professor-stage5/rollback-plan.md)
- [Outside-LAN acceptance](professor-stage5/external-acceptance.md)
- [Vercel cutover](professor-stage5/vercel-cutover.md)
- [Cloud retirement](professor-stage5/cloud-retirement.md)

Never touch `/dev/sda`, X9 source, serving transaction rows or existing volumes.
Keep verified data at `/srv/proptech-data/DB`, special-transaction exclusions,
unknown/limited GIS/ML semantics, Stage1–4 auth/ownership, market_ops disabled and
paid providers disabled. The CWA1897–1989 gap stays accepted and unfilled. No
public-readiness or cloud-retirement claim follows from local health checks.
