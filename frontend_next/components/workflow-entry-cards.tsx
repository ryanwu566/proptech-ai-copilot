"use client";

type WorkflowEntryCardsProps = {
  onStartBuying: () => void;
  onOpenTax: () => void;
  onOpenAdvanced: () => void;
  onGuidedDemo: () => void;
  onOpenCompare: () => void;
};

const entries = [
  { key: "buying", eyebrow: "從自己的條件開始", title: "我想判斷一間房值不值得看", description: "輸入地點、預算與坪數，一步一步產生看屋決策報告。", action: "開始我的看屋初篩", primary: true },
  { key: "demo", eyebrow: "懶得輸入？先看示範", title: "我想快速看一次示範", description: "用台北市大安區示範條件，實際跑完整分析流程。", action: "跑一次示範流程", primary: false },
  { key: "compare", eyebrow: "已經有幾個選項", title: "我想比較幾個候選物件", description: "保存 2 個以上案件後，比較價格、月付、區位與風險。", action: "查看最近案件與比較", primary: false },
] as const;

export function WorkflowEntryCards({ onStartBuying, onOpenTax, onOpenAdvanced, onGuidedDemo, onOpenCompare }: WorkflowEntryCardsProps) {
  const actions = { buying: onStartBuying, demo: onGuidedDemo, compare: onOpenCompare };
  return <section aria-label="選擇你現在想完成的事情" className="space-y-4">
    <div><p className="text-[10px] font-bold tracking-[0.18em] text-cyan-700">你現在想做什麼？</p><h2 className="mt-1 text-xl font-extrabold text-slate-950">選一個最接近你目前狀況的入口</h2></div>
    <div className="grid gap-4 lg:grid-cols-3">
      {entries.map((entry) => <article key={entry.key} className={`flex min-w-0 flex-col rounded-2xl border p-5 shadow-sm ${entry.primary ? "border-cyan-300 bg-gradient-to-br from-cyan-950 to-slate-900 text-white" : "border-stone-200 bg-white text-slate-950"}`}>
        <p className={`text-[10px] font-bold tracking-[0.18em] ${entry.primary ? "text-cyan-200" : "text-cyan-700"}`}>{entry.eyebrow}</p>
        <h3 className="mt-2 text-lg font-extrabold">{entry.title}</h3>
        <p className={`mt-2 flex-1 text-sm leading-6 ${entry.primary ? "text-slate-200" : "text-slate-600"}`}>{entry.description}</p>
        <button type="button" onClick={actions[entry.key]} className={`mt-5 w-full rounded-xl px-4 py-3 text-sm font-bold transition ${entry.primary ? "bg-cyan-400 text-slate-950 hover:bg-cyan-300" : "border border-stone-200 bg-stone-50 text-slate-800 hover:border-cyan-300 hover:bg-cyan-50"}`}>{entry.action}</button>
      </article>)}
    </div>
    <div className="flex flex-col gap-2 rounded-xl border border-stone-200 bg-stone-50 p-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-xs text-slate-600">其他需求可以晚一點再做，不會影響看屋初篩流程。</p>
      <div className="flex flex-col gap-2 sm:flex-row">
        <button type="button" onClick={onOpenTax} className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs font-bold text-slate-700">我要做稅務快篩</button>
        <button type="button" onClick={onOpenAdvanced} className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs font-bold text-slate-700">我要看更多工具</button>
      </div>
    </div>
  </section>;
}
