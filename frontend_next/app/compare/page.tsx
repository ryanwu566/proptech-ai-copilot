import { Suspense } from "react";
import type { Metadata } from "next";
import { CompareView } from "@/components/evidence/evidence-entry";
export const metadata: Metadata = { title: "案件證據比較 | PropTech AI Copilot" };
export default function ComparePage() { return <Suspense fallback={<main aria-busy="true">正在開啟案件比較…</main>}><CompareView /></Suspense>; }
