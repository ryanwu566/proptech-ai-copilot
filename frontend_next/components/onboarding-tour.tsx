"use client";

import { useEffect, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { RuntimeCopyKey } from "@/lib/runtime-copy";

const STORAGE_KEY = "proptech_onboarding_seen";
const VERSION_KEY = "proptech_onboarding_version";
const TOUR_VERSION = "2";

type TourAction = "tax-low" | "map" | "explore";
type TourStep = {
  eyebrow: RuntimeCopyKey;
  title: RuntimeCopyKey;
  description: RuntimeCopyKey;
  preview: "cases" | "tax" | "map" | "value" | "report";
};

const steps: TourStep[] = [
  {
    eyebrow: "tour.step1Eyebrow", title: "tour.step1Title", description: "tour.step1Description",
    preview: "cases",
  },
  {
    eyebrow: "tour.step2Eyebrow", title: "tour.step2Title", description: "tour.step2Description",
    preview: "tax",
  },
  {
    eyebrow: "tour.step3Eyebrow", title: "tour.step3Title", description: "tour.step3Description",
    preview: "map",
  },
  {
    eyebrow: "tour.step4Eyebrow", title: "tour.step4Title", description: "tour.step4Description",
    preview: "value",
  },
  {
    eyebrow: "tour.step5Eyebrow", title: "tour.step5Title", description: "tour.step5Description",
    preview: "report",
  },
];

export function OnboardingTour({ open, onClose, onAction }: { open: boolean; onClose: () => void; onAction: (action: TourAction) => void }) {
  const { copy } = useExperienceLocale();
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (open) setStep(0);
  }, [open]);

  if (!open) return null;
  const current = steps[step];
  const finish = (action: TourAction = "explore") => {
    window.localStorage.setItem(STORAGE_KEY, "true");
    window.localStorage.setItem(VERSION_KEY, TOUR_VERSION);
    onClose();
    onAction(action);
  };

  return <div className="fixed inset-0 z-[1000] grid place-items-center bg-slate-950/45 p-2 backdrop-blur-[3px] animate-onboarding-fade sm:p-4" role="dialog" aria-modal="true" aria-label={copy("tour.dialogLabel")}>
    <section className="flex max-h-[calc(100dvh-1rem)] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-white/70 bg-[#fffdf8] shadow-2xl sm:max-h-[calc(100dvh-2rem)]">
      <div className="h-1 bg-stone-100"><div className="h-full bg-cyan-600 transition-all duration-500 motion-reduce:transition-none" style={{ width: `${((step + 1) / steps.length) * 100}%` }} /></div>
      <div key={step} className="grid min-h-0 flex-1 overflow-y-auto animate-onboarding-step md:grid-cols-[minmax(0,0.9fr)_minmax(360px,1.1fr)]">
        <div className="order-2 flex flex-col justify-center px-5 py-5 sm:px-8 sm:py-7 md:order-1 lg:px-10">
          <div className="flex items-center justify-between gap-4"><p className="text-[10px] font-bold tracking-[0.16em] text-cyan-700">{copy(current.eyebrow)}</p><p className="text-[10px] font-bold text-slate-400">{step + 1} / {steps.length}</p></div>
          <h2 className="mt-3 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">{copy(current.title)}</h2>
          <p className="mt-3 text-sm leading-7 text-slate-600">{copy(current.description)}</p>
          <DecisionJourney active={step} />
          {step === steps.length - 1 && <p className="mt-5 text-[10px] leading-5 text-slate-400">{copy("tour.skipNotice")}</p>}
        </div>
        <div className="order-1 min-h-[230px] border-b border-stone-200 bg-[#edf4f1] p-4 sm:min-h-[280px] sm:p-6 md:order-2 md:min-h-[470px] md:border-b-0 md:border-l">
          <TourPreview type={current.preview} />
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-stone-200 bg-white px-4 py-3 sm:px-8 sm:py-4">
        <button onClick={() => finish("explore")} className="text-xs font-bold text-slate-400 transition hover:text-slate-700">{copy("tour.skip")}</button>
        {step < steps.length - 1 ? <div className="flex items-center gap-2">
          {step > 0 && <button onClick={() => setStep((value) => value - 1)} className="rounded-lg border border-stone-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-600 transition hover:bg-stone-50">{copy("tour.previous")}</button>}
          <button onClick={() => setStep((value) => value + 1)} className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-bold text-white transition hover:bg-cyan-800">{step === 0 ? copy("tour.start") : copy("tour.next")}</button>
        </div> : <div className="flex w-full flex-wrap gap-2 sm:w-auto sm:justify-end">
          <button onClick={() => finish("tax-low")} className="w-full rounded-lg bg-cyan-700 px-4 py-2 text-xs font-bold text-white transition hover:bg-cyan-800 sm:w-auto">{copy("tour.openTax")}</button>
          <button onClick={() => finish("map")} className="w-full rounded-lg border border-cyan-200 bg-cyan-50 px-4 py-2 text-xs font-bold text-cyan-800 transition hover:bg-cyan-100 sm:w-auto">{copy("tour.openMap")}</button>
          <button onClick={() => finish("explore")} className="w-full rounded-lg px-3 py-2 text-xs font-bold text-slate-500 hover:bg-stone-50 sm:w-auto">{copy("tour.explore")}</button>
        </div>}
      </div>
    </section>
  </div>;
}

function DecisionJourney({ active }: { active: number }) {
  const { copy } = useExperienceLocale();
  const labels = [copy("case.title"), copy("tax.title"), copy("map.title"), copy("valuation.title"), copy("tour.clientReport")];
  return <div className="mt-6 flex items-center gap-1 overflow-hidden">{labels.map((label, index) => <div key={label} className="flex min-w-0 flex-1 items-center"><div className="min-w-0 flex-1 text-center"><span className={`mx-auto block h-2 w-2 rounded-full transition ${index <= active ? "bg-cyan-600 ring-4 ring-cyan-100" : "bg-stone-300"}`} /><p className={`mt-2 truncate text-[9px] font-bold ${index === active ? "text-cyan-800" : "text-slate-400"}`}>{label}</p></div>{index < labels.length - 1 && <span className={`h-px w-2 shrink-0 sm:w-4 ${index < active ? "bg-cyan-400" : "bg-stone-200"}`} />}</div>)}</div>;
}

function TourPreview({ type }: { type: TourStep["preview"] }) {
  return <div className="relative flex h-full min-h-[200px] items-center justify-center overflow-hidden rounded-xl border border-white/80 bg-white/75 p-4 shadow-[0_18px_45px_rgba(15,23,42,0.12)] backdrop-blur-sm sm:min-h-[245px]">
    {type === "cases" && <CasePreview />}
    {type === "tax" && <TaxPreview />}
    {type === "map" && <MapPreview />}
    {type === "value" && <ValuePreview />}
    {type === "report" && <ReportPreview />}
  </div>;
}

function CasePreview() {
  const { copy } = useExperienceLocale();
  return <div className="grid w-full max-w-md gap-2 sm:grid-cols-3">{[[copy("tour.caseLowRisk"), copy("tour.feasible"), "border-emerald-400 bg-emerald-50 ring-4 ring-emerald-100"], [copy("tour.caseMediumRisk"), copy("tour.review"), "border-amber-200 bg-white"], [copy("tour.caseHighRisk"), copy("tour.highRisk"), "border-rose-200 bg-white"]].map(([name, state, tone], index) => <div key={name} className={`tour-float rounded-xl border p-3 shadow-sm ${tone}`} style={{ animationDelay: `${index * 180}ms` }}><span className={`block h-2 w-2 rounded-full ${index === 0 ? "bg-emerald-500" : index === 1 ? "bg-amber-500" : "bg-rose-500"}`} /><p className="mt-7 text-xs font-bold text-slate-900">{name}</p><p className="mt-1 text-[10px] text-slate-500">{state}</p></div>)}</div>;
}

function TaxPreview() {
  const { copy } = useExperienceLocale();
  const items = [[copy("tour.eligibility"), copy("tour.feasible"), "bg-emerald-50 text-emerald-700"], [copy("tour.risk"), "12 / 100", "bg-cyan-50 text-cyan-700"], [copy("tour.missing"), "0", "bg-amber-50 text-amber-700"], [copy("tour.fiveYear"), copy("action.open"), "bg-violet-50 text-violet-700"]];
  return <div className="w-full max-w-md"><div className="flex items-center justify-between"><div><p className="text-[10px] font-bold text-cyan-700">TX001–TX009</p><p className="mt-1 text-sm font-bold text-slate-900">{copy("tour.ruleComplete")}</p></div><span className="h-3 w-3 rounded-full bg-emerald-500 ring-4 ring-emerald-100" /></div><div className="mt-5 grid grid-cols-2 gap-2">{items.map(([label, value, tone], index) => <div key={label} className={`tour-pop rounded-lg p-3 ${tone}`} style={{ animationDelay: `${index * 140}ms` }}><p className="text-[9px] opacity-70">{label}</p><p className="mt-1 text-xs font-bold">{value}</p></div>)}</div></div>;
}

function MapPreview() {
  const { copy } = useExperienceLocale();
  return <div className="relative h-full min-h-[190px] w-full max-w-md overflow-hidden rounded-xl bg-[#dceae5]"><div className="absolute inset-0 opacity-70"><i className="absolute left-[18%] top-[-15%] h-[140%] w-7 rotate-12 bg-white" /><i className="absolute left-[-10%] top-[45%] h-6 w-[130%] -rotate-6 bg-white" /></div><div className="absolute left-1/2 top-1/2 h-32 w-32 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-dashed border-cyan-600/60 bg-cyan-100/30" /><span className="tour-pulse absolute left-[48%] top-[47%] h-3 w-3 rounded-full bg-slate-900 ring-4 ring-white" />{[["left-[30%] top-[32%]", "bg-blue-500"], ["right-[25%] top-[28%]", "bg-violet-500"], ["left-[34%] bottom-[23%]", "bg-emerald-500"], ["right-[28%] bottom-[27%]", "bg-amber-500"]].map(([position, color]) => <span key={position} className={`tour-pop absolute h-2.5 w-2.5 rounded-full ring-4 ring-white ${position} ${color}`} />)}<div className="absolute left-3 top-3 rounded-lg bg-white/90 px-3 py-2 text-[10px] font-bold text-slate-700 shadow-sm">{copy("map.nearby")} · 800m</div><div className="absolute bottom-3 right-3 flex gap-1 rounded-lg bg-white/90 p-1.5 text-[8px] font-bold text-slate-500 shadow-sm"><span>{copy("tour.standard")}</span><span>{copy("tour.light")}</span><span>{copy("tour.satellite")}</span></div></div>;
}

function ValuePreview() {
  const { copy } = useExperienceLocale();
  return <div className="grid w-full max-w-md gap-3 sm:grid-cols-2"><div className="rounded-xl border border-stone-200 bg-white p-4"><p className="text-[10px] font-bold text-slate-400">{copy("tour.comparableRange")}</p><div className="mt-6 flex items-end gap-2"><span className="h-8 flex-1 rounded-t bg-cyan-100" /><span className="h-16 flex-1 rounded-t bg-cyan-600" /><span className="h-11 flex-1 rounded-t bg-cyan-200" /></div><div className="mt-2 flex justify-between text-[8px] text-slate-400"><span>P25</span><span>{copy("valuation.mid")}</span><span>P75</span></div><p className="mt-3 text-xs font-bold text-slate-800">{copy("valuation.confidence")} 86</p></div><div className="rounded-xl bg-slate-900 p-4 text-white"><p className="text-[10px] font-bold text-slate-400">{copy("tour.bankRate")}</p><p className="mt-4 text-3xl font-bold">1.72<span className="text-xs text-slate-400">%</span></p><p className="mt-1 text-[9px] text-slate-400">{copy("tour.marketReference")}</p><div className="mt-5 rounded-lg bg-amber-400/15 px-2 py-2 text-[9px] font-bold text-amber-200">{copy("tour.riskNotice")}</div></div></div>;
}

function ReportPreview() {
  const { copy } = useExperienceLocale();
  return <div className="relative w-full max-w-sm"><div className="absolute -right-3 -top-3 h-full w-full rotate-3 rounded-xl border border-stone-200 bg-stone-100" /><div className="tour-report relative rounded-xl border border-stone-200 bg-white p-5 shadow-lg"><div className="flex items-start justify-between"><div><p className="text-[9px] font-bold tracking-widest text-cyan-700">TAXORACLE REPORT</p><h3 className="mt-1 text-sm font-bold text-slate-900">{copy("tour.clientReport")}</h3></div><span className="rounded-full bg-emerald-100 px-2 py-1 text-[9px] font-bold text-emerald-700">{copy("tour.feasible")}</span></div><div className="mt-5 grid grid-cols-3 gap-2">{[copy("tour.eligibilityReason"), copy("tour.riskReason"), copy("tour.missingReminder")].map((item) => <div key={item} className="rounded-lg bg-stone-50 p-2 text-center text-[9px] font-bold text-slate-600">{item}</div>)}</div><div className="mt-4 space-y-2">{[72, 92, 64].map((width) => <span key={width} className="block h-1.5 rounded bg-stone-100" style={{ width: `${width}%` }} />)}</div><div className="mt-5 rounded-lg bg-cyan-700 py-2 text-center text-[10px] font-bold text-white">{copy("tour.downloadHtml")}</div></div></div>;
}

export function hasSeenOnboarding(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(STORAGE_KEY) === "true" && window.localStorage.getItem(VERSION_KEY) === TOUR_VERSION;
}
