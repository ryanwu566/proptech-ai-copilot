# Satellite Reference Evidence V1

This feature provides bounded visual context for an already accepted terrain coordinate. It is reference evidence only and does not establish parcel identity, parcel geometry, ownership, zoning, statutory land use, building identity or permits, disaster certification, environmental compliance, or development entitlement.

## Server configuration

- `EARTH_ENGINE_SATELLITE_REFERENCE_V1` defaults to `false` and must be explicitly set to `true`.
- `EARTH_ENGINE_PROJECT` names the Google Cloud project registered for Earth Engine use.
- Authentication uses Application Default Credentials on the backend only. The application does not perform interactive OAuth and does not accept credential JSON through its API.
- Production remains unavailable unless the flag is enabled, the project is present, and ADC initialization succeeds.

Google recommends ADC for unattended Google Cloud environments. The configured project must have the Earth Engine API enabled, Earth Engine registration, and the necessary project permissions.

## Fixed query contract

- Dataset: `COPERNICUS/S2_SR_HARMONIZED`.
- Window: one trailing 90-day interval; an empty interval is not widened.
- AOI: a 500 m buffer around the accepted point, bounded to approximately 1 km of context; it is not a parcel boundary.
- Scene filter: `CLOUDY_PIXEL_PERCENTAGE <= 35`.
- Pixel mask: Sentinel-2 SCL classes 3 (cloud shadow), 8 (medium-probability cloud), 9 (high-probability cloud), 10 (cirrus), and 11 (snow/ice) are excluded.
- Composite: median B4/B3/B2 satellite reference composite. It may combine observations throughout the window and is neither current nor real-time imagery.
- Rendering: JPEG, at most 512 by 512 pixels and 250,000 provider bytes.
- Operation boundary: eight seconds across queueing and execution, measured from before submission to a dedicated two-thread provider executor. At most two provider workers run and two requests queue; excess requests fail closed before executor submission. The isolated worker is terminated before a timeout response returns. There is no retry, export, batch task, Drive/Cloud Storage delivery, or background job.

The endpoint accepts only finite latitude and longitude values. Dataset, bands, dates, geometry, scale, reducers, visualization parameters, and Earth Engine expressions are not caller-controlled.

## Image delivery and retention

Earth Engine's temporary thumbnail URL is allowlisted to the official HTTPS host, used once by the backend, and never returned or logged. The backend streams at most 250,000 JPEG bytes, converts them to a bounded data reference, and returns that reference in the allowlisted response. The frontend holds it only in component memory and does not attach it to durable Evidence or saved cases.

Cloud filtering and masking may leave residual cloud, haze, or incomplete coverage. Every state displays: “Satellite reference imagery — not cadastral or statutory evidence.”
