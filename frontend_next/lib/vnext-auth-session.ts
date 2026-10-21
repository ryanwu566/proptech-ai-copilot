"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { publishAuthSessionStatus, V_NEXT_SESSION_EXPIRED_EVENT } from "./auth-session-status";

export type AccessTokenResult =
  | { status: "authenticated"; accessToken: string }
  | { status: "missing_session" | "expired_session" | "configuration_error" };

export { V_NEXT_SESSION_EXPIRED_EVENT } from "./auth-session-status";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
let browserClient: SupabaseClient | null = null;
let unusableSession = false;
let sessionGeneration = 0;
let hadValidSession = false;
let clearingPromise: Promise<boolean> | null = null;
let sessionEndGeneration = 0;
const pendingSessionWrites = new Set<Promise<unknown>>();

async function sessionWrite<T>(operation: () => Promise<T>): Promise<T> {
  const pending = operation();
  pendingSessionWrites.add(pending);
  try { return await pending; }
  finally { pendingSessionWrites.delete(pending); }
}

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
      global: { fetch: (input, init) => fetch(input, {
        ...init,
        signal: init?.signal ? AbortSignal.any([init.signal, AbortSignal.timeout(10_000)]) : AbortSignal.timeout(10_000),
      }) },
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
    });
    browserClient.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_IN" && !clearingPromise) { sessionGeneration += 1; unusableSession = false; }
      if (event === "SIGNED_OUT") {
        sessionEndGeneration += 1; sessionGeneration += 1; unusableSession = true; hadValidSession = false;
        // A signout notification from another tab must also drain local writes.
        // Do not await SDK calls inside its auth-state callback.
        if (pendingSessionWrites.size && !clearingPromise) void clearSession(false);
      }
      if (["INITIAL_SESSION", "SIGNED_IN", "SIGNED_OUT", "TOKEN_REFRESHED"].includes(event)) {
        publishAuthSessionStatus(async () => (await getVNextAccessToken()).status === "authenticated");
      }
    });
    // Preserve in-memory sessions when storage is unavailable or entry controls
    // remount after navigating away from an account route.
    publishAuthSessionStatus(async () => (await getVNextAccessToken()).status === "authenticated");
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

async function clearSession(expired: boolean): Promise<boolean> {
  if (!clearingPromise) {
    unusableSession = true;
    sessionEndGeneration += 1;
    sessionGeneration += 1;
    hadValidSession = false;
    const client = getVNextAuthClient();
    clearingPromise = (async () => {
      // SDK password/signup requests can persist sessions outside its read lock.
      // Invalidate immediately, then drain bounded writes before SDK local logout.
      // Late SIGNED_IN events cannot reopen access while logout is pending.
      await Promise.allSettled([...pendingSessionWrites]);
      if (client) {
        try { return !(await client.auth.signOut({ scope: "local" })).error; } catch { return false; }
      }
      return false;
    })();
  }
  const cleared = await clearingPromise;
  clearingPromise = null;
  if (expired) window.dispatchEvent(new Event(V_NEXT_SESSION_EXPIRED_EVENT));
  return cleared;
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
    const generation = sessionEndGeneration;
    const { data, error } = await sessionWrite(() => client.auth.signInWithPassword({ email, password }));
    if (generation !== sessionEndGeneration) return false;
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

export async function signOutVNext(): Promise<boolean> {
  return clearSession(false);
}

export type ConsumerAuthResult = { status: "authenticated" | "confirmation_required" | "request_accepted" | "configuration_unavailable" | "validation_error" | "provider_error" };

export function validConsumerEmail(email: string): boolean {
  return email.trim().length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

export async function signUpVNext(email: string, password: string): Promise<ConsumerAuthResult> {
  if (!validConsumerEmail(email) || password.length < 8 || password.length > 1024) return { status: "validation_error" };
  const client = getVNextAuthClient();
  if (!client) return { status: "configuration_unavailable" };
  try {
    if (clearingPromise) await clearingPromise;
    const generation = sessionEndGeneration;
    const { data, error } = await sessionWrite(() => client.auth.signUp({ email: email.trim(), password }));
    if (generation !== sessionEndGeneration) return { status: "provider_error" };
    if (error) return { status: ["user_already_exists", "email_exists"].includes(error.code ?? "") ? "request_accepted" : "provider_error" };
    if (data.session) {
      if (!validToken(data.session.access_token)) { await clearSession(false); return { status: "provider_error" }; }
      unusableSession = false;
      sessionGeneration += 1;
      hadValidSession = true;
      return { status: "authenticated" };
    }
    // No delivery assertion, even when the provider returns an obfuscated user.
    return { status: data.user ? "confirmation_required" : "request_accepted" };
  } catch { return { status: "provider_error" }; }
}

export async function requestPasswordResetVNext(email: string): Promise<ConsumerAuthResult> {
  if (!validConsumerEmail(email)) return { status: "validation_error" };
  const client = getVNextAuthClient();
  if (!client) return { status: "configuration_unavailable" };
  try {
    // Provider Site URL/email template owns the recovery destination. Never accept a user redirect.
    const { error } = await client.auth.resetPasswordForEmail(email.trim());
    return { status: error ? "provider_error" : "request_accepted" };
  } catch { return { status: "provider_error" }; }
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
