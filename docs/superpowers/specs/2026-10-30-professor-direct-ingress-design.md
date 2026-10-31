# Direct Professor ingress preparation

The operator authorized autonomous preparation and deferred every host, router,
DNS, firewall and production change to a reviewed gate. This design implements
that preparation; it does not authorize activation or manufacture missing facts.

Observed before edits: LAN192.168.200.215/24, gateway192.168.200.1; two independent
HTTPS observations report140.119.55.43. Trace hops after the private gateway are
public. WAN assignment/NAT ownership remains unknown. IPv6 is link-local only,
with no default route. Outbound public-IP observation is not inbound confirmation.
Host nginx1.28.3 already serves its default site on80;443 is free. Caddy/Certbot
are absent. UFW is enabled in configuration, but effective rules require a
privileged read-only inspection. No owned backend hostname was found.

Choose the installed nginx package over adding Caddy: keep its existing service
and default80 site, add a named HTTP-01/redirect site there, and prepare a separate
TLS-only nginx service on443. Certificate expiry must not stop the HTTP-01 site
needed for recovery. Proxy every public application request only to
127.0.0.1:8080. Caddy adds another daemon/port80 conflict; its default local IP
certificates are not a public trust solution. Domain and public-IPv4 certificate
plans are both representable, but neither is selected without ownership and
network evidence. Public-IP webroot issuance requires verified Certbot>=5.4 and
the shortlived profile. Staging certificates never count as trusted production.

The inner Docker nginx keeps its private binding. ML currently listens separately
on loopback8081 in an interactive-session scope. Prepare socket activation for
that same companion and a read-only Unix-socket mount into the inner proxy; route
only its documented ML endpoints there. The public TLS edge never proxies8081
directly and no model/data/training/feature contract changes are made. Existing
manual loopback startup remains compatible. Installation/restart is not performed.

Public edge configuration validates exact Host/SNI, fixes the upstream canonical
Host, overwrites forwarding headers, disables credential-bearing request logs,
blocks management endpoints and bounds bodies/concurrency/time. The current
inner proxy strips forwarding headers and FastAPI trusts none; preserve that
boundary. Origin admission and bearer ownership remain independent of headers.
Real client-IP propagation would require a separate explicit trusted-chain review.

Prepare pure configuration/network/credential validators, deterministic nginx and
systemd rendering, metadata-only audits and focused tests. The root operator
inspection tool must never open credential values, dump environment values,
change firewall/listeners or invoke installation. It is explicitly an audit,
not a disguised apply script. No public apply command is released while WAN,
ownership, effective firewall, ACME tooling, trusted TLS and reboot material
recovery remain unproved. Rendered plans show exact blocked gates.

Reboot preparation must address volatile /run secrets AND PostgreSQL TLS, not
just Docker restart policies. Stage2/4A staging does not restore trusted DB TLS.
Do not install a boot unit with an invented TLS source. Prepare ordering and
refuse readiness until the root-owned recovery source/identity and deployment
snapshot are verified. The ML service must not depend on a terminal or Codex.

Build a complete repository credential-name matrix from accepted Stage2 inventory,
source/CI/Compose/docs and Stage4A runtime evidence. Keep six active API files
separate from optional provider files and DB-only credentials. Three remote
control planes are not accessible through available connectors/CLIs; label those
inventories UNKNOWN and supply a strict names-only import format. No credential
is READY_TO_RETIRE until outside-LAN HTTPS, Preview/Production E2E, required-provider
admission, reboot and rollback gates pass. Supabase Auth remains the identity
provider; Cloud Run/Render are never used as the new ingress or backend.

All changes live in a new managed worktree based on accepted Stage4A cf3a227.
Preserve the main/frontend and historical-data worktrees, next-env.d.ts, X9,
all data/volumes and /dev/sda. No push, reboot, deployment, provider activation,
certificate order or host mutation is included in this task.
