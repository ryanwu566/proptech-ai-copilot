"use client";

import { useEffect, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function FriendlyIntroWalkthrough() {
  const { copy } = useExperienceLocale();
  const scenes = [
    { title: copy("intro.scene1"), chips: ["PropTech", "AI", "Copilot"] },
    { title: copy("intro.scene2"), chips: ["Property Finder", "Budget", "Area"] },
    { title: copy("intro.scene3"), chips: ["Valuation", "Loan", "Holding Cost"] },
    { title: copy("intro.scene4"), chips: ["Location", "Terrain", "Market"] },
    { title: copy("intro.scene5"), chips: ["Report", "Decision", "Compare"] },
  ];
  const [scene, setScene] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [reducedMotion, setReducedMotion] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => { setReducedMotion(query.matches); if (query.matches) setPlaying(false); };
    update(); query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (!playing || reducedMotion) return;
    const timer = window.setInterval(() => setScene((value) => value === scenes.length - 1 ? (setPlaying(false), value) : value + 1), 2600);
    return () => window.clearInterval(timer);
  }, [playing, reducedMotion, scenes.length]);
  function replay() { setScene(0); setPlaying(!reducedMotion); }
  return <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm" aria-label={copy("intro.ariaLabel")}>
    <div className="flex items-center justify-between gap-3"><div><p className="text-[10px] font-bold tracking-wider text-yellow-200">{copy("intro.mascotLabel")}</p><p className="mt-1 text-sm font-bold">{copy("wizard.introNote")}</p></div><span className="rounded-full bg-yellow-300 px-2 py-1 text-[10px] font-black text-amber-950">{scene + 1} / {scenes.length}</span></div>
    <div className="mt-4 min-h-28 rounded-xl border border-cyan-200/15 bg-slate-900/75 p-4 motion-reduce:transition-none" aria-live="polite">
      <p className="text-sm font-extrabold leading-6 text-white">{scenes[scene].title}</p>
      <div className="mt-3 flex flex-wrap gap-2">{scenes[scene].chips.map((chip) => <span key={chip} className="hero-sequence rounded-lg border border-cyan-200/20 bg-cyan-300/10 px-2.5 py-1.5 text-[10px] font-bold text-cyan-100 motion-reduce:animate-none">{chip}</span>)}</div>
    </div>
    <div className="mt-3 flex items-center gap-1">{scenes.map((item, index) => <button key={item.title} type="button" aria-label={`${index + 1}`} onClick={() => { setScene(index); setPlaying(false); }} className={`h-1.5 flex-1 rounded-full ${index === scene ? "bg-cyan-300" : "bg-white/15"}`} />)}</div>
    <div className="mt-3 flex flex-wrap gap-2"><button type="button" onClick={() => setPlaying(false)} className="rounded-lg border border-white/20 px-3 py-1.5 text-[10px] font-bold text-slate-200">{copy("intro.skipButton")}</button><button type="button" onClick={replay} className="rounded-lg bg-cyan-300 px-3 py-1.5 text-[10px] font-bold text-slate-950">{copy("intro.replayButton")}</button>{reducedMotion && <span className="self-center text-[9px] text-slate-400">{copy("intro.reducedMotionNote")}</span>}</div>
  </div>;
}
