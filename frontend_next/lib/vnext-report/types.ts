import type {
  HoldingCostResult,
  LoanCalculationResult,
  LocationInsightResult,
  PropertySearchResult,
  TaxResult,
  TerrainRiskResult,
  ValuationResult,
} from "@/lib/api";
import type { RiskSummary } from "@/lib/risk-summary";
import type { ViewingDecision, ViewingDecisionInputs, ViewingDecisionStatus } from "@/lib/viewing-decision";

export type ReportEvidenceStatus =
  | "available"
  | "partial"
  | "limited"
  | "stale"
  | "conflicting"
  | "unknown"
  | "unavailable"
  | "error"
  | "no_match"
  | "not_assessed"
  | "unverified";

export type ReportIdentityStatus =
  | "confirmed"
  | "unverified"
  | "legacy_unverified"
  | "resolving"
  | "conflicting"
  | "unknown";

export type ReportSectionId = "valuation" | "affordability" | "terrain" | "tax";

export type ReportIdentityInput = {
  status: ReportIdentityStatus;
  humanConfirmed: boolean;
  detail?: string;
};

export type ReportEvidenceInput = {
  id?: string | null;
  section: ReportSectionId | "identity" | "other";
  label: string;
  status: ReportEvidenceStatus;
  sourceLabel?: string | null;
  retrievedAt?: string | null;
  effectiveAt?: string | null;
  coverage?: string | null;
  limitation?: string | null;
};

export type ReportActionInput = {
  id: string;
  label: string;
  detail?: string;
};

export type DecisionReportAdapterInput = ViewingDecisionInputs & {
  caseLabel: string;
  propertyLabel: string;
  generatedAt: string;
  syntheticPreview: boolean;
  identity: ReportIdentityInput;
  decision?: ViewingDecision;
  propertySearch?: PropertySearchResult;
  evidence?: ReportEvidenceInput[];
  sectionStates?: Partial<Record<ReportSectionId, ReportEvidenceStatus>>;
  suppliedNextActions?: ReportActionInput[];
  otherObservations?: string[];
  reportLimitations?: string[];
};

export type ReportMetric = {
  label: string;
  value: string | null;
  note?: string;
};

export type ReportSectionModel = {
  id: ReportSectionId;
  title: string;
  eyebrow: string;
  status: ReportEvidenceStatus;
  summary: string;
  metrics: ReportMetric[];
  observations: string[];
  limitations: string[];
  evidenceIds: string[];
};

export type ReportEvidenceModel = Omit<ReportEvidenceInput, "id"> & {
  id: string | null;
};

export type ReportChecklistItem = ReportActionInput & {
  reviewOnlyNotice: string;
};

export type ReportDecisionModel = {
  sourceStatus: ViewingDecisionStatus;
  displayStatus: ViewingDecisionStatus | "cannot_determine";
  label: string;
  summary: string;
  reasons: string[];
  knownRisks: string[];
  missingInformation: string[];
};

export type DecisionReportModel = {
  schemaVersion: 1;
  caseLabel: string;
  propertyLabel: string;
  generatedAt: string;
  syntheticPreview: boolean;
  identity: ReportIdentityInput & { label: string; boundary: string };
  decision: ReportDecisionModel;
  sections: ReportSectionModel[];
  evidence: ReportEvidenceModel[];
  checklist: ReportChecklistItem[];
  otherObservations: string[];
  limitations: string[];
};

export type ExistingReportInputs = {
  propertySearch?: PropertySearchResult;
  valuation?: ValuationResult;
  loan?: LoanCalculationResult;
  holding?: HoldingCostResult;
  location?: LocationInsightResult;
  terrainRisk?: TerrainRiskResult;
  riskSummary?: RiskSummary;
  taxOracleResult?: TaxResult;
};
