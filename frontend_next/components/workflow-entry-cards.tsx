"use client";

type WorkflowEntryCardsProps = {
  onStartBuying: () => void;
  onOpenTax: () => void;
  onOpenAdvanced: () => void;
  onGuidedDemo: () => void;
};

const entries = [
  { key: "buying", eyebrow: "主要流程", title: "開始看房分析", description: "從找房、估價與成本，一步一步完成看屋決策報告。", action: "開始 7 步分析", primary: true },
  { key: "tax", eyebrow: "補充檢查", title: "稅務快篩", description: "直接進入 TaxOracle，檢查交易條件與規則原因。", action: "進行稅務快篩", primary: false },
  { key: "advanced", eyebrow: "需要時使用", title: "進階工具", description: "展開 Map Insight、GeoMap、行情與資料狀態等補充工具。", action: "展開進階工具", primary: false },
] as const;

export function WorkflowEntryCards({ onStartBuying, onOpenTax, onOpenAdvanced, onGuidedDemo }: WorkflowEntryCardsProps) {
  const actions = { buying: onStartBuying, tax: onOpenTax, advanced: onOpenAdvanced };
  return <section aria-label="首頁流程入口" className="grid gap-4 lg:grid-cols-3">
    {entries.map((entry) => <article key={entry.key} className={`flex min-w-0 flex-col rounded-2xl border p-5 shadow-sm ${entry.primary ? "border-cyan-300 bg-gradient-to-br from-cyan-950 to-slate-900 text-white" : "border-stone-200 bg-white text-slate-950"}`}>
      <p className={`text-[10px] font-bold tracking-[0.18em] ${entry.primary ? "text-cyan-200" : "text-cyan-700"}`}>{entry.eyebrow}</p>
      <h2 className="mt-2 text-xl font-extrabold">{entry.title}</h2>
      <p className={`mt-2 flex-1 text-sm leading-6 ${entry.primary ? "text-slate-200" : "text-slate-600"}`}>{entry.description}</p>
      <button type="button" onClick={actions[entry.key]} className={`mt-5 w-full rounded-xl px-4 py-3 text-sm font-bold transition ${entry.primary ? "bg-cyan-400 text-slate-950 hover:bg-cyan-300" : "border border-stone-200 bg-stone-50 text-slate-800 hover:border-cyan-300 hover:bg-cyan-50"}`}>{entry.action}</button>
    </article>)}
    <article className="min-w-0 rounded-2xl border border-violet-200 bg-gradient-to-r from-violet-50 to-cyan-50 p-5 shadow-sm lg:col-span-3"><div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-[10px] font-bold tracking-[0.18em] text-violet-700">GUIDED DEMO</p><h2 className="mt-1 text-lg font-extrabold text-slate-950">快速 Demo：一鍵跑完整流程</h2><p className="mt-2 text-sm leading-6 text-slate-600">用大安區示範條件，實際呼叫 API 跑完找房、估價、貸款、持有成本、區位與風險總評。</p></div><button type="button" onClick={onGuidedDemo} className="w-full rounded-xl bg-violet-700 px-5 py-3 text-sm font-bold text-white hover:bg-violet-800 sm:w-auto">一鍵跑完整流程</button></div></article>
  </section>;
}
