import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { e9Case, E9_NOW } from "./e9-test-fixtures.ts";
// @ts-expect-error Native TS runner extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
const feature = await import("./document-evidence.ts").catch(() => null);

function model(id = "case-a") { return projectCaseEvidence(adaptSavedCaseToWorkspace(e9Case(id))); }

test("citation contract is available", () => assert.ok(feature, "Wave 5 read model must exist"));
test("missing observations cannot mint valid citations, while saved zero and history remain resolvable", () => {
  assert.ok(feature);
  const evidence = model();
  assert.equal(evidence.price.valuationEstimate.value, null);
  assert.equal(evidence.price.valuationEstimate.historicalValue, null);
  const graph = feature.buildCaseEvidenceGraph(evidence);
  assert.ok(!graph.citations.some(c => c.observationId === "valuation-estimate"));
  assert.deepEqual(graph.claims.find(c => c.id === "claim-valuation-estimate")?.citationIds, []);
  const zero = graph.citations.find(c => c.observationId === "finance-rate");
  assert.ok(zero);
  assert.equal(feature.resolveCopilotCitation(graph, evidence.caseId, zero.id)?.id, zero.id);
  evidence.price.asking.historicalValue = evidence.price.asking.value;
  evidence.price.asking.value = null; evidence.price.asking.status = "stale";
  const historical = feature.buildCaseEvidenceGraph(evidence);
  const citation = historical.citations.find(c => c.observationId === "price-asking");
  assert.ok(citation);
  assert.equal(feature.resolveCopilotCitation(historical, evidence.caseId, citation.id)?.state, "stale");
});
test("resolver rejects dangling observations and mismatched versions", () => {
  assert.ok(feature);
  const graph = feature.buildCaseEvidenceGraph(model());
  const citation = graph.citations[0];
  assert.equal(feature.resolveCopilotCitation({ ...graph, observations: [] }, graph.caseId, citation.id), null);
  const wrongVersion = structuredClone(graph);
  wrongVersion.observations.forEach(o => { o.versionId = "missing-version"; });
  assert.equal(feature.resolveCopilotCitation(wrongVersion, graph.caseId, citation.id), null);
});
test("stable citation identity survives labels, locales and ordering", () => {
  assert.ok(feature);
  const a = model(); const b = structuredClone(a); b.title = "日本語 한국어 English";
  b.price.asking.label = "Asking price"; b.price.asking.source = "Translated source";
  b.price.basis.value = "Manual price basis"; b.finance.basis.value = "Localized presentation label";
  b.price = Object.fromEntries(Object.entries(b.price).reverse()) as typeof b.price;
  b.risk.reverse(); b.finance.breakdown.reverse();
  const first = feature.buildCaseEvidenceGraph(a);
  const second = feature.buildCaseEvidenceGraph(b);
  assert.deepEqual(first.citations.map(c => c.id), second.citations.map(c => c.id));
  assert.ok(first.citations.every(c => c.href.startsWith("/cases/case-a/evidence#")));
  assert.equal(new Set(first.citations.map(c => c.id)).size, first.citations.length);
  const expired = structuredClone(a);
  expired.price.asking.historicalValue = expired.price.asking.value;
  expired.price.asking.value = null; expired.price.asking.status = "stale";
  expired.price.asking.freshness.timeRelation = "stale";
  assert.deepEqual(first.citations.map(c => c.id), feature.buildCaseEvidenceGraph(expired).citations.map(c => c.id), "freshness projections do not change citation identity");
});
test("Copilot resolver rejects invented citations, wrong snapshots and other cases", () => {
  assert.ok(feature);
  const graph = feature.buildCaseEvidenceGraph(model()); const citation = graph.citations[0];
  assert.equal(feature.resolveCopilotCitation(graph, "case-b", citation.id), null);
  assert.equal(feature.resolveCopilotCitation(feature.buildCaseEvidenceGraph(model("case-b")), "case-b", citation.id), null);
  assert.equal(feature.resolveCopilotCitation(graph, "case-a", "https://invented.example/source"), null);
  const changed = model(); changed.savedAt = "2026-10-16T00:00:00Z";
  assert.equal(feature.resolveCopilotCitation(feature.buildCaseEvidenceGraph(changed), "case-a", citation.id), null);
  assert.equal(feature.resolveCopilotCitation(graph, "case-a", citation.id)?.id, citation.id);
});
test("stale, failed, unknown and superseded stay distinct and history is immutable", () => {
  assert.ok(feature);
  const a = { lifecycle: "current", verification: "unverified", expiresAt: "2026-10-16T00:00:00Z", supersedesId: null } as const;
  assert.equal(feature.projectEvidenceState(a, "2026-10-15T23:59:59Z"), "current");
  assert.equal(feature.projectEvidenceState(a, "2026-10-16T00:00:00Z"), "stale");
  assert.equal(feature.projectEvidenceState({ ...a, expiresAt: null }, E9_NOW), "unknown");
  assert.equal(feature.projectEvidenceState({ ...a, lifecycle: "failed" }, E9_NOW), "failed");
  assert.equal(feature.projectEvidenceState(a, E9_NOW, true), "superseded");
  assert.equal(a.lifecycle, "current");
  const graph = feature.buildCaseEvidenceGraph(model());
  const citation = graph.citations.find(c => c.state === "unknown"); assert.ok(citation);
  assert.equal(feature.resolveCopilotCitation(graph, "case-a", citation.id)?.supportsCurrentClaim, false);
});
test("claim and decision edges traverse both ways without crossing cases", () => {
  assert.ok(feature);
  const graph = feature.buildCaseEvidenceGraph(model());
  assert.ok(graph.claims.length > 0);
  assert.ok(graph.decisions.every(d => d.href === "/cases/case-a/decision-room#saved-evidence" && d.analysisHref.startsWith("/cases/case-a/")));
  for (const claim of graph.claims) {
    const citations = graph.citations.filter(c => claim.citationIds.includes(c.id));
    assert.equal(citations.length, claim.citationIds.length);
    assert.ok(citations.every(c => c.claimIds.includes(claim.id) && c.decisionIds.includes(claim.decisionId)));
  }
});
test("document metadata is allowlisted and scope checked, never coerced", () => {
  assert.ok(feature);
  const scope = { workspaceId: "workspace-a", caseId: "case-a" };
  const doc = { schemaVersion: 1, ...scope, documentId: "doc-a", versionId: "v-a", sourceId: "user-upload",
    documentClass: "registry_extract", sha256: "a".repeat(64), byteLength: 100, mediaType: "application/pdf",
    observedAt: E9_NOW, effectiveAt: null, expiresAt: null, verification: "unverified", lifecycle: "unknown",
    extraction: "not_attempted", scan: "pending", supersedesId: null, canonicalUrl: null };
  assert.ok(feature.readDocumentMetadata(doc, scope));
  for (const patch of [{ caseId: "case-b" }, { workspaceId: "workspace-b" }, { byteLength: -1 },
    { byteLength: "100" }, { documentClass: "exe" }, { observedAt: "tomorrow" }, { sha256: "x" },
    { raw_artifact_ref: "secret/path" }, { mediaType: "text/html" }, { canonicalUrl: "javascript:alert(1)" },
    { effectiveAt: "2026-02-30T00:00:00Z" }, { supersedesId: "v-a" }, { verification: ["unverified"] }, { documentClass: ["registry_extract"] }]) {
    assert.equal(feature.readDocumentMetadata({ ...doc, ...patch }, scope), null, JSON.stringify(patch));
  }
});
test("report references use the same resolver contract and retain frozen IDs", async () => {
  assert.ok(feature);
  // @ts-expect-error Native TS runner extension.
  const { buildReportModel } = await import("./compare-report-model.ts");
  const evidence = model(); const report = buildReportModel(evidence, E9_NOW);
  assert.ok(report.citations?.length);
  assert.deepEqual(report.citations, feature.buildCaseEvidenceGraph(evidence).citations);
  const frozen = JSON.stringify(report.citations); evidence.savedAt = "2026-10-16T00:00:00Z";
  assert.equal(JSON.stringify(report.citations), frozen);
  assert.equal(buildReportModel(null, E9_NOW).citations.length, 0);
});

test("document graph keeps superseded editions and scopes every observation link", () => {
  assert.ok(feature);
  const scope = { workspaceId: "workspace-a", caseId: "case-a" };
  const doc = { schemaVersion: 1, ...scope, documentId: "doc-a", versionId: "v-a", sourceId: "user-upload",
    documentClass: "registry_extract", sha256: "a".repeat(64), byteLength: 100, mediaType: "application/pdf",
    observedAt: E9_NOW, effectiveAt: null, expiresAt: "2027-01-01T00:00:00Z", verification: "human_reviewed", lifecycle: "current",
    extraction: "not_attempted", scan: "clean", supersedesId: null, canonicalUrl: null };
  const next = { ...doc, versionId: "v-b", supersedesId: "v-a" };
  const observation = { ...scope, id: "obs-a", versionId: "v-a", claimId: "claim-a", claimLabel: "Registry entry requires review",
    decisionDomain: "overview", verification: "human_reviewed", relation: "supports", limitation: "Not proof of legal ownership" } as const;
  const documents = [doc, next]; const before = JSON.stringify(documents);
  const graph = feature.buildDocumentEvidenceGraph(scope, documents, [observation, { ...observation, id: "obs-b", versionId: "v-b" }], E9_NOW);
  assert.equal(graph.citations.length, 2);
  assert.equal(graph.citations[0].state, "superseded");
  assert.equal(graph.citations[0].supportsCurrentClaim, false);
  assert.equal(graph.citations[1].supportsCurrentClaim, true);
  assert.equal(feature.resolveCopilotCitation(graph, "case-a", graph.citations[0].id, scope.workspaceId)?.state, "superseded");
  assert.equal(feature.resolveCopilotCitation(graph, "case-a", graph.citations[0].id, "workspace-b"), null);
  assert.equal(feature.resolveCopilotCitation(graph, "case-a", graph.citations[0].id), null, "document references require workspace scope");
  for (const patch of [null, { ...doc, versionId: "missing" }, { ...doc, caseId: "case-b" }, { ...doc, workspaceId: "workspace-b" }]) {
    const broken = structuredClone(graph); broken.citations[0].document = patch as never;
    assert.equal(feature.resolveCopilotCitation(broken, "case-a", broken.citations[0].id, scope.workspaceId), null);
  }
  assert.equal(JSON.stringify(documents), before);
  const original = feature.buildDocumentEvidenceGraph(scope, [doc], [observation], E9_NOW);
  assert.equal(original.citations[0].id, graph.citations[0].id, "new evidence does not renumber historical citations");
  for (const patch of [{ caseId: "case-b" }, { workspaceId: "workspace-b" }, { versionId: "missing" }, { relation: "invented" }]) {
    // Deliberately malformed wire data must also fail runtime guards.
    assert.throws(() => feature.buildDocumentEvidenceGraph(scope, documents, [{ ...observation, ...patch } as never], E9_NOW));
  }
  assert.throws(() => feature.buildDocumentEvidenceGraph(scope, [doc, { ...next, documentId: "doc-b" }], [], E9_NOW));
  assert.throws(() => feature.buildDocumentEvidenceGraph(scope, [doc, next, { ...next, versionId: "v-c" }], [], E9_NOW), "supersession forks are ambiguous");
  assert.throws(() => feature.buildDocumentEvidenceGraph(scope, [doc, { ...doc, versionId: "v-root2" }], [], E9_NOW), "disconnected document versions are ambiguous");
  const conflict = feature.buildDocumentEvidenceGraph(scope, [doc], [{ ...observation, relation: "contradicts" }], E9_NOW);
  assert.equal(conflict.citations[0].supportsCurrentClaim, false);
  const contested = feature.buildDocumentEvidenceGraph(scope, [doc], [observation, { ...observation, id: "obs-c", relation: "contradicts" }], E9_NOW);
  assert.ok(contested.citations.every(c => !c.supportsCurrentClaim));
  for (const scan of ["pending", "unknown", "rejected", "failed"]) {
    const quarantined = feature.buildDocumentEvidenceGraph(scope, [{ ...doc, scan }], [observation], E9_NOW);
    assert.equal(quarantined.citations[0].supportsCurrentClaim, false, scan);
    assert.notEqual(quarantined.citations[0].state, "current", scan);
  }
  const future = { ...doc, effectiveAt: "2027-01-01T00:00:00Z", expiresAt: "2028-01-01T00:00:00Z" };
  assert.equal(feature.buildDocumentEvidenceGraph(scope, [future], [observation], E9_NOW).citations[0].supportsCurrentClaim, false);
  assert.equal(feature.buildDocumentEvidenceGraph(scope, [future], [observation], future.effectiveAt).citations[0].supportsCurrentClaim, true);
  assert.equal(feature.buildDocumentEvidenceGraph(scope, [{ ...doc, observedAt: "2027-01-01T00:00:00Z" }], [observation], E9_NOW).citations[0].supportsCurrentClaim, false);
  assert.equal(feature.buildDocumentEvidenceGraph(scope, [{ ...doc, lifecycle: "failed", scan: "pending" }], [observation], E9_NOW).citations[0].state, "failed");
});

test("Grounded Copilot snapshot selections resolve through legitimate Wave 5 evidence", async () => {
  assert.ok(feature);
  // @ts-expect-error Native TS runner extension.
  const { assembleCopilotContext, answerQuestion } = await import("./grounded-copilot.ts");
  const workspace = adaptSavedCaseToWorkspace(e9Case());
  const context = assembleCopilotContext(workspace);
  const graph = feature.buildCaseEvidenceGraph(projectCaseEvidence(workspace));
  const answer = answerQuestion(context, "market finance commute risk");
  for (const row of answer.used) {
    const citation = graph.citations.find(c => c.observationId === row.id);
    assert.ok(citation, row.id);
    const resolved = feature.resolveCopilotCitation(graph, context.caseId, citation.id);
    assert.equal(resolved?.source.kind, "saved_snapshot");
    assert.equal(resolved?.supportsCurrentClaim, false, "saved sources never become document authority");
  }
  assert.ok(!graph.citations.some(c => c.observationId === "valuation-estimate"));
});
