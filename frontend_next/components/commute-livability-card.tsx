"use client";

import { useEffect, useRef, useState } from "react";
import { api, type CommuteAddressLookupResult } from "@/lib/api";
import { Button, Notice } from "@/components/ui";
import { COMMUTE_LIVABILITY_NOTICE, commuteStatusMessage, isBlankAddress, normalizeCommuteResult, type CommuteLivabilityStatus } from "@/lib/commute-livability-ui";

export function CommuteLivabilityCard({ address }: { address: string }) {
  const [status, setStatus] = useState<CommuteLivabilityStatus>("idle");
  const [result, setResult] = useState<CommuteAddressLookupResult | null>(null);
  const [message, setMessage] = useState(commuteStatusMessage("idle"));
  const latestAddressRef = useRef(address);

  useEffect(() => {
    latestAddressRef.current = address;
    setStatus("idle");
    setResult(null);
    setMessage(commuteStatusMessage("idle"));
  }, [address]);

  async function lookupCommute() {
    const requestedAddress = address.trim();
    if (isBlankAddress(requestedAddress)) {
      setStatus("idle");
      setResult(null);
      setMessage("請先輸入完整物件地址。");
      return;
    }
    if (status === "loading") return;

    setStatus("loading");
    setResult(null);
    setMessage(commuteStatusMessage("loading"));
    try {
      const next = normalizeCommuteResult(await api.commuteAddressLookup({ address: requestedAddress }));
      if (latestAddressRef.current.trim() !== requestedAddress) return;
      if (next.status === "resolved") {
        setResult(next);
        setStatus("resolved");
        setMessage("");
      } else if (next.status === "unresolved") {
        setResult(null);
        setStatus("unresolved");
        setMessage(commuteStatusMessage("unresolved"));
      } else {
        setResult(null);
        setStatus("unavailable");
        setMessage(commuteStatusMessage("unavailable"));
      }
    } catch {
      if (latestAddressRef.current.trim() !== requestedAddress) return;
      setResult(null);
      setStatus("error");
      setMessage(commuteStatusMessage("error"));
    }
  }

  return (
    <div className="rounded-xl border border-cyan-100 bg-cyan-50/50 p-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-bold text-slate-900">通勤與生活機能</p>
          <p className="mt-1 text-[11px] leading-5 text-slate-600">只查最近捷運站與官方快照時間，不會改變任何風險或看房結論。</p>
        </div>
        <Button secondary className="w-full shrink-0 sm:w-auto" disabled={status === "loading"} onClick={lookupCommute}>
          {status === "loading" ? "正在查詢通勤資訊⋯" : "查看通勤資訊"}
        </Button>
      </div>

      {message && (
        <p className={`mt-3 text-xs leading-5 ${message === "請先輸入完整物件地址。" ? "text-amber-700" : "text-slate-600"}`}>
          {message}
        </p>
      )}

      {result?.status === "resolved" && (
        <div className="mt-3 grid gap-2 rounded-lg border border-cyan-100 bg-white p-3 text-xs text-slate-700 sm:grid-cols-2">
          <SafeField label="最近捷運站" value={result.station_name ?? "資料不足"} />
          <SafeField label="路線" value={result.line_ids.length ? result.line_ids.join("、") : "資料不足"} />
          <SafeField label="步行前的直線距離（公尺）" value={result.distance_meters === null ? "資料不足" : `${Math.round(result.distance_meters)} 公尺`} />
          <SafeField label="資料來源／資料更新時間" value={`TDX / ${result.source_updated_at ?? result.snapshot_generated_at ?? "資料不足"}`} />
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
