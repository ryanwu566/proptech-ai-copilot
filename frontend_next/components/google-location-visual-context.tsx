"use client";

import { useEffect, useState } from "react";

import type { LocationInsightResult } from "@/lib/api";
import { buildGoogleMapsEmbedUrls, hasValidGoogleMapsCoordinates } from "@/lib/google-maps-embed";

const DISCLAIMER = "Google visual context — not property identity, parcel geometry, cadastral boundary, ownership, or zoning evidence.";
const LOAD_TIMEOUT_MS = process.env.NEXT_PUBLIC_APP_ENV === "test" ? 500 : 12_000;

type PreviewLoadState = "loading" | "loaded" | "load_not_confirmed";

export function GoogleLocationVisualContext({ result }: { result?: LocationInsightResult }) {
  const location = result?.resolved_location;
  const acceptance = result?.geocoding_acceptance;
  const confirmationRequired = !location
    || acceptance?.accepted_for_analysis !== true
    || acceptance.requires_confirmation === true;
  const browserKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY;

  if (confirmationRequired) {
    return <Panel state="confirmation_required">
      <BoundedState message="Confirm the resolved location before loading Google visual context." />
    </Panel>;
  }

  if (!hasValidGoogleMapsCoordinates(location.latitude, location.longitude)) {
    return <Panel state="preview_unavailable">
      <BoundedState message="The accepted location does not contain valid preview coordinates." />
    </Panel>;
  }

  if (!browserKey?.trim()) {
    return <Panel state="unavailable">
      <BoundedState message="Google preview is not configured." />
    </Panel>;
  }

  const urls = buildGoogleMapsEmbedUrls({ browserKey, latitude: location.latitude, longitude: location.longitude });
  if (!urls) {
    return <Panel state="preview_unavailable">
      <BoundedState message="Google visual context is unavailable for this accepted location." />
    </Panel>;
  }

  return <Panel state="available">
    <div className="grid min-w-0 gap-4 lg:grid-cols-2">
      <GoogleEmbedPreview
        ariaLabel="Google map preview"
        frameTitle="Google map visual context"
        heading="Map preview"
        key={urls.mapUrl}
        note="Centered on the accepted coordinate. V1 does not add a Google marker."
        src={urls.mapUrl}
        unavailableMeaning="This does not mean the location is unavailable in Google Maps."
      />
      <GoogleEmbedPreview
        ariaLabel="Google Street View preview"
        frameTitle="Google Street View visual context"
        heading="Street View preview"
        key={urls.streetViewUrl}
        note="Shown when Google has panorama imagery; otherwise Google provides its own no-imagery UI."
        src={urls.streetViewUrl}
        unavailableMeaning="This does not mean Street View imagery is unavailable."
      />
    </div>
  </Panel>;
}

function Panel({ children, state }: { children: React.ReactNode; state: "available" | "confirmation_required" | "preview_unavailable" | "unavailable" }) {
  return <section data-testid="google-location-visual-context" data-google-visual-state={state} aria-labelledby="google-location-visual-heading" className="min-w-0 overflow-hidden rounded-xl border border-stone-200 bg-white p-4">
    <div className="flex flex-wrap items-start justify-between gap-2">
      <div>
        <h3 id="google-location-visual-heading" className="text-sm font-black text-slate-950">Google visual context</h3>
        <p className="mt-1 text-xs leading-5 text-slate-600">Location visualization only, based on the accepted Location Insight coordinate.</p>
      </div>
      <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[10px] font-bold text-slate-700">Google Maps</span>
    </div>
    <div className="mt-4">{children}</div>
    <p className="mt-4 border-t border-stone-100 pt-3 text-xs font-semibold leading-5 text-amber-800">{DISCLAIMER}</p>
  </section>;
}

function BoundedState({ message }: { message: string }) {
  return <div role="status" className="rounded-lg border border-dashed border-stone-300 bg-stone-50 px-4 py-5 text-sm text-slate-600">{message}</div>;
}

function GoogleEmbedPreview({
  ariaLabel,
  frameTitle,
  heading,
  note,
  src,
  unavailableMeaning,
}: {
  ariaLabel: string;
  frameTitle: string;
  heading: string;
  note: string;
  src: string;
  unavailableMeaning: string;
}) {
  const [loadState, setLoadState] = useState<PreviewLoadState>("loading");

  useEffect(() => {
    setLoadState("loading");
    const timeout = window.setTimeout(() => {
      setLoadState((current) => current === "loading" ? "load_not_confirmed" : current);
    }, LOAD_TIMEOUT_MS);
    return () => window.clearTimeout(timeout);
  }, [src]);

  function markLoaded() {
    setLoadState("loaded");
  }

  function markLoadNotConfirmed() {
    setLoadState((current) => current === "loading" ? "load_not_confirmed" : current);
  }

  return <section role="region" aria-label={ariaLabel} data-preview-state={loadState} className="min-w-0 overflow-hidden rounded-lg border border-stone-200 bg-stone-50">
    <div className="min-h-[88px] px-3 py-3">
      <h4 className="text-xs font-bold text-slate-900">{heading}</h4>
      <p className="mt-1 text-[11px] leading-5 text-slate-600">{note}</p>
      {loadState === "loading" && <p role="status" className="mt-1 text-[11px] font-semibold text-slate-500">Loading Google preview…</p>}
      {loadState === "load_not_confirmed" && <p role="status" className="mt-1 text-[11px] font-semibold leading-5 text-amber-800"><span className="block">Load not confirmed</span>{unavailableMeaning}</p>}
    </div>
    <iframe
      allowFullScreen
      className="block h-[260px] min-h-[200px] w-full border-0 bg-stone-100"
      loading="lazy"
      onError={markLoadNotConfirmed}
      onLoad={markLoaded}
      referrerPolicy="strict-origin-when-cross-origin"
      src={src}
      title={frameTitle}
    />
  </section>;
}
