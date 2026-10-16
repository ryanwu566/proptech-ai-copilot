// @ts-expect-error Native TS test runner uses explicit extensions.
import { parseSnapshot, sections, type AdminSection, type AdminSnapshot } from "./model.ts";

export type AdminErrorCode = "authentication" | "denied" | "configuration" | "error" | "cancelled" | "not_found" | "conflict" | "invalid_command";
export class AdminReadError extends Error {
  code: AdminErrorCode;
  constructor(code: AdminErrorCode) { super(code); this.code = code; }
}
export type AdminTransport = {
  base: string;
  fetcher: typeof fetch;
  session: () => Promise<{ status: "authenticated"; accessToken: string } | { status: "missing_session" | "expired_session" | "configuration_error" }>;
  generation: () => number;
  current: (generation: number) => boolean;
  expire: (generation: number, token: string) => Promise<unknown>;
  ready?: () => Promise<unknown>;
};

/** Closed Admin endpoints only. A caller retains the same body for safe retry. */
export async function adminRequest(deps: AdminTransport, path: string, body?: object, signal?: AbortSignal): Promise<unknown> {
  if (!/^\/(?:accounts\/[a-f0-9-]{36}(?:\/commands)?|quota-policy(?:\/commands)?)$/.test(path)) throw new AdminReadError('error');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  const combined = signal ? AbortSignal.any([signal, controller.signal]) : controller.signal;
  try {
    if (!deps.base) throw new AdminReadError('configuration');
    if (deps.ready) await withinSignal(deps.ready, combined);
    const generation = deps.generation();
    const session = await withinSignal(deps.session, combined);
    if (session.status !== 'authenticated') throw new AdminReadError(session.status === 'configuration_error' ? 'configuration' : 'authentication');
    if (!deps.current(generation)) throw new AdminReadError('authentication');
    const fetcher = deps.fetcher;
    const response = await fetcher(`${deps.base}/v1/admin${path}`, {
      method: body ? 'POST' : 'GET', body: body ? JSON.stringify(body) : undefined,
      headers: { Authorization: `Bearer ${session.accessToken}`, Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}) },
      cache: 'no-store', credentials: 'omit', redirect: 'error', signal: combined,
    });
    if (response.status === 401) { await withinSignal(() => deps.expire(generation, session.accessToken), combined); throw new AdminReadError('authentication'); }
    if (response.status === 403) throw new AdminReadError('denied');
    if (response.status === 404) throw new AdminReadError('not_found');
    if (response.status === 409) throw new AdminReadError('conflict');
    if (response.status === 422) throw new AdminReadError('invalid_command');
    if (!response.ok) throw new AdminReadError('error');
    const result = await boundedJson(response);
    if (!deps.current(generation)) throw new AdminReadError('authentication');
    if (combined.aborted) throw new AdminReadError('cancelled');
    return result;
  } catch (error) {
    if (signal?.aborted) throw new AdminReadError('cancelled');
    if (error instanceof AdminReadError) throw error;
    throw new AdminReadError('error');
  } finally { clearTimeout(timeout); }
}

function withinSignal<T>(operation: () => Promise<T>, signal: AbortSignal): Promise<T> {
  return new Promise((resolve, reject) => {
    const abort = () => reject(new AdminReadError("error"));
    if (signal.aborted) { abort(); return; }
    signal.addEventListener("abort", abort, { once: true });
    Promise.resolve().then(operation).then(resolve, reject).finally(() => signal.removeEventListener("abort", abort));
  });
}

async function boundedJson(response: Response): Promise<unknown> {
  const reader = response.body?.getReader();
  if (!reader) throw new AdminReadError("error");
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > 262_144) throw new AdminReadError("error");
      chunks.push(value);
    }
  } finally { await reader.cancel().catch(() => {}); }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return JSON.parse(new TextDecoder().decode(bytes)) as unknown;
}

export async function readAdmin(deps: AdminTransport, section: AdminSection, cursor: string | null = null, signal?: AbortSignal): Promise<AdminSnapshot> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  const combined = signal ? AbortSignal.any([controller.signal, signal]) : controller.signal;
  try {
    if (combined.aborted) throw new AdminReadError("cancelled");
    if (!deps.base) throw new AdminReadError("configuration");
    if (!sections.includes(section) || (cursor !== null && !/^[A-Za-z0-9_-]{1,128}$/.test(cursor))) throw new AdminReadError("error");
    // Existing SDK recovery may emit SIGNED_IN and advance the session generation.
    if (deps.ready) await withinSignal(deps.ready, combined);
    const generation = deps.generation();
    const session = await withinSignal(deps.session, combined);
    if (session.status !== "authenticated") throw new AdminReadError(session.status === "configuration_error" ? "configuration" : "authentication");
    if (!deps.current(generation)) throw new AdminReadError("authentication");
    if (combined.aborted) throw new AdminReadError("cancelled");
    const fetcher = deps.fetcher;
    const response = await fetcher(`${deps.base}/v1/admin/${section}${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`, {
      headers: { Authorization: `Bearer ${session.accessToken}`, Accept: "application/json" },
      method: "GET", cache: "no-store", credentials: "omit", redirect: "error", signal: combined,
    });
    if (!deps.current(generation)) throw new AdminReadError("authentication");
    if (response.status === 401) { await withinSignal(() => deps.expire(generation, session.accessToken), combined); throw new AdminReadError("authentication"); }
    if (response.status === 403) throw new AdminReadError("denied");
    if (!response.ok) throw new AdminReadError("error");
    const body = await boundedJson(response);
    const result = parseSnapshot(body, section);
    if (!deps.current(generation)) throw new AdminReadError("authentication");
    if (combined.aborted) throw new AdminReadError("cancelled");
    return result;
  } catch (error) {
    if (signal?.aborted) throw new AdminReadError("cancelled");
    if (error instanceof AdminReadError) throw error;
    throw new AdminReadError("error");
  } finally { clearTimeout(timeout); }
}
