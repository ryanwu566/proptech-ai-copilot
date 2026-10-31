# Taiwan imagery runtime preparation

This branch prepares code only. It does not rebuild, deploy, enable a provider,
alter the accepted Stage 2 secret profile, or touch public ingress/hardening.
No credentials are installed. The main checkout, its unrelated next-env change,
accepted Stage 1–4 data and separate hardening worktree remain outside scope.

The service defaults to `SATELLITE_REFERENCE_PROVIDER=nlsc_photo2`. Existing
satellite admission/quotas still apply. Professor Server's accepted
`ANTI_ABUSE_SATELLITE_DISABLED=true` remains unchanged. Selecting a provider is
different from enabling it. A future controlled activation must review the
exact image/profile and admission guard; do not bypass the Stage 2 validators.
Earth Engine is retained and default-disabled. Only explicit `earth_engine`
selection resolves its manager; its existing enabled/project/ADC requirements,
bounded worker processes and short legacy cache remain confined to that mode.
Taiwan modes neither initialize EE nor access ADC.

PHOTO2 uses official HTTPS WMS GetMap at `https://wms.nlsc.gov.tw/wms`, layer
PHOTO2, WMS 1.3.0, EPSG:3857, a geodesic 500 m context bounding box and 512×512
JPEG. It needs no key. The advertised service extent is an upper bound, not a
coverage assertion. Blank/invalid imagery is unavailable. Different places may
have different capture years; no source capture date is available in this
contract. Retrieval time is never substituted for vintage. Retain NLSC
attribution and any upstream marks in the image.

CSRSR is an explicitly admitted noncommercial/competition alternative:
`SATELLITE_REFERENCE_PROVIDER=csrsr_spot`, `CSRSR_SPOT_YEAR=2025`, and
`CSRSR_SPOT_NONCOMMERCIAL_USE=true`. These are operator configuration, never
caller parameters. Supported years are 1996–2025; there is no `latest` alias or
automatic year rollover. Each on-demand request reads bounded official
capabilities from `https://data.csrsr.ncu.edu.tw/SP/wmts` and verifies the exact
annual layer, EPSG:3857 matrix, image format, fixed HTTPS tile template and
advertised limits. Tile paths use column before row. Older annual resolution
limits are respected. The service selects an appropriate supported zoom and
refuses more than nine tiles; tiles are fetched sequentially (below the maximum
two concurrent calls). Annual vintage is not a single acquisition date. CSRSR,
source/year attribution and noncommercial restriction must remain visible.

Official source references from the audit:

- [NLSC map service](https://maps.nlsc.gov.tw/S09SOA/homePage.action?Language=ZH)
- [NLSC service layer list](https://maps.nlsc.gov.tw/S09SOA/pro/Wmts_ajax_list.jsp)
- [CSRSR WMTS service guide](https://opendata.csrsr.ncu.edu.tw/2_WMTS.aspx)
- [CSRSR WMTS manual](https://opendata.csrsr.ncu.edu.tw/WMTSguide4.pdf)

Live on-demand service integration is the scope authorized here. There is no
bulk downloader, offline mirror, prefetch or completed Taiwan imagery cache.
Only concurrent identical in-flight requests are shared; sequential requests
fetch again. Images are neither written to disk nor sent to Saved Cases. This
implementation does not grant rights to redistribute imagery or imply a
commercial CSRSR license. Recheck official terms before broader/commercial use;
the noncommercial gate must stay closed unless that use is accepted.

Transport uses HTTPX with normal CA verification, exact host/path allowlists,
HTTPS only, no redirects or environment proxies, a cancellable absolute total
deadline and bounded bytes/MIME/encoding. XML is parsed with defusedxml. Pillow
checks complete image decode, format, exact pixel bounds, alpha and blank-data
heuristics, then produces a JPEG no larger than 250,000 bytes. The response is
bounded to 365,000 bytes. The service has one physical work slot, held until
the worker actually finishes even after client timeout. Blank/transparent or
near-uniform images are unavailable; legitimate uniform scenes can therefore
be false negatives. Textured source error placeholders are not a proof of
useful imagery: local visual acceptance is still required. No NoData result
means safe or verified absence of risk.

Pillow 13.x is the only new dependency, matching the installed 13.0.0 focused-test
baseline and [official 13.0 security fixes](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html),
including JPEG decoder fixes. HTTPX, pyproj and defusedxml already exist.
There is no GDAL/rasterio, GPU, new database schema or background imagery job.
A 512×512 output and at most nine 256px tiles fit the N4505/14 GiB server; no
performance SLA is asserted until an actual-image smoke passes.

Exact providers are retained in API metadata and process-local observations
and usage aggregates. Existing immutable usage DB migration 021 has older
provider labels, so SQL serialization alone maps `nlsc_photo2 → nlsc` and
`csrsr_spot → unknown`. Durable summaries explicitly expose this mapping. The
CSRSR bucket can include other unknown providers and cannot give a CSRSR-only
durable breakdown. It never counts Taiwan calls as EE. Physical calls include
capabilities and each tile; logical requests and admitted operations remain
separate. Pricing for these providers stays unknown, never fabricated as zero.

## TLS and candidate-image smoke

Source `Dockerfile.cloudrun` uses Python 3.12; the self-host Dockerfile extends
its digest-pinned image. Accepted Stage 4A evidence also records Python 3.12.
The current Docker socket is inaccessible to this agent, so the active image's
Python/TLS behavior has not been re-proven. Earlier read-only audit observed
Python 3.14 rejecting NLSC's certificate for Missing Subject Key Identifier,
while ordinary curl CA validation succeeded. This implementation does not
relax verification flags, downgrade HTTPS, disable TLS verification or switch
transport to evade a certificate rejection. Such failures return
`tls_verification_failed` and no image. Actual candidate-image validation is a
required external gate before any activation.

[Python's SSL documentation](https://docs.python.org/3.13/library/ssl.html#ssl.create_default_context)
records stricter default certificate flags starting in 3.13. That explains a
plausible version-dependent difference, not proof that a particular candidate
image will succeed. Normal CA validation is retained on every version.

`scripts/ops/taiwan_imagery_preflight.py` is offline by default and returns only
sanitized runtime metadata. In a separately reviewed candidate Python 3.12 API
image, the operator may run:

```sh
python -B scripts/ops/taiwan_imagery_preflight.py --provider nlsc_photo2 --allow-network
```

It performs one bounded known-location fetch and prints only status,
Python/OpenSSL versions, call/byte counts, imagery type and nullable vintage.
It does not print or save an image, read ADC, enable a runtime feature or
change the host. Never run it in a loop. For a separately accepted competition
SPOT smoke, add `--provider csrsr_spot --year 2025 --accept-noncommercial` instead.
No container/network changes or image build are authorized by these examples.

Before runtime activation: verify candidate-image normal TLS and image decode;
review Stage 2 profile/admission configuration without changing paid providers;
confirm only the intended API image changes; then separately admit one manual
API request and verify source/attribution/unknown date, UI semantics, NoData,
auth/quota and Stage 1–4 regression health. Do not alter hardening, DNS, public
ports or database volumes. Runtime rollback is restoring the accepted prior
API image/profile with satellite disabled; this branch makes no host changes
requiring rollback now. Preserve the existing accepted runtime/rollback evidence.
