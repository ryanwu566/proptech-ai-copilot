"use client";

import { useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { CommercialButton } from "@/components/design-system/button";
import { createBrowserCaseRepository } from "@/lib/workspace/case-repository";
import { Panel } from "@/components/design-system/section";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { StatusLabel } from "@/components/design-system/status-label";
import { resolveCommercialState } from "@/lib/commercial/state";
import { formatExactDate, formatWan } from "@/lib/commercial/formatters";
import { useWorkspace } from "./workspace-provider";

const priceLabels = { asking: "開價", estimate: "成交資料推估中點", manual: "比較基準價格" } as const;

export function PropertyContextHeader() {
  const workspace = useWorkspace();
  const isFinance = usePathname().endsWith("/finance");
  const repository = useMemo(createBrowserCaseRepository, []);
  const [saveStatus, setSaveStatus] = useState("");
  function saveSnapshot() {
    setSaveStatus("");
    try {
      const result = repository.saveSnapshot(workspace);
      setSaveStatus(result.status === "saved"
        ? "已保存目前已知狀態；未知、無法取得與尚未完成的項目仍保持原狀。"
        : result.message);
    } catch {
      setSaveStatus("儲存失敗：瀏覽器儲存空間無法寫入。請保留目前頁面，確認儲存設定後重試。");
    }
  }
  const identity = resolveCommercialState("identity", workspace.identity.state);
  const activePrice = workspace.assumptions.activePriceWan;
  const anchor = workspace.identity.anchor;
  return <header role="banner" aria-label="目前物件" className="workspace-property-header">
    <Panel className="workspace-property-header__panel">
      <div className="workspace-property-header__primary">
        <div className="workspace-property-header__title">
          <p className="text-meta">目前物件 · {workspace.title}</p>
          <strong>{workspace.displayAddress}</strong>
        </div>
        <StatusLabel semanticRole={identity.role}>{identity.label["zh-TW"]}</StatusLabel>
        <div className="workspace-property-header__save">{isFinance ? <a className="ds-button ds-button--secondary ds-button--compact" href="#finance-save-section">儲存財務摘要</a> : <CommercialButton size="compact" onClick={saveSnapshot}>保存目前案件快照</CommercialButton>}</div>
      </div>
      <div className="workspace-property-header__secondary">
        <span><span className="text-meta">{priceLabels[workspace.assumptions.activePriceBasis]}</span> <strong data-numeric>{activePrice ? formatWan(activePrice) : "未提供"}</strong></span>
        <StatusLabel semanticRole="information">已儲存快照</StatusLabel>
        <span className="text-meta">最後儲存：{formatExactDate(workspace.updatedAt)}</span>
      </div>
      {workspace.identity.state === "revalidation_required" && <p className="workspace-property-header__warning">先前受影響的證據保留為過期狀態，重新確認前不會顯示為目前證據。</p>}
      <div data-testid="context-save-status"><p data-testid="overview-save-status" aria-live="polite" className="workspace-property-header__save-status text-dense">{saveStatus}</p></div>
      <DetailsDisclosure summary="物件與來源詳細資料" variant="compact">
        <dl className="workspace-property-header__details text-dense">
          <div><dt>正規化地址</dt><dd>{anchor?.normalized_address || "尚未取得"}</dd></div>
          <div><dt>關聯範圍</dt><dd>{anchor ? "瀏覽器案件關聯錨點" : "物件尚待確認"}</dd></div>
          <div><dt>證據檢查時間</dt><dd>{anchor ? formatExactDate(anchor.evidence.checked_at) : "尚未檢查"}</dd></div>
          <div><dt>邊界</dt><dd>不代表地號、建物、所有權或法律身分，也不啟用 VNext PropertyEntity。</dd></div>
        </dl>
      </DetailsDisclosure>
    </Panel>
  </header>;
}
