import { ConsumerAccount } from "@/components/account/consumer-account";
export default async function SignupPage({ searchParams }: { searchParams: Promise<{ next?: string | string[] }> }) {
  const { next } = await searchParams;
  return <ConsumerAccount mode="signup" returnIntent={typeof next === "string" ? next : null} />;
}
