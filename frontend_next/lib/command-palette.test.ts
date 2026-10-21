import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native Node tests use source extensions.
import { buildCaseCommands, filterCaseCommands } from "./command-palette.ts";
// @ts-expect-error Native Node tests use source extensions.
import { adaptSavedCaseToWorkspace } from "./workspace/legacy-case-adapter.ts";
// @ts-expect-error Native Node tests use source extensions.
import { e9Case } from "./workspace/e9-test-fixtures.ts";
// @ts-expect-error Native Node tests use source extensions.
import { emptyDecisionRoom } from "./decision-room-store.ts";
import type { PropertyCaseWorkspace } from "./workspace/workspace-model";

const commands = (workspace: PropertyCaseWorkspace | null = null, pathname = "/") => buildCaseCommands({ pathname, workspace, room: null, locale: "en" });
test("no case offers only global actions", () => {
  assert.deepEqual(commands().map((c) => c.id), ["new", "saved", "compare", "account", "tour"]);
});
test("case routes use encoded IDs and expose Report and Compare", () => {
  const w = adaptSavedCaseToWorkspace(e9Case("case / a"));
  const list = commands(w, "/cases/case%20%2F%20a/overview");
  assert.equal(list.find((c) => c.id === "report")?.href, "/cases/case%20%2F%20a/report");
  assert.equal(list.find((c) => c.id === "compare")?.href, "/compare?cases=case%20%2F%20a");
  assert.equal(list.find((c) => c.id === "overview")?.current, true);
});
test("unconfirmed location prioritizes confirmation, overview and saved cases", () => {
  const saved = e9Case(); delete saved.data.propertyIdentityAnchor;
  const list = commands(adaptSavedCaseToWorkspace(saved), "/cases/case-a/overview");
  assert.deepEqual(list.slice(0, 3).map((c) => c.id), ["confirm-location", "overview", "saved"]);
  assert.equal(list[0].href, "/cases/case-a/location");
});
test("confirmed location removes confirmation action", () => {
  assert.ok(!commands(adaptSavedCaseToWorkspace(e9Case()), "/cases/case-a/overview").some((c) => c.id === "confirm-location"));
});
test("unresolved saved risk leads followed by Decision Room and Report", () => {
  const list = commands(adaptSavedCaseToWorkspace(e9Case()), "/cases/case-a/market");
  assert.deepEqual(list.slice(0, 3).map((c) => c.id), ["risk-review", "decision-room", "report"]);
});
test("unqueried risk does not invent a risk follow-up", () => {
  const saved = e9Case(); delete saved.data.terrainReference;
  assert.ok(!commands(adaptSavedCaseToWorkspace(saved), "/cases/case-a/overview").some((c) => c.id === "risk-review"));
});
test("three saved evidence domains prioritize room, compare and report without a score", () => {
  const w = adaptSavedCaseToWorkspace(e9Case()); w.risk = null;
  assert.deepEqual(commands(w, "/cases/case-a/market").slice(0, 3).map((c) => c.id), ["decision-room", "compare", "report"]);
});
test("only a matching route activates case commands", () => {
  const w = adaptSavedCaseToWorkspace(e9Case());
  assert.deepEqual(commands(w, "/cases/other/overview").map((c) => c.id), commands().map((c) => c.id));
  assert.equal(commands(null, "/cases/%ZZ/overview").length, 5);
});
test("room count counts open items once and ignores done records and missing-room defaults", () => {
  const room = emptyDecisionRoom("case-a");
  room.items = Array.from({ length: 5 }, (_, i) => ({ id: String(i), kind: "task", title: "Check", owner: "", dueDate: "", status: i === 4 ? "done" : "open", resolution: i === 4 ? "Checked" : "" }));
  const w = adaptSavedCaseToWorkspace(e9Case());
  const list = buildCaseCommands({ pathname: "/cases/case-a/overview", workspace: w, room: { status: "ready", room }, locale: "en" });
  assert.equal(list.find((c) => c.id === "decision-room")?.title, "Handle 4 outstanding items");
  assert.equal(commands(w, "/cases/case-a/overview").find((c) => c.id === "decision-room")?.title, "Open Decision Room");
});
test("corrupt and wrong-case room records do not expose counts", () => {
  const w = adaptSavedCaseToWorkspace(e9Case());
  for (const room of [{ status: "corrupt" as const }, { status: "ready" as const, room: emptyDecisionRoom("other") }]) {
    assert.equal(buildCaseCommands({ pathname: "/cases/case-a/overview", workspace: w, room, locale: "en" }).find((c) => c.id === "decision-room")?.title, "Open Decision Room");
  }
});
for (const [locale, report] of [["zh-TW", "查看案件報告"], ["en", "View case report"], ["ja", "案件レポートを表示"], ["ko", "사례 보고서 보기"]] as const) {
  test(`${locale}: localized label and stable multilingual aliases filter`, () => {
    const list = buildCaseCommands({ pathname: "/cases/case-a/overview", workspace: adaptSavedCaseToWorkspace(e9Case()), room: null, locale });
    assert.equal(filterCaseCommands(list, report)[0]?.id, "report");
    for (const alias of ["report", "報告", "ＲＥＰＯＲＴ"]) assert.equal(filterCaseCommands(list, alias)[0]?.id, "report");
    for (const alias of ["money", "通勤", "risk", "compare"]) assert.ok(filterCaseCommands(list, alias).length > 0);
    assert.deepEqual(filterCaseCommands(list, "no such action"), []);
  });
}
