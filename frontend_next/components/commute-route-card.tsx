"use client";

import { useState } from "react";
import { api, type CommuteRouteMode, type CommuteRouteResult } from "@/lib/api";
import { Button, Notice } from "@/components/ui";


const MODE_LABELS: Record<CommuteRouteMode, string> = {
  transit: "大眾運輸",
  driving: "開車",
  walking: "步行",
};

const SOURCE_LABELS: Record<CommuteRouteResult["source"], string> = {
  google_routes: "Google Routes",
  mock: "示範估算（非即時 Google 路線結果）",
  none: "無",
};

/**
 * Minimal travel-time surface: given a resolved property origin, estimate travel
 * duration/distance to a user-entered destination for one bounded mode. This is
 * external accessibility observation only; it does not affect property identity.
 */
export function CommuteRouteCard({ originLatitude, originLongitude }: { originLatitude: number; originLongitude: number }) {
  const [destination, setDestination] = useState("");
  const [mode, setMode] = useState<CommuteRouteMode>("transit");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CommuteRouteResult | null>(null);
  const [message, setMessage] = useState("");

  async function lookupRoute() {
    const trimmed = destination.trim();
    if (!trimmed) {
      setResult(null);
      setMessage("請輸入目的地地址。");
      return;
    }
    if (loading) return;
    setLoading(true);
    setResult(null);
    setMessage("路線估算中…");
    try {
      const next = await api.commuteRoute({
        origin_latitude: originLatitude,
        origin_longitude: originLongitude,
        destination_address: trimmed,
        mode,
      });
      if (next.status === "resolved") {
        setResult(next);
        setMessage("");
      } else if (next.status === "unresolved") {
        setResult(null);
        setMessage("找不到可用路線，請確認目的地是否正確。");
      } else {
        setResult(null);
        setMessage("路線服務暫時無法完成查詢，請稍後再試。");
      }
    } catch {
      setResult(null);
      setMessage("路線服務暫時無法完成查詢，請稍後再試。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-cyan-100 bg-cyan-50/50 p-3" data-testid="commute-route-card">
      <p className="text-xs font-bold text-slate-900">通勤時間估算</p>
      <p className="mt-1 text-[11px] leading-5 text-slate-600">輸入常用目的地與交通方式，估算從此物件出發的通勤時間與距離。</p>

      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <input
          aria-label="目的地地址"
          value={destination}
          onChange={(event) => setDestination(event.target.value)}
          placeholder="例如：台北市信義區市府路45號"
          className="min-w-0 flex-1 rounded-lg bg-stone-50 px-3 py-3 text-sm outline-none focus:ring-2 focus:ring-cyan-200"
        />
        <select
          aria-label="交通方式"
          value={mode}
          onChange={(event) => setMode(event.target.value as CommuteRouteMode)}
          className="rounded-lg bg-stone-50 px-3 py-3 text-sm outline-none focus:ring-2 focus:ring-cyan-200"
        >
          {(Object.keys(MODE_LABELS) as CommuteRouteMode[]).map((key) => (
            <option key={key} value={key}>{MODE_LABELS[key]}</option>
          ))}
        </select>
        <Button secondary className="w-full shrink-0 sm:w-auto" disabled={loading} onClick={lookupRoute}>
          {loading ? "估算中…" : "估算通勤"}
        </Button>
      </div>

      {message && <p className="mt-3 text-xs leading-5 text-slate-600">{message}</p>}

      {result?.status === "resolved" && (
        <div className="mt-3 grid gap-2 rounded-lg border border-cyan-100 bg-white p-3 text-xs text-slate-700 sm:grid-cols-3">
          {result.fallback && (
            <div className="sm:col-span-3">
              <div data-testid="commute-route-mock-banner" className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-[11px] font-bold leading-5 text-amber-900">
                示範估算 · 非即時 Google 路線結果
              </div>
            </div>
          )}
          <SafeField label="交通方式" value={MODE_LABELS[result.mode]} />
          <SafeField
            label={result.fallback ? "估計時間（示範估算）" : "估計時間"}
            value={result.duration_min === null ? "無資料" : `約 ${result.duration_min} 分鐘${result.fallback ? "（非即時）" : ""}`}
          />
          <SafeField label="估計距離" value={result.distance_m === null ? "無資料" : `${(result.distance_m / 1000).toFixed(1)} km`} />
          <div className="sm:col-span-3">
            <SafeField label="資料來源" value={SOURCE_LABELS[result.source]} />
          </div>
          {result.fallback && (
            <div className="sm:col-span-3">
              <Notice tone="warning">{result.message}</Notice>
            </div>
          )}
          <div className="sm:col-span-3">
            <Notice>{result.disclaimer}</Notice>
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
