"use client";
import Link from "next/link";
import type { SavedCase } from "@/lib/case-storage";
import { compareHref } from "@/lib/workspace/compare-selection";
import { useExperienceLocale } from "@/components/experience-locale-provider";
/** Legacy entry delegates to validated descriptive evidence comparison. */
export function CaseComparisonPanel({ selectedIds }: { savedCases: SavedCase[]; selectedIds: string[] }) {
  const { copy } = useExperienceLocale();
  return <section className="ds-panel"><p>以保存證據與假設逐項比較，不提供排名或推薦。</p><Link className="ds-button ds-button--primary" href={compareHref(selectedIds)}>{copy("case.compare")}</Link></section>;
}
