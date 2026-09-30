import type { ReactNode } from "react";
import { AsyncState } from "@/components/design-system/async-state";
import type { WorkspaceEvidenceState } from "@/lib/workspace/workspace-model";

export function EvidenceStateBoundary({ state, children }: { state: WorkspaceEvidenceState; children: ReactNode }) {
  if (state.query === "in_progress") return <AsyncState kind="loading" title="正在取得此區段的證據" />;
  if (state.query === "failed") return <AsyncState kind="error" title="此區段目前無法更新" detail="既有證據與其他區段不受影響。" />;
  if (state.query === "not_started") return <AsyncState kind="not_started" title="尚未查詢此區段" detail="可在後續分析階段從目前案件開始查詢。" />;
  if (state.usability === "stale") return <AsyncState kind="unavailable" title="此區段的既有證據需要重新確認" detail="資料仍保留，但不視為目前有效。" />;
  return <>{children}</>;
}
