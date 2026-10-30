# Public acceptance — external network required

All public items are PENDING. Local API regression PASS is not public acceptance.
Use an authorized client on a different network/mobile connection, outside the
Professor LAN/NAT. Record timestamp, public target and independent source address,
statuses and outcome booleans only. No keys, JWTs, cookies, profile contents or
case snapshots in reports. Do not create Supabase users without separate authority.

- [ ] Router WAN/control, fixed LAN reservation and upstream inbound policy proven.
- [ ] Exact approved A record or controlled public-IP identity; no stale AAAA.
- [ ]443 certificate chain trusted by browser and standard CA bundle, identity
  matches, TLS1.2/1.3 accepted, no self-signed/staging chain, expiry sufficient.
- [ ] HTTP80 serves only bounded ACME challenge paths or308 canonical HTTPS.
- [ ] Wrong Host/SNI, forged forwarding headers and management paths rejected.
- [ ]8080,8081,5432,2375,2376 unreachable publicly. No new project SSH/DMZ/UPnP.
- [ ] `/health` ok and `/readiness` ready over trusted HTTPS; no CA bypass flags.
- [ ] Exact approved Vercel Origin gets CORS, foreign Origin denied, no wildcard.
- [ ] ML POST preflight and responses include exact Origin; no credential cookies.
- [ ] Authorized existing Supabase JWT accepted for `/v1/session` and `/v1/account`.
- [ ] Missing, malformed, expired and revoked auth receives honest401; suspension403.
- [ ] Profile update/readback and preferences persist under the same verified UUID.
- [ ] Explicitly consented Saved Case create/list/reopen/update persists through
  refresh, backend logout -> SDK signout -> new login, and another authorized device.
- [ ] Already-authorized second user cannot read/update/delete foreign cases,
  profiles/reports; no owner override. Record statuses only, not resource contents.
- [ ] Market excludes known related-party row38652, preserved in storage; persisted
  coverage and direct eligible counts agree. Ambiguous matches remain unmutated.
- [ ] Valuation estimate/data-status, Trend and Finder uphold available/limited/
  unavailable semantics; no forced price or fabricated coverage.
- [ ] Known NLSC point25.035570879000026,121.4525876531026 ->新北市/新莊區/榮和里,
  code65000050016 ->RIS population6134 (or explicitly reviewed newer statistic).
- [ ] WRA local matched/no-match checks preserve scenario/version/SHA provenance;
  no-match distinct from safe/unavailable. Unsupported GIS remains explicit.
- [ ] ML pinned status/estimate traverses HTTPS ->8080 ->private socket, honest
  support/date/geography abstention, `is_actionable=false`, no probability fiction.
- [ ] Oversized body413, excessive request429, upstream timeout bounded. No paid
  provider calls, private token logging, account bypass or refresh/admin exposure.
- [ ] Certificate staging/production issuance, automatic renewal/deploy hook and
  expired-cert startup/recovery tested without disabling existing HTTP-01 service.
- [ ] Reboot test passes before operator login, then repeat external checks.

The plan validator requires a fresh independent vantage receipt bound to the
selected target and443 with trusted TLS and health. This is a planning attestation,
not a substitute for these full end-to-end checks or packet/DNS ownership proof.
Never mark an item PASS merely because an operator edited a JSON boolean.
