import { notFound } from "next/navigation";
import { PropertyIdentityPreview } from "@/components/property-identity-preview";

export default async function PropertyIdentityPreviewPage({ searchParams }: { searchParams: Promise<{ state?: string }> }) {
  if (process.env.NODE_ENV !== "development" && process.env.NEXT_PUBLIC_APP_ENV !== "test") notFound();
  const state = (await searchParams).state ?? "default";
  return <PropertyIdentityPreview state={state} />;
}
