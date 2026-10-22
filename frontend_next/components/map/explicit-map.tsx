"use client";

import { useState, type ReactNode } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";

const labels = {
  location: { "zh-TW": "顯示位置地圖", en: "Show location map", ja: "位置の地図を表示", ko: "위치 지도 표시" },
  risk: { "zh-TW": "顯示風險地圖", en: "Show risk map", ja: "リスク地図を表示", ko: "위험 지도 표시" },
};

/** Viewing saved evidence never loads external basemap tiles until the user asks. */
export function ExplicitMap({ kind, children }: { kind: keyof typeof labels; children: ReactNode }) {
  const [visible, setVisible] = useState(false);
  const { locale } = useExperienceLocale();
  return visible ? children : <div className="grid min-h-40 place-items-center p-6">
    <button type="button" className="ds-button ds-button--secondary" data-testid={`show-${kind}-map`} onClick={() => setVisible(true)}>{labels[kind][locale]}</button>
  </div>;
}
