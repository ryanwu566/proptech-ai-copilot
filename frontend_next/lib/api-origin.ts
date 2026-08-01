export type ApiRuntimeEnvironment = "development" | "test" | "preview" | "production";

export type ApiOriginOptions = {
  configuredOrigin?: string;
  environment?: ApiRuntimeEnvironment;
  allowRelativeProxy?: boolean;
};

const LOCAL_API_ORIGIN = "http://localhost:8000";

function isLocalHost(hostname: string): boolean {
  const host = hostname.toLowerCase().replace(/\.$/, "");
  return host === "localhost" || host === "127.0.0.1" || host === "::1" || host === "[::1]";
}

function normalizedOrigin(value: string): string | null {
  try {
    const parsed = new URL(value);
    if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password || parsed.pathname !== "/" || parsed.search || parsed.hash) {
      return null;
    }
    return parsed.origin.replace(/\/+$/, "");
  } catch {
    return null;
  }
}

export function resolveApiOrigin(options: ApiOriginOptions = {}): string {
  const environment = options.environment ?? (process.env.NODE_ENV === "development" ? "development" : "production");
  const configured = options.configuredOrigin?.trim() ?? "";

  if (!configured) {
    if (environment === "development") return LOCAL_API_ORIGIN;
    if (environment === "test" && options.allowRelativeProxy) return "";
    throw new Error("NEXT_PUBLIC_API_BASE_URL is required outside local development.");
  }
  if (configured.startsWith("/")) {
    if (options.allowRelativeProxy && (environment === "test" || environment === "preview")) return configured.replace(/\/+$/, "") || "/";
    throw new Error("A relative API origin is not allowed for this environment.");
  }
  const origin = normalizedOrigin(configured);
  if (!origin) throw new Error("NEXT_PUBLIC_API_BASE_URL must be an absolute HTTP(S) origin.");
  if (environment === "production" && isLocalHost(new URL(origin).hostname)) {
    throw new Error("A localhost API origin is not allowed in production.");
  }
  if (environment === "preview" && isLocalHost(new URL(origin).hostname)) {
    throw new Error("A localhost API origin is not allowed in preview.");
  }
  if (environment === "production" && new URL(origin).protocol !== "https:") {
    throw new Error("Production API origin must use HTTPS.");
  }
  return origin;
}
