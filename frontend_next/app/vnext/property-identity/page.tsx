import type { Metadata } from "next";
import { VNextPropertyIdentityWorkflow } from "@/components/vnext-property-identity-workflow";

export const metadata: Metadata = {
  title: "Property identity human review | PropTech AI Copilot",
  description: "Feature-gated property identity candidate review and explicit human confirmation.",
};

export default function PropertyIdentityPage() {
  return <VNextPropertyIdentityWorkflow />;
}
