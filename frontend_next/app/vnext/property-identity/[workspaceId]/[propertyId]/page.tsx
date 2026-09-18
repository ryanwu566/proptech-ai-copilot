import type { Metadata } from "next";
import { PropertyIdentityLiveRoute } from "@/components/property-identity-live-route";
import { VNextAuthGate } from "@/components/vnext-auth-gate";

export const metadata: Metadata = {
  title: "房產識別審閱 | PropTech AI Copilot",
  description: "審閱房產的地號、建號、關係與證據狀態。",
};

export default async function PropertyIdentityLivePage({ params }: { params: Promise<{ workspaceId: string; propertyId: string }> }) {
  const { workspaceId, propertyId } = await params;
  return <VNextAuthGate><PropertyIdentityLiveRoute workspaceId={workspaceId} propertyId={propertyId} /></VNextAuthGate>;
}
