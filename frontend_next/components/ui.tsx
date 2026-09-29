import type { ReactNode } from "react";
import { AsyncState } from "@/components/design-system/async-state";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { Panel } from "@/components/design-system/section";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <Panel className={className}>{children}</Panel>;
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
  return <Panel className="p-4"><p className="text-label text-muted">{label}</p><div className="mt-2 text-kpi text-ink" data-numeric>{value}</div>{note && <p className="mt-1 text-helper">{note}</p>}</Panel>;
}

export function Button({ children, onClick, secondary = false, disabled = false, className = "" }: { children: ReactNode; onClick?: () => void; secondary?: boolean; disabled?: boolean; className?: string }) {
  return <CommercialButton type="submit" disabled={disabled} onClick={onClick} variant={secondary ? "secondary" : "primary"} className={className}>{children}</CommercialButton>;
}

export function Notice({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "error" | "warning" }) {
  return <Message variant={tone === "info" ? "information" : tone}>{children}</Message>;
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <AsyncState kind="not_started" title={title} detail={detail} />;
}
