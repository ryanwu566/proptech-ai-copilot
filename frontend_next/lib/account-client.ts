"use client";
import { API_BASE } from "@/lib/api";
import { expireVNextSession, getVNextAccessToken, getVNextAuthClient, getVNextSessionGeneration, isVNextSessionGenerationCurrent } from "@/lib/vnext-auth-session";

export type ConsumerAccount = {
  user_id: string; status: "active" | "suspended"; platform_role: "consumer" | "platform_admin";
  created_at: string; updated_at: string;
};
export type AccountState =
  | { status: "ready"; account: ConsumerAccount; email: string | null }
  | { status: "missing_session" | "expired_session" | "configuration_unavailable" | "account_unavailable" };

export async function restoreConsumerAccount(): Promise<AccountState> {
  const session = await getVNextAccessToken();
  if (session.status !== "authenticated") return { status: session.status === "configuration_error" ? "configuration_unavailable" : session.status };
  if (!API_BASE) return { status: "configuration_unavailable" };
  const generation = getVNextSessionGeneration();
  try {
    const response = await fetch(`${API_BASE}/v1/account`, {
      headers: { Authorization: `Bearer ${session.accessToken}`, Accept: "application/json" },
      credentials: "omit", cache: "no-store", redirect: "error", signal: AbortSignal.timeout(10_000),
    });
    if (!isVNextSessionGenerationCurrent(generation)) return { status: "missing_session" };
    if (response.status === 401) {
      await expireVNextSession(generation, session.accessToken);
      return { status: "expired_session" };
    }
    if (!response.ok) return { status: "account_unavailable" };
    const value: unknown = await response.json();
    if (!value || typeof value !== "object") return { status: "account_unavailable" };
    const a = value as Record<string, unknown>;
    const { data, error } = await getVNextAuthClient()!.auth.getSession();
    if (!isVNextSessionGenerationCurrent(generation)) return { status: "missing_session" };
    if (error || !data.session || data.session.access_token !== session.accessToken) return { status: "missing_session" };
    if (a.user_id !== data.session.user.id || !["active", "suspended"].includes(String(a.status))
      || !["consumer", "platform_admin"].includes(String(a.platform_role))
      || typeof a.created_at !== "string" || !Number.isFinite(Date.parse(a.created_at))
      || typeof a.updated_at !== "string" || !Number.isFinite(Date.parse(a.updated_at))) return { status: "account_unavailable" };
    return { status: "ready", account: a as ConsumerAccount, email: data.session.user.email ?? null };
  } catch {
    return { status: isVNextSessionGenerationCurrent(generation) ? "account_unavailable" : "missing_session" };
  }
}
