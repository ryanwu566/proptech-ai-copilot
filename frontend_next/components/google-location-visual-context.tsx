"use client";

import { useEffect, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";

import type { LocationInsightResult } from "@/lib/api";
import { buildGoogleMapsEmbedUrls, hasValidGoogleMapsCoordinates } from "@/lib/google-maps-embed";

const LOAD_TIMEOUT_MS = process.env.NEXT_PUBLIC_APP_ENV === "test" ? 500 : 12_000;

type PreviewLoadState = "loading" | "loaded" | "load_not_confirmed";

export function GoogleLocationVisualContext({ result }: { result?: LocationInsightResult }) {
  const { t } = useExperienceLocale();
  const [view, setView] = useState<"map" | "street">("map");
  const location = result?.resolved_location;
  const acceptance = result?.geocoding_acceptance;
  const confirmationRequired = !location
    || acceptance?.accepted_for_analysis !== true
    || acceptance.requires_confirmation === true;
  const browserKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY;

  if (confirmationRequired) {
    return <Panel state="confirmation_required">
      <BoundedState message={t("commercial.googleConfirm")} />
    </Panel>;
  }

  if (!hasValidGoogleMapsCoordinates(location.latitude, location.longitude)) {
    return <Panel state="preview_unavailable">
      <BoundedState message={t("commercial.googleInvalid")} />
    </Panel>;
  }

  if (!browserKey?.trim()) {
    return <Panel state="unavailable">
      <BoundedState message={t("commercial.googleUnconfigured")} />
    </Panel>;
  }

  const urls = buildGoogleMapsEmbedUrls({ browserKey, latitude: location.latitude, longitude: location.longitude });
  if (!urls) {
    return <Panel state="preview_unavailable">
      <BoundedState message={t("commercial.googleUnavailable")} />
    </Panel>;
  }

  return <Panel state="available">
    <div className="flex flex-wrap gap-2 mb-3" role="group" aria-label={t("commercial.googleTitle")}>
      <button type="button" className={`ds-button ds-button--${view === "map" ? "primary" : "secondary"}`} aria-pressed={view === "map"} onClick={() => setView("map")}>{t("commercial.mapTab")}</button>
      <button type="button" className={`ds-button ds-button--${view === "street" ? "primary" : "secondary"}`} aria-pressed={view === "street"} onClick={() => setView("street")}>{t("commercial.streetTab")}</button>
    </div>
    {view === "map" ? <GoogleEmbedPreview ariaLabel={t("commercial.mapPreview")} frameTitle={t("commercial.mapFrame")} heading={t("commercial.mapTab")} key={urls.mapUrl} note={t("commercial.mapNote")} src={urls.mapUrl} unavailableMeaning={t("commercial.mapMeaning")} />
      : <GoogleEmbedPreview ariaLabel={t("commercial.streetPreview")} frameTitle={t("commercial.streetFrame")} heading={t("commercial.streetTab")} key={urls.streetViewUrl} note={t("commercial.streetNote")} src={urls.streetViewUrl} unavailableMeaning={t("commercial.streetMeaning")} />}
  </Panel>;
}

function Panel({ children, state }: { children: React.ReactNode; state: "available" | "confirmation_required" | "preview_unavailable" | "unavailable" }) {
  const { t } = useExperienceLocale();
  return <section data-testid="google-location-visual-context" data-google-visual-state={state} aria-labelledby="google-location-visual-heading" className="min-w-0 overflow-hidden rounded-xl border border-stone-200 bg-white p-4">
    <div className="flex flex-wrap items-start justify-between gap-2">
      <div>
        <h3 id="google-location-visual-heading" className="text-sm font-black text-slate-950">{t("commercial.googleTitle")}</h3>
        <p className="mt-1 text-xs leading-5 text-slate-600">{t("commercial.googleDescription")}</p>
      </div>
      <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[10px] font-bold text-slate-700">Google Maps</span>
    </div>
    <div className="mt-4">{children}</div>
    <p className="mt-4 border-t border-stone-100 pt-3 text-xs font-semibold leading-5 text-amber-800">{t("commercial.googleDisclaimer")}</p>
  </section>;
}

function BoundedState({ message }: { message: string }) {
  return <div role="status" className="rounded-lg border-y border-stone-300 bg-stone-50 px-4 py-5 text-sm text-slate-600">{message}</div>;
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
  const { t } = useExperienceLocale();
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
      {loadState === "loading" && <p role="status" className="mt-1 text-[11px] font-semibold text-slate-500">{t("commercial.googleLoading")}</p>}
      {loadState === "load_not_confirmed" && <p role="status" className="mt-1 text-[11px] font-semibold leading-5 text-amber-800"><span className="block">{t("commercial.googleUnconfirmed")}</span>{unavailableMeaning}</p>}
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
