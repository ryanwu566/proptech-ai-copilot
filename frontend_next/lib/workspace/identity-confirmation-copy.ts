import type { CopyCatalogue } from "../copy-catalogue";
import type { WorkspaceIdentity } from "./workspace-model";

/** No pending candidate can supply confirmation history. Only existing identity state can. */
export function identityConfirmationKind(identity: WorkspaceIdentity): "confirmed" | "pending" | "reconfirmation" {
  if (identity.state === "confirmed") return "confirmed";
  // Reconciliation deliberately clears current confidence on an existing stale anchor.
  const wasConfirmed = identity.anchor && (["high", "medium"].includes(identity.anchor.confidence.level) || identity.anchor.location_status === "stale");
  return wasConfirmed && (identity.state === "revalidation_required" || identity.state === "conflict") ? "reconfirmation" : "pending";
}

type Key = "pendingTitle" | "reconfirmationTitle" | "pendingLocation" | "reconfirmationLocation" | "pendingRisk" | "reconfirmationRisk" | "pendingReport" | "reconfirmationReport" | "pendingAction" | "reconfirmationAction" | "pendingRoute" | "reconfirmationRoute";
export const identityConfirmationCopy: CopyCatalogue<Key> = {
  "zh-TW": {
    pendingTitle: "物件位置尚未確認", reconfirmationTitle: "物件位置已變更，需重新確認",
    pendingLocation: "請先確認物件位置，再查看地圖與路線。", reconfirmationLocation: "目前不把先前位置或通勤結果當作本案現況；完成物件位置重新確認後再查看地圖與路線。",
    pendingRisk: "物件位置尚未確認，請先確認位置再查詢。", reconfirmationRisk: "物件資料已變更，需重新確認後再查詢。",
    pendingReport: "物件位置尚未確認；確認後才能產生正式報告與列印。", reconfirmationReport: "案件身分需重新確認；正式報告與列印已停止。",
    pendingAction: "確認物件位置", reconfirmationAction: "重新確認物件",
    pendingRoute: "確認物件位置後，即可查詢目的地路線。", reconfirmationRoute: "請先重新確認物件位置，再查詢目的地路線。",
  },
  en: {
    pendingTitle: "Property location not yet confirmed", reconfirmationTitle: "Property location changed; confirm it again",
    pendingLocation: "Confirm the property location to view the map and routes.", reconfirmationLocation: "Previous location and route results are not current. Confirm the changed property location again to view the map and routes.",
    pendingRisk: "Confirm the property location before checking risk evidence.", reconfirmationRisk: "Property details changed. Confirm them again before querying.",
    pendingReport: "Confirm the property location before generating or printing the formal report.", reconfirmationReport: "The case identity needs reconfirmation. Formal reporting and printing are blocked.",
    pendingAction: "Confirm property location", reconfirmationAction: "Confirm property again",
    pendingRoute: "Destination routes can be checked once the property location is confirmed.", reconfirmationRoute: "Confirm the changed property location again before checking routes.",
  },
  ja: {
    pendingTitle: "物件の位置は未確認です", reconfirmationTitle: "物件の位置が変更されたため再確認が必要です",
    pendingLocation: "地図と経路を表示するには物件の位置を確認してください。", reconfirmationLocation: "以前の位置と経路は現在の情報ではありません。変更された位置を再確認してください。",
    pendingRisk: "リスク情報を照会する前に物件の位置を確認してください。", reconfirmationRisk: "物件情報が変更されました。照会前に再確認してください。",
    pendingReport: "正式なレポートの作成・印刷前に物件の位置を確認してください。", reconfirmationReport: "案件の識別情報は再確認が必要です。正式なレポートと印刷は停止しています。",
    pendingAction: "物件の位置を確認", reconfirmationAction: "物件を再確認",
    pendingRoute: "物件の位置を確認すると目的地への経路を照会できます。", reconfirmationRoute: "経路を照会する前に変更された位置を再確認してください。",
  },
  ko: {
    pendingTitle: "부동산 위치가 아직 확인되지 않았습니다", reconfirmationTitle: "부동산 위치가 변경되어 다시 확인해야 합니다",
    pendingLocation: "지도와 경로를 보려면 부동산 위치를 확인하세요.", reconfirmationLocation: "이전 위치와 경로는 현재 정보가 아닙니다. 변경된 위치를 다시 확인하세요.",
    pendingRisk: "위험 정보를 조회하기 전에 부동산 위치를 확인하세요.", reconfirmationRisk: "매물 정보가 변경되었습니다. 조회 전에 다시 확인하세요.",
    pendingReport: "정식 보고서를 생성하거나 인쇄하기 전에 부동산 위치를 확인하세요.", reconfirmationReport: "사례 식별 정보를 다시 확인해야 합니다. 정식 보고서와 인쇄가 중단되었습니다.",
    pendingAction: "부동산 위치 확인", reconfirmationAction: "부동산 다시 확인",
    pendingRoute: "부동산 위치를 확인하면 목적지 경로를 조회할 수 있습니다.", reconfirmationRoute: "경로 조회 전에 변경된 위치를 다시 확인하세요.",
  },
};
