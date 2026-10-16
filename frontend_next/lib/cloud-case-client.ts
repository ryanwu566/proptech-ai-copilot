"use client";
import { API_BASE } from "@/lib/api";
import { expireVNextSession, getVNextAccessToken, getVNextSessionGeneration, isVNextSessionGenerationCurrent } from "@/lib/vnext-auth-session";
import { validActivity, validCloudCase, validCloudSummary, type CloudActivity, type CloudCase, type CloudResult, type CloudSummary, type ImportPreview } from "@/lib/cloud-case-contract";

async function request<T>(path: string, method: string, validate: (v: unknown) => v is T, body?: unknown, canSend: () => boolean = () => true): Promise<CloudResult<T>> {
  if (typeof navigator !== "undefined" && !navigator.onLine) return { status: "offline" };
  if (!canSend()) return { status: "sign_in_required" };
  const session = await getVNextAccessToken();
  if (session.status !== "authenticated") return { status: "sign_in_required" };
  if (!canSend()) return { status: "sign_in_required" };
  if (!API_BASE) return { status: "unavailable" };
  const generation = getVNextSessionGeneration();
  try {
    const response = await fetch(`${API_BASE}/v1/saved-cases${path}`, {
      method, headers: { Authorization: `Bearer ${session.accessToken}`, Accept: "application/json", ...(body ? { "Content-Type": "application/json" } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}), credentials: "omit", cache: "no-store", redirect: "error", signal: AbortSignal.timeout(10_000),
    });
    if (!isVNextSessionGenerationCurrent(generation)) return { status: "sign_in_required" };
    if (response.status === 401) { await expireVNextSession(generation, session.accessToken); return { status: "sign_in_required" }; }
    if (response.status === 409) return { status: "conflict" };
    if ([403, 404].includes(response.status)) return { status: "forbidden" };
    if (response.status === 422) return { status: "invalid" };
    if (response.status === 503) {
      const error: unknown = await response.json();
      if (!isVNextSessionGenerationCurrent(generation)) return { status: "sign_in_required" };
      const pending = error && typeof error === "object" && "error" in error ? error.error as { details?: { reason_code?: string } } : null;
      return { status: pending?.details?.reason_code === "persistence_pending" ? "persistence_pending" : "unavailable" };
    }
    if (!response.ok) return { status: "unavailable" };
    const value: unknown = await response.json();
    if (!isVNextSessionGenerationCurrent(generation)) return { status: "sign_in_required" };
    return validate(value) ? { status: "ready", value } : { status: "unavailable" };
  } catch { return { status: isVNextSessionGenerationCurrent(generation) ? "unavailable" : "sign_in_required" }; }
}

const casePath = (id: string) => `/${encodeURIComponent(id)}`;
export const cloudCases = {
  list: (scope: "owned" | "shared", offset = 0) => request(`?scope=${scope}&limit=20&offset=${offset}`, "GET", (v): v is CloudSummary[] => Array.isArray(v) && v.length <= 20 && v.every(validCloudSummary)),
  open: (id: string) => request(casePath(id), "GET", validCloudCase),
  create: (preview: ImportPreview, canSend?: () => boolean) => request("", "POST", validCloudCase, preview, canSend),
  metadata: (row: CloudCase, title: string, notes: string) => request(`${casePath(row.id)}/metadata`, "PATCH", validCloudCase, { expected_revision: row.revision, title, notes }),
  membership: (row: CloudCase, member_id: string, role: "editor" | "viewer" | null) => request(`${casePath(row.id)}/membership`, "PUT", validCloudCase, { expected_revision: row.revision, member_id, role }),
  monitoring: (row: CloudCase, cadence: "off" | "daily" | "weekly") => request(`${casePath(row.id)}/monitoring`, "PUT", validCloudCase, { expected_revision: row.revision, cadence, refresh_policy: "manual_only" }),
  activity: (id: string, offset = 0) => request(`${casePath(id)}/activity?limit=20&offset=${offset}`, "GET", (v): v is CloudActivity[] => Array.isArray(v) && v.length <= 20 && v.every(validActivity)),
};
