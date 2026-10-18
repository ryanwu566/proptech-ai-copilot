"use client";
import { API_BASE } from "@/lib/api";
import { getVNextAccessToken, getVNextAuthClient, getVNextSessionGeneration, isVNextSessionGenerationCurrent, expireVNextSession } from "@/lib/vnext-auth-session";
import { readAdmin, adminRequest } from "./transport";
import type { AdminSection } from "./model";

export function loadAdminSection(section: AdminSection, cursor: string | null, signal: AbortSignal) {
  return readAdmin({ base: API_BASE, fetcher: fetch, session: getVNextAccessToken, generation: getVNextSessionGeneration,
    current: isVNextSessionGenerationCurrent, expire: expireVNextSession,
    ready: async () => { await getVNextAuthClient()?.auth.getSession(); } }, section, cursor, signal);
}

export function requestAdmin(path: string, body?: object, signal?: AbortSignal) {
  return adminRequest({ base: API_BASE, fetcher: fetch, session: getVNextAccessToken, generation: getVNextSessionGeneration,
    current: isVNextSessionGenerationCurrent, expire: expireVNextSession,
    ready: async () => { await getVNextAuthClient()?.auth.getSession(); } }, path, body, signal);
}
