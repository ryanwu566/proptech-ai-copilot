"use client";

import { useEffect, useRef, useState } from "react";
import { HOLDING_COST_RESULT_EVENT, HOLDING_COST_SESSION_KEY } from "@/components/holding-cost-calculator";
import { LOCATION_INSIGHT_RESULT_EVENT, LOCATION_INSIGHT_SESSION_KEY } from "@/components/location-insight";
import { TERRAIN_RISK_RESULT_EVENT, TERRAIN_RISK_SESSION_KEY } from "@/components/terrain-risk-analysis";
import { DEMO_STEPS, DemoRunError, GUIDED_DEMO_PENDING_KEY, GUIDED_DEMO_RESULT_EVENT, runDemoPreflight, runGuidedDemo, runOptionalTaxOracleDemo, START_GUIDED_DEMO_EVENT, type DemoPreflightStatus, type DemoResults, type DemoStepState } from "@/lib/demo-runner";
import { markTaxOracleCompleted, WORKFLOW_STATUS_EVENT } from "@/lib/workflow-status";
import { HelpTooltip } from "@/components/help-tooltip";
import { HELP_CONTENT } from "@/lib/help-content";

type Props = {
  onMessage?: (message: string) => void;
  onSave?: () => void;
  onExport?: () => void;
  canExport?: boolean;
};

export function GuidedDemoRunner({ onMessage, onSave, onExport, canExport = false }: Props) {
  const [steps, setSteps] = useState<DemoStepState[]>(freshSteps);
  const [results, setResults] = useState<DemoResults>();
  const [running, setRunning] = useState(false);
  const [failedIndex, setFailedIndex] = useState<number>();
  const [completed, setCompleted] = useState(false);
  const [preflight, setPreflight] = useState<{ status: DemoPreflightStatus; message: string }>({ status: "checking", message: "尚未執行 API 預檢。" });
  const [taxStatus, setTaxStatus] = useState<"idle" | "running" | "done" | "failed">("idle");
  const cancelled = useRef(false);
  const resultsRef = useRef<DemoResults | undefined>(undefined);

  useEffect(() => { resultsRef.current = results; }, [results]);
  useEffect(() => {
    const start = () => void restart();
    window.addEventListener(START_GUIDED_DEMO_EVENT, start);
    if (window.sessionStorage.getItem(GUIDED_DEMO_PENDING_KEY) === "true") {
      window.sessionStorage.removeItem(GUIDED_DEMO_PENDING_KEY);
      void restart();
    }
    return () => window.removeEventListener(START_GUIDED_DEMO_EVENT, start);
  }, []);

  async function execute(startIndex: number, existing?: DemoResults) {
    cancelled.current = false;
    setRunning(true);
    setFailedIndex(undefined);
    setCompleted(false);
    setSteps((rows) => rows.map((row, index) => index < startIndex && row.status === "done" ? row : index >= startIndex ? { ...DEMO_STEPS[index], status: "queued" } : row));
    try {
      await runDemoPreflight((status, message) => {
        setPreflight({ status, message });
        onMessage?.(status === "checking" ? "先確認後端服務是否醒著。" : status === "waking" ? "後端服務可能正在喚醒，請稍候。" : message);
      });
      if (cancelled.current) return;
      onMessage?.("Demo 正在跑，請等目前步驟完成。");
      const final = await runGuidedDemo({
        startIndex, existing, isCancelled: () => cancelled.current,
        onStep: (index, state) => setSteps((rows) => rows.map((row, rowIndex) => rowIndex === index ? state : row)),
        onResults: publishResults,
      });
      setResults(final);
      if (!cancelled.current) {
        setCompleted(true);
        onMessage?.("Demo 已完成，可以保存案件或匯出報告。");
      }
    } catch (caught) {
      if (caught instanceof DemoRunError) {
        setResults(caught.results);
        setFailedIndex(caught.stepIndex);
        onMessage?.("目前卡在這一步，可以重試或改手動操作。");
      }
    } finally {
      setRunning(false);
    }
  }

  function publishResults(next: DemoResults) {
    resultsRef.current = next;
    setResults(next);
    const context = { inputs: next.inputs, propertySearch: next.propertySearch, valuation: next.valuation, trend: next.trend, loan: next.loan, holding: next.holdingCost };
    window.sessionStorage.setItem("proptech:viewing-workspace-context", JSON.stringify(context));
    window.dispatchEvent(new CustomEvent("proptech:viewing-workspace-context", { detail: context }));
    if (next.holdingCost) { window.sessionStorage.setItem(HOLDING_COST_SESSION_KEY, JSON.stringify(next.holdingCost)); window.dispatchEvent(new CustomEvent(HOLDING_COST_RESULT_EVENT, { detail: next.holdingCost })); }
    if (next.locationInsight) { window.sessionStorage.setItem(LOCATION_INSIGHT_SESSION_KEY, JSON.stringify(next.locationInsight)); window.dispatchEvent(new CustomEvent(LOCATION_INSIGHT_RESULT_EVENT, { detail: next.locationInsight })); }
    if (next.terrainRisk) { window.sessionStorage.setItem(TERRAIN_RISK_SESSION_KEY, JSON.stringify(next.terrainRisk)); window.dispatchEvent(new CustomEvent(TERRAIN_RISK_RESULT_EVENT, { detail: next.terrainRisk })); }
    window.dispatchEvent(new CustomEvent(GUIDED_DEMO_RESULT_EVENT, { detail: next }));
    window.dispatchEvent(new Event(WORKFLOW_STATUS_EVENT));
  }

  function cancel() {
    cancelled.current = true;
    setRunning(false);
    setSteps((rows) => rows.map((row) => row.status === "running" ? { ...row, status: "queued" } : row));
    onMessage?.("Demo 已取消，已成功取得的結果仍可繼續使用。");
  }

  function retryFailed() {
    if (failedIndex !== undefined) void execute(failedIndex, resultsRef.current);
  }

  function continueFromProgress() {
    const nextIndex = steps.findIndex((step) => step.status !== "done");
    if (nextIndex >= 0) void execute(nextIndex, resultsRef.current);
  }

  function restart() {
    cancelled.current = false;
    resultsRef.current = undefined;
    setResults(undefined);
    setSteps(freshSteps());
    setFailedIndex(undefined);
    setCompleted(false);
    setTaxStatus("idle");
    void execute(0);
  }

  async function runTax() {
    setTaxStatus("running");
    try {
      const result = await runOptionalTaxOracleDemo();
      markTaxOracleCompleted(result);
      setTaxStatus("done");
      onMessage?.("TaxOracle 低風險示範案已完成。");
    } catch {
      setTaxStatus("failed");
      onMessage?.("TaxOracle API 暫時無法完成，可稍後再試。");
    }
  }

  const hasProgress = steps.some((step) => step.status === "done");
  return <section className="min-w-0 rounded-2xl border border-violet-200 bg-violet-50/60 p-4 shadow-sm" aria-label="一鍵 Demo 流程">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div><p className="text-[10px] font-bold tracking-wider text-violet-700">GUIDED DEMO RUN</p><div className="mt-1 flex items-center gap-2"><h2 className="font-bold text-slate-950">一鍵 Demo 流程</h2><HelpTooltip title={HELP_CONTENT.guidedDemo.title}>{HELP_CONTENT.guidedDemo.body}</HelpTooltip></div><p className="mt-1 text-xs text-slate-600">依序實際呼叫既有 API；失敗時保留已完成結果，可重試或改手動流程。</p></div>
      <div className="flex flex-wrap gap-2">
        {!running && preflight.status === "failed" && <button type="button" onClick={continueFromProgress} className="rounded-lg bg-amber-600 px-3 py-2 text-xs font-bold text-white">重試 API 預檢</button>}
        {!running && failedIndex !== undefined && <button type="button" onClick={retryFailed} className="rounded-lg bg-violet-700 px-3 py-2 text-xs font-bold text-white">重試失敗步驟</button>}
        {!running && hasProgress && !completed && <button type="button" onClick={continueFromProgress} className="rounded-lg border border-violet-300 bg-white px-3 py-2 text-xs font-bold text-violet-800">從目前進度繼續</button>}
        {!running && <button type="button" onClick={restart} className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs font-bold text-slate-700">重新開始 Demo</button>}
        {running && <button type="button" onClick={cancel} className="rounded-lg border border-rose-200 bg-white px-3 py-2 text-xs font-bold text-rose-700">取消 Demo</button>}
      </div>
    </div>

    <div className={`mt-4 rounded-xl border px-3 py-2 text-xs ${preflight.status === "failed" ? "border-rose-200 bg-rose-50 text-rose-800" : preflight.status === "ready" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-200 bg-amber-50 text-amber-800"}`}>
      <strong>API 預檢 · {preflight.status}</strong><span className="ml-2">{preflight.message}</span>
    </div>

    <ol className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">{steps.map((step) => <li key={step.id} className={`rounded-xl border bg-white p-3 ${step.status === "failed" ? "border-rose-300" : step.status === "done" ? "border-emerald-200" : step.status === "running" ? "border-violet-400" : "border-stone-200"}`}>
      <div className="flex items-center justify-between gap-2"><strong className="text-xs text-slate-800">{step.label}</strong><span className="text-[10px] font-bold uppercase text-slate-500">{step.status}</span></div>
      <p className="mt-1 break-all font-mono text-[9px] text-slate-400">{step.endpoint}</p>
      {step.summary && <p className="mt-2 text-[10px] leading-5 text-emerald-700">{step.summary}</p>}
      {step.error && <p className="mt-2 text-[10px] leading-5 text-rose-700">{step.error}</p>}
      {step.recovery && <p className="mt-1 text-[10px] leading-5 text-amber-700">{step.recovery}</p>}
    </li>)}</ol>

    {completed && <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3">
      <p className="text-xs font-bold text-emerald-900">Demo 已完成：找房、估價、趨勢、貸款、持有成本、區位與風險總評均已完成。</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <button type="button" onClick={onSave} disabled={!onSave} title={onSave ? "保存目前 Demo 案件" : "目前無法保存"} className="rounded-lg bg-cyan-700 px-3 py-2 text-xs font-bold text-white disabled:opacity-45">保存案件</button>
        <button type="button" onClick={onExport} disabled={!canExport || !onExport} title={canExport ? "匯出目前看屋報告" : "請先完成估價"} className="rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-bold text-cyan-800 disabled:opacity-45">匯出看屋報告</button>
        <button type="button" disabled={taxStatus === "running"} onClick={runTax} className="rounded-lg border border-violet-200 bg-white px-3 py-2 text-xs font-bold text-violet-800 disabled:opacity-45">{taxStatus === "running" ? "TaxOracle 快篩中..." : taxStatus === "done" ? "TaxOracle 示範案已完成" : "接著跑 TaxOracle 示範案"}</button>
      </div>
      {taxStatus === "failed" && <p className="mt-2 text-[10px] text-rose-700">TaxOracle 是 optional step，失敗不影響主 Demo，可稍後重試。</p>}
    </div>}
  </section>;
}

function freshSteps(): DemoStepState[] {
  return DEMO_STEPS.map((step) => ({ ...step, status: "queued" }));
}
