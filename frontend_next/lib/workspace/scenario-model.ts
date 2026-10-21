// @ts-expect-error Native TS runner extension.
import { calculateScenario, SCENARIO_FIELDS, type ScenarioInput } from "./scenario-calculator.ts";
// @ts-expect-error Native TS runner extension.
export { calculateScenario, emptyScenario, SCENARIO_FIELDS, type ScenarioField, type ScenarioInput, type ScenarioResult } from "./scenario-calculator.ts";

export const SCENARIO_STORAGE_KEY = "proptech.scenarios.v1";
export type ScenarioSave = { version: 1; context: string; drafts: ScenarioInput[]; baseline: ScenarioInput | null };

function isInput(value: unknown): value is ScenarioInput {
  if (!value || typeof value !== "object") return false;
  const row = value as ScenarioInput;
  return ["amount", "ratio"].includes(row.downMode)
    && SCENARIO_FIELDS.every((field) => row[field] === null || (typeof row[field] === "number" && Number.isFinite(row[field])))
    && Object.keys(calculateScenario(row).errors).length === 0;
}

export function parseScenarioSave(raw: string | null, context: string): ScenarioSave | null {
  try {
    const row = JSON.parse(raw ?? "null") as ScenarioSave | null;
    return row?.version === 1 && row.context === context && Array.isArray(row.drafts) && row.drafts.length === 3
      && row.drafts.every(isInput) && (row.baseline === null || isInput(row.baseline)) ? row : null;
  } catch { return null; }
}
