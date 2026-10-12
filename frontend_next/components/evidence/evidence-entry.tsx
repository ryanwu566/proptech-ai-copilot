"use client";
import dynamic from "next/dynamic";
// One shared client boundary keeps local repository/projection code shared across E9 entry routes.
export { CompareView } from "./compare-view";
export { ReportView } from "./report-view";
export { SavedCasesEntry } from "../workspace/saved-cases-entry";
export { OverviewView } from "../workspace/overview/overview-view";
export { MarketPriceView } from "../workspace/market/market-price-view";
export { CaseRouteLayout } from "../workspace/case-route-layout";

// Share workspace dependencies, but download the editor only on route entry.
export const ScenarioLabEntry = dynamic(() => import("../workspace/scenarios/scenario-lab").then(module => module.ScenarioLab));
