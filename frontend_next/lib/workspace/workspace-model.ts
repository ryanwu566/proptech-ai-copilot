import type { JourneyPropertyIdentityAnchorV1 } from "../journey-property-identity";
import type {
  AnalysisCompletenessState,
  EvidenceUsabilityState,
  PropertyIdentityState,
  QueryExecutionState,
} from "../commercial/state";
import type { MarketPriceModel } from "./market-price-model";
import type { LocationWorkspaceSnapshot } from "./location-context";
import type { FinanceModel } from "./finance-model";

export const WORKSPACE_SECTIONS = ["overview", "market", "location", "risk", "finance"] as const;
export type WorkspaceSection = (typeof WORKSPACE_SECTIONS)[number];

export const EVIDENCE_KEYS = ["market", "valuation", "location", "commute", "risk", "finance"] as const;
export type EvidenceKey = (typeof EVIDENCE_KEYS)[number];
export type InputFingerprint = string;

export type WorkspaceEvidenceState = {
  query: QueryExecutionState;
  usability?: EvidenceUsabilityState;
  completeness: AnalysisCompletenessState;
  checkedAt?: string;
  summaryOnly: boolean;
};

export type WorkspaceIdentity = {
  state: PropertyIdentityState;
  scope: "journey_browser_anchor" | "unconfirmed";
  anchor: JourneyPropertyIdentityAnchorV1 | null;
};

export type PropertyCaseWorkspace = {
  caseId: string;
  revision: number;
  title: string;
  displayAddress: string;
  updatedAt: string;
  identity: WorkspaceIdentity;
  assumptions: {
    activePriceBasis: "asking" | "estimate" | "manual";
    activePriceWan?: number;
    askingPriceWan?: number;
    manualPriceWan?: number;
    areaPing?: number;
  };
  evidence: Record<EvidenceKey, WorkspaceEvidenceState>;
  marketPrice: MarketPriceModel;
  location: LocationWorkspaceSnapshot;
  /** Optional only for backwards-compatible test/consumer fixtures; repository adapters always populate it. */
  finance?: FinanceModel;
  saveState: "saved" | "saving" | "unsaved" | "save_failed";
};

export type WorkspaceLoadState =
  | { status: "loading" }
  | { status: "not_found"; caseId: string }
  | { status: "ready"; workspace: PropertyCaseWorkspace };
