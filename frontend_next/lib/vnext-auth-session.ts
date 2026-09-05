"use client";

export type AccessTokenResult =
  | { status: "authenticated"; accessToken: string }
  | { status: "missing_session" }
  | { status: "configuration_error" };

type StoredSession = {
  record: Record<string, unknown>;
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
};

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function allowedBrowserUrl(rawUrl: string): URL | null {
  try {
    const url = new URL(rawUrl);
    if (url.username || url.password || url.pathname !== "/" || url.search || url.hash) return null;
    if (url.protocol === "https:" || (url.protocol === "http:" && ["localhost", "127.0.0.1", "e2e.test"].includes(url.hostname))) return url;
  } catch { /* Fail closed below. */ }
  return null;
}

function authStorageKey(url: URL): string | null {
  const configured = process.env.NEXT_PUBLIC_SUPABASE_AUTH_STORAGE_KEY?.trim();
  if (configured) return /^sb-[a-z0-9-]{1,100}-auth-token$/i.test(configured) ? configured : null;
  if (!url.hostname.endsWith(".supabase.co")) return null;
  const projectReference = url.hostname.slice(0, -".supabase.co".length);
  return /^[a-z0-9-]{1,100}$/i.test(projectReference) ? `sb-${projectReference}-auth-token` : null;
}

function jwtPayload(token: string): Record<string, unknown> | null {
  const parts = token.split(".");
  if (parts.length !== 3 || parts.some((part) => !/^[A-Za-z0-9_-]+$/.test(part))) return null;
  try {
    const encoded = parts[1].replaceAll("-", "+").replaceAll("_", "/");
    const padded = encoded.padEnd(Math.ceil(encoded.length / 4) * 4, "=");
    return record(JSON.parse(atob(padded)) as unknown);
  } catch { return null; }
}

function jwtExpiry(accessToken: string): number | null {
  const payload = jwtPayload(accessToken);
  return payload && typeof payload.exp === "number" && Number.isSafeInteger(payload.exp) ? payload.exp : null;
}

function allowedPublishableKey(key: string): boolean {
  if (key.length < 20 || key.length > 2048) return false;
  if (/^sb_publishable_[A-Za-z0-9_-]{8,2030}$/.test(key)) return true;
  return jwtPayload(key)?.role === "anon";
}

function storedSession(storageKey: string): StoredSession | null {
  try {
    const parsed = record(JSON.parse(window.localStorage.getItem(storageKey) ?? "null") as unknown);
    if (!parsed) return null;
    const accessToken = typeof parsed.access_token === "string" ? parsed.access_token.trim() : "";
    const refreshToken = typeof parsed.refresh_token === "string" ? parsed.refresh_token.trim() : "";
    const expiresAt = jwtExpiry(accessToken);
    if (accessToken.length < 20 || accessToken.length > 16_384 || refreshToken.length < 8 || refreshToken.length > 4096 || expiresAt === null) return null;
    return { record: parsed, accessToken, refreshToken, expiresAt };
  } catch { return null; }
}

async function refreshSession(url: URL, publishableKey: string, storageKey: string, previous: StoredSession): Promise<StoredSession | null> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 10_000);
  try {
    const response = await fetch(`${url.origin}/auth/v1/token?grant_type=refresh_token`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json", apikey: publishableKey },
      body: JSON.stringify({ refresh_token: previous.refreshToken }),
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) return null;
    const payload = record(await response.json() as unknown);
    if (!payload) return null;
    const accessToken = typeof payload.access_token === "string" ? payload.access_token.trim() : "";
    const refreshToken = typeof payload.refresh_token === "string" ? payload.refresh_token.trim() : "";
    const expiresIn = typeof payload.expires_in === "number" && Number.isFinite(payload.expires_in) ? payload.expires_in : 0;
    const expiresAt = jwtExpiry(accessToken);
    if (accessToken.length < 20 || accessToken.length > 16_384 || refreshToken.length < 8 || refreshToken.length > 4096 || expiresAt === null || expiresAt <= Math.floor(Date.now() / 1000) + 30 || expiresIn <= 0 || expiresIn > 604_800) return null;
    const updated: Record<string, unknown> = { ...previous.record, ...payload, access_token: accessToken, refresh_token: refreshToken, expires_at: expiresAt };
    window.localStorage.setItem(storageKey, JSON.stringify(updated));
    return { record: updated, accessToken, refreshToken, expiresAt };
  } catch { return null; }
  finally { window.clearTimeout(timeout); }
}

export async function getVNextAccessToken(): Promise<AccessTokenResult> {
  const url = allowedBrowserUrl(process.env.NEXT_PUBLIC_SUPABASE_URL?.trim() ?? "");
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim() ?? "";
  if (!url || !allowedPublishableKey(publishableKey)) return { status: "configuration_error" };
  const storageKey = authStorageKey(url);
  if (!storageKey) return { status: "configuration_error" };
  const session = storedSession(storageKey);
  if (!session) return { status: "missing_session" };
  if (session.expiresAt > Math.floor(Date.now() / 1000) + 60) return { status: "authenticated", accessToken: session.accessToken };
  const refreshed = await refreshSession(url, publishableKey, storageKey, session);
  return refreshed ? { status: "authenticated", accessToken: refreshed.accessToken } : { status: "missing_session" };
}
