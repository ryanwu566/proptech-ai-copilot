"use client";

import { useEffect, useRef, useState } from "react";
import { api, type CommuteRouteEvidence, type CommuteRouteMode, type CommuteRouteReasonCode, type CommuteRouteResult } from "@/lib/api";
import type { LocationMarketDisplayStatus } from "@/lib/location-market-journey";
import { Button, Notice } from "@/components/ui";
import { formatDistance, formatDuration, formatMissing } from "@/lib/commercial/formatters";

const MODE_LABELS: Record<CommuteRouteMode, string> = { transit: "大眾運輸", driving: "開車", walking: "步行" };
const SOURCE_LABELS: Record<CommuteRouteResult["source"], string> = {
  google_routes: "Google Routes",
  mock: "測試／展示模擬路線（非 Google 實際結果）",
  none: "無",
};
const SAFE_MESSAGES: Record<Exclude<CommuteRouteReasonCode, "success">, string> = {
  destination_required: "請輸入通勤目的地。",
  invalid_input: "輸入資料無效，請檢查後重試。",
  provider_timeout: "路線服務逾時，請稍後重試。",
  configuration_error: "路線服務尚未完成設定。",
  provider_error: "路線服務目前無法使用，請稍後重試。",
  malformed_response: "路線服務回傳了無法讀取的資料。",
  route_not_found: "找不到符合條件的路線，請調整目的地或交通方式。",
};

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
  const [message, setMessage] = useState("");
  const requestId = useRef(0);
  const onStatusRef = useRef(onStatusChange);
  const onEvidenceRef = useRef(onEvidence);
  const mountedOrigin = useRef(false);

  useEffect(() => { onStatusRef.current = onStatusChange; }, [onStatusChange]);
  useEffect(() => { onEvidenceRef.current = onEvidence; }, [onEvidence]);
  useEffect(() => () => {
    requestId.current += 1;
    onStatusRef.current = undefined;
    onEvidenceRef.current = undefined;
  }, []);

  function clearRoute(reason: Exclude<CommuteRouteReasonCode, "success"> = "destination_required") {
    requestId.current += 1;
    setLoading(false);
    setResult(null);
    setReasonCode(reason);
    setRouteDisplayStatus("not_started");
    setMessage(reason === "destination_required" ? "" : SAFE_MESSAGES[reason]);
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
      setMessage(SAFE_MESSAGES.destination_required);
      return;
    }
    if (loading) return;
    const currentRequest = requestId.current + 1;
    requestId.current = currentRequest;
    setLoading(true);
    setResult(null);
    setReasonCode("destination_required");
    setRouteDisplayStatus("loading");
    setMessage("正在查詢路線…");
    onEvidenceRef.current?.(null);
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
        onEvidenceRef.current?.(evidenceFrom(next, originLatitude, originLongitude, trimmed));
      } else {
        setResult(null);
        const safeReason: Exclude<CommuteRouteReasonCode, "success"> = next.reason_code === "success" ? "provider_error" : next.reason_code;
        setMessage(SAFE_MESSAGES[safeReason]);
        onEvidenceRef.current?.(evidenceFrom(next, originLatitude, originLongitude, trimmed));
      }
    } catch {
      if (requestId.current !== currentRequest) return;
      setResult(null);
      setReasonCode("provider_error");
      setRouteDisplayStatus("unavailable");
      setMessage(SAFE_MESSAGES.provider_error);
      onEvidenceRef.current?.(failedEvidence("provider_error", originLatitude, originLongitude, trimmed, mode));
      onStatusRef.current?.("unavailable");
    } finally {
      if (requestId.current === currentRequest) setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-cyan-100 bg-cyan-50/50 p-3" data-testid="commute-route-card">
      <span className="sr-only" data-testid="commute-route-state" data-status={routeDisplayStatus} data-reason-code={reasonCode} />
      <p className="text-xs font-bold text-slate-900">Google 路線時間與距離</p>
      <p className="mt-1 text-[11px] leading-5 text-slate-600">以目前房屋位置為起點，查詢指定目的地的路線證據；與 TDX 大眾運輸情境資料分開呈現。</p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <input aria-label="目的地地址" value={destination} onChange={(event) => { setDestination(event.target.value); clearRoute(); }} placeholder="例如：台北車站" className="min-w-0 flex-1 rounded-lg bg-stone-50 px-3 py-3 text-sm outline-none focus:ring-2 focus:ring-cyan-200" />
        <select aria-label="交通方式" value={mode} onChange={(event) => { setMode(event.target.value as CommuteRouteMode); clearRoute(); }} className="rounded-lg bg-stone-50 px-3 py-3 text-sm outline-none focus:ring-2 focus:ring-cyan-200">
          {(Object.keys(MODE_LABELS) as CommuteRouteMode[]).map((key) => <option key={key} value={key}>{MODE_LABELS[key]}</option>)}
        </select>
        <Button secondary className="w-full shrink-0 sm:w-auto" disabled={loading} onClick={lookupRoute}>{loading ? "查詢中…" : "估算通勤"}</Button>
      </div>
      {message && <p className="mt-3 text-xs leading-5 text-slate-600">{message}</p>}
      {result?.status === "resolved" && (
        <div className="mt-3 grid gap-2 rounded-lg border border-cyan-100 bg-white p-3 text-xs text-slate-700 sm:grid-cols-3">
          {result.fallback && <div className="sm:col-span-3"><div data-testid="commute-route-mock-banner" className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-[11px] font-bold leading-5 text-amber-900">測試／展示模擬路線 — 非 Google 實際結果</div></div>}
          <SafeField label="交通方式" value={MODE_LABELS[result.mode]} />
          <SafeField label="路線時間" value={`${result.duration_min === null ? formatMissing("not_provided") : formatDuration(result.duration_min)}${result.fallback ? "（模擬）" : ""}`} />
          <SafeField label="路線距離" value={result.distance_m === null ? formatMissing("not_provided") : formatDistance(result.distance_m)} />
          <div className="sm:col-span-3"><SafeField label="資料來源" value={SOURCE_LABELS[result.source]} /></div>
          <div className="sm:col-span-3"><SafeField label="查詢時間" value={result.checked_at} /></div>
          {result.fallback && <div className="sm:col-span-3"><Notice tone="warning">{result.message}</Notice></div>}
          <div className="sm:col-span-3"><Notice>{result.disclaimer}</Notice></div>
        </div>
      )}
    </div>
  );
}

function SafeField({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg bg-stone-50 p-2"><p className="text-[10px] font-bold text-slate-500">{label}</p><p className="mt-1 break-words text-sm font-bold text-slate-900">{value}</p></div>;
}
