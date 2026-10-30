# Professor direct ingress implementation plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation, followed by one independent whole-branch security review.

**Goal:** Prepare direct self-hosted HTTPS and credential migration without changing live infrastructure.

**Architecture:** Keep host nginx as TLS edge, existing loopback8080 as the only public-edge upstream, and a private Unix socket for the ML companion behind the inner proxy. All missing real-world facts remain explicit gates.

**Tech Stack:** Python standard library, nginx, systemd, existing FastAPI and Stage2 secret architecture; Certbot selected only after capability verification.

**Spec:** `docs/superpowers/specs/2026-10-30-professor-direct-ingress-design.md` and the operator's Stage5 requirements.

## Global constraints

- No /dev/sda or X9 writes; no database mutation/volume recreation.
- No listeners, router, firewall, DNS, certificate order or cloud deployment changes.
- No secrets read/printed/committed; names/metadata only in audit artifacts.
- No paid providers or market_ops enabled;8080/8081 and PostgreSQL remain private.
- Only focused tests; no full repository suite or frontend changes; no push.

## Review focus

- An observed outbound IP must not imply inbound access or router ownership.
- Unknown NAT, IPv6, certificate tooling or cloud inventory must fail closed.
- Host/origin/config injection and credential-bearing metadata must be rejected.
- Public ML must traverse8080; socket activation must reject foreign descriptors.
- Docker restart policy alone must not imply safe reboot with volatile credentials/TLS.

### Task 1: Configuration and network gates

Files: `services/professor_ingress.py`, `tests/test_professor_ingress.py`.

- [x] Write tests for NAT classification, missing/external proof, identities/origins and certificate capability gates; observe RED.
- [x] Implement pure `classify_network`, `validate_plan`, `readiness`, nginx/renewal/systemd rendering and firewall/rollback manifest.
- [x] Verify strict fixed upstream, Host/SNI, logging, management-path denial and local ML socket; run focused tests and isolated nginx syntax validation.

### Task 2: Metadata-only audits and credential matrix

Files: `services/professor_credentials.py`, `scripts/ops/professor_stage5.py`, `tests/test_professor_stage5_audit.py`.

- [x] Test source-name extraction, classification, unknown cloud stores and rejection of value-bearing imports; observe RED.
- [x] Implement sanitized non-privileged network audit, root-only read-only host audit, names-only remote inventory import and deterministic plan output.
- [x] Preserve six runtime files; optional providers remain unmounted and unactivated. Verify static no-mutation checks and structured output.

### Task 3: Private ML lifecycle preparation

Files: `scripts/ops/serve_valuation_ml.py`, `tests/test_professor_ml_socket.py` and rendered unit/config templates.

- [x] Test inherited PID/count/names/listening socket validation and default loopback compatibility; observe RED.
- [x] Add bounded systemd socket activation without changing inference or current runtime; render dedicated unprivileged service/socket units.
- [x] Verify descriptor ownership/cleanup and conservative resource limits with focused tests; no live restart.

### Task 4: Evidence and operator handoff

Files: `reports/professor-stage5-ingress/*`, `docs/operations/professor-public-ingress.md`, `docs/operations/provider-credential-matrix.md`, and adjacent Stage5 dry-run/firewall/rollback/external/cutover/retirement checklists.

- [x] Record actual network/listener/tool observations and all remaining gates. Publish no fake domain or public acceptance.
- [x] Record reboot ordering including missing TLS recovery proof and ML session dependence.
- [x] Recheck accepted local API/ML behavior without provider activation; run relevant tests/AST/nginx/systemd checks.
- [x] Perform independent whole-branch security review; fix important findings with focused regressions.
- [x] Commit intentional local changes; leave all external/runtime actions pending behind explicit operator approval.

The design was not submitted for another ordinary engineering approval because
the operator explicitly authorized autonomous decisions/preparation. Host/network
and production approvals remain mandatory and ungranted.

Completion scope: preparation and focused private regression only. Public apply,
WAN/identity ownership, effective firewall, CA deployment, real external browser
acceptance, remote cloud inventories and reboot acceptance remain blocked/pending.
No live public configuration was changed. Focused pack:165passed; one existing
Starlette/httpx deprecation warning. Static validation:7source ASTs,1generated
Python AST,2bash hooks and7systemd fixture units. Independent review found five
important preparation issues; all were fixed and rereviewed without remaining
critical/important findings. See Stage5acceptance.json and review.json.
