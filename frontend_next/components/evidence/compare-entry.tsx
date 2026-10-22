"use client";
import dynamic from "next/dynamic";

// Keep comparison builders on the Compare route, outside shared case entries.
export const CompareView = dynamic(() => import("./compare-view").then(module => module.CompareView));
