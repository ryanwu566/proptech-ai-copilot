"use client";

import { useEffect, useState } from "react";

const scenes = [
  { title: "先告訴我你想看哪裡、預算多少。", chips: ["台北市大安區", "1,500–2,500 萬", "25–35 坪"] },
  { title: "我會用實價登錄幫你找可負擔路段。", chips: ["找房雷達", "推薦路段", "成交樣本"] },
  { title: "再幫你看價格、月付和持有成本。", chips: ["合理價格", "每月月付", "每月總成本"] },
  { title: "也會檢查附近生活機能與區位。", chips: ["交通", "便利", "學校", "醫療"] },
  { title: "最後給你紅黃綠燈號和看屋報告。", chips: ["綠燈", "黃燈", "紅燈", "HTML 報告"] },
];

export function FriendlyIntroWalkthrough() {
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
  }, [playing, reducedMotion]);
  function replay() { setScene(0); setPlaying(!reducedMotion); }
  return <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm" aria-label="新手使用介紹">
    <div className="flex items-center justify-between gap-3"><div><p className="text-[10px] font-bold tracking-wider text-yellow-200">黃色看房助手帶你看</p><p className="mt-1 text-sm font-bold">第一次使用？先花十秒看懂流程</p></div><span className="rounded-full bg-yellow-300 px-2 py-1 text-[10px] font-black text-amber-950">{scene + 1} / {scenes.length}</span></div>
    <div className="mt-4 min-h-28 rounded-xl border border-cyan-200/15 bg-slate-900/75 p-4 motion-reduce:transition-none" aria-live="polite">
      <p className="text-sm font-extrabold leading-6 text-white">{scenes[scene].title}</p>
      <div className="mt-3 flex flex-wrap gap-2">{scenes[scene].chips.map((chip) => <span key={chip} className="hero-sequence rounded-lg border border-cyan-200/20 bg-cyan-300/10 px-2.5 py-1.5 text-[10px] font-bold text-cyan-100 motion-reduce:animate-none">{chip}</span>)}</div>
    </div>
    <div className="mt-3 flex items-center gap-1">{scenes.map((item, index) => <button key={item.title} type="button" aria-label={`查看介紹第 ${index + 1} 幕`} onClick={() => { setScene(index); setPlaying(false); }} className={`h-1.5 flex-1 rounded-full ${index === scene ? "bg-cyan-300" : "bg-white/15"}`} />)}</div>
    <div className="mt-3 flex flex-wrap gap-2"><button type="button" onClick={() => setPlaying(false)} className="rounded-lg border border-white/20 px-3 py-1.5 text-[10px] font-bold text-slate-200">略過介紹</button><button type="button" onClick={replay} className="rounded-lg bg-cyan-300 px-3 py-1.5 text-[10px] font-bold text-slate-950">重新播放介紹</button>{reducedMotion && <span className="self-center text-[9px] text-slate-400">已依減少動態偏好顯示靜態步驟</span>}</div>
  </div>;
}
