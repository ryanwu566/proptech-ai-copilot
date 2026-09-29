import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { createProvenanceDisclosure, serializePrimaryProvenance } from "./provenance.ts";

test("primary provenance stays customer-facing while diagnostics remain separately available", () => {
  const disclosure = createProvenanceDisclosure({
    primary: { result: "市場成交中位數：52.4 萬元／坪", effectivePeriod: "2025/01–2026/07", limitation: "樣本 18 筆" },
    supportingContext: "依目前行政區與建物類型整理",
    evidenceDetail: { agency: "內政部", dataset: "不動產實價登錄開放資料", coverage: "大安區", method: "中位數" },
    diagnostics: { providerId: "official_plvr_opendata", endpoint: "/market-insights", httpStatus: 200, requestId: "req-123", rawCode: "success" },
  });

  const primary = serializePrimaryProvenance(disclosure);
  assert.match(primary, /52\.4 萬元／坪/);
  assert.match(primary, /2025\/01–2026\/07/);
  assert.doesNotMatch(primary, /official_plvr_opendata|market-insights|HTTP|req-123|success/);
  assert.equal(disclosure.diagnostics?.providerId, "official_plvr_opendata");
});
