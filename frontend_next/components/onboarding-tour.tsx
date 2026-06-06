"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "proptech_onboarding_seen";
const steps = [
  {
    eyebrow: "歡迎使用 Urban Copilot",
    title: "快速整理一筆房地產案件",
    description: "這是一個房地產案件決策工作台，用來快速整理稅務、地圖、行情與風險資訊。",
    nodes: ["案件", "稅務", "地圖", "報告"],
  },
  {
    eyebrow: "第一步",
    title: "先從 TaxOracle 開始",
    description: "選擇低風險、中風險或高風險案例，系統會用 TX001–TX009 規則引擎完成稅務快篩。",
    nodes: ["選案例", "規則快篩", "查看原因"],
  },
  {
    eyebrow: "補強說明",
    title: "查看地圖與生活機能",
    description: "Map Insight 可搜尋地址，查看周遭交通、學校、公園、醫療、商圈與餐飲。",
    nodes: ["搜尋地址", "切換設施", "理解生活圈"],
  },
  {
    eyebrow: "完成決策摘要",
    title: "下載客戶溝通報告",
    description: "分析完成後可以下載 HTML 報告，作為展示型客戶溝通摘要。",
    nodes: ["資格判斷", "風險原因", "報告輸出"],
  },
];

export function OnboardingTour({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (open) setStep(0);
  }, [open]);

  if (!open) return null;
  const current = steps[step];
  const finish = () => {
    window.localStorage.setItem(STORAGE_KEY, "true");
    onClose();
  };

  return <div className="fixed inset-0 z-[1000] grid place-items-center bg-slate-950/40 p-3 backdrop-blur-[2px] animate-onboarding-fade" role="dialog" aria-modal="true" aria-label="Urban Copilot 操作導覽">
    <section className="flex max-h-[calc(100vh-1.5rem)] w-full max-w-xl flex-col overflow-hidden rounded-2xl border border-white/70 bg-[#fffdf8] shadow-2xl">
      <div className="h-1 bg-stone-100"><div className="h-full bg-cyan-600 transition-all duration-300" style={{ width: `${((step + 1) / steps.length) * 100}%` }} /></div>
      <div key={step} className="overflow-y-auto px-5 py-5 animate-onboarding-step sm:px-7 sm:py-7">
        <div className="flex items-center justify-between gap-4"><p className="text-[10px] font-bold tracking-[0.16em] text-cyan-700">{current.eyebrow}</p><p className="text-[10px] font-bold text-slate-400">{step + 1} / {steps.length}</p></div>
        <h2 className="mt-3 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">{current.title}</h2>
        <p className="mt-3 text-sm leading-7 text-slate-600">{current.description}</p>
        <TourFlow nodes={current.nodes} />
        <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-3 text-[11px] leading-5 text-amber-800">本系統使用展示資料與 Google Places fallback，僅供案件溝通與區域理解，不構成正式稅務、法律、估價或投資建議。</div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-stone-200 bg-white px-5 py-4 sm:px-7">
        <button onClick={finish} className="text-xs font-bold text-slate-400 transition hover:text-slate-700">跳過導覽</button>
        <div className="flex items-center gap-2">
          {step > 0 && <button onClick={() => setStep((value) => value - 1)} className="rounded-lg border border-stone-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-600 transition hover:bg-stone-50">上一步</button>}
          <button onClick={() => step === steps.length - 1 ? finish() : setStep((value) => value + 1)} className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-bold text-white transition hover:bg-cyan-800">{step === 0 ? "開始導覽" : step === steps.length - 1 ? "開始使用" : "下一步"}</button>
        </div>
      </div>
    </section>
  </div>;
}

function TourFlow({ nodes }: { nodes: string[] }) {
  return <div className="mt-6 flex min-w-0 items-center rounded-xl border border-stone-200 bg-white px-3 py-4">{nodes.map((node, index) => <div key={node} className="flex min-w-0 flex-1 items-center"><div className="min-w-0 flex-1 text-center"><span className="mx-auto grid h-8 w-8 place-items-center rounded-full bg-cyan-50 text-[11px] font-bold text-cyan-800">{index + 1}</span><p className="mt-2 truncate text-[10px] font-bold text-slate-600">{node}</p></div>{index < nodes.length - 1 && <span className="h-px w-4 shrink-0 bg-gradient-to-r from-cyan-300 to-stone-200 sm:w-8" />}</div>)}</div>;
}

export function hasSeenOnboarding(): boolean {
  return typeof window !== "undefined" && window.localStorage.getItem(STORAGE_KEY) === "true";
}
