# Reboot survival plan

Plan prepared; **live reboot acceptance PENDING**, no reboot performed. Docker
and host nginx are enabled. Existing Compose restart policies preserve most
containers, but cannot recover missing bind-mount files in volatile `/run`.
The present ML process is under a terminal/session scope, not a system boot unit.

Required ordering for a future controlled, reviewed installer:

1. Local filesystems mounted; `/srv/proptech-data/DB` and pinned ML artifact
   readable from the approved disk, never/dev/sda or X9.
2. Restore existing trusted PostgreSQL TLS from a verified root-owned persistent
   recovery source to `/run/proptech-selfhost/tls`. Preserve CA/server identity,
   ownership and least privilege. **Recovery source and restoration procedure are
   not yet proved.** Stage2/4 secret staging does not restore DB TLS. Do not
   regenerate CA/keys, use arbitrary backup files or infer safe boot from Docker.
3. Run accepted Stage2 secret staging and Stage4 user-runtime credential staging
   as boot services, after their protected persistent stores are ready. Never
   print values, rotate credentials, reprovision schema, or require an interactive
   login/sudo ticket. Credential consumers must wait for correctly staged files.
4. Prevent early Docker project consumers from racing volatile mounts. A reviewed
   project startup dependency must wait for steps2–3 before existing-container
   startup or scoped `up`; review Docker daemon ordering globally before adding
   any override. Do not disrupt unrelated containers or recreate DB volumes.
5. Enable the prepared ML socket/service. Preserve127.0.0.1:8081 and add only
   `/run/proptech-ml/inference.sock`; dedicated process uses inherited descriptors,
   same model hash and one CPU maximum. The current session process must be
   handed over explicitly by verified PID/source, not restarted during prep.
6. Inner proxy mounts the socket directory read-only; API/proxy starts against
   exact reviewed Compose model. Only API and reverse_proxy need controlled
   recreation; DBs retain original volumes and configuration.
7. Host nginx80 remains independent. Start trusted TLS edge only after local
   health, DB TLS and exact cert identity/expiry validation. Enable renewal and
   sanitized health timers. No tmux, Codex, terminal or manual sudo dependency.

Prepared ML unit source install `/opt/proptech-selfhost/ml` must be root-owned and
read-only to runtime. Venv/runtime and pinned artifacts remain the existing
verified paths. The future environment file must be root-owned0600, non-secret, containing exact
model root/hash, safe Host/CORS and private-profile guard settings. Before release,
verify all model/interpreter dependency paths and Unix socket group against the
actual inner nginx UID/GID; template uses accepted container group101. Do not
install against a changed image/group. Reference model manifest SHA256:
`54eba6a04069b0f8d569c2fe62bbe1ca70771b5594cb220e908e9f7e3524fac4`.

systemd passes listening sockets through validated file descriptors, avoiding
wildcard rebinding. References: [systemd.socket](https://www.freedesktop.org/software/systemd/man/latest/systemd.socket.html),
[sd_listen_fds](https://www.freedesktop.org/software/systemd/man/latest/sd_listen_fds.html).

Reboot only with separate operator approval, console recovery and verified
protected backups. After reboot and **before operator login**, check enabled/
active project services/timers, trusted local TLS, `/health`, `/readiness`,
NLSC/RIS, WRA, Market exclusions/coverage, Valuation, Trend, Finder and pinned ML
status/estimate. Check secret/TLS metadata only, auth/session/profile/case flows,
same DB volume IDs, private5432, loopback8080/8081, no X9 bind, disabled paid
providers/market_ops. Repeat full public acceptance from outside the LAN.
Record boot ID and outcomes, not credentials. Only then pass the reboot gate.
