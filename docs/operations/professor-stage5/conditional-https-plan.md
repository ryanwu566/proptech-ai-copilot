# Conditional direct HTTPS plan — never applied by this tool

The plan is prepared; network feasibility, identity, CA tooling and activation
remain pending. See [router checklist](router-cgnat-checklist.md) and generated
`reports/professor-stage5-ingress/conditional-https-plan.json`.

If the network owner confirms a controllable direct public IPv4 and later approves
the change, the intended path is:

```text
Internet TCP443
 -> approved router forwarding
 -> 192.168.200.215:443
 -> Professor NGINX TLS-only edge
 -> 127.0.0.1:8080
 -> FastAPI / private ML Unix socket
 -> private PostgreSQL and local GIS
```

Proposed forward TCP443->192.168.200.215:443. Include TCP80->192.168.200.215:80
**only for the selected HTTP-01 validation/renewal and canonical HTTPS redirect**.
Port80 must remain available for every renewal if HTTP-01 is selected. No other
ports are forwarded for this project. The current plan uses existing nginx80
for a separately named ACME site and a TLS-only service for443; no replacement
of the existing default site. The production identity is still unselected.

Before any future apply: network-owner/router and firewall approvals, stable
LAN reservation, actual Compose delta validation, trusted domain or controlled
IP certificate capability, ACME staging/renewal tests, persistent TLS/credential
boot recovery, root backups and exact rollback receipt. A public-IP observation,
WAN match or checked JSON flag is insufficient. Public acceptance must come
from outside the Professor LAN, followed by Vercel Preview then Production E2E.

If CGNAT is confirmed, label ingressCGNAT_BLOCKED and stop public preparation at
the reviewed plan. Compatible next options are ISP public IPv4, ISP static IPv4,
or separately approved routable IPv6 with an explicit firewall review. No
Cloudflare Tunnel/Access, ngrok, Funnel, external VPS, Cloud Run or Render ingress.

Always preserve: PostgreSQL private-only;8080/8081 loopback-only; Docker API
private; ML behind the private socket for public requests; Supabase identity and
Professor application-data ownership; market_ops and paid providers disabled.
No runtime/service/volume change or public cloud cutover accompanies this plan.

Neither this document nor `--router-plan` is an executable public apply.
