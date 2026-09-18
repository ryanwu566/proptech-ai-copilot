"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

export type AccessTokenResult =
  | { status: "authenticated"; accessToken: string }
  | { status: "missing_session" | "expired_session" | "configuration_error" };

export const V_NEXT_SESSION_EXPIRED_EVENT = "vnext-session-expired";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
let browserClient: SupabaseClient | null = null;
let unusableSession = false;
let sessionGeneration = 0;
let hadValidSession = false;
let clearingPromise: Promise<void> | null = null;

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function jwtPart(token: string, index: number): Record<string, unknown> | null {
  const parts = token.split(".");
  if (parts.length !== 3 || parts.some((part) => !/^[A-Za-z0-9_-]+$/.test(part))) return null;
  try {
    const encoded = parts[index].replaceAll("-", "+").replaceAll("_", "/");
    return record(JSON.parse(atob(encoded.padEnd(Math.ceil(encoded.length / 4) * 4, "="))) as unknown);
  } catch { return null; }
}

function browserConfig(): { url: string; key: string } | null {
  const rawUrl = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim() ?? "";
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim() ?? "";
  if (!/^sb_publishable_[A-Za-z0-9_-]{8,2030}$/.test(key)) return null;
  try {
    const url = new URL(rawUrl);
    if (url.username || url.password || url.pathname !== "/" || url.search || url.hash) return null;
    if (url.protocol === "https:" && /^[a-z0-9-]+\.supabase\.co$/i.test(url.hostname)) return { url: url.origin, key };
    if (process.env.NODE_ENV === "development" && url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname)) {
      return { url: url.origin, key };
    }
  } catch { /* Invalid configuration fails closed. */ }
  return null;
}

export function getVNextAuthClient(): SupabaseClient | null {
  if (typeof window === "undefined") return null;
  const config = browserConfig();
  if (!config) return null;
  if (!browserClient) {
    browserClient = createClient(config.url, config.key, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
    });
    browserClient.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_IN") { sessionGeneration += 1; unusableSession = false; }
      if (event === "SIGNED_OUT") { sessionGeneration += 1; unusableSession = true; hadValidSession = false; }
    });
  }
  return browserClient;
}

export function getVNextSessionGeneration(): number { return sessionGeneration; }
export function isVNextSessionGenerationCurrent(generation: number): boolean {
  return generation === sessionGeneration && !unusableSession;
}

function tokenExpiry(token: string, issuer: string): number | null {
  if (token.length < 20 || token.length > 16_384) return null;
  const header = jwtPart(token, 0);
  const payload = jwtPart(token, 1);
  const audience = payload?.aud;
  if (!header || !["RS256", "ES256"].includes(String(header.alg)) || typeof header.kid !== "string" || !header.kid
    || !payload || payload.iss !== issuer
    || !(audience === "authenticated" || (Array.isArray(audience) && audience.includes("authenticated")))
    || payload.role !== "authenticated" || typeof payload.sub !== "string" || !UUID_PATTERN.test(payload.sub)
    || typeof payload.exp !== "number" || !Number.isSafeInteger(payload.exp)) return null;
  return payload.exp;
}

function validToken(token: string): boolean {
  const config = browserConfig();
  const expiry = config ? tokenExpiry(token, `${config.url}/auth/v1`) : null;
  return expiry !== null && expiry > Math.floor(Date.now() / 1000) + 30;
}

async function clearSession(expired: boolean): Promise<void> {
  if (!clearingPromise) {
    unusableSession = true;
    sessionGeneration += 1;
    hadValidSession = false;
    const client = getVNextAuthClient();
    clearingPromise = (async () => {
      if (client) {
        try { await client.auth.signOut({ scope: "local" }); } catch { /* Rejected session remains unusable in this tab. */ }
      }
    })();
  }
  await clearingPromise;
  clearingPromise = null;
  if (expired) window.dispatchEvent(new Event(V_NEXT_SESSION_EXPIRED_EVENT));
}

export async function getVNextAccessToken(): Promise<AccessTokenResult> {
  const client = getVNextAuthClient();
  const config = browserConfig();
  if (!client || !config) return { status: "configuration_error" };
  if (unusableSession) return { status: "missing_session" };
  const generation = sessionGeneration;
  try {
    const { data, error } = await client.auth.getSession();
    if (!isVNextSessionGenerationCurrent(generation)) return { status: "missing_session" };
    if (error) { await clearSession(true); return { status: "expired_session" }; }
    if (!data.session) {
      if (hadValidSession) { await clearSession(true); return { status: "expired_session" }; }
      return { status: "missing_session" };
    }
    let accessToken = data.session.access_token;
    const expiry = tokenExpiry(accessToken, `${config.url}/auth/v1`);
    if (expiry === null) { await clearSession(true); return { status: "expired_session" }; }
    if (expiry <= Math.floor(Date.now() / 1000) + 60) {
      const refreshed = await client.auth.refreshSession();
      if (!isVNextSessionGenerationCurrent(generation)) return { status: "missing_session" };
      if (refreshed.error || !refreshed.data.session) { await clearSession(true); return { status: "expired_session" }; }
      accessToken = refreshed.data.session.access_token;
    }
    if (!validToken(accessToken)) { await clearSession(true); return { status: "expired_session" }; }
    if (!isVNextSessionGenerationCurrent(generation)) return { status: "missing_session" };
    hadValidSession = true;
    return { status: "authenticated", accessToken };
  } catch {
    if (!isVNextSessionGenerationCurrent(generation)) return { status: "missing_session" };
    await clearSession(true);
    return { status: "expired_session" };
  }
}

export async function signInVNext(email: string, password: string): Promise<boolean> {
  const client = getVNextAuthClient();
  if (!client) return false;
  try {
    if (clearingPromise) await clearingPromise;
    const { data, error } = await client.auth.signInWithPassword({ email, password });
    if (error || !data.session || !validToken(data.session.access_token)) {
      if (data.session) await clearSession(false);
      return false;
    }
    unusableSession = false;
    sessionGeneration += 1;
    hadValidSession = true;
    return true;
  } catch { return false; }
}

export async function signOutVNext(): Promise<void> {
  await clearSession(false);
}

export async function expireVNextSession(expectedGeneration: number, expectedAccessToken: string): Promise<boolean> {
  if (!isVNextSessionGenerationCurrent(expectedGeneration)) return false;
  const client = getVNextAuthClient();
  if (!client) return false;
  try {
    const { data, error } = await client.auth.getSession();
    if (error || !data.session || data.session.access_token !== expectedAccessToken
      || !isVNextSessionGenerationCurrent(expectedGeneration)) return false;
    await clearSession(true);
    return true;
  } catch { return false; }
}
