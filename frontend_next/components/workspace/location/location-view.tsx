"use client";

import dynamic from "next/dynamic";
import { CommuteEvidencePanel } from "@/components/commute-evidence-panel";
import { DemographicsInsightCard } from "@/components/demographics-insight-card";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { MapFrame } from "@/components/design-system/map-frame";
import { Message } from "@/components/design-system/message";
import { EvidenceSection, Panel, Section } from "@/components/design-system/section";
import { MetricItem, SummaryStrip } from "@/components/design-system/summary-strip";
import { StatusLabel } from "@/components/design-system/status-label";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import type { CommuteAddressLookupResult, CommuteRouteEvidence } from "@/lib/api";
import { updateSavedCaseLocationEvidence } from "@/lib/case-storage";
import { formatDistance, formatDuration } from "@/lib/commercial/formatters";
import { resolveCommercialState } from "@/lib/commercial/state";
import { buildLocationOverviewHandoff } from "@/lib/workspace/location-context";

const GeoMap = dynamic(() => import("@/components/map/geo-map"), {
  ssr: false,
  loading: () => <div className="grid min-h-[360px] place-items-center bg-stone-100 text-sm text-slate-500">正在載入地圖…</div>,
});

const POI_LABELS = {
  transit_count: "交通",
  convenience_count: "日常便利",
  school_count: "學校",
  park_count: "公園綠地",
  medical_count: "醫療",
  risk_facility_count: "需實地確認設施",
} as const;

const MODE_LABELS = { transit: "大眾運輸", driving: "開車", walking: "步行" } as const;

export function LocationView() {
  const workspace = useWorkspace();
  const snapshot = workspace.location;
  const handoff = buildLocationOverviewHandoff(workspace);
  const coordinates = snapshot.property.coordinates;
  const identity = resolveCommercialState("identity", workspace.identity.state);
  const locationState = workspace.evidence.location.usability
    ? resolveCommercialState("evidence", workspace.evidence.location.usability)
    : resolveCommercialState("query", workspace.evidence.location.query);
  const readiness = resolveCommercialState("readiness", handoff.commuteReadiness);
  const anchor = workspace.identity.state === "confirmed" ? workspace.identity.anchor : undefined;
  const identityExpectation = anchor?.coordinates ? {
    journeyAnchorId: anchor.journey_anchor_id,
    normalizedAddress: anchor.normalized_address,
    coordinates: anchor.coordinates,
  } : undefined;

  function persistRoute(evidence: CommuteRouteEvidence | null) {
    if (identityExpectation) updateSavedCaseLocationEvidence(workspace.caseId, { commuteRoute: evidence }, identityExpectation);
  }

  function persistTransit(result: CommuteAddressLookupResult | null) {
    if (identityExpectation) updateSavedCaseLocationEvidence(workspace.caseId, { commuteTransit: result }, identityExpectation);
  }

  return <div className="workspace-view" data-testid="commercial-location-workspace">
    <header className="workspace-view__heading">
      <p className="text-meta">案件分析區段</p>
      <h1 className="text-page">區位與通勤</h1>
      <p className="text-body">這個物件位在什麼位置，周邊有哪些可核對的設施，前往重要目的地是否實際可行？</p>
    </header>

    <SummaryStrip label="區位與通勤狀態">
      <MetricItem label="物件位置" value={<StatusLabel semanticRole={identity.role}>{identity.label["zh-TW"]}</StatusLabel>} />
      <MetricItem label="周邊證據" value={<StatusLabel semanticRole={locationState.role}>{locationState.label["zh-TW"]}</StatusLabel>} note="案件重開後的摘要會標示為有限證據" />
      <MetricItem label="目的地通勤" value={<StatusLabel semanticRole={readiness.role}>{readiness.label["zh-TW"]}</StatusLabel>} />
    </SummaryStrip>

    <div className="commercial-location-grid">
      <div className="min-w-0">    {handoff.mapReady && coordinates ? <MapFrame
      title="目前物件位置與周邊證據"
      description={<><span className="block">{snapshot.property.normalizedAddress}</span><span className="block font-mono text-[11px]">{coordinates.latitude.toFixed(6)}, {coordinates.longitude.toFixed(6)}</span></>}
      attribution="地圖底圖依畫面標示；點位不是地籍界線"
      detail={<span>位置核對：{snapshot.property.checkedAt ?? "未提供"}</span>}
    >
      <GeoMap center={{ lat: coordinates.latitude, lng: coordinates.longitude }} zoom={16} categories={[]} centerLabel={snapshot.property.normalizedAddress} radiusMeters={snapshot.insight?.radius_m ?? 800} scrollWheelZoomEnabled={false} />
    </MapFrame> : <Message variant="warning" title="物件位置已變更，需重新確認">
      目前不把先前位置或通勤結果當作本案現況；完成物件位置重新確認後再查看地圖與路線。
    </Message>}

</div>
      <div className="min-w-0">    <Section title="目的地通勤證據" description="目的地路線與大眾運輸周邊資料是兩個獨立來源；其中一項不可用時，另一項仍可判讀。">
      <div data-evidence-key="commute" className="space-y-3">
      {handoff.selectedRoute && snapshot.transitContext?.status !== "resolved" && <Message variant="warning">目的地路線可用；大眾運輸周邊資料目前無法取得。</Message>}
      {handoff.mapReady && coordinates ? <CommuteEvidencePanel
        address={snapshot.property.normalizedAddress}
        locationResult={snapshot.insight ?? null}
        origin={{ latitude: coordinates.latitude, longitude: coordinates.longitude }}
        routeEvidence={snapshot.routeEvidence}
        transitResult={snapshot.transitContext}
        onRouteStatusChange={() => undefined}
        onRouteEvidence={persistRoute}
        onTransitStatusChange={() => undefined}
        onTransitResult={persistTransit}
      /> : <Message variant="warning">請先重新確認物件位置，再查詢目的地路線。</Message>}
      </div>
    </Section>

</div>
    </div>

    <Section title="重要周邊證據" description="以實際設施筆數與距離為主；設施較多不代表物件較好。">
      <div data-evidence-key="location" className="space-y-3">
      {snapshot.poiSummary ? <SummaryStrip label="周邊設施摘要" className="location-poi-summary">
        {(Object.keys(POI_LABELS) as Array<keyof typeof POI_LABELS>).map((key) => <MetricItem key={key} label={POI_LABELS[key]} value={snapshot.poiSummary?.[key] ?? "未提供"} />)}
      </SummaryStrip> : <Message variant="inline" title="尚未取得周邊設施摘要">此案件尚未保存可供判讀的周邊設施結果。</Message>}
      <div data-testid="poi-summary" className="sr-only">{snapshot.poiSummary ? Object.entries(POI_LABELS).map(([key, label]) => `${label} ${snapshot.poiSummary?.[key as keyof typeof snapshot.poiSummary] ?? "未提供"}`).join("；") : "尚未取得周邊設施摘要"}</div>
      {snapshot.insight && (!Array.isArray(snapshot.insight.nearest_pois) || snapshot.insight.nearest_pois.length === 0) && <Message variant="information" title="完整設施明細未隨案件保存">已保存的分類筆數仍可作為範圍參考；請勿由摘要重建或推測個別設施。需要最新明細時，應在原位置分析流程重新查詢。</Message>}
      </div>
    </Section>

    <Section title="次要社區背景" description="人口資料只協助理解行政區位，不作為物件好壞或投資判斷。">
      <DetailsDisclosure summary="次要里鄰人口背景">
        <DemographicsInsightCard village={snapshot.insight?.village_resolution} demographics={snapshot.insight?.demographics} />
      </DetailsDisclosure>
    </Section>

    <Section title="未知事項與限制">
      <div className="grid gap-3 md:grid-cols-2">
        <Panel variant="plain">
          <h2 className="text-subsection">目前限制</h2>
          <ul className="mt-2 space-y-1 text-dense">
            {handoff.unresolved.length ? handoff.unresolved.map((item) => <li key={item}>• {item}</li>) : <li>• 目前沒有阻擋此區段判讀的主要限制。</li>}
            {snapshot.insight?.data_quality?.warnings?.map((item) => <li key={item}>• {item}</li>)}
          </ul>
        </Panel>
        <Panel variant="plain">
          <h2 className="text-subsection">下一步</h2>
          <ul className="mt-2 space-y-1 text-dense">
            <li>• 加入工作地點、客戶據點或常用車站，逐一比較實際路線。</li>
            <li>• 對重要設施核對營業狀態、出入口與現場步行條件。</li>
            <li>• 將無法取得的資料列入看屋或客戶討論清單。</li>
          </ul>
        </Panel>
      </div>
    </Section>

    <EvidenceSection>
      <DetailsDisclosure summary="來源與查詢細節">
        <dl className="grid gap-3 text-dense sm:grid-cols-2">
          <SourceDetail label="物件位置" value={`${friendlySources(snapshot.property.sourceIds)}；核對時間 ${snapshot.property.checkedAt ?? "未提供"}`} />
          <SourceDetail label="行政位置" value={`${snapshot.property.village.name ?? "村里未確認"}${snapshot.insight?.village_resolution?.source_vintage ? `；圖資版本 ${snapshot.insight.village_resolution.source_vintage}` : ""}`} />
          <SourceDetail label="目的地路線" value={handoff.identityState !== "confirmed" ? "物件位置需重新確認" : snapshot.routeEvidence ? `${snapshot.routeEvidence.source === "google_routes" ? "Google Routes" : "模擬／備援路線"}；${snapshot.routeEvidence.checked_at}` : "尚未取得"} />
          <SourceDetail label="大眾運輸周邊" value={snapshot.transitContext ? `TDX；${snapshot.transitContext.source_updated_at ?? snapshot.transitContext.snapshot_generated_at ?? "日期未提供"}` : "尚未取得"} />
          <SourceDetail label="人口背景" value={snapshot.insight?.demographics?.status === "available" ? `RIS；統計期 ${snapshot.insight.demographics.statistic_yyymm ?? "未提供"}` : "目前無可用資料"} />
        </dl>
        {handoff.selectedRoute && <p className="mt-3 text-meta">已選路線：{handoff.selectedRoute.destination} · {MODE_LABELS[handoff.selectedRoute.mode]} · {formatDistance(handoff.selectedRoute.distanceM)} · {formatDuration(handoff.selectedRoute.durationMinutes)}</p>}
      </DetailsDisclosure>
    </EvidenceSection>
  </div>;
}

function friendlySources(sourceIds: string[]): string {
  if (!sourceIds.length) return "來源未提供";
  return sourceIds.map((source) => source === "google_geocoding" ? "Google 地址解析" : source === "tgos_geocoding" ? "TGOS 地址解析" : source === "nlsc_village_boundary" ? "NLSC 村里界" : "使用者確認").join("、");
}

function SourceDetail({ label, value }: { label: string; value: string }) {
  return <div><dt className="font-bold text-slate-800">{label}</dt><dd className="mt-1 break-words text-slate-600">{value}</dd></div>;
}
