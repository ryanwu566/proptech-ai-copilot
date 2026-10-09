import type { CommercialSemanticRole } from "./state";

/** Narrow E2 compatibility adapter; keep localized registries out of generic async UI bundles. */
export function resolveAsyncStateRole(kind: unknown): CommercialSemanticRole {
  switch (kind) {
    case "not_started": case "no_match": return "neutral";
    case "input_required": case "no_coverage": case "unavailable": return "warning";
    case "loading": return "information";
    case "unsupported": return "disabled";
    default: return "error";
  }
}
