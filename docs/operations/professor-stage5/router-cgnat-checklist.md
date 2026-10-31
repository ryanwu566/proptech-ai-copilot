# Router WAN / CGNAT checklist — observation only

Do not change settings or request router credentials in an agent session. The
gateway may be campus-managed. The operator/network administrator should read
the existing WAN/status and DHCP reservation pages using their own authorized
session. No DMZ, UPnP, forwarding, firewall or administrative-access change.

Record these exact **non-secret** values in a names-only observation receipt:

| Field | Existing server evidence | Operator observation required |
|---|---|---|
| Router WAN IPv4 | UNKNOWN | Exact IPv4 shown for active WAN interface |
| Professor Server LAN IPv4 |192.168.200.215/24 on enp2s0 | Confirm current assignment |
| Default gateway |192.168.200.1 | Confirm this is the inspected gateway |
| Observed outbound public IPv4 |140.119.55.43 from two HTTPS observers | Compare with WAN, do not assume inbound |
| WAN equals observed public IPv4 |UNKNOWN | Equality of exact addresses |
| Router behind another router/modem |UNKNOWN | Yes/no; distinguish bridge from another routed/NAT boundary |
| DHCP reservation192.168.200.215 exists |UNKNOWN | Yes/no from existing reservation table; no new reservation yet |
| Authority to admit inbound TCP443 |UNKNOWN | Explicit network-owner approval/denial, not possession of a router password |

Do not supply passwords, Wi-Fi keys, management tokens, complete screenshots,
router exports, session cookies or unrelated account details. Use
`config/professor-router-observation.example.json`; null means unobserved,
false means an actual negative observation. No secret fields are accepted.

Decision rules:

- WAN equals140.119.55.43 and is globally routable: **candidate direct IPv4**;
  confirm ownership/control, upstream policy and reservation. This does not prove
  inbound reachability. A modem in bridge mode is different from upstream NAT.
- WAN100.64.0.0/10: **CGNAT_BLOCKED** for the proposed direct IPv4 route until
  ISP/network-owner supplies an approved public/static IPv4 or a separately
  reviewed self-host-compatible route. Never add a tunnel.
- WAN in10/8,172.16/12 or192.168/16: **UPSTREAM_PRIVATE_NAT**; inspect the
  next router/modem with its authorized administrator. Do not equate this alone
  with carrier-grade NAT. All upstream boundaries need permission/forwarding.
- A different global WAN: **WAN_EGRESS_MISMATCH**; check multi-WAN, campus egress
  and actual assignment. Do not forward or publish DNS based on the observed IP.
- Unavailable/ambiguous WAN: retainUNKNOWN andPENDING.

The decision logic and checklist are ready; the actual network decision remains
pending these observations. IPv6 currently has no global address/default route,
so it is not an admitted fallback. All paths require outside-LAN confirmation
after separately approved activation.

Local validation only, no router contact:

```bash
python3 -B scripts/ops/professor_stage5.py --router-plan config/professor-router-observation.example.json
```

An unfilled template produces a conditional plan with `ingress_apply_allowed=false`.
Never convert that output into an authorization to change the router.
