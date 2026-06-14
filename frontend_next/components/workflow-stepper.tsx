const steps = [
  ["01", "選案", "載入案件情境"],
  ["02", "稅務快篩", "檢核 TX001–TX009"],
  ["03", "原因追蹤", "確認風險與補件"],
  ["04", "報告輸出", "產生客戶溝通報告"],
];

export function WorkflowStepper({ activeStep = 1 }: { activeStep?: number }) {
  return <div className="flex flex-col gap-2 rounded-xl border border-stone-200 bg-white px-4 py-3 md:flex-row md:items-center md:gap-0">
    {steps.map(([number, title, detail], index) => { const step=index+1,active=step===activeStep,done=step<activeStep; return <div key={number} className="flex min-w-0 flex-1 items-center">
      <div className={`flex min-w-0 items-center gap-2.5 rounded-lg px-2 py-1.5 ${active?"bg-cyan-50 ring-2 ring-cyan-100":""}`}><span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-[9px] font-bold ${done?"border-emerald-300 bg-emerald-100 text-emerald-800":active?"border-cyan-500 bg-cyan-700 text-white":"border-stone-200 bg-stone-50 text-slate-400"}`}>{done?"✓":number}</span><div className="min-w-0"><h3 className={`text-xs font-bold ${active?"text-cyan-900":"text-slate-800"}`}>{title}</h3><p className="truncate text-[9px] text-slate-400">{detail}</p></div></div>
      {index < steps.length - 1 && <div className="mx-3 hidden h-px flex-1 bg-gradient-to-r from-cyan-200 to-stone-200 md:block" />}
    </div>;})}
  </div>;
}
