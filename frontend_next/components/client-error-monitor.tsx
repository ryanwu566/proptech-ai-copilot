"use client";

import { useEffect } from "react";
import { reportClientError } from "@/lib/client-error-reporting";

export function ClientErrorMonitor() {
  useEffect(() => {
    const onError = () => reportClientError("render_failure", "window-error");
    const onRejection = () => reportClientError("unhandled_rejection", "window-rejection");
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => { window.removeEventListener("error", onError); window.removeEventListener("unhandledrejection", onRejection); };
  }, []);
  return null;
}
