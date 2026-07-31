"use client";

import { useExperienceLocale } from "@/components/experience-locale-provider";

export function HelpCallout({ children }: { children: string }) {
  const { locale } = useExperienceLocale();
  const prefix = {
    "zh-TW": "這頁怎麼用：",
    en: "How to use:",
    ja: "このページの使い方：",
    ko: "이 페이지 사용법:",
  }[locale];
  return <aside aria-label={prefix} className="flex items-start gap-2.5 rounded-xl border border-cyan-100 bg-cyan-50/65 px-3.5 py-2.5 text-xs leading-5 text-slate-600"><span aria-hidden="true" className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-white text-[10px] font-bold text-cyan-700 shadow-sm">?</span><div><span className="font-bold text-slate-700">{prefix}</span> {children}</div></aside>;
}
