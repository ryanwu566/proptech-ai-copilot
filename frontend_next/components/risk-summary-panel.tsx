"use client";

import type { RiskSummary } from "@/lib/risk-summary";

const tones = {
  green: "border-emerald-300 bg-emerald-50 text-emerald-900",
  yellow: "border-amber-300 bg-amber-50 text-amber-900",
  red: "border-rose-300 bg-rose-50 text-rose-900",
  unknown: "border-slate-300 bg-slate-50 text-slate-700",
};

const lights = { green: "bg-emerald-500", yellow: "bg-amber-400", red: "bg-rose-500", unknown: "bg-slate-400" };

export function RiskSummaryPanel({ summary }: { summary: RiskSummary }) {
  return <section className="min-w-0 overflow-hidden rounded-xl border border-stone-200 bg-white" aria-label="風險總評">
    <div className={`border-b p-4 ${tones[summary.overallSignal]}`}>
      <div className="flex flex-wrap items-center gap-3"><span className={`h-12 w-12 shrink-0 rounded-full border-4 border-white shadow-md ${lights[summary.overallSignal]}`} /><div className="min-w-0 flex-1"><p className="text-[10px] font-bold tracking-wider">RULE-BASED RISK SUMMARY</p><h2 className="mt-1 text-lg font-extrabold">風險總評：{summary.overallLabel}</h2><p className="mt-1 text-xs leading-5">{summary.decisionSuggestion}</p></div><div className="rounded-lg bg-white/75 px-3 py-2 text-center"><p className="text-[10px]">總分</p><p className="text-xl font-black">{summary.overallScore ?? "—"}</p></div></div>
    </div>
    <div className="grid min-w-0 gap-3 p-4 md:grid-cols-2">
      <SummaryBlock title="開價合理性" items={[`${summary.priceReasonableness.label}：${summary.priceReasonableness.explanation}`]} />
      <SummaryBlock title="資料信心" items={[confidenceLabel(summary.dataConfidence)]} />
      <SummaryBlock title="主要加分因素" items={summary.positiveFactors.map((item) => `${item.title}：${item.message}`)} empty="尚無明確加分因素。" />
      <SummaryBlock title="主要風險因素" items={summary.riskFactors.map((item) => `${item.title}：${item.message}`)} empty="尚無明確高風險訊號。" />
      <SummaryBlock title="尚需補查" items={summary.missingChecks} empty="核心分析已完成，仍建議實地確認。" />
      <SummaryBlock title="下一步建議" items={summary.nextActions} empty="完成更多分析後會提供下一步建議。" />
    </div>
    <p className="border-t border-stone-100 px-4 py-3 text-[10px] leading-5 text-slate-500">本總評為規則式買房決策提醒，不代表正式鑑價、銀行核貸或投資建議。</p>
  </section>;
}

function SummaryBlock({ title, items, empty }: { title: string; items: string[]; empty?: string }) {
  const visible = items.length ? items : [empty ?? "尚未完成"];
  return <div className="min-w-0 rounded-lg bg-stone-50 p-3"><p className="text-xs font-bold text-slate-800">{title}</p><ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">{visible.map((item) => <li key={item} className="break-words">• {item}</li>)}</ul></div>;
}

function confidenceLabel(value: RiskSummary["dataConfidence"]) {
  return { high: "高：估價信心達 80 分且採官方資料。", medium: "中：估價信心達 60 分，仍需確認資料限制。", low: "低：估價信心偏低或含展示樣本。", unknown: "尚未完成估價，無法判斷資料信心。" }[value];
}
