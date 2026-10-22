"use client";
import dynamic from "next/dynamic";

// Keep report builders and its Decision Room section on the Report route.
export const ReportView = dynamic(() => import("./report-view").then(module => module.ReportView));
