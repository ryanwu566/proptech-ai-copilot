import { ConsumerAccount } from "@/components/account/consumer-account";
export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string | string[] }> }) {
  const { next } = await searchParams;
  return <ConsumerAccount mode="login" returnIntent={typeof next === "string" ? next : null} />;
}
