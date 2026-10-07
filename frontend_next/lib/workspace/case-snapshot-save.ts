import type { SavedCase, SavedCaseData, SavedCaseIdentityExpectation } from "../case-storage";

export type SaveSnapshotBlockedReason = "case_not_found" | "identity_unconfirmed" | "identity_revalidation_required" | "identity_mismatch" | "revision_mismatch";
export type SaveSnapshotIdentityState = "confirmed" | "confirming" | "unconfirmed" | "revalidation_required" | "conflict";

export type SaveSnapshotResult =
  | { status: "saved"; saved: SavedCase }
  | { status: "blocked"; reason: SaveSnapshotBlockedReason; message: string };

type SnapshotUpdate = { result: SaveSnapshotResult; rows: SavedCase[] };

function blocked(rows: SavedCase[], reason: SaveSnapshotBlockedReason, message: string): SnapshotUpdate {
  return { result: { status: "blocked", reason, message }, rows };
}

function coordinatesMatch(left: { latitude: number; longitude: number }, right: { latitude: number; longitude: number }): boolean {
  return Math.abs(left.latitude - right.latitude) <= 0.000001 && Math.abs(left.longitude - right.longitude) <= 0.000001;
}

export function buildSavedCaseSnapshotUpdate(
  rows: SavedCase[],
  caseId: string,
  expected: SavedCaseIdentityExpectation | undefined,
  identityState: SaveSnapshotIdentityState,
  expectedUpdatedAt: string,
  now: () => string,
  compact: (data: SavedCaseData) => SavedCaseData,
): SnapshotUpdate {
  const index = rows.findIndex((row) => row.id === caseId);
  if (index < 0) return blocked(rows, "case_not_found", "找不到目前案件；請返回已儲存案件重新開啟。");
  const current = rows[index];
  const anchor = current.data.propertyIdentityAnchor;
  if (identityState === "revalidation_required" || identityState === "conflict") {
    return blocked(rows, "identity_revalidation_required", "物件資料已變更；請重新確認地址與定位後再保存。");
  }
  if (identityState !== "confirmed") {
    return blocked(rows, "identity_unconfirmed", "需要先完成地址定位並確認目前物件，才能保存這份案件快照。");
  }
  if (!anchor || !anchor.coordinates || !expected) {
    return blocked(rows, "identity_unconfirmed", "需要先完成地址定位並確認目前物件，才能保存這份案件快照。");
  }
  if (anchor.revalidation.status !== "current" || anchor.location_status === "stale") {
    return blocked(rows, "identity_revalidation_required", "物件資料已變更；請重新確認地址與定位後再保存。");
  }
  if (
    anchor.journey_anchor_id !== expected.journeyAnchorId
    || anchor.normalized_address !== expected.normalizedAddress
    || !coordinatesMatch(anchor.coordinates, expected.coordinates)
  ) {
    return blocked(rows, "identity_mismatch", "目前物件與要保存的案件脈絡不一致；請重新開啟正確案件或確認地址。");
  }
  if (current.updatedAt !== expectedUpdatedAt) {
    return blocked(rows, "revision_mismatch", "案件已在另一個畫面更新；請重新開啟案件後再保存，以免覆蓋較新的內容。");
  }

  const saved: SavedCase = { ...current, updatedAt: now(), data: compact(current.data) };
  const nextRows = [...rows];
  nextRows[index] = saved;
  return { result: { status: "saved", saved }, rows: nextRows };
}
