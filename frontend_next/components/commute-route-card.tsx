"use client";

import { useEffect, useRef, useState } from "react";
import { api, type CommuteRouteEvidence, type CommuteRouteMode, type CommuteRouteReasonCode, type CommuteRouteResult } from "@/lib/api";
import type { LocationMarketDisplayStatus } from "@/lib/location-market-journey";
import { Button, Notice } from "@/components/ui";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { commuteRouteCopy, type CommuteRouteCopyKey } from "@/lib/commute-route-copy";
import { formatLocationDistance, formatLocationDuration } from "@/lib/workspace/location-view-copy";

const MODE_KEYS: Record<CommuteRouteMode, CommuteRouteCopyKey> = { transit: "modeTransit", driving: "modeDriving", walking: "modeWalking" };
type SafeReason = Exclude<CommuteRouteReasonCode, "success">;
/** What the card says; held as a key so a locale switch re-renders it without re-querying. */
type RouteMessage = SafeReason | "looking" | "";

type Props = {
  originLatitude: number;
  originLongitude: number;
  initialEvidence?: CommuteRouteEvidence;
  onStatusChange?: (status: LocationMarketDisplayStatus) => void;
  onEvidence?: (evidence: CommuteRouteEvidence | null) => void;
};

function matchesOrigin(evidence: CommuteRouteEvidence | undefined, latitude: number, longitude: number): evidence is CommuteRouteEvidence {
  return Boolean(evidence && evidence.origin.latitude === latitude && evidence.origin.longitude === longitude);
}

function resultFromEvidence(evidence: CommuteRouteEvidence): CommuteRouteResult {
  return { ...evidence, message: "Saved route evidence.", disclaimer: "Route time and distance are reference evidence only." };
}

function evidenceFrom(result: CommuteRouteResult, originLatitude: number, originLongitude: number, destination: string): CommuteRouteEvidence {
  return {
    source: result.source,
    origin: { latitude: originLatitude, longitude: originLongitude },
    destination: { address: destination },
    mode: result.mode,
    distance_m: result.distance_m,
    duration_seconds: result.duration_seconds,
    duration_min: result.duration_min,
    partial: result.partial,
    checked_at: result.checked_at,
    reason_code: result.reason_code,
    status: result.status,
    fallback: result.fallback,
  };
}

function failedEvidence(reasonCode: CommuteRouteReasonCode, originLatitude: number, originLongitude: number, destination: string, mode: CommuteRouteMode): CommuteRouteEvidence {
  return {
    source: "none",
    origin: { latitude: originLatitude, longitude: originLongitude },
    destination: { address: destination },
    mode,
    distance_m: null,
    duration_seconds: null,
    duration_min: null,
    checked_at: new Date().toISOString(),
    reason_code: reasonCode,
    status: "unavailable",
    partial: false,
    fallback: false,
  };
}

function displayStatus(result: Pick<CommuteRouteResult, "status" | "reason_code">): LocationMarketDisplayStatus {
  if (result.status === "resolved") return "available";
  if (result.reason_code === "destination_required") return "not_started";
  if (result.status === "unresolved") return "no_data";
  return "unavailable";
}

export function CommuteRouteCard({ originLatitude, originLongitude, initialEvidence, onStatusChange, onEvidence }: Props) {
  const restored = matchesOrigin(initialEvidence, originLatitude, originLongitude) ? initialEvidence : undefined;
  const [destination, setDestination] = useState(restored?.destination.address ?? "");
  const [mode, setMode] = useState<CommuteRouteMode>(restored?.mode ?? "transit");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CommuteRouteResult | null>(restored ? resultFromEvidence(restored) : null);
  const [reasonCode, setReasonCode] = useState<CommuteRouteReasonCode>(restored?.reason_code ?? "destination_required");
  const [routeDisplayStatus, setRouteDisplayStatus] = useState<LocationMarketDisplayStatus>(restored ? displayStatus(restored) : "not_started");
  const { copyFrom, locale } = useExperienceLocale();
  const copy = (key: CommuteRouteCopyKey) => copyFrom(commuteRouteCopy, key);
  const sourceLabel = (source: CommuteRouteResult["source"]) => source === "google_routes" ? "Google Routes" : copy(source === "mock" ? "sourceMock" : "sourceNone");
  const [message, setMessage] = useState<RouteMessage>("");
  const requestId = useRef(0);
  const activeRequest = useRef<number | null>(null);
  const onStatusRef = useRef(onStatusChange);
  const onEvidenceRef = useRef(onEvidence);
  const mountedOrigin = useRef(false);

  useEffect(() => { onStatusRef.current = onStatusChange; }, [onStatusChange]);
  useEffect(() => { onEvidenceRef.current = onEvidence; }, [onEvidence]);
  useEffect(() => () => {
    requestId.current += 1;
    activeRequest.current = null;
    onStatusRef.current = undefined;
    onEvidenceRef.current = undefined;
  }, []);

  function clearRoute(reason: SafeReason = "destination_required") {
    requestId.current += 1;
    activeRequest.current = null;
    setLoading(false);
    setResult(null);
    setReasonCode(reason);
    setRouteDisplayStatus("not_started");
    setMessage(reason === "destination_required" ? "" : reason);
    onEvidenceRef.current?.(null);
    onStatusRef.current?.("not_started");
  }

  useEffect(() => {
    if (!mountedOrigin.current) {
      mountedOrigin.current = true;
      return;
    }
    clearRoute();
  }, [originLatitude, originLongitude]);

  async function lookupRoute() {
    const trimmed = destination.trim();
    if (!trimmed) {
      clearRoute("destination_required");
      setMessage("destination_required");
      return;
    }
    if (activeRequest.current !== null) return;
    const currentRequest = requestId.current + 1;
    requestId.current = currentRequest;
    activeRequest.current = currentRequest;
    const onRequestedEvidence = onEvidenceRef.current;
    setLoading(true);
    setResult(null);
    setReasonCode("destination_required");
    setRouteDisplayStatus("loading");
    setMessage("looking");
    onStatusRef.current?.("loading");
    try {
      const next = await api.commuteRoute({ origin_latitude: originLatitude, origin_longitude: originLongitude, destination_address: trimmed, mode });
      if (requestId.current !== currentRequest) return;
      setReasonCode(next.reason_code);
      const nextStatus = displayStatus(next);
      setRouteDisplayStatus(nextStatus);
      onStatusRef.current?.(nextStatus);
      if (next.status === "resolved") {
        setResult(next);
        setMessage("");
        onRequestedEvidence?.(evidenceFrom(next, originLatitude, originLongitude, trimmed));
      } else {
        setResult(null);
        const safeReason: SafeReason = next.reason_code === "success" ? "provider_error" : next.reason_code;
        setMessage(safeReason);
        onRequestedEvidence?.(evidenceFrom(next, originLatitude, originLongitude, trimmed));
      }
    } catch {
      if (requestId.current !== currentRequest) return;
      setResult(null);
      setReasonCode("provider_error");
      setRouteDisplayStatus("unavailable");
      setMessage("provider_error");
      onRequestedEvidence?.(failedEvidence("provider_error", originLatitude, originLongitude, trimmed, mode));
      onStatusRef.current?.("unavailable");
    } finally {
      if (requestId.current === currentRequest) { activeRequest.current = null; setLoading(false); }
    }
  }

  return (
    <div className="rounded-xl border border-cyan-100 bg-cyan-50/50 p-3" data-testid="commute-route-card">
      <span className="sr-only" data-testid="commute-route-state" data-status={routeDisplayStatus} data-reason-code={reasonCode} />
      <p className="text-xs font-bold text-slate-900">{copy("title")}</p>
      <p className="mt-1 text-[11px] leading-5 text-slate-600">{copy("intro")}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <input aria-label={copy("destination")} value={destination} onChange={(event) => { setDestination(event.target.value); clearRoute(); }} placeholder={copy("destinationPlaceholder")} className="min-w-0 flex-1 basis-48 rounded-lg bg-stone-50 px-3 py-3 text-sm outline-none focus:ring-2 focus:ring-cyan-200" />
        <select aria-label={copy("mode")} value={mode} onChange={(event) => { setMode(event.target.value as CommuteRouteMode); clearRoute(); }} className="min-w-0 w-full rounded-lg bg-stone-50 px-3 py-3 text-sm outline-none focus:ring-2 focus:ring-cyan-200 sm:w-auto">
          {(Object.keys(MODE_KEYS) as CommuteRouteMode[]).map((key) => <option key={key} value={key}>{copy(MODE_KEYS[key])}</option>)}
        </select>
        <Button secondary className="w-full max-w-full whitespace-normal sm:w-auto" disabled={loading} onClick={lookupRoute}>{loading ? copy("estimating") : copy("estimate")}</Button>
      </div>
      {message && <p className="mt-3 text-xs leading-5 text-slate-600">{copy(message)}</p>}
      {result?.status === "resolved" && (
        <div className="mt-3 grid gap-2 rounded-lg border border-cyan-100 bg-white p-3 text-xs text-slate-700 sm:grid-cols-3">
          {result.fallback && <div className="sm:col-span-3"><div data-testid="commute-route-mock-banner" className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-[11px] font-bold leading-5 text-amber-900">{copy("mockBanner")}</div></div>}
          <SafeField label={copy("mode")} value={copy(MODE_KEYS[result.mode])} />
          <SafeField label={copy("duration")} value={`${formatLocationDuration(result.duration_min, locale)}${result.fallback ? copy("simulatedSuffix") : ""}`} />
          <SafeField label={copy("distance")} value={formatLocationDistance(result.distance_m, locale)} />
          <div className="sm:col-span-3"><SafeField label={copy("source")} value={sourceLabel(result.source)} /></div>
          <div className="sm:col-span-3"><SafeField label={copy("checked")} value={result.checked_at} /></div>
          {result.fallback && <div className="sm:col-span-3"><Notice tone="warning">{copy("mockNote")}</Notice></div>}
          <div className="sm:col-span-3"><Notice>{copy("disclaimer")}</Notice></div>
        </div>
      )}
    </div>
  );
}

function SafeField({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg bg-stone-50 p-2"><p className="text-[10px] font-bold text-slate-500">{label}</p><p className="mt-1 break-words text-sm font-bold text-slate-900">{value}</p></div>;
}
