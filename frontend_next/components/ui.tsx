import type { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-card ${className}`}>{children}</section>;
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
  return <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-bold ${tones[value] ?? "border-slate-200 bg-slate-100 text-slate-700"}`}><span className={`h-2 w-2 rounded-full ${dots[value] ?? "bg-slate-400"}`} />{value}</span>;
}

export function Metric({ label, value, note }: { label: string; value: ReactNode; note?: string }) {
  return <Card><p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</p><div className="mt-3 text-2xl font-bold text-ink">{value}</div>{note && <p className="mt-2 text-xs text-muted">{note}</p>}</Card>;
}

export function Button({ children, onClick, secondary = false, disabled = false }: { children: ReactNode; onClick?: () => void; secondary?: boolean; disabled?: boolean }) {
  return <button disabled={disabled} onClick={onClick} className={`rounded-xl px-4 py-2 text-sm font-bold transition disabled:cursor-not-allowed disabled:opacity-50 ${secondary ? "border border-slate-200 bg-white text-ink hover:bg-slate-50" : "bg-primary text-white hover:bg-blue-700"}`}>{children}</button>;
}

export function Notice({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "error" | "warning" }) {
  const tones = { info: "border-blue-200 bg-blue-50 text-blue-800", error: "border-rose-200 bg-rose-50 text-rose-800", warning: "border-amber-200 bg-amber-50 text-amber-800" };
  return <div className={`rounded-xl border px-4 py-3 text-sm ${tones[tone]}`}>{children}</div>;
}
