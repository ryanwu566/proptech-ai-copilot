"use client";

export function PropertyGuideMascot({ stage }: { stage: "start" | "finder" | "valuation" | "loan" | "location" | "complete" }) {
  const messages = {
    start: "先用預算和地區找可負擔路段。",
    finder: "可以把推薦路段帶入估價，確認合理價格。",
    valuation: "下一步建議試算月付，看是否符合收入。",
    loan: "月付之外，還要加管理費、稅費與修繕。",
    location: "區位分數高也要實地確認交通噪音與環境。",
    complete: "可以匯出報告給家人或客戶討論。",
  };
  return <div className="flex min-w-0 items-center gap-3 rounded-xl border border-amber-300 bg-gradient-to-br from-yellow-50 to-amber-100 p-3 shadow-md ring-2 ring-yellow-200/70" aria-label="黃色看房助手" role="status">
    <div className="relative grid h-12 w-12 shrink-0 place-items-center rounded-[18px] bg-yellow-300 shadow-sm">
      <span className="absolute left-3 top-4 h-2 w-2 rounded-full bg-slate-800" /><span className="absolute right-3 top-4 h-2 w-2 rounded-full bg-slate-800" />
      <span className="mt-4 h-1.5 w-5 rounded-full bg-amber-700" />
      <span className="absolute -bottom-1 left-2 h-3 w-2 rounded-full bg-yellow-400" /><span className="absolute -bottom-1 right-2 h-3 w-2 rounded-full bg-yellow-400" />
    </div>
    <div className="min-w-0"><p className="text-xs font-extrabold tracking-wider text-amber-800">黃色看房助手</p><p className="mt-1 text-xs font-medium leading-5 text-slate-700">{messages[stage]}</p></div>
  </div>;
}
