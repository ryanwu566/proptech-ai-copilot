import assert from "node:assert/strict";
import { test } from "node:test";
// @ts-expect-error Native TS runner extension.
import { previewLocalImport, safeCloudJSON, validCloudCase } from "./cloud-case-contract.ts";

const saved = { id: "local-a", title: "Original", version: 1, workflowMode: "buying_wizard", createdAt: "2026-10-01T00:00:00Z", updatedAt: "2026-10-02T00:00:00Z", inputSummary: {}, data: { inputs: {}, provider: { status: "failed", checked_at: "2026-09-01", source: "original" }, unknown: null, authoredNote: "Do not edit" } };
function storage(rows: unknown = [saved], room: unknown = { version: 1, caseId: "local-a", notes: [{ text: "Keep exact notes" }] }) {
  const map = new Map([["proptech.savedCases.v1", JSON.stringify(rows)], ["proptech.decisionRoom.v1.local-a", JSON.stringify(room)]]);
  const before = [...map];
  return { getItem: (key: string) => map.get(key) ?? null, map, before };
}

test("preview preserves original evidence, timestamps, failed/unknown states and separate notes without writes", async () => {
  const s = storage(); const preview = await previewLocalImport(s, "local-a");
  assert.deepEqual(preview?.snapshot, saved);
  assert.equal((preview?.user_authored.decision_room as { notes: { text: string }[] }).notes[0].text, "Keep exact notes");
  assert.deepEqual([...s.map], s.before);
  assert.equal((await previewLocalImport(s, "local-a"))?.import_key, preview?.import_key);
  assert.equal(preview?.explicit_consent, true);
});

test("changed local evidence produces a distinct import preview; duplicate and malformed records fail closed", async () => {
  assert.notEqual((await previewLocalImport(storage(), "local-a"))?.import_key, (await previewLocalImport(storage([{ ...saved, updatedAt: "2026-10-03T00:00:00Z" }]), "local-a"))?.import_key);
  for (const rows of [[saved, saved], {}, [{ ...saved, version: 2 }], [{ ...saved, data: null }]]) assert.equal(await previewLocalImport(storage(rows), "local-a"), null);
  assert.equal(await previewLocalImport({ getItem: () => { throw Error("unavailable"); } }, "local-a"), null);
  assert.equal(await previewLocalImport(storage([saved], { version: 1, caseId: "other" }), "local-a"), null);
});

test("no credentials persist: reject full import rather than strip historical data", async () => {
  for (const unsafe of [{ access_token: "secret" }, { provider_access_token: "secret" }, { openai_api_key: "secret" }, { Authorization: "Bearer secret" }, { apiKey: "secret" }, { password: "secret" }, { note: "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhIn0.signature" }, { url: "https://example.invalid/?key=secret" }]) {
    const s = storage([{ ...saved, data: { ...saved.data, unsafe } }]);
    assert.equal(await previewLocalImport(s, "local-a"), null);
    assert.deepEqual([...s.map], s.before);
  }
  assert.equal(safeCloudJSON({ identityToken: "c1-0123456789abcdef", evidenceToken: "c1-0123456789abcdef", notes: "human-authored" }), true);
  assert.equal(await previewLocalImport(storage([{ ...saved, data: { ...saved.data, notes: "x".repeat(270000) } }]), "local-a"), null);
});

test("cloud response validator fails closed for malformed roles and fake delivery", () => {
  const row = { id: "11111111-1111-4111-8111-111111111111", owner_id: "11111111-1111-4111-8111-111111111111", role: "owner", revision: 1, title: "case", notes: "", created_at: saved.createdAt, updated_at: saved.updatedAt, snapshot: saved, user_authored: {}, members: {}, sharing: "private", monitoring: { cadence: "off", refresh_policy: "manual_only", execution_status: "not_configured", delivery_status: "not_configured" } };
  assert.equal(validCloudCase(row), true);
  assert.equal(validCloudCase({ ...row, role: "workspace_admin" }), false);
  assert.equal(validCloudCase({ ...row, monitoring: { ...row.monitoring, delivery_status: "delivered" } }), false);
});
