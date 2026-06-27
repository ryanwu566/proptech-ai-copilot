"use client";

import { useEffect, useState } from "react";

import { ViewingDecisionCard } from "@/components/viewing-decision-card";
import { buildViewingDecision, readStoredViewingAssessments, type ModuleAssessment, type ModuleSlug } from "@/lib/viewing-decision";

type ViewingDecisionReportCardProps = { assessmentId: string; moduleName: string; moduleSlug: ModuleSlug };

export function ViewingDecisionReportCard({ assessmentId, moduleName, moduleSlug }: ViewingDecisionReportCardProps) {
  const [assessments, setAssessments] = useState<ModuleAssessment[]>([]);

  useEffect(() => {
    const stored = readStoredViewingAssessments();
    if (stored.some((item) => item.moduleSlug === moduleSlug && String(item.assessmentId) === assessmentId)) {
      setAssessments(stored);
      return;
    }
    setAssessments([...stored, { assessmentId, moduleName, moduleSlug }]);
  }, [assessmentId, moduleName, moduleSlug]);

  return <ViewingDecisionCard decision={buildViewingDecision(assessments)} />;
}
