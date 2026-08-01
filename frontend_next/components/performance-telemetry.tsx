"use client";

import { useEffect } from "react";

type MetricName = "LCP" | "CLS" | "INP" | "TTFB";

const enabled = process.env.NEXT_PUBLIC_PERFORMANCE_TELEMETRY === "true";
const sampled = enabled && Math.random() < 0.1;

function viewportClass(width: number) {
  if (width < 640) return "mobile";
  if (width < 1024) return "tablet";
  return "desktop";
}

function report(metric: MetricName, value: number) {
  if (!sampled || !Number.isFinite(value) || value < 0) return;
  const body = JSON.stringify({
    metric,
    value: Math.min(value, 120000),
    route: window.location.pathname,
    viewport_class: viewportClass(window.innerWidth),
    release_version: process.env.NEXT_PUBLIC_RELEASE_VERSION || "unknown",
    locale: document.documentElement.lang || "unknown",
    pilot_mode: "normal",
    device_class: "unknown",
    sampled: true,
  });
  const endpoint = `${process.env.NEXT_PUBLIC_API_BASE_URL || ""}/performance/metrics`;
  if (navigator.sendBeacon) {
    navigator.sendBeacon(endpoint, new Blob([body], { type: "application/json" }));
  }
}

export function PerformanceTelemetry() {
  useEffect(() => {
    if (!sampled || typeof PerformanceObserver === "undefined") return;
    const observers: PerformanceObserver[] = [];
    try {
      const lcp = new PerformanceObserver((list) => {
        const entry = list.getEntries().at(-1);
        if (entry) report("LCP", entry.startTime);
      });
      lcp.observe({ type: "largest-contentful-paint", buffered: true });
      observers.push(lcp);
    } catch { /* unsupported browser */ }
    try {
      const cls = new PerformanceObserver((list) => {
        const value = list.getEntries().reduce((total, entry) => total + ((entry as PerformanceEntry & { value?: number }).value || 0), 0);
        report("CLS", value);
      });
      cls.observe({ type: "layout-shift", buffered: true });
      observers.push(cls);
    } catch { /* unsupported browser */ }
    const navigation = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
    if (navigation) report("TTFB", navigation.responseStart);
    return () => observers.forEach((observer) => observer.disconnect());
  }, []);
  return null;
}
