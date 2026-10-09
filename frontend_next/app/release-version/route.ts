import { NextResponse } from "next/server";

// The value is bound at build time in next.config.mjs; no local git fallback.
export function GET() {
  const sha = process.env.NEXT_PUBLIC_RELEASE_COMMIT_SHA ?? "";
  return NextResponse.json({
    product: "proptech-ai-copilot-frontend",
    commit_sha: /^[a-f0-9]{40}$/i.test(sha) ? sha.toLowerCase() : "unconfigured",
    release_version: process.env.NEXT_PUBLIC_RELEASE_VERSION ?? "unconfigured",
    environment: process.env.NEXT_PUBLIC_RELEASE_ENVIRONMENT ?? "unconfigured",
  }, { headers: { "Cache-Control": "no-store" } });
}
