import type { Metadata } from "next";
import { SavedCasesEntry } from "@/components/workspace/saved-cases-entry";

export const metadata: Metadata = { title: "已儲存案件 | PropTech AI Copilot", description: "開啟瀏覽器本機儲存的商用物件案件。" };

export default function SavedCasesPage() { return <SavedCasesEntry />; }
