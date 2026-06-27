"use client";
import { useEffect, useState, type ReactNode } from "react";
import { useViewMode } from "@/lib/view-mode";

export function DetailDisclosure({ title = "查看詳細資料", children, className = "" }: { title?: string; children: ReactNode; className?: string }) {
  const [viewMode] = useViewMode();
  const [open, setOpen] = useState(viewMode === "pro");
  useEffect(() => setOpen(viewMode === "pro"), [viewMode]);
  return <details open={open} onToggle={(event) => setOpen(event.currentTarget.open)} className={`min-w-0 rounded-xl border border-stone-200 bg-white ${className}`}>
    <summary className="cursor-pointer px-3 py-2.5 text-xs font-bold text-slate-700">{title}<span className="ml-2 text-[9px] font-normal text-slate-400">{viewMode === "pro" ? "專業模式預設展開" : "新手模式預設收合"}</span></summary>
    <div className="min-w-0 border-t border-stone-100 p-3">{children}</div>
  </details>;
}
