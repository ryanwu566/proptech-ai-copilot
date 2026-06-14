"use client";

const flowNodes = ["找房雷達", "實價估價", "貸款月付", "持有成本", "區位分析", "風險總評", "看屋報告"];

export function HeroIntro({ onStart, onWorkspace, reportReady = false, onReport }: { onStart: () => void; onWorkspace: () => void; reportReady?: boolean; onReport: () => void }) {
  return <section id="hero" className="relative min-w-0 overflow-hidden rounded-3xl border border-cyan-200/70 bg-slate-950 px-4 py-6 text-white shadow-xl sm:px-7 sm:py-8 lg:px-10 lg:py-10">
    <div className="hero-grid pointer-events-none absolute inset-0 opacity-35" />
    <div className="hero-orb pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-cyan-400/25 blur-3xl motion-reduce:animate-none" />
    <div className="relative grid min-w-0 gap-7 xl:grid-cols-[minmax(0,1fr)_minmax(420px,0.95fr)] xl:items-center">
      <div className="min-w-0 hero-reveal motion-reduce:animate-none">
        <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_18px_4px_rgba(103,232,249,.65)]" /><p className="text-[10px] font-bold tracking-[0.22em] text-cyan-200">PROPTECH AI COPILOT</p></div>
        <h1 className="mt-4 max-w-2xl text-3xl font-black tracking-tight sm:text-4xl lg:text-5xl">從找房到決策，一次完成</h1>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">整合實價登錄、估價、貸款、持有成本、區位與風險燈號，快速產出看屋決策報告。</p>
        <div className="mt-6 grid gap-2 sm:flex sm:flex-wrap">
          <button type="button" onClick={onStart} className="rounded-xl bg-cyan-400 px-5 py-3 text-sm font-extrabold text-slate-950 shadow-lg shadow-cyan-500/20 transition hover:bg-cyan-300 focus:outline-none focus:ring-2 focus:ring-cyan-200 motion-reduce:transition-none">開始找房</button>
          <button type="button" onClick={onWorkspace} className="rounded-xl border border-white/25 bg-white/10 px-5 py-3 text-sm font-bold text-white transition hover:bg-white/15 focus:outline-none focus:ring-2 focus:ring-white/40 motion-reduce:transition-none">查看看房工作台</button>
          <button type="button" disabled={!reportReady} onClick={onReport} title={reportReady ? "查看決策報告" : "完成估價與分析後即可查看報告"} className="rounded-xl border border-white/15 px-5 py-3 text-sm font-bold text-slate-300 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-45 motion-reduce:transition-none">查看報告</button>
        </div>
        <p className="mt-3 text-[10px] text-slate-400">從預算與地區開始，最後得到可與家人或客戶討論的決策摘要。</p>
      </div>
      <div className="relative min-w-0 rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm">
        <div className="mb-4 flex items-center justify-between gap-3"><div><p className="text-[10px] font-bold tracking-wider text-cyan-200">DECISION FLOW</p><p className="mt-1 text-sm font-bold">五步完成看屋判斷</p></div><GuideMark /></div>
        <div className="relative grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-2">
          <div className="hero-flow-line pointer-events-none absolute left-4 right-4 top-1/2 hidden h-px bg-gradient-to-r from-transparent via-cyan-300/60 to-transparent sm:block motion-reduce:animate-none" />
          {flowNodes.map((node, index) => <div key={node} className="hero-sequence relative rounded-xl border border-white/10 bg-slate-900/80 px-3 py-3 shadow-sm motion-reduce:animate-none" style={{ animationDelay: `${index * 0.45}s` }}><div className="flex items-center gap-2"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-cyan-300/15 text-[10px] font-black text-cyan-200">{index + 1}</span><span className="text-xs font-bold text-slate-100">{node}</span></div></div>)}
        </div>
      </div>
    </div>
    <div className="relative mt-7 grid grid-cols-2 gap-2 border-t border-white/10 pt-5 text-center sm:grid-cols-5">
      {["Step 1 找房", "Step 2 估價", "Step 3 月付與持有成本", "Step 4 區位分析", "Step 5 風險總評與報告"].map((step) => <div key={step} className="rounded-lg bg-white/[0.05] px-2 py-2 text-[10px] font-bold text-slate-300">{step}</div>)}
    </div>
  </section>;
}

function GuideMark() {
  return <div className="flex items-center gap-2 rounded-xl border border-yellow-200/20 bg-yellow-300/10 px-2 py-1.5" aria-label="黃色看房助手導覽"><div className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-yellow-300"><span className="h-1.5 w-4 rounded-full bg-amber-800" /></div><span className="hidden text-[10px] font-bold text-yellow-100 sm:block">跟著流程往下走</span></div>;
}
