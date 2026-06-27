export type ModuleSlug = "tax-oracle" | "aegis-credit" | "lex-prop";

export type AssessmentResult = {
  risk_level: "low" | "medium" | "high";
  score?: number;
  summary?: string;
  recommendations?: string[];
};

export type ModuleAssessment = {
  moduleSlug: ModuleSlug;
  moduleName?: string;
  assessmentId?: number | string;
  result?: AssessmentResult | null;
};

export type ViewingDecisionStatus = "continue_viewing" | "needs_more_information" | "clarify_risk_first";

export type ViewingDecision = {
  status: ViewingDecisionStatus;
  label: string;
  completedItems: string[];
  knownReminders: string[];
  missingChecks: string[];
  nextAction: { label: string; href: string };
  basis: string;
};

export const VIEWING_DECISION_STORAGE_KEY = "propguard:viewing-decision:v1";

const zh = (codes: number[]) => String.fromCodePoint(...codes);

const COPY = {
  continueLabel: zh([0x53ef,0x4ee5,0x7e7c,0x7e8c,0x770b,0x623f,0xff0f,0x503c,0x5f97,0x9032,0x4e00,0x6b65,0x6838,0x5c0d]),
  needsLabel: zh([0x9700,0x8981,0x88dc,0x8cc7,0x6599,0x6216,0x5148,0x78ba,0x8a8d]),
  clarifyLabel: zh([0x5efa,0x8b70,0x5148,0x91d0,0x6e05,0x98a8,0x96aa,0x518d,0x5b89,0x6392]),
  tax: zh([0x7a05,0x8cbb]),
  credit: zh([0x8cb8,0x6b3e,0x53ef,0x884c,0x6027]),
  lex: zh([0x6cd5,0x898f,0xff0f,0x6587,0x4ef6,0x98a8,0x96aa]),
  noData: zh([0x8cc7,0x6599,0x4e0d,0x8db3,0xff0c,0x5c1a,0x7121,0x6cd5,0x5f62,0x6210,0x6574,0x9ad4,0x770b,0x623f,0x5efa,0x8b70,0x3002]),
  notLowRisk: zh([0x8cc7,0x6599,0x4e0d,0x8db3,0xff0c,0x4e0d,0x6703,0x8996,0x70ba,0x4f4e,0x98a8,0x96aa,0x3002]),
  firstTax: zh([0x5148,0x5b8c,0x6210,0x7a05,0x8cbb,0x521d,0x6b65,0x6aa2,0x67e5]),
  highRiskSuffix: zh([0x986f,0x793a,0x9ad8,0x98a8,0x96aa,0xff0c,0x5efa,0x8b70,0x5148,0x78ba,0x8a8d,0x539f,0x56e0,0x8207,0x88dc,0x4ef6,0x9700,0x6c42,0x3002]),
  backTo: zh([0x56de,0x5230]),
  resultCheck: zh([0x7d50,0x679c,0x78ba,0x8a8d]),
  noGuess: zh([0x6839,0x64da,0x76ee,0x524d,0x5df2,0x5b8c,0x6210,0x7d50,0x679c,0x6574,0x7406,0xff1b,0x6c92,0x6709,0x63a8,0x8ad6,0x672a,0x5b8c,0x6210,0x9805,0x76ee,0x3002]),
  partial: zh([0x76ee,0x524d,0x5df2,0x5b8c,0x6210,0x90e8,0x5206,0x5206,0x6790,0xff0c,0x4f46,0x4ecd,0x7f3a,0x5c11,0x5176,0x4ed6,0x770b,0x623f,0x524d,0x6aa2,0x67e5,0x3002]),
  next: zh([0x4e0b,0x4e00,0x6b65,0xff1a,0x5b8c,0x6210]),
  assessment: zh([0x8a55,0x4f30]),
  reviewReports: zh([0x67e5,0x770b,0x5df2,0x5b8c,0x6210,0x5831,0x544a,0x4e26,0x88dc,0x5145,0x4f50,0x8b49]),
  missingBasis: zh([0x7f3a,0x5c11,0x7684,0x6aa2,0x67e5,0x4ecd,0x9700,0x88dc,0x9f4a,0x3002]),
  readyReminder: zh([0x76ee,0x524d,0x5df2,0x5b8c,0x6210,0x7684,0x4e09,0x9805,0x6aa2,0x67e5,0x6c92,0x6709,0x51fa,0x73fe,0x9ad8,0x98a8,0x96aa,0x8a0a,0x865f,0x3002]),
  verifyBeforeViewing: zh([0x770b,0x5c4b,0x524d,0x4ecd,0x5efa,0x8b70,0x6838,0x5c0d,0x6b0a,0x72c0,0x3001,0x5c4b,0x6cc1,0x3001,0x8cb8,0x6b3e,0x689d,0x4ef6,0x8207,0x73fe,0x5834,0x72c0,0x6cc1,0x3002]),
  homeNext: zh([0x56de,0x9996,0x9801,0x6574,0x7406,0x4e0b,0x4e00,0x500b,0x7269,0x4ef6]),
  notOverall: zh([0x53ea,0x6839,0x64da,0x5df2,0x5b8c,0x6210,0x7684,0x4e09,0x9805,0x6a21,0x7d44,0x7d50,0x679c,0x6574,0x7406,0xff0c,0x4e0d,0x4ee3,0x8868,0x5168,0x9762,0x5224,0x5b9a,0x3002]),
};

export const MODULE_LABELS: Record<ModuleSlug, string> = {
  "tax-oracle": COPY.tax,
  "aegis-credit": COPY.credit,
  "lex-prop": COPY.lex,
};

const MODULE_ORDER: ModuleSlug[] = ["tax-oracle", "aegis-credit", "lex-prop"];

export function buildViewingDecision(assessments: ModuleAssessment[]): ViewingDecision {
  const byModule = new Map<ModuleSlug, ModuleAssessment>();
  for (const assessment of assessments) byModule.set(assessment.moduleSlug, assessment);

  const completedItems = MODULE_ORDER.filter((slug) => byModule.has(slug)).map((slug) => MODULE_LABELS[slug]);
  const missingChecks = MODULE_ORDER.filter((slug) => !byModule.has(slug)).map((slug) => MODULE_LABELS[slug]);
  const highRisk = assessments.find((item) => item.result?.risk_level === "high");
  const mediumRiskItems = assessments.filter((item) => item.result?.risk_level === "medium");
  const knownReminders = buildKnownReminders(assessments);

  if (assessments.length === 0) {
    return { status: "needs_more_information", label: COPY.needsLabel, completedItems: [], knownReminders: [COPY.noData], missingChecks, nextAction: { label: COPY.firstTax, href: "/tax-oracle" }, basis: COPY.notLowRisk };
  }
  if (highRisk) {
    const label = MODULE_LABELS[highRisk.moduleSlug];
    return { status: "clarify_risk_first", label: COPY.clarifyLabel, completedItems, knownReminders: [`${label} ${COPY.highRiskSuffix}`, ...knownReminders.slice(0, 2)], missingChecks, nextAction: { label: `${COPY.backTo}${label}${COPY.resultCheck}`, href: moduleHref(highRisk.moduleSlug) }, basis: COPY.noGuess };
  }
  if (missingChecks.length > 0 || mediumRiskItems.length > 0) {
    const nextMissing = MODULE_ORDER.find((slug) => !byModule.has(slug));
    return { status: "needs_more_information", label: COPY.needsLabel, completedItems, knownReminders: knownReminders.length ? knownReminders.slice(0, 3) : [COPY.partial], missingChecks, nextAction: nextMissing ? { label: `${COPY.next}${MODULE_LABELS[nextMissing]}${COPY.assessment}`, href: moduleHref(nextMissing) } : { label: COPY.reviewReports, href: "/" }, basis: COPY.missingBasis };
  }
  return { status: "continue_viewing", label: COPY.continueLabel, completedItems, knownReminders: [COPY.readyReminder, COPY.verifyBeforeViewing], missingChecks: [], nextAction: { label: COPY.homeNext, href: "/" }, basis: COPY.notOverall };
}

export function mergeStoredAssessment(assessments: ModuleAssessment[], nextAssessment: ModuleAssessment) {
  const sanitized = sanitizeModuleAssessment(nextAssessment);
  if (!sanitized) return assessments;
  return [...assessments.filter((item) => item.moduleSlug !== sanitized.moduleSlug), sanitized];
}

export function readStoredViewingAssessments(): ModuleAssessment[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(VIEWING_DECISION_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const sanitized = parsed.map(sanitizeModuleAssessment).filter((item): item is ModuleAssessment => Boolean(item));
    if (JSON.stringify(parsed) !== JSON.stringify(sanitized)) {
      window.localStorage.setItem(VIEWING_DECISION_STORAGE_KEY, JSON.stringify(sanitized));
    }
    return sanitized;
  } catch {
    return [];
  }
}

export function writeStoredViewingAssessment(assessment: ModuleAssessment) {
  if (typeof window === "undefined") return;
  const merged = mergeStoredAssessment(readStoredViewingAssessments(), assessment);
  window.localStorage.setItem(VIEWING_DECISION_STORAGE_KEY, JSON.stringify(merged));
}

export function toViewingDecisionResult(result: unknown): AssessmentResult | null {
  if (!result || typeof result !== "object") return null;
  const candidate = result as {
    risk_level?: unknown;
    score?: unknown;
    summary?: unknown;
    recommendations?: unknown;
  };
  if (candidate.risk_level !== "low" && candidate.risk_level !== "medium" && candidate.risk_level !== "high") {
    return null;
  }
  return {
    risk_level: candidate.risk_level,
    score: typeof candidate.score === "number" ? candidate.score : undefined,
    summary: typeof candidate.summary === "string" ? candidate.summary : undefined,
    recommendations: Array.isArray(candidate.recommendations)
      ? candidate.recommendations.filter((item): item is string => typeof item === "string")
      : undefined,
  };
}

export function moduleHref(moduleSlug: ModuleSlug) {
  return `/${moduleSlug}`;
}

function buildKnownReminders(assessments: ModuleAssessment[]) {
  const reminders: string[] = [];
  for (const assessment of assessments) {
    const label = MODULE_LABELS[assessment.moduleSlug];
    if (!assessment.result) {
      reminders.push(`${label}${zh([0x5df2,0x6709,0x7d00,0x9304,0xff0c,0x4f46,0x7f3a,0x5c11,0x53ef,0x8b80,0x53d6,0x7684,0x5206,0x6790,0x6458,0x8981,0x3002])}`);
      continue;
    }
    reminders.push(`${label}: ${assessment.result.summary ?? zh([0x5df2,0x5b8c,0x6210,0x521d,0x6b65,0x898f,0x5247,0x6aa2,0x67e5,0x3002])}`);
    for (const recommendation of assessment.result.recommendations ?? []) reminders.push(`${label}: ${recommendation}`);
  }
  return reminders;
}

function isModuleAssessment(value: unknown): value is ModuleAssessment {
  if (!value || typeof value !== "object") return false;
  const moduleSlug = (value as { moduleSlug?: unknown }).moduleSlug;
  return moduleSlug === "tax-oracle" || moduleSlug === "aegis-credit" || moduleSlug === "lex-prop";
}

function sanitizeModuleAssessment(value: unknown): ModuleAssessment | null {
  if (!isModuleAssessment(value)) return null;
  const assessment = value as ModuleAssessment;
  return {
    moduleSlug: assessment.moduleSlug,
    moduleName: typeof assessment.moduleName === "string" ? assessment.moduleName : undefined,
    assessmentId:
      typeof assessment.assessmentId === "string" || typeof assessment.assessmentId === "number"
        ? assessment.assessmentId
        : undefined,
    result: toViewingDecisionResult(assessment.result),
  };
}
