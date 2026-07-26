import type { ReactNode } from "react";
import type { ValuationResult } from "@/lib/api";
import { getValuationDisplayState } from "@/lib/valuation-result-state";

export function ValuationResultBoundary({ result, children }: { result: ValuationResult; children: ReactNode }) {
  const state = getValuationDisplayState(result);
  if (state.kind === "available") return <>{children}</>;
  return <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm leading-6 text-amber-900" role="status">{state.message}</div>;
}
