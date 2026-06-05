import type { ReactNode } from "react";
import { Badge, Button } from "@/components/ui";

export function PageHeader({ kicker, title, description, action }: { kicker?: string; title: string; description: string; action?: ReactNode }) {
  return <div className="flex flex-wrap items-end justify-between gap-4">
    <div>{kicker && <p className="text-[10px] font-bold tracking-[0.14em] text-cyan-700">{kicker}</p>}<h1 className="mt-1 text-[28px] font-bold tracking-[-0.025em] text-slate-950">{title}</h1><p className="mt-1.5 max-w-3xl text-sm leading-6 text-slate-500">{description}</p></div>{action}
  </div>;
}

export function DecisionHero({ onPrimary, onSecondary }: { onPrimary: () => void; onSecondary: () => void }) {
  return <section className="grid min-w-0 overflow-hidden rounded-2xl border border-stone-200 bg-[#fffdf8] shadow-[0_12px_35px_rgba(71,85,105,0.08)] lg:grid-cols-[minmax(0,3fr)_minmax(340px,2fr)]">
    <div className="flex min-w-0 flex-col justify-center px-5 py-6 sm:px-7 sm:py-7 lg:px-9">
      <p className="text-[11px] font-bold tracking-[0.16em] text-cyan-700">房地產案件決策工作台</p>
      <h1 className="mt-3 max-w-2xl break-words text-[28px] font-bold leading-[1.18] tracking-[-0.035em] text-slate-950 sm:text-[34px]">今天要判斷哪一筆交易風險？</h1>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">用 TaxOracle 先完成稅務快篩，再用地圖與區域資料補強客戶說明。</p>
      <div className="mt-5 flex flex-col gap-2.5 sm:flex-row sm:flex-wrap">
        <button onClick={onPrimary} className="w-full rounded-lg bg-slate-900 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-cyan-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 sm:w-auto">開始稅務快篩 →</button>
        <button onClick={onSecondary} className="w-full rounded-lg border border-stone-300 bg-white px-5 py-3 text-sm font-bold text-slate-700 transition hover:border-cyan-300 hover:text-cyan-800 sm:w-auto">查看區域地圖</button>
      </div>
      <div className="mt-5 flex flex-wrap gap-2"><HeroPill text="Mock Data" /><HeroPill text="TX001–TX009" /><HeroPill text="客戶溝通報告" /></div>
    </div>
    <CasePreviewVisual />
  </section>;
}

function HeroPill({ text }: { text: string }) {
  return <span className="rounded-full border border-stone-200 bg-white px-3 py-1 text-[10px] font-bold text-slate-500">{text}</span>;
}

function CasePreviewVisual() {
  return <div className="relative min-h-[260px] overflow-hidden border-t border-stone-200 bg-[#eaf2ef] p-5 lg:border-l lg:border-t-0">
    <MiniMap />
    <div className="relative z-10 flex h-full flex-col justify-between rounded-xl border border-white/80 bg-white/88 p-4 shadow-[0_12px_30px_rgba(15,23,42,0.12)] backdrop-blur-sm">
      <div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-bold tracking-wider text-slate-400">目前預覽案件</p><h2 className="mt-1 text-base font-bold text-slate-950">大安區自住換屋案</h2><p className="mt-1 text-xs text-slate-500">和平東路二段 · DEMO-LOW</p></div><Badge value="eligible" /></div>
      <div className="my-4 grid grid-cols-3 gap-2"><PreviewMetric label="稅務風險" value="12" /><PreviewMetric label="生活機能" value="86" /><PreviewMetric label="文件狀態" value="齊備" /></div>
      <div className="flex items-center justify-between border-t border-stone-200 pt-3 text-xs"><span className="font-semibold text-slate-500">客戶溝通報告</span><span className="font-bold text-emerald-700">可產生 HTML</span></div>
    </div>
  </div>;
}

function MiniMap() {
  return <div aria-hidden className="absolute inset-0 opacity-55">
    <div className="absolute left-[14%] top-[-10%] h-[130%] w-8 rotate-[18deg] bg-white/70" />
    <div className="absolute left-[53%] top-[-10%] h-[130%] w-5 -rotate-[12deg] bg-white/60" />
    <div className="absolute left-[-10%] top-[33%] h-7 w-[130%] -rotate-[4deg] bg-white/70" />
    <div className="absolute left-[-10%] top-[72%] h-5 w-[130%] rotate-[6deg] bg-white/60" />
    <span className="absolute left-[22%] top-[25%] h-2.5 w-2.5 rounded-full bg-cyan-600 ring-4 ring-white/80" /><span className="absolute right-[19%] top-[18%] h-2 w-2 rounded-full bg-amber-500 ring-4 ring-white/80" /><span className="absolute bottom-[17%] left-[45%] h-2 w-2 rounded-full bg-emerald-500 ring-4 ring-white/80" />
  </div>;
}

function PreviewMetric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg bg-stone-50 px-2.5 py-2"><p className="text-[9px] text-slate-400">{label}</p><p className="mt-1 text-xs font-bold text-slate-800">{value}</p></div>;
}

export function CaseCard({ title, status, signal, description, selected, onSelect, onOpen }: { title: string; status: string; signal: string; description: string; selected?: boolean; onSelect: () => void; onOpen: () => void }) {
  const accent = signal === "green" ? "bg-emerald-500" : signal === "yellow" ? "bg-amber-500" : "bg-rose-500";
  const labels: Record<string, string> = { eligible: "可行", manual_review: "需複核", not_eligible: "高風險" };
  return <article onClick={onSelect} className={`relative cursor-pointer overflow-hidden rounded-xl border bg-white p-4 transition ${selected ? "border-cyan-500 shadow-[0_8px_24px_rgba(8,145,178,0.12)] ring-2 ring-cyan-100" : "border-stone-200 hover:border-stone-300 hover:shadow-sm"}`}>
    <span className={`absolute inset-y-0 left-0 w-1 ${accent}`} />
    <div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-bold tracking-wider text-slate-400">展示案件</p><h3 className="mt-1 text-sm font-bold text-slate-950">{title}</h3></div><StatusBadge value={signal} /></div>
    <p className="mt-3 text-xs leading-5 text-slate-500">{description}</p>
    <div className="mt-3 flex items-center justify-between border-t border-stone-100 pt-3"><span className="text-[11px] font-bold text-slate-500">{labels[status] ?? status}</span><button onClick={(event) => { event.stopPropagation(); onOpen(); }} className="rounded-md bg-slate-900 px-3 py-1.5 text-[11px] font-bold text-white hover:bg-cyan-800">載入案例</button></div>
  </article>;
}

export function ModuleTile({ title, description, onClick, tone = "cyan", hint }: { title: string; description: string; onClick: () => void; tone?: "cyan" | "green" | "amber" | "violet"; hint: string }) {
  const tones = { cyan: "from-cyan-50 text-cyan-800", green: "from-emerald-50 text-emerald-800", amber: "from-amber-50 text-amber-800", violet: "from-violet-50 text-violet-800" };
  return <button onClick={onClick} className={`group min-h-32 overflow-hidden rounded-xl border border-stone-200 bg-gradient-to-br ${tones[tone]} to-white p-4 text-left transition hover:-translate-y-0.5 hover:border-stone-300 hover:shadow-sm`}>
    <div className="flex items-center justify-between"><span className="text-[10px] font-bold tracking-wider opacity-65">{hint}</span><span className="text-sm transition group-hover:translate-x-1">→</span></div><h3 className="mt-7 text-sm font-bold text-slate-950">{title}</h3><p className="mt-1 text-xs leading-5 text-slate-500">{description}</p>
  </button>;
}

export function StatusBadge({ value }: { value: string }) { return <Badge value={value} />; }

export function MetricTile({ label, value, note }: { label: string; value: ReactNode; note?: string }) {
  return <div className="rounded-xl border border-stone-200 bg-white px-4 py-3"><p className="text-xs font-semibold text-slate-500">{label}</p><div className="mt-1 text-2xl font-bold text-slate-950">{value}</div>{note && <p className="mt-1 text-xs text-slate-400">{note}</p>}</div>;
}

export function SectionCard({ title, description, children, className = "" }: { title?: string; description?: string; children: ReactNode; className?: string }) {
  return <section className={`rounded-xl border border-stone-200 bg-white ${className}`}>{title && <div className="border-b border-stone-100 px-4 py-3.5"><h2 className="font-bold text-slate-950">{title}</h2>{description && <p className="mt-1 text-xs text-slate-500">{description}</p>}</div>}<div className="p-4">{children}</div></section>;
}

export function ResultSummaryPanel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-[0_12px_35px_rgba(71,85,105,0.09)] ${className}`}>{children}</section>;
}

export function ErrorState({ message }: { message: string }) { return <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{message}</div>; }
export function LoadingState({ label = "資料載入中..." }: { label?: string }) { return <div className="flex min-h-32 items-center justify-center rounded-xl border border-dashed border-stone-300 bg-white/60 text-sm text-slate-500">{label}</div>; }
