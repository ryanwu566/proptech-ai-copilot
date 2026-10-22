"use client";
import dynamic from "next/dynamic";
// One shared client boundary keeps local repository/projection code shared across E9 entry routes.
// /cases imports SavedCasesEntry directly; keep its Cloud/Auth modules off evidence routes.
export { OverviewView } from "../workspace/overview/overview-view";
export { MarketPriceView } from "../workspace/market/market-price-view";
export { CaseRouteLayout } from "../workspace/case-route-layout";

// Share workspace dependencies, but download the editor only on route entry.
export const ScenarioLabEntry = dynamic(() => import("../workspace/scenarios/scenario-lab").then(module => module.ScenarioLab));
// Report and Compare are single-route views: their builders, copy and the report's Decision Room
// section download on their own route instead of with every case page.
export const ReportView = dynamic(() => import("./report-view").then(module => module.ReportView));
export const CompareView = dynamic(() => import("./compare-view").then(module => module.CompareView));
