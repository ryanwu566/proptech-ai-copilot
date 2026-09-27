"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";
import type { ValuationResult } from "@/lib/api";
import { getValuationDisplayState } from "@/lib/valuation-result-state";

const fallbackClass = "rounded-xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm leading-6 text-amber-900";

export function ValuationResultBoundary({ result, children }: { result: ValuationResult; children: ReactNode }) {
  const state = getValuationDisplayState(result);
  if (state.kind === "available") return <>{children}</>;
  return <div className={fallbackClass} role={state.kind === "error" ? "alert" : "status"}>{state.message}</div>;
}

export class ValuationRenderErrorBoundary extends Component<{ children: ReactNode; message?: string }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo) {
    // Keep unexpected valuation rendering failures inside this section.
  }

  render() {
    if (this.state.failed) {
      return <div className={fallbackClass} role="alert">{this.props.message ?? "估價結果暫時無法顯示，其他功能仍可繼續使用。"}</div>;
    }
    return this.props.children;
  }
}
