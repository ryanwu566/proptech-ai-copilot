export type CommercialLocale = "zh-TW" | "en" | "ja" | "ko";
export type CommercialSemanticRole = "neutral" | "information" | "warning" | "error" | "success" | "disabled";
export type CommercialStateAxis = "query" | "evidence" | "completeness" | "risk" | "identity" | "readiness";

export type QueryExecutionState = "not_started" | "input_required" | "in_progress" | "succeeded" | "failed" | "cancelled";
export type EvidenceUsabilityState = "usable" | "limited" | "no_match" | "no_coverage" | "unavailable" | "stale" | "unverified" | "unsupported";
export type AnalysisCompletenessState = "not_started" | "insufficient" | "partial" | "sufficient_for_task" | "blocked";
export type RiskInterpretationState = "elevated_signal" | "caution_signal" | "no_identified_signal" | "unknown" | "not_assessed";
export type PropertyIdentityState = "unconfirmed" | "confirming" | "confirmed" | "conflict" | "revalidation_required";
export type TaskReadinessState = "not_ready" | "ready_with_limits" | "ready" | "blocked";

export type LocalizedLabel = Record<CommercialLocale, string>;
export type CommercialStateContract<T extends string = string> = {
  value: T;
  label: LocalizedLabel;
  meaning: string;
  role: CommercialSemanticRole;
  actionable: boolean;
};

export type ResolvedCommercialState = CommercialStateContract & { axis: CommercialStateAxis; recognized: boolean };

const label = (zh: string, en: string, ja: string, ko: string): LocalizedLabel => ({ "zh-TW": zh, en, ja, ko });
const contract = <T extends string>(value: T, localized: LocalizedLabel, meaning: string, role: CommercialSemanticRole, actionable: boolean): CommercialStateContract<T> => ({ value, label: localized, meaning, role, actionable });

export const QUERY_STATE_REGISTRY: Record<QueryExecutionState, CommercialStateContract<QueryExecutionState>> = {
  not_started: contract("not_started", label("尚未查詢", "Not queried", "未照会", "조회 전"), "尚未提出查詢。", "neutral", true),
  input_required: contract("input_required", label("需要輸入資料", "Input required", "入力が必要", "입력 필요"), "缺少可開始查詢的必要輸入。", "warning", true),
  in_progress: contract("in_progress", label("查詢中", "Querying", "照会中", "조회 중"), "查詢或計算正在執行。", "information", false),
  succeeded: contract("succeeded", label("查詢完成", "Query complete", "照会完了", "조회 완료"), "查詢正常結束；不代表證據可用、分析完整或安全。", "success", false),
  failed: contract("failed", label("查詢失敗", "Query failed", "照会失敗", "조회 실패"), "本次查詢因錯誤而未完成。", "error", true),
  cancelled: contract("cancelled", label("已停止查詢", "Query stopped", "照会停止", "조회 중지"), "查詢被使用者或更新後的請求停止。", "neutral", true),
};

export const EVIDENCE_STATE_REGISTRY: Record<EvidenceUsabilityState, CommercialStateContract<EvidenceUsabilityState>> = {
  usable: contract("usable", label("證據可供判讀", "Evidence usable", "判読可能な根拠", "판독 가능한 근거"), "來源、範圍、期間與內容符合目前任務的最低要求。", "information", false),
  limited: contract("limited", label("證據有限", "Limited evidence", "根拠に制約あり", "근거 제한"), "部分證據可用，但涵蓋、樣本或欄位限制判讀。", "warning", true),
  no_match: contract("no_match", label("查無符合資料", "No matching data", "該当データなし", "일치 자료 없음"), "已涵蓋的查詢範圍內沒有符合紀錄；不等於安全。", "neutral", true),
  no_coverage: contract("no_coverage", label("不在資料涵蓋範圍", "Outside data coverage", "データ対象外", "데이터 범위 밖"), "資料來源不涵蓋目前地點、期間或類型。", "warning", true),
  unavailable: contract("unavailable", label("目前無法取得證據", "Evidence unavailable", "根拠を取得できません", "근거를 가져올 수 없음"), "目前因來源或應用程式失敗而無法取得證據。", "warning", true),
  stale: contract("stale", label("資料可能已過期", "Evidence may be outdated", "情報が古い可能性", "자료가 오래되었을 수 있음"), "既有證據已不符合時效或物件版本要求。", "warning", true),
  unverified: contract("unverified", label("來源尚未驗證", "Source not verified", "出典未検証", "출처 미검증"), "證據存在，但來源或完整性尚未確認。", "warning", true),
  unsupported: contract("unsupported", label("目前不支援此項資料", "Evidence unsupported", "現在は未対応", "현재 지원하지 않음"), "產品目前不支援這項證據。", "disabled", false),
};

export const COMPLETENESS_STATE_REGISTRY: Record<AnalysisCompletenessState, CommercialStateContract<AnalysisCompletenessState>> = {
  not_started: contract("not_started", label("尚未分析", "Not analyzed", "未分析", "분석 전"), "尚未針對指定任務進行分析。", "neutral", true),
  insufficient: contract("insufficient", label("資料不足，無法判讀", "Insufficient for analysis", "分析には不十分", "분석 자료 부족"), "現有證據不足以支援指定任務。", "warning", true),
  partial: contract("partial", label("分析僅完成部分", "Partially complete", "一部のみ完了", "일부 분석 완료"), "部分必要分析已完成，仍有重要問題未解。", "warning", true),
  sufficient_for_task: contract("sufficient_for_task", label("已足以進行指定任務", "Sufficient for the named task", "指定タスクに十分", "지정 작업에 충분"), "證據符合指定任務的最低要求。", "success", false),
  blocked: contract("blocked", label("分析無法完成", "Analysis blocked", "分析不可", "분석 차단"), "具體前置條件或衝突阻止安全分析。", "error", true),
};

export const RISK_STATE_REGISTRY: Record<RiskInterpretationState, CommercialStateContract<RiskInterpretationState>> = {
  elevated_signal: contract("elevated_signal", label("發現需優先確認的風險訊號", "Elevated risk signal", "優先確認が必要なリスク信号", "우선 확인할 위험 신호"), "可用的領域證據顯示應優先查核的訊號。", "error", true),
  caution_signal: contract("caution_signal", label("發現需進一步確認的訊號", "Caution signal", "追加確認が必要な信号", "추가 확인 신호"), "證據顯示需要進一步確認，但未建立嚴重度結論。", "warning", true),
  no_identified_signal: contract("no_identified_signal", label("目前資料未發現明確風險訊號", "No identified signal in current evidence", "現在の根拠に明確な信号なし", "현재 근거에서 명확한 신호 없음"), "僅在涵蓋已確認且領域契約明定的檢查範圍內未發現訊號；不代表安全。", "neutral", false),
  unknown: contract("unknown", label("風險仍無法判定", "Risk remains unknown", "リスクは未判定", "위험 판단 불가"), "證據不可用、不涵蓋、過期、未驗證或不足。", "warning", true),
  not_assessed: contract("not_assessed", label("尚未評估風險", "Risk not assessed", "リスク未評価", "위험 미평가"), "尚未執行風險判讀。", "neutral", true),
};

export const IDENTITY_STATE_REGISTRY: Record<PropertyIdentityState, CommercialStateContract<PropertyIdentityState>> = {
  unconfirmed: contract("unconfirmed", label("物件尚待確認", "Property not confirmed", "物件未確認", "매물 미확인"), "瀏覽器案件的物件錨點尚未確認。", "neutral", true),
  confirming: contract("confirming", label("正在確認物件", "Confirming property", "物件を確認中", "매물 확인 중"), "正在比對地址、座標與物件指紋。", "information", false),
  confirmed: contract("confirmed", label("物件已確認", "Property confirmed", "物件確認済み", "매물 확인됨"), "瀏覽器案件錨點在目前版本內一致；不代表法律或地籍身分。", "success", false),
  conflict: contract("conflict", label("物件資料不一致，需要確認", "Property details conflict and need confirmation", "物件情報の不一致を確認してください", "매물 정보 불일치 확인 필요"), "物件識別輸入互相衝突，需阻擋不安全的綜合結果。", "error", true),
  revalidation_required: contract("revalidation_required", label("物件資料已變更，需重新確認", "Property changed and needs revalidation", "物件変更の再確認が必要", "매물 변경 재확인 필요"), "物件或相關假設變更，受影響證據不可視為目前有效。", "warning", true),
};

export const READINESS_STATE_REGISTRY: Record<TaskReadinessState, CommercialStateContract<TaskReadinessState>> = {
  not_ready: contract("not_ready", label("尚不足以進行指定任務", "Not ready for the named task", "指定タスクには未準備", "지정 작업 준비 부족"), "指定任務缺少必要證據。", "warning", true),
  ready_with_limits: contract("ready_with_limits", label("可進行指定任務，但仍有限制", "Ready for the named task with limits", "制約付きで実行可能", "제한적으로 작업 가능"), "指定任務可在清楚揭露限制的前提下進行。", "warning", true),
  ready: contract("ready", label("可進行指定任務", "Ready for the named task", "指定タスクを実行可能", "지정 작업 가능"), "目前案件版本符合指定任務的最低要求；不是物件推薦。", "success", false),
  blocked: contract("blocked", label("需先解決阻擋事項", "Resolve the blocker first", "先に阻害要因を解決", "차단 사항 해결 필요"), "具體問題阻止指定任務安全進行。", "error", true),
};

export const COMMERCIAL_STATE_REGISTRIES = {
  query: QUERY_STATE_REGISTRY,
  evidence: EVIDENCE_STATE_REGISTRY,
  completeness: COMPLETENESS_STATE_REGISTRY,
  risk: RISK_STATE_REGISTRY,
  identity: IDENTITY_STATE_REGISTRY,
  readiness: READINESS_STATE_REGISTRY,
} as const;

const FALLBACKS: Record<CommercialStateAxis, string> = {
  query: "failed",
  evidence: "unavailable",
  completeness: "blocked",
  risk: "unknown",
  identity: "conflict",
  readiness: "blocked",
};

export function resolveCommercialState(axis: CommercialStateAxis, value: unknown, options: { task?: string } = {}): ResolvedCommercialState {
  const registry = COMMERCIAL_STATE_REGISTRIES[axis] as Record<string, CommercialStateContract>;
  const recognized = typeof value === "string" && Object.hasOwn(registry, value);
  const resolved = registry[recognized ? value : FALLBACKS[axis]];
  const task = options.task?.trim();
  if (!task || axis !== "completeness") return { ...resolved, axis, recognized };
  const zh = resolved.value === "sufficient_for_task"
    ? `已足以進行「${task}」`
    : resolved.value === "not_started"
      ? `尚未進行「${task}」分析`
      : `${resolved.label["zh-TW"]}，目前無法進行「${task}」`;
  return { ...resolved, label: { ...resolved.label, "zh-TW": zh }, axis, recognized };
}
export function deriveRiskInterpretation(input: {
  evidenceStatus?: EvidenceUsabilityState;
  signal: "elevated" | "caution" | "no_match" | "not_assessed";
  noMatchMeansNoDefinedSignal?: boolean;
}): RiskInterpretationState {
  if (input.signal === "not_assessed") return "not_assessed";
  if (input.signal === "elevated" && input.evidenceStatus === "usable") return "elevated_signal";
  if (input.signal === "caution" && (input.evidenceStatus === "usable" || input.evidenceStatus === "limited")) return "caution_signal";
  if (input.signal === "no_match" && input.evidenceStatus === "no_match" && input.noMatchMeansNoDefinedSignal === true) return "no_identified_signal";
  return "unknown";
}
