"use client";

import { api } from "@/lib/api";

const ALLOWED_CODES = new Set(["render_failure", "unhandled_rejection", "network_failure", "pilot_submission_failure", "unsupported_browser"]);
let lastKey = "";
let lastAt = 0;

export function reportClientError(code: string, boundary: string): void {
  const safeCode = ALLOWED_CODES.has(code) ? code : "network_failure";
  const route = typeof window === "undefined" ? "unknown" : window.location.pathname.slice(0, 120);
  const key = `${safeCode}:${boundary}:${route}`;
  const now = Date.now();
  if (key === lastKey && now - lastAt < 30000) return;
  lastKey = key;
  lastAt = now;
  void api.reportClientError({ error_code: safeCode, route, boundary: boundary.slice(0, 40), pilot_mode: "normal" }).catch(() => undefined);
}
