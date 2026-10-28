/** Reserved local IDs for the two demonstration snapshots. Real cases use random IDs, so these never collide. */
export const DEMO_CASE_A_ID = "proptech-demo-a";
export const DEMO_CASE_B_ID = "proptech-demo-b";
export const DEMO_CASE_IDS = [DEMO_CASE_A_ID, DEMO_CASE_B_ID] as const;
/** Reference date of the demonstration snapshot; shown wherever a demo case is open. */
export const DEMO_SNAPSHOT_DATE = "2026-10-01";
export function isDemoCaseId(value: unknown): boolean {
  return typeof value === "string" && (DEMO_CASE_IDS as readonly string[]).includes(value);
}
/** Query flag that asks Demo A's Location view to play the provider-free Auto Brief showcase once. */
export const SHOWCASE_PARAM = "showcase";
