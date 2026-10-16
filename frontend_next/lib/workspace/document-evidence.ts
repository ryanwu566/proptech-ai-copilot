import type { CaseEvidenceModel } from "./case-evidence";
// @ts-expect-error Native TS runner extension.
import { evidenceFields } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { checklistToken } from "./checklist-persistence.ts";
// @ts-expect-error Native TS runner extension.
import { safePublicEvidenceUrl } from "../terrain-reference-evidence.ts";

export type EvidenceState = "current" | "stale" | "superseded" | "failed" | "unknown";
export type Verification = "unverified" | "human_reviewed" | "rejected";
export type DocumentClass = "registry_extract" | "cadastral_map" | "permit" | "zoning" | "valuation_attachment" | "official_export";
export type DocumentMetadata = {
  schemaVersion: 1; workspaceId: string; caseId: string; documentId: string; versionId: string;
  sourceId: "user-upload"; documentClass: DocumentClass; sha256: string; byteLength: number;
  mediaType: "application/pdf" | "image/png" | "image/jpeg" | "application/json";
  observedAt: string; effectiveAt: string | null; expiresAt: string | null;
  verification: Verification; lifecycle: Exclude<EvidenceState, "stale">;
  extraction: "not_attempted" | "pending" | "failed" | "succeeded";
  scan: "pending" | "clean" | "rejected" | "failed" | "unknown";
  supersedesId: string | null; canonicalUrl: string | null;
};
export type Citation = {
  contract: "proptech-citation-v1"; id: string; caseId: string; versionId: string;
  observationId: string; label: string; source: { id: string; label: string; kind: "saved_snapshot" | "document" };
  document: DocumentMetadata | null; observedAt: string | null; effectiveAt: string | null;
  sourceUpdatedAt: string | null; relation: "supports" | "contradicts" | "context";
  verification: Verification; state: EvidenceState; supportsCurrentClaim: boolean;
  limitation: string; href: string; canonicalUrl: string | null; claimIds: string[]; decisionIds: string[];
};
export type EvidenceClaim = { id: string; label: string; citationIds: string[]; decisionId: string };
export type EvidenceDecision = { id: string; domain: string; href: string; analysisHref: string; claimIds: string[] };
export type EvidenceObservation = { id: string; versionId: string; value: string | number | null; historicalValue: string | number | null; unit: string };
export type EvidenceGraph = { contract: "proptech-evidence-graph-v1"; workspaceId: string | null; caseId: string; versionId: string;
  observations: EvidenceObservation[]; citations: Citation[]; claims: EvidenceClaim[]; decisions: EvidenceDecision[] };

const ID = /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$/;
function opaque(value: unknown): value is string { return typeof value === "string" && ID.test(value); }
const documentKeys = ["schemaVersion", "workspaceId", "caseId", "documentId", "versionId", "sourceId", "documentClass", "sha256", "byteLength", "mediaType", "observedAt", "effectiveAt", "expiresAt", "verification", "lifecycle", "extraction", "scan", "supersedesId", "canonicalUrl"];
/** Strict UTC/offset timestamp; Date.parse alone silently normalizes invalid days. */
function validDate(value: unknown): value is string {
  if (typeof value !== "string" || value.length > 40 || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return false;
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  const [hour, minute, second] = value.slice(11, 19).split(":").map(Number);
  return month >= 1 && month <= 12 && day >= 1 && day <= new Date(Date.UTC(year, month, 0)).getUTCDate() && hour <= 23 && minute <= 59 && second <= 59 && Number.isFinite(Date.parse(value));
}
/** Only minimized metadata from a future authorized server read may cross this seam. */
export function readDocumentMetadata(value: unknown, scope: { workspaceId: string; caseId: string }): DocumentMetadata | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const v = value as Record<string, unknown>;
  if (Object.keys(v).length !== documentKeys.length || Object.keys(v).some(k => !documentKeys.includes(k)) || v.schemaVersion !== 1 || v.workspaceId !== scope.workspaceId || v.caseId !== scope.caseId) return null;
  if (![v.workspaceId, v.caseId, v.documentId, v.versionId].every(opaque)) return null;
  if (v.sourceId !== "user-upload" || typeof v.documentClass !== "string" || !["registry_extract", "cadastral_map", "permit", "zoning", "valuation_attachment", "official_export"].includes(v.documentClass)) return null;
  if (typeof v.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(v.sha256) || typeof v.byteLength !== "number" || !Number.isInteger(v.byteLength) || v.byteLength <= 0 || v.byteLength > 10 * 1024 * 1024) return null;
  if (typeof v.mediaType !== "string" || !["application/pdf", "image/png", "image/jpeg", "application/json"].includes(v.mediaType) || !validDate(v.observedAt) || !(v.effectiveAt === null || validDate(v.effectiveAt)) || !(v.expiresAt === null || validDate(v.expiresAt))) return null;
  if (typeof v.effectiveAt === "string" && typeof v.expiresAt === "string" && Date.parse(v.expiresAt) <= Date.parse(v.effectiveAt)) return null;
  if (typeof v.verification !== "string" || !["unverified", "human_reviewed", "rejected"].includes(v.verification) || typeof v.lifecycle !== "string" || !["current", "superseded", "failed", "unknown"].includes(v.lifecycle) || typeof v.extraction !== "string" || !["not_attempted", "pending", "failed", "succeeded"].includes(v.extraction)) return null;
  if (typeof v.scan !== "string" || !["pending", "clean", "rejected", "failed", "unknown"].includes(v.scan)) return null;
  if (!(v.supersedesId === null || typeof v.supersedesId === "string" && ID.test(v.supersedesId) && v.supersedesId !== v.versionId)) return null;
  if (v.canonicalUrl !== null && (typeof v.canonicalUrl !== "string" || safePublicEvidenceUrl(v.canonicalUrl) !== v.canonicalUrl || !v.canonicalUrl.startsWith("https://"))) return null;
  return { ...v } as DocumentMetadata;
}

export function projectEvidenceState(item: { lifecycle: Exclude<EvidenceState, "stale">; expiresAt: string | null; effectiveAt?: string | null; observedAt?: string | null }, now: string, superseded = false): EvidenceState {
  if (superseded || item.lifecycle === "superseded") return "superseded";
  if (item.lifecycle === "failed") return "failed";
  if (item.lifecycle === "unknown" || !validDate(now) || !validDate(item.expiresAt)) return "unknown";
  if (item.effectiveAt && (!validDate(item.effectiveAt) || Date.parse(now) < Date.parse(item.effectiveAt)) || item.observedAt && (!validDate(item.observedAt) || Date.parse(now) < Date.parse(item.observedAt))) return "unknown";
  return Date.parse(now) >= Date.parse(item.expiresAt) ? "stale" : "current";
}

/** Local snapshot fingerprint, not a durable ledger ID or authorization token.
 * Presentation labels, source display names and explanatory copy are excluded.
 * Durable adapters must use immutable ledger/version IDs in their own namespace.
 */
export function buildCaseEvidenceGraph(model: CaseEvidenceModel): EvidenceGraph {
  const fields = evidenceFields(model).slice().sort((a, b) => a.id.localeCompare(b.id, "en"));
  // The existing repository identifies a saved edition by case + savedAt.
  // Values include translated presentation enums; neither those nor expiry may
  // renumber an edition. This is explicitly not a durable ledger revision.
  const versionId = checklistToken(["saved-case-edition-v1", model.caseId, model.savedAt]);
  const base = `/cases/${encodeURIComponent(model.caseId)}`;
  // Missing-field placeholders explain gaps; they are not evidence to cite.
  const citations: Citation[] = fields.filter(field => field.value !== null || field.historicalValue !== null).map(field => {
    const id = `ec1.${encodeURIComponent(model.caseId)}.${versionId}.${field.id}`;
    const state: EvidenceState = field.status === "stale" || field.freshness.inputRelation === "stale" || field.freshness.timeRelation === "stale" ? "stale"
      : field.status === "unavailable" ? "failed"
      : field.status === "available" && field.freshness.timeRelation === "within_source_policy" && field.freshness.inputRelation === "matches" ? "current" : "unknown";
    return { contract: "proptech-citation-v1", id, caseId: model.caseId, versionId, observationId: field.id,
      label: field.label, source: { id: `snapshot-${field.domain}`, label: field.source, kind: "saved_snapshot" },
      document: null, observedAt: field.freshness.checkedAt, effectiveAt: null, sourceUpdatedAt: field.freshness.sourceUpdatedAt, relation: "context",
      verification: "unverified", state, supportsCurrentClaim: false, limitation: field.limitation,
      href: `${base}/evidence#${id}`, canonicalUrl: null,
      claimIds: [`claim-${field.id}`], decisionIds: [`decision-${field.domain}`] };
  });
  const claims = fields.map(field => ({ id: `claim-${field.id}`, label: field.label, citationIds: citations.filter(c => c.observationId === field.id).map(c => c.id), decisionId: `decision-${field.domain}` }));
  const decisions = [...new Set(fields.map(f => f.domain))].map(domain => ({ id: `decision-${domain}`, domain, href: `${base}/decision-room#saved-evidence`, analysisHref: `${base}/${domain}`, claimIds: claims.filter(c => c.decisionId === `decision-${domain}`).map(c => c.id) }));
  const observations = fields.map(field => ({ id: field.id, versionId, value: field.value, historicalValue: field.historicalValue, unit: field.unit }));
  return { contract: "proptech-evidence-graph-v1", workspaceId: null, caseId: model.caseId, versionId, observations, citations, claims, decisions };
}

/** Provider-free allowlist resolver: AI may supply IDs only, never URLs or labels.
 * The caller must supply a graph obtained through its authorized case read.
 * Historical/unknown citations resolve with restrictions; they do not become support.
 */
export function resolveCopilotCitation(graph: EvidenceGraph, caseId: string, citationId: string, workspaceId: string | null = null): Citation | null {
  if (graph.caseId !== caseId || graph.workspaceId !== workspaceId || typeof citationId !== "string" || citationId.length > 600) return null;
  const found = graph.citations.find(c => c.id === citationId && c.caseId === caseId);
  if (!found) return null;
  const observation = graph.observations.find(o => o.id === found.observationId && o.versionId === found.versionId);
  if (!observation) return null;
  if (found.source.kind === "saved_snapshot") {
    if (workspaceId !== null || found.document !== null || observation.value === null && observation.historicalValue === null) return null;
  } else {
    const doc = workspaceId === null ? null : readDocumentMetadata(found.document, { workspaceId, caseId });
    if (!doc || doc.versionId !== found.versionId || doc.sourceId !== found.source.id) return null;
  }
  return structuredClone(found);
}

export function reportEvidenceReferences(model: CaseEvidenceModel): Citation[] { return buildCaseEvidenceGraph(model).citations; }

export type DocumentObservation = {
  workspaceId: string; caseId: string; id: string; versionId: string; claimId: string;
  claimLabel: string; decisionDomain: "overview" | "market" | "location" | "risk" | "finance";
  verification: Verification; relation: "supports" | "contradicts" | "context"; limitation: string;
};
/** Future authorized read adapter. It accepts minimized observations, never OCR output.
 * All versions must be loaded together; incomplete or ambiguous lineage fails closed.
 * Inputs remain unchanged, including superseded versions and failed extraction attempts.
 */
export function buildDocumentEvidenceGraph(scope: { workspaceId: string; caseId: string }, documents: unknown[], observations: DocumentObservation[], now: string): EvidenceGraph {
  if (!opaque(scope.workspaceId) || !opaque(scope.caseId) || documents.length > 200 || observations.length > 1000 || !validDate(now)) throw new Error("invalid_evidence_graph");
  const versions = documents.map(doc => readDocumentMetadata(doc, scope));
  if (versions.some(doc => !doc)) throw new Error("invalid_document_metadata");
  const docs = versions as DocumentMetadata[];
  const byVersion = new Map(docs.map(doc => [doc.versionId, doc]));
  if (byVersion.size !== docs.length) throw new Error("duplicate_document_version");
  for (const documentId of new Set(docs.map(doc => doc.documentId))) {
    if (docs.filter(doc => doc.documentId === documentId && doc.supersedesId === null).length !== 1) throw new Error("ambiguous_document_roots");
  }
  const superseded = new Set<string>();
  for (const doc of docs) {
    if (!doc.supersedesId) continue;
    const previous = byVersion.get(doc.supersedesId);
    if (!previous || previous.documentId !== doc.documentId || superseded.has(previous.versionId)) throw new Error("invalid_document_lineage");
    superseded.add(previous.versionId);
    const seen = new Set([doc.versionId]); let parent: DocumentMetadata | undefined = previous;
    while (parent) {
      if (seen.has(parent.versionId)) throw new Error("cyclic_document_lineage");
      seen.add(parent.versionId); parent = parent.supersedesId ? byVersion.get(parent.supersedesId) : undefined;
    }
  }
  const seen = new Set<string>();
  const citations: Citation[] = observations.map(observation => {
    const doc = byVersion.get(observation.versionId);
    if (!doc || observation.workspaceId !== scope.workspaceId || observation.caseId !== scope.caseId || !opaque(observation.id) || !opaque(observation.claimId) || seen.has(observation.id)
      || !["supports", "contradicts", "context"].includes(observation.relation) || !["unverified", "human_reviewed", "rejected"].includes(observation.verification)
      || !["overview", "market", "location", "risk", "finance"].includes(observation.decisionDomain)
      || typeof observation.claimLabel !== "string" || !observation.claimLabel.trim() || observation.claimLabel.length > 240
      || typeof observation.limitation !== "string" || !observation.limitation.trim() || observation.limitation.length > 1000) throw new Error("invalid_document_observation");
    seen.add(observation.id);
    const projected = projectEvidenceState(doc, now, superseded.has(doc.versionId));
    const state = projected === "superseded" || projected === "failed" ? projected : doc.scan === "rejected" || doc.scan === "failed" || doc.verification === "rejected" ? "failed" : doc.scan !== "clean" ? "unknown" : projected;
    const id = `dc1.${scope.workspaceId}.${scope.caseId}.${doc.versionId}.${observation.id}`;
    return { contract: "proptech-citation-v1", id, caseId: scope.caseId, versionId: doc.versionId,
      observationId: observation.id, label: observation.claimLabel, source: { id: doc.sourceId, label: doc.sourceId, kind: "document" },
      document: structuredClone(doc), observedAt: doc.observedAt, effectiveAt: doc.effectiveAt, sourceUpdatedAt: null, relation: observation.relation,
      verification: observation.verification, state, supportsCurrentClaim: state === "current" && observation.verification === "human_reviewed" && doc.verification === "human_reviewed" && observation.relation === "supports" && doc.extraction !== "failed",
      limitation: observation.limitation, href: `/cases/${encodeURIComponent(scope.caseId)}/evidence#${id}`, canonicalUrl: doc.canonicalUrl,
      claimIds: [observation.claimId], decisionIds: [`decision-${observation.decisionDomain}`] };
  });
  for (const citation of citations) {
    if (citations.some(other => other.state === "current" && other.verification !== "rejected" && other.relation === "contradicts" && other.claimIds.some(id => citation.claimIds.includes(id)))) citation.supportsCurrentClaim = false;
  }
  const claims = [...new Set(observations.map(o => o.claimId))].map(id => {
    const items = observations.filter(o => o.claimId === id);
    if (items.some(o => o.decisionDomain !== items[0].decisionDomain || o.claimLabel !== items[0].claimLabel)) throw new Error("conflicting_claim_metadata");
    return { id, label: items[0].claimLabel, citationIds: citations.filter(c => c.claimIds.includes(id)).map(c => c.id), decisionId: `decision-${items[0].decisionDomain}` };
  });
  const decisions = [...new Set(observations.map(o => o.decisionDomain))].map(domain => ({ id: `decision-${domain}`, domain, href: `/cases/${encodeURIComponent(scope.caseId)}/decision-room#saved-evidence`, analysisHref: `/cases/${encodeURIComponent(scope.caseId)}/${domain}`, claimIds: claims.filter(c => c.decisionId === `decision-${domain}`).map(c => c.id) }));
  return { contract: "proptech-evidence-graph-v1", workspaceId: scope.workspaceId, caseId: scope.caseId, versionId: checklistToken(docs.map(d => d.versionId).sort()), observations: observations.map(o => ({ id: o.id, versionId: o.versionId, value: null, historicalValue: null, unit: "" })), citations, claims, decisions };
}
