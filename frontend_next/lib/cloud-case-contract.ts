/** Provider-free, non-persisting Cloud Saved Case contract. */
export type CloudRole = "owner" | "editor" | "viewer";
export type CloudSummary = { id: string; role: CloudRole; revision: number; title: string; updated_at: string; sharing: "private" | "members_only" };
export type CloudCase = CloudSummary & {
  owner_id: string; notes: string; created_at: string; snapshot: Record<string, unknown>;
  user_authored: Record<string, unknown>; members: Record<string, "editor" | "viewer">;
  monitoring: { cadence: "off" | "daily" | "weekly"; refresh_policy: "manual_only"; execution_status: "not_configured"; delivery_status: "not_configured" };
};
export type CloudActivity = { revision: number; actor_id: string; kind: "case_imported" | "metadata_updated" | "membership_updated" | "monitoring_updated"; occurred_at: string };
export type CloudErrorCode = "sign_in_required" | "unavailable" | "persistence_pending" | "conflict" | "forbidden" | "invalid" | "offline";
export type CloudResult<T> = { status: "ready"; value: T } | { status: CloudErrorCode };
export type ImportPreview = { snapshot: Record<string, unknown>; user_authored: Record<string, unknown>; import_key: string; explicit_consent: true };
const record = (v: unknown): v is Record<string, unknown> => Boolean(v && typeof v === "object" && !Array.isArray(v));
const uuid = (v: unknown): v is string => typeof v === "string" && /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(v);
const date = (v: unknown) => typeof v === "string" && v.length <= 40 && Number.isFinite(Date.parse(v));
const credentialKeys = new Set(["token", "idtoken", "privatekey", "secretkey", "accesstoken", "refreshtoken", "authorization", "password", "apikey", "servicekey", "servicerolekey", "secret", "clientsecret", "cookie", "session", "credentials", "bearertoken", "jwt"]);
const credentialValue = /\bbearer\s+\S+|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|\bsb_(?:secret|publishable)_[A-Za-z0-9_-]+|[?&](?:key|api_key|token|access_token|signature)=[^&#\s]+|https?:\/\/[^/\s]+:[^/@\s]+@/i;

export function safeCloudJSON(value: unknown, depth = 0): boolean {
  if (depth > 24) return false;
  if (typeof value === "string") return !credentialValue.test(value);
  if (Array.isArray(value)) return value.length <= 2000 && value.every(v => safeCloudJSON(v, depth + 1));
  if (record(value)) return Object.entries(value).every(([key, v]) => {
    const normalized = key.toLowerCase().replace(/[^a-z]/g, "");
    const credential = credentialKeys.has(normalized) || normalized.endsWith("token") && !["identitytoken", "evidencetoken"].includes(normalized) || /(?:apikey|secretkey|privatekey|password)$/.test(normalized);
    return key.length <= 200 && !credential && safeCloudJSON(v, depth + 1);
  });
  return value === null || typeof value === "boolean" || typeof value === "number" && Number.isFinite(value);
}

export function validCloudSummary(v: unknown): v is CloudSummary {
  return record(v) && uuid(v.id) && ["owner", "editor", "viewer"].includes(String(v.role)) && Number.isSafeInteger(v.revision) && Number(v.revision) > 0
    && typeof v.title === "string" && v.title.length <= 500 && date(v.updated_at) && ["private", "members_only"].includes(String(v.sharing)) && safeCloudJSON(v);
}
export function validCloudCase(v: unknown): v is CloudCase {
  if (!record(v)) return false;
  const detail = v;
  if (!validCloudSummary(v)) return false;
  const m = detail.monitoring;
  return uuid(detail.owner_id) && typeof detail.notes === "string" && detail.notes.length <= 8000 && date(detail.created_at) && record(detail.snapshot) && record(detail.user_authored)
    && record(detail.members) && Object.keys(detail.members).length <= 50 && Object.entries(detail.members).every(([id, role]) => uuid(id) && ["editor", "viewer"].includes(String(role)))
    && record(m) && ["off", "daily", "weekly"].includes(String(m.cadence)) && m.refresh_policy === "manual_only"
    && m.execution_status === "not_configured" && m.delivery_status === "not_configured" && safeCloudJSON(v);
}
export function validActivity(v: unknown): v is CloudActivity {
  return record(v) && Number.isSafeInteger(v.revision) && Number(v.revision) > 0 && uuid(v.actor_id) && date(v.occurred_at)
    && ["case_imported", "metadata_updated", "membership_updated", "monitoring_updated"].includes(String(v.kind));
}

/** Reads ONLY the selected original JSON. No normalization, storage write or upload.
 * Include the separately authored Decision Room, including historical notes, intact.
 */
export async function previewLocalImport(storage: Pick<Storage, "getItem">, caseId: string): Promise<ImportPreview | null> {
  try {
    const raw = storage.getItem("proptech.savedCases.v1");
    if (!raw || raw.length > 4_000_000) return null;
    const rows: unknown = JSON.parse(raw);
    if (!Array.isArray(rows) || rows.length > 10) return null;
    const matches = rows.filter(row => record(row) && row.id === caseId);
    if (matches.length !== 1 || !record(matches[0])) return null;
    const snapshot = matches[0];
    if (snapshot.version !== 1 || snapshot.workflowMode !== "buying_wizard" || typeof snapshot.title !== "string" || !snapshot.title.length || snapshot.title.length > 500
      || !date(snapshot.createdAt) || !date(snapshot.updatedAt) || !record(snapshot.data) || !record(snapshot.data.inputs) || !record(snapshot.inputSummary)) return null;
    const roomRaw = storage.getItem(`proptech.decisionRoom.v1.${encodeURIComponent(caseId)}`);
    const user_authored: Record<string, unknown> = {};
    if (roomRaw !== null) {
      const room: unknown = JSON.parse(roomRaw);
      if (!record(room) || room.version !== 1 || room.caseId !== caseId) return null;
      user_authored.decision_room = room;
    }
    const text = JSON.stringify([snapshot, user_authored]);
    const bytes = new TextEncoder().encode(text);
    if (bytes.length > 250_000 || !safeCloudJSON([snapshot, user_authored])) return null;
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    const import_key = `browser-v1:${Array.from(new Uint8Array(digest), n => n.toString(16).padStart(2, "0")).join("")}`;
    return { snapshot, user_authored, import_key, explicit_consent: true };
  } catch { return null; }
}
