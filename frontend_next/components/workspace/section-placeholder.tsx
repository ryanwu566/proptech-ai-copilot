"use client";

import { Message } from "@/components/design-system/message";
import { Panel, Section } from "@/components/design-system/section";
import { EvidenceStateBoundary } from "./evidence-state-boundary";
import { useWorkspace } from "./workspace-provider";
import type { EvidenceKey } from "@/lib/workspace/workspace-model";

const content = {
  market: { title: "價格與市場", question: "這個價格是否合理，目前有哪些可判讀的市場證據？", keys: ["market", "valuation"] as EvidenceKey[] },
  location: { title: "區位與通勤", question: "物件周邊有哪些重要條件，實際目的地通勤如何？", keys: ["location", "commute"] as EvidenceKey[] },
  risk: { title: "風險與環境", question: "有哪些環境證據與未知事項需要進一步查核？", keys: ["risk"] as EvidenceKey[] },
  finance: { title: "資金與持有成本", question: "目前情境需要多少資金與成本，還缺少哪些假設？", keys: ["finance"] as EvidenceKey[] },
} as const;

const evidenceLabels: Record<EvidenceKey, string> = {
  market: "市場資料",
  valuation: "價格推估",
  location: "地點資料",
  commute: "通勤資料",
  risk: "風險資料",
  finance: "財務資料",
};

export function WorkspaceSectionPlaceholder({ section }: { section: keyof typeof content }) {
  const workspace = useWorkspace();
  const definition = content[section];
  return <div className="workspace-view">
    <header className="workspace-view__heading">
      <p className="text-meta">案件分析區段</p>
      <h1 className="text-page">{definition.title}</h1>
      <p className="text-body">{definition.question}</p>
    </header>
    <Section title="區段基礎已建立">
      <div className="workspace-action-grid">
        {definition.keys.map((key) => <Panel key={key} data-evidence-key={key}>
          <h2 className="text-subsection">{evidenceLabels[key]}</h2>
          <EvidenceStateBoundary state={workspace.evidence[key]}>
            <Message variant="warning" title="已恢復有限摘要">此案件只保留可安全轉移的摘要；完整分析與刷新控制由後續領域階段接入。</Message>
          </EvidenceStateBoundary>
        </Panel>)}
      </div>
    </Section>
    <Section title="本階段邊界">
      <Message variant="information">E3 只提供路由、物件脈絡與證據狀態邊界，不在此處重寫領域分析。</Message>
    </Section>
  </div>;
}
