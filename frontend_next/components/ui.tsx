import type { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-xl border border-slate-200 bg-white p-5 shadow-card ${className}`}>{children}</section>;
}

export function Badge({ value }: { value: string }) {
  const tones: Record<string, string> = {
    green: "border-emerald-200 bg-emerald-100 text-emerald-800",
    yellow: "border-amber-200 bg-amber-100 text-amber-800",
    red: "border-rose-200 bg-rose-100 text-rose-800",
    eligible: "border-emerald-200 bg-emerald-100 text-emerald-800",
    manual_review: "border-amber-200 bg-amber-100 text-amber-800",
    not_eligible: "border-rose-200 bg-rose-100 text-rose-800",
  };
  const dots: Record<string, string> = {
    green: "bg-emerald-500", yellow: "bg-amber-500", red: "bg-rose-500",
    eligible: "bg-emerald-500", manual_review: "bg-amber-500", not_eligible: "bg-rose-500",
  };
  const labels: Record<string, string> = {
    green: "低風險", yellow: "需留意", red: "高風險",
    eligible: "符合資格", manual_review: "人工複核", not_eligible: "不符合資格",
    passed: "通過", manual_review_required: "人工複核", failed: "未通過",
  };
  return <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-bold ${tones[value] ?? "border-slate-200 bg-slate-100 text-slate-700"}`}><span className={`h-1.5 w-1.5 rounded-full ${dots[value] ?? "bg-slate-400"}`} />{labels[value] ?? value}</span>;
}

export function Metric({ label, value, note }: { label: string; value: ReactNode; note?: string }) {
  return <Card className="p-4"><p className="text-xs font-semibold text-slate-500">{label}</p><div className="mt-2 text-2xl font-bold tracking-tight text-ink">{value}</div>{note && <p className="mt-1 text-xs leading-5 text-muted">{note}</p>}</Card>;
}

export function Button({ children, onClick, secondary = false, disabled = false, className = "" }: { children: ReactNode; onClick?: () => void; secondary?: boolean; disabled?: boolean; className?: string }) {
  return <button disabled={disabled} onClick={onClick} className={`inline-flex items-center justify-center rounded-lg px-4 py-2.5 text-sm font-bold transition focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${secondary ? "border border-slate-300 bg-white text-ink hover:bg-slate-50" : "bg-slate-950 text-white hover:bg-cyan-800"} ${className}`}>{children}</button>;
}

export function Notice({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "error" | "warning" }) {
  const tones = { info: "border-blue-200 bg-blue-50 text-blue-800", error: "border-rose-200 bg-rose-50 text-rose-800", warning: "border-amber-200 bg-amber-50 text-amber-800" };
  return <div className={`rounded-lg border px-4 py-3 text-sm ${tones[tone]}`}>{children}</div>;
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="flex min-h-40 flex-col items-center justify-center border border-dashed border-slate-300 bg-slate-50/70 px-6 text-center"><div className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-sm shadow-sm">→</div><h3 className="mt-3 font-bold text-slate-800">{title}</h3><p className="mt-1 max-w-sm text-sm leading-6 text-muted">{detail}</p></div>;
}
