"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";

const labels = {
  location: { "zh-TW": "顯示位置地圖", en: "Show location map", ja: "位置の地図を表示", ko: "위치 지도 표시" },
  risk: { "zh-TW": "顯示風險地圖", en: "Show risk map", ja: "リスク地図を表示", ko: "위험 지도 표시" },
  nearby: { "zh-TW": "顯示附近設施地圖", en: "Show nearby facilities map", ja: "周辺施設の地図を表示", ko: "주변 시설 지도 표시" },
};

/** Viewing saved evidence never loads external basemap tiles until the user asks (`open` is another explicit ask). */
export function ExplicitMap({ kind, children, open = false }: { kind: keyof typeof labels; children: ReactNode; open?: boolean }) {
  const [shown, setVisible] = useState(false);
  useEffect(() => { if (open) setVisible(true); }, [open]);
  const visible = shown || open;
  const { locale } = useExperienceLocale();
  return visible ? children : <div className="grid min-h-40 place-items-center p-6">
    <button type="button" className="ds-button ds-button--secondary" data-testid={`show-${kind}-map`} onClick={() => setVisible(true)}>{labels[kind][locale]}</button>
  </div>;
}
