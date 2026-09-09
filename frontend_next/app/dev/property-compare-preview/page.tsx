import type { Metadata } from "next";
import { notFound } from "next/navigation";

export const metadata: Metadata = {
  title: "本機物件比較預覽",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function PropertyComparePreviewPage() {
  if (process.env.NODE_ENV === "production") notFound();
  const { PropertyComparePreview } = await import("./preview-client");
  return <PropertyComparePreview />;
}
