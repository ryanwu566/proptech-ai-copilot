import { runProviderHealth } from "./provider-health";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const runtime = "nodejs";

export async function GET(): Promise<Response> {
  const health = await runProviderHealth({
    env: process.env,
    fetchImpl: fetch,
  });

  return Response.json(health, {
    headers: {
      "Cache-Control": "no-store, max-age=0",
    },
  });
}
