import type { Metadata } from "next";
import { VNextPropertyIdentityWorkflow } from "@/components/vnext-property-identity-workflow";
import { VNextAuthGate } from "@/components/vnext-auth-gate";

export const metadata: Metadata = {
  title: "Property identity human review | PropTech AI Copilot",
  description: "Feature-gated property identity candidate review and explicit human confirmation.",
};

export default function PropertyIdentityPage() {
  return <VNextAuthGate><VNextPropertyIdentityWorkflow /></VNextAuthGate>;
}
