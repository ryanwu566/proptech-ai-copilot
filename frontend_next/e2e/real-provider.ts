export function realProviderUrl(path: string): string {
  const configured = process.env.REAL_PROVIDER_API_BASE_URL?.trim();
  if (!configured) throw new Error("REAL_PROVIDER_API_BASE_URL is required for @real-provider tests.");
  const base = new URL(configured);
  if (base.protocol !== "https:" && base.protocol !== "http:") {
    throw new Error("REAL_PROVIDER_API_BASE_URL must use HTTP or HTTPS.");
  }
  return new URL(path, `${base.toString().replace(/\/$/, "")}/`).toString();
}
