import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { formatEvidenceDate } from "./evidence-date.ts";
// @ts-expect-error Native TS runner extension.
import { e9Case } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { buildReportModel } from "./compare-report-model.ts";

const unknown = "Unknown / not preserved";
const forbidden = () => { throw new Error("Non-date must never reach formatDate"); };
const date = (value: string) => new Intl.DateTimeFormat("en", { dateStyle: "medium", timeZone: "Asia/Taipei" }).format(new Date(value));

test("source vintages and official periods never reach the timestamp formatter", () => {
  for (const value of ["113年度（官方公開 MVT）", "113年度", "2026", "113", "2026-08", "2025–2026", "官方公開 MVT", "2026-02-30", "2026-08-20T25:00:00Z"]) {
    assert.equal(formatEvidenceDate(value, forbidden, unknown, "source"), value);
    assert.equal(formatEvidenceDate(value, forbidden, unknown), unknown);
  }
});

test("unavailable and meaningless values use the supplied localized fallback", () => {
  for (const value of [null, undefined, "", " ", "未提供", "未知", "未保存", "UNKNOWN", "unavailable", "N/A", "-", "…", "bad\u0000label"]) {
    for (const kind of ["date", "source"] as const) {
      assert.equal(formatEvidenceDate(value, forbidden, "不明・未保存", kind), "不明・未保存");
    }
  }
});

test("valid full dates and timestamps retain the existing formatter's behavior", () => {
  for (const value of ["2026-08-20", "2026-08-20T03:00:00Z", "2026-08-20T11:00:00+08:00", "2026-08-20T11:00:00", "2024-02-29"]) {
    assert.equal(formatEvidenceDate(value, date, unknown, "source"), value.startsWith("2024") ? "Feb 29, 2024" : "Aug 20, 2026");
  }
  for (const value of ["2026-02-29", "2026-13-01", "2026-00-01", "2026-04-31", "2026-08-00", "2026-08-20junk", "2026-08-20T24:00:00Z"]) {
    assert.equal(formatEvidenceDate(value, forbidden, unknown), unknown);
  }
});

test("meaningful source text is trimmed and bounded without inventing a date", () => {
  assert.equal(formatEvidenceDate("  113年度（官方公開 MVT）  ", forbidden, unknown, "source"), "113年度（官方公開 MVT）");
  assert.equal(formatEvidenceDate("官方".repeat(300), forbidden, unknown, "source"), "官方".repeat(100));
});

test("saved mixed Risk traverses the actual Report model with source labels and UNKNOWN intact", () => {
  const saved = e9Case();
  saved.data.terrainReference!.layers[0].data_updated_at = "未提供";
  saved.data.terrainReference!.layers[1].data_updated_at = "113年度（官方公開 MVT）";
  saved.data.terrainReference!.layers[2].data_updated_at = "2026-08-20";
  const original = structuredClone(saved);
  const report = buildReportModel(projectCaseEvidence(adaptSavedCaseToWorkspace(saved)), "2026-10-23T03:00:00Z");
  assert.equal(report.sections.length, 9);
  const flood = report.citations.find(c => c.observationId === "risk-flood")!;
  const landslide = report.citations.find(c => c.observationId === "risk-landslide")!;
  assert.equal(formatEvidenceDate(flood.sourceUpdatedAt, forbidden, unknown, "source"), unknown);
  assert.equal(formatEvidenceDate(landslide.sourceUpdatedAt, forbidden, unknown, "source"), "113年度（官方公開 MVT）");
  assert.equal(flood.state, "unknown");
  assert.equal(flood.supportsCurrentClaim, false);
  const source = report.evidence!.sources.find(s => s.id === "risk-geological_sensitivity")!;
  assert.equal(formatEvidenceDate(source.updatedAt, date, unknown, "source"), "Aug 20, 2026");
  assert.deepEqual(saved, original);
});
