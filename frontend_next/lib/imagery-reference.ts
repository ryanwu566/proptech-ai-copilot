import type { SatelliteReference } from './api';

export function imageryMetadata(value: Partial<SatelliteReference>) {
  const earthEngine = value.provider === 'earth_engine' ||
    ((!value.provider || value.provider === 'unknown') && value.dataset === 'COPERNICUS/S2_SR_HARMONIZED');
  const aerial = value.provider === 'nlsc_photo2' || value.source_type === 'orthophoto';
  const annual = value.provider === 'csrsr_spot';
  return {
    titleKey: aerial ? 'commercial.orthophotoTitle' : annual || earthEngine || value.source_type === 'satellite' ? 'commercial.actualSatelliteTitle' : 'commercial.satelliteTitle',
    annual,
    vintage: value.vintage ?? null,
    captureDate: !annual && value.provider !== 'nlsc_photo2' && value.date_precision === 'day' ? value.observation_date ?? null : null,
    showCloud: earthEngine && typeof value.cloud_filter_percent === 'number' && Number.isFinite(value.cloud_filter_percent),
  } as const;
}

export function embeddedJpeg(value: string | null | undefined): string | null {
  return value && /^data:image\/jpeg;base64,\/9j\/[A-Za-z0-9+/]*={0,2}$/.test(value) ? value : null;
}
