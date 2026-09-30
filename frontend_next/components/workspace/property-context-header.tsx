"use client";

import Link from "next/link";
import { ActionSection, Panel } from "@/components/design-system/section";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { StatusLabel } from "@/components/design-system/status-label";
import { resolveCommercialState } from "@/lib/commercial/state";
import { formatExactDate, formatWan } from "@/lib/commercial/formatters";
import { useWorkspace } from "./workspace-provider";

const priceLabels = { asking: "開價", estimate: "成交資料推估中點", manual: "比較基準價格" } as const;

export function PropertyContextHeader() {
  const workspace = useWorkspace();
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
      </div>
      <div className="workspace-property-header__secondary">
        <span><span className="text-meta">{priceLabels[workspace.assumptions.activePriceBasis]}</span> <strong data-numeric>{activePrice ? formatWan(activePrice) : "未提供"}</strong></span>
        <StatusLabel semanticRole="success">已儲存</StatusLabel>
        <span className="text-meta">最後儲存：{formatExactDate(workspace.updatedAt)}</span>
      </div>
      {workspace.identity.state === "revalidation_required" && <p className="workspace-property-header__warning">先前受影響的證據保留為過期狀態，重新確認前不會顯示為目前證據。</p>}
      <DetailsDisclosure summary="物件與來源詳細資料" variant="compact">
        <dl className="workspace-property-header__details text-dense">
          <div><dt>正規化地址</dt><dd>{anchor?.normalized_address || "尚未取得"}</dd></div>
          <div><dt>關聯範圍</dt><dd>{anchor ? "瀏覽器案件關聯錨點" : "物件尚待確認"}</dd></div>
          <div><dt>證據檢查時間</dt><dd>{anchor ? formatExactDate(anchor.evidence.checked_at) : "尚未檢查"}</dd></div>
          <div><dt>邊界</dt><dd>不代表地號、建物、所有權或法律身分，也不啟用 VNext PropertyEntity。</dd></div>
        </dl>
      </DetailsDisclosure>
      <ActionSection className="workspace-property-header__actions">
        <Link className="ds-button ds-button--secondary ds-button--compact" href="/cases">已儲存案件</Link>
        <span className="text-meta" aria-disabled="true">比較與報告為獨立流程，將於後續階段接入。</span>
      </ActionSection>
    </Panel>
  </header>;
}
