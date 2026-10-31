# Firewall and router plan

Policy prepared; live effective-rule review and apply PENDING. UFW enabled
configuration is not proof of effective packet policy. Root metadata audit must
review nftables input/forward/Docker chains and preserve existing administration.
Docker publishing can bypass UFW; review bindings independently using
[Docker firewall guidance](https://docs.docker.com/engine/network/packet-filtering-firewalls/).

Only after WAN/control, LAN reservation and host-policy approval:

- TCP443 ->192.168.200.215:443, direct TLS edge.
- TCP80 ->192.168.200.215:80, necessary for selected HTTP-01 issuance, all renewals,
  and canonical redirects. If validation changes later, reassess instead of opening it by habit.
- Host allowances limited to the reviewed ingress interface enp2s0 and these ports.
- Keep DB on Docker internal networks without host publication; keep8080 and8081
  bound127.0.0.1 only. ML Unix socket is permission-limited and never public.
- Never forward5432,8080,8081,2375,2376,22 or existing administrative3322 merely for
  this project. No DMZ, UPnP, Docker API, broad forwarding or allow-all policies.
- No global IPv6/route is present; no AAAA, IPv6 TLS listener or new IPv6 public
  rule is admitted. Existing unrelated IPv6 services remain unchanged.

Before a firewall apply, save a root-only effective-rules snapshot, identify the
operator's current management path and source, preserve its exact admission rule,
and arrange local console access/time-bounded rollback. Never UFW reset/disable,
flush nftables/iptables, disable Docker firewall management, or replace the whole
ruleset. Review campus/upstream policy with its administrator; forwarding on an
uncontrolled shared address is not sufficient.

After apply, test from an external network:443 trusted/functional;80 only
challenge or redirect;8080/8081/5432/2375/2376 closed. Separately recheck host
bindings and management access. An absence of a host listener alone does not
prove absence of an upstream forward; both sides are acceptance requirements.

If router WAN is100.64/10 and inbound impossible, mark CGNAT_BLOCKED. Ask ISP for
public/static IPv4; routable IPv6 requires a new explicit address/firewall review.
Do not introduce an external tunnel, managed backend or VPS reverse proxy.
