"use client";
import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import type { AppPage } from "@/components/sidebar";
import { PRODUCT_ENTRIES } from "@/lib/navigation/model";
import { isPropertyWorkflow } from "@/lib/navigation/product-workflow";

/** Observe query-only Next links as well as native browser back/forward. */
export function HomeLocationObserver({ onTool, onWorkflow }: { onTool: (page: AppPage | null) => void; onWorkflow: (open: boolean) => void }) {
  const search = useSearchParams();
  const query = search.toString();
  useEffect(() => {
    const params = new URLSearchParams(query);
    const tool = params.get("tool");
    onTool(PRODUCT_ENTRIES.some((entry) => "tool" in entry && entry.tool === tool) ? tool as AppPage : null);
    onWorkflow(isPropertyWorkflow(query));
  }, [query, onTool, onWorkflow]);
  return null;
}
