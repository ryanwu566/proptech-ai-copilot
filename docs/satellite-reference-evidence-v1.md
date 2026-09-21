# Satellite Reference Evidence V1

This feature provides bounded visual context for an already accepted terrain coordinate. It is reference evidence only and does not establish parcel identity, parcel geometry, ownership, zoning, statutory land use, building identity or permits, disaster certification, environmental compliance, or development entitlement.

## Server configuration

- `EARTH_ENGINE_SATELLITE_REFERENCE_V1` defaults to `false` and must be explicitly set to `true`.
- `EARTH_ENGINE_PROJECT` names the Google Cloud project registered for Earth Engine use.
- Authentication uses Application Default Credentials on the backend only. The application does not perform interactive OAuth and does not accept credential JSON through its API.
- FastAPI starts the optional Earth Engine manager without awaiting readiness. An Earth Engine or ADC outage does not prevent unrelated routes from serving.
- While the manager is starting, disabled, or unavailable, only the satellite-reference route fails closed with an allowlisted unavailable reason.

Google recommends ADC for unattended Google Cloud environments. The configured project must have the Earth Engine API enabled, Earth Engine registration, and the necessary project permissions.

## Fixed query contract

- Dataset: `COPERNICUS/S2_SR_HARMONIZED`.
- Window: one fixed trailing 90-day interval; it is never widened.
- AOI: the exact 500 m circular buffer around the accepted point; it is not a parcel boundary.
- Scene filter: `CLOUDY_PIXEL_PERCENTAGE <= 35`.
- Pixel mask: Sentinel-2 SCL classes 3 (cloud shadow), 8 (medium-probability cloud), 9 (high-probability cloud), 10 (cirrus), and 11 (snow/ice) are excluded.
- Composite: median B4/B3/B2 satellite reference composite. It may combine observations throughout the window and is neither current nor real-time imagery.
- Rendering: JPEG, at most 512 by 512 pixels and 250,000 provider bytes.
- Operation boundary: eight seconds across admission queueing, worker acquisition, IPC, provider execution, JPEG validation, response construction, and return. At most two requests execute and two requests queue; a fifth request fails closed before executor submission.
- Worker lifecycle: exactly two persistent spawned workers initialize Earth Engine once per worker for the server-selected project. Each worker handles one request at a time. A timed-out, crashed, or protocol-invalid worker is terminated and joined before one bounded replacement attempt restores capacity. A failed replacement makes the capability unavailable and cleans up the remaining worker and every pipe; it never starts a restart loop.
- Retry boundary: application retries, Earth Engine SDK retries, and HTTP thumbnail retries are all zero. `ee.data.setMaxRetries(0)` is applied before Earth Engine initialization. There is no request replay, export, batch task, Drive/Cloud Storage delivery, persistence, or background imagery job.
- Provider operations: after worker initialization, a successful request performs thumbnail creation and one bounded JPEG download. It does not issue a separate `collection.size().getInfo()` call.

The endpoint accepts only finite latitude and longitude values. Dataset, bands, dates, geometry, scale, reducers, visualization parameters, and Earth Engine expressions are not caller-controlled.

## Image delivery and retention

Earth Engine's temporary thumbnail URL is allowlisted to the official HTTPS host, used once by the backend, and never returned or logged. The backend streams at most 250,000 JPEG bytes, converts them to a bounded data reference, and returns that reference in the allowlisted response. The frontend holds it only in component memory and does not attach it to durable Evidence or saved cases.

Cloud filtering and masking may leave residual cloud, haze, or incomplete coverage. Every state displays: “Satellite reference imagery — not cadastral or statutory evidence.”

## Preview availability semantics

`status="available"` means only that the bounded Earth Engine pipeline produced and validated a reference JPEG for that request. It does not state or imply a scene count, sufficient temporal coverage, cloud-free or coverage completeness, imagery quality or currency, parcel identity, ownership, zoning, or legal/cadastral truth.

The exact disclaimer is:

> Satellite reference imagery — not cadastral or statutory evidence.
