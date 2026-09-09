import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MapWorkspace } from "@/components/vnext-map";
import { syntheticMapWorkspace } from "@/lib/vnext-map-preview/fixtures";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Spatial Map Workspace component preview",
  description: "Development-only synthetic preview for reusable Map Workspace frontend components.",
  robots: { index: false, follow: false, nocache: true },
};

export default function SpatialMapPreviewPage() {
  if (process.env.NODE_ENV !== "development") notFound();
  return <MapWorkspace workspace={syntheticMapWorkspace} />;
}
