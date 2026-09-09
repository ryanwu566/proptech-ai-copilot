import type { TerrainReferenceState } from "@/lib/terrain-reference-evidence";

export type CompareDataState =
  | "known"
  | "unknown"
  | "unavailable"
  | "partial"
  | "limited"
  | "stale"
  | "conflicting"
  | "no_match"
  | "not_assessed"
  | "unverified"
  | "malformed";

export type CompareCurrency = "TWD" | "USD" | null;
export type CompareUnit = "currency_10k" | "currency" | "ping" | "sqm";
export type ComparePeriod = "one_time" | "monthly" | "annual" | null;
export type CompareBasis =
  | "asking_price"
  | "transaction_price"
  | "official_valuation"
  | "down_payment"
  | "mortgage_payment"
  | "holding_cost"
  | "floor_area";

export type CompareMetric = {
  value: number | null;
  state: CompareDataState;
  unit: CompareUnit;
  currency: CompareCurrency;
  period: ComparePeriod;
  basis: CompareBasis;
  limitation?: string;
};

export type CompareIdentity = {
  status: "confirmed" | "resolving" | "unverified" | "legacy_unverified";
  displayLabel: string | null;
  propertyEntityId: string | null;
  note: string;
};

export type CompareSourceDisclosure = {
  sourceId: string;
  label: string;
  state: CompareDataState;
  coverage: "known" | "partial" | "unknown" | "unavailable";
  retrievedAt: string | null;
  effectiveAt: string | null;
  limitation: string;
};

export type CompareValuation = {
  state: CompareDataState;
  transferable: boolean;
  low: CompareMetric;
  midpoint: CompareMetric;
  high: CompareMetric;
  statusLabel: string;
  limitation: string;
};

export type CompareObservation = {
  state: CompareDataState;
  items: string[];
  limitation: string;
};

export type CompareTerrain = {
  state: TerrainReferenceState;
  riskLevel: "low" | "medium" | "high" | "unknown";
  summary: string;
  observations: string[];
  limitation: string;
};

export type CompareTaxReference = {
  state: CompareDataState;
  summary: string;
  limitation: string;
};

export type CompareWarning = {
  severity: "high" | "caution" | "information";
  label: string;
};

export type PropertyCompareCase = {
  caseId: string;
  title: string;
  locationSummary: string;
  identity: CompareIdentity;
  caseUpdatedAt: string | null;
  askingPrice: CompareMetric;
  area: CompareMetric;
  buildingType: { value: string | null; state: CompareDataState; limitation?: string };
  valuation: CompareValuation;
  downPayment: CompareMetric;
  monthlyMortgage: CompareMetric;
  monthlyHoldingCost: CompareMetric;
  location: CompareObservation;
  terrain: CompareTerrain;
  tax: CompareTaxReference;
  warnings: CompareWarning[];
  sources: CompareSourceDisclosure[];
  nextChecks: string[];
};

export type CompareDatasetIssue = {
  code: "empty_case_id" | "duplicate_case_id";
  message: string;
  itemIndex: number;
};

export type NormalizedCompareDataset = {
  cases: PropertyCompareCase[];
  issues: CompareDatasetIssue[];
};
