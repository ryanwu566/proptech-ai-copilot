import type { RiskEvidenceKey, RiskEvidenceModel, RiskEvidenceRow } from "./risk-evidence-model";

export const BUYER_HAZARDS = ["flood", "liquefaction", "landslide", "debris_flow", "geological_sensitivity", "active_fault"] as const satisfies readonly RiskEvidenceKey[];
export type BuyerHazard = (typeof BUYER_HAZARDS)[number];
export type BuyerState = "MATCHED" | "NO MATCH" | "NO COVERAGE" | "UNKNOWN" | "UNAVAILABLE" | "UNSUPPORTED" | "LIMITED" | "STALE" | "NOT QUERIED";
export type BuyerFreshness = RiskEvidenceModel["freshness"]["status"] | "not_queried";
export type RiskBuyerCardModel = {
  key: BuyerHazard;
  state: BuyerState;
  freshness: BuyerFreshness;
  checkedAt: string | null;
  actionKey: BuyerHazard;
  // Keep the bounded evidence as received. Missing provenance remains missing.
  evidence: Readonly<RiskEvidenceRow> | undefined;
};

export function buyerState(row: Readonly<RiskEvidenceRow> | undefined): BuyerState {
  if (!row) return "NOT QUERIED";
  switch (row.usability) {
    case "stale": return "STALE";
    case "no_coverage": return "NO COVERAGE";
    case "unavailable": return "UNAVAILABLE";
    case "unsupported": return "UNSUPPORTED";
    case "limited": return "LIMITED";
    case "no_match": return "NO MATCH";
    case "usable": return row.matched === true ? "MATCHED" : "UNKNOWN";
    default: return "UNKNOWN";
  }
}

export function buildRiskBuyerModel(model: RiskEvidenceModel | null): { cards: RiskBuyerCardModel[]; verificationCount: number | null } {
  const cards = BUYER_HAZARDS.map((key): RiskBuyerCardModel => {
    const evidence = model?.rows.find((row) => row.key === key);
    return {
      key,
      state: evidence && model?.freshness.status === "stale" ? "STALE" : buyerState(evidence),
      freshness: evidence && model ? model.freshness.status : "not_queried",
      checkedAt: evidence ? model?.freshness.checkedAt ?? null : null,
      actionKey: key,
      evidence,
    };
  });
  // Every distinct topic has routine verification, including NO MATCH and missing topics.
  // Card/disclosure interactions never change this count; there is no completion ledger.
  return { cards, verificationCount: model ? cards.length : null };
}
