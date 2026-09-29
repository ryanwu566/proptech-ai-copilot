export type VisualRole = "neutral" | "information" | "warning" | "error" | "success" | "disabled";
export type ButtonVariant = "primary" | "secondary" | "tertiary" | "destructive";
export type ButtonSize = "compact" | "standard" | "touch";
export type MessageVariant = "inline" | "information" | "warning" | "confirmation" | "error" | "success";
export type AsyncStateKind = "not_started" | "input_required" | "no_match" | "no_coverage" | "unavailable" | "unsupported" | "error" | "loading";

export function joinClassNames(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}
