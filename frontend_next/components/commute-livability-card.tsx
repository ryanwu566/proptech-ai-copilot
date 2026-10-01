"use client";

import { useEffect, useRef, useState } from "react";
import { api, type CommuteAddressLookupResult } from "@/lib/api";
import { Button, Notice } from "@/components/ui";
import { COMMUTE_LIVABILITY_NOTICE, isBlankAddress, normalizeCommuteResult, type CommuteLivabilityStatus } from "@/lib/commute-livability-ui";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { formatDistance } from "@/lib/commercial/formatters";


function restoredStatus(result: CommuteAddressLookupResult | undefined): CommuteLivabilityStatus {
  if (!result) return "idle";
  if (result.status === "resolved") return "resolved";
  if (result.status === "unresolved") return "unresolved";
  return "unavailable";
}

export function CommuteLivabilityCard({ address, initialResult, onStatusChange, onResult }: { address: string; initialResult?: CommuteAddressLookupResult; onStatusChange?: (status: CommuteLivabilityStatus) => void; onResult?: (result: CommuteAddressLookupResult | null) => void }) {
  const [status, setStatus] = useState<CommuteLivabilityStatus>(() => restoredStatus(initialResult));
  const [result, setResult] = useState<CommuteAddressLookupResult | null>(initialResult?.status === "resolved" ? initialResult : null);
  const [message, setMessage] = useState("");
  const { copy } = useExperienceLocale();
  const latestAddressRef = useRef(address);
  const onStatusRef = useRef(onStatusChange);
  const onResultRef = useRef(onResult);
  const previousAddressRef = useRef(address);

  useEffect(() => { onStatusRef.current = onStatusChange; }, [onStatusChange]);
  useEffect(() => { onResultRef.current = onResult; }, [onResult]);

  useEffect(() => {
    latestAddressRef.current = address;
    if (previousAddressRef.current === address) return;
    previousAddressRef.current = address;
    setStatus("idle");
    setResult(null);
    setMessage(copy("commute.idle"));
    onResultRef.current?.(null);
  }, [address]);

  useEffect(() => {
    onStatusRef.current?.(status);
  }, [status]);

  async function lookupCommute() {
    const requestedAddress = address.trim();
    if (isBlankAddress(requestedAddress)) {
      setStatus("idle");
      setResult(null);
      setMessage(copy("commute.empty"));
      return;
    }
    if (status === "loading") return;

    setStatus("loading");
    setResult(null);
    setMessage(copy("commute.checking"));
    try {
      const next = normalizeCommuteResult(await api.commuteAddressLookup({ address: requestedAddress }));
      if (latestAddressRef.current.trim() !== requestedAddress) return;
      if (next.status === "resolved") {
        setResult(next);
        onResultRef.current?.(next);
        setStatus("resolved");
        setMessage("");
      } else if (next.status === "unresolved") {
        setResult(null);
        onResultRef.current?.(next);
        setStatus("unresolved");
        setMessage(copy("commute.unresolved"));
      } else {
        setResult(null);
        onResultRef.current?.(next);
        setStatus("unavailable");
        setMessage(copy("commute.unavailable"));
      }
    } catch {
      if (latestAddressRef.current.trim() !== requestedAddress) return;
      setResult(null);
      onResultRef.current?.(null);
      setStatus("error");
      setMessage(copy("commute.error"));
    }
  }

  const visibleMessage = message
    || (status === "unresolved" ? copy("commute.unresolved") : status === "unavailable" ? copy("commute.unavailable") : "");

  return (
    <div className="rounded-xl border border-cyan-100 bg-cyan-50/50 p-3">
      <span className="sr-only" data-testid="commute-transit-context-state" data-status={status === "resolved" ? "available" : status === "unresolved" ? "no_data" : status === "error" ? "unavailable" : status} />
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-bold text-slate-900">{copy("commute.title")}</p>
          <p className="mt-1 text-[11px] leading-5 text-slate-600">{copy("commute.description")}</p>
        </div>
        <Button secondary className="w-full shrink-0 sm:w-auto" disabled={status === "loading"} onClick={lookupCommute}>
          {status === "loading" ? copy("commute.checking") : copy("commute.check")}
        </Button>
      </div>

      {visibleMessage && (
        <p className={`mt-3 text-xs leading-5 ${visibleMessage === copy("commute.empty") ? "text-amber-700" : "text-slate-600"}`}>
          {visibleMessage}
        </p>
      )}

      {result?.status === "resolved" && (
        <div className="mt-3 grid gap-2 rounded-lg border border-cyan-100 bg-white p-3 text-xs text-slate-700 sm:grid-cols-2">
          <SafeField label={copy("commute.station")} value={result.station_name ?? copy("commute.noData")} />
          <SafeField label={copy("commute.lines")} value={result.line_ids.length ? result.line_ids.join("、") : copy("commute.noData")} />
          <SafeField label={copy("commute.distance")} value={result.distance_meters === null ? copy("commute.noData") : formatDistance(result.distance_meters)} />
          <SafeField label={copy("commute.updated")} value={`${copy("commute.source")} / ${result.source_updated_at ?? result.snapshot_generated_at ?? copy("commute.noData")}`} />
          <div className="sm:col-span-2">
            <Notice>{COMMUTE_LIVABILITY_NOTICE}</Notice>
          </div>
        </div>
      )}
    </div>
  );
}

function SafeField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-stone-50 p-2">
      <p className="text-[10px] font-bold text-slate-500">{label}</p>
      <p className="mt-1 break-words text-sm font-bold text-slate-900">{value}</p>
    </div>
  );
}
