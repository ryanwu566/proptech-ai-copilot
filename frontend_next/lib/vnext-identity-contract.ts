export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

export type WorkspaceRole = "owner" | "admin" | "manager" | "member" | "viewer";
export type CoverageStatus = "known" | "partial" | "unknown" | "unavailable";
export type ResolutionState =
  | "received"
  | "normalizing"
  | "candidates_found"
  | "ambiguous"
  | "partially_resolved"
  | "unresolved"
  | "failed"
  | "superseded"
  | "confirmed"
  | "rejected";

export class VNextContractError extends Error {
  constructor(readonly path: string) {
    super(`Invalid VNext response at ${path}`);
    this.name = "VNextContractError";
  }
}

function objectAt(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) throw new VNextContractError(path);
  return value as Record<string, unknown>;
}

function stringAt(value: unknown, path: string, maximum = 4096): string {
  if (typeof value !== "string" || value.length === 0 || value.length > maximum) throw new VNextContractError(path);
  return value;
}

function nullableStringAt(value: unknown, path: string, maximum = 4096): string | null {
  return value === null ? null : stringAt(value, path, maximum);
}

function booleanAt(value: unknown, path: string): boolean {
  if (typeof value !== "boolean") throw new VNextContractError(path);
  return value;
}

function numberAt(value: unknown, path: string, minimum?: number, maximum?: number): number {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new VNextContractError(path);
  if ((minimum !== undefined && value < minimum) || (maximum !== undefined && value > maximum)) {
    throw new VNextContractError(path);
  }
  return value;
}

function integerAt(value: unknown, path: string, minimum = 0): number {
  const selected = numberAt(value, path, minimum);
  if (!Number.isInteger(selected)) throw new VNextContractError(path);
  return selected;
}

function enumAt<const T extends readonly string[]>(value: unknown, path: string, allowed: T): T[number] {
  if (typeof value !== "string" || !allowed.includes(value)) throw new VNextContractError(path);
  return value as T[number];
}

function uuidAt(value: unknown, path: string): string {
  const selected = stringAt(value, path, 36);
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(selected)) {
    throw new VNextContractError(path);
  }
  return selected;
}

function nullableUuidAt(value: unknown, path: string): string | null {
  return value === null ? null : uuidAt(value, path);
}

function dateAt(value: unknown, path: string): string {
  const selected = stringAt(value, path, 80);
  if (!/^\d{4}-\d{2}-\d{2}T/.test(selected) || Number.isNaN(Date.parse(selected))) throw new VNextContractError(path);
  return selected;
}

function nullableDateAt(value: unknown, path: string): string | null {
  return value === null ? null : dateAt(value, path);
}

function jsonValueAt(value: unknown, path: string, depth = 0): JsonValue {
  if (depth > 8) throw new VNextContractError(path);
  if (value === null || typeof value === "boolean") return value;
  if (typeof value === "string") return stringAt(value, path, 8192);
  if (typeof value === "number") return numberAt(value, path);
  if (Array.isArray(value)) {
    if (value.length > 500) throw new VNextContractError(path);
    return value.map((item, index) => jsonValueAt(item, `${path}[${index}]`, depth + 1));
  }
  const source = objectAt(value, path);
  const entries = Object.entries(source);
  if (entries.length > 200) throw new VNextContractError(path);
  const parsed: JsonObject = {};
  for (const [key, item] of entries) {
    if (key.length === 0 || key.length > 160) throw new VNextContractError(`${path}.${key}`);
    parsed[key] = jsonValueAt(item, `${path}.${key}`, depth + 1);
  }
  return parsed;
}

function jsonObjectAt(value: unknown, path: string): JsonObject {
  const parsed = jsonValueAt(value, path);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) throw new VNextContractError(path);
  return parsed;
}

function arrayAt<T>(value: unknown, path: string, parse: (item: unknown, path: string) => T, maximum = 500): T[] {
  if (!Array.isArray(value) || value.length > maximum) throw new VNextContractError(path);
  return value.map((item, index) => parse(item, `${path}[${index}]`));
}

const coverageStatuses = ["known", "partial", "unknown", "unavailable"] as const;
const resolutionStates = [
  "received", "normalizing", "candidates_found", "ambiguous", "partially_resolved",
  "unresolved", "failed", "superseded", "confirmed", "rejected",
] as const;
const ambiguityStates = ["none", "multiple_candidates", "material_conflict", "insufficient_evidence", "provider_limitation"] as const;
const attemptStatuses = ["available", "limited", "unavailable", "timeout", "unsupported", "no_match", "error"] as const;
const candidateTypes = ["address", "geo_reference", "parcel", "building", "composite_property"] as const;
const candidateStatuses = ["proposed", "plausible", "conflicting", "insufficient", "rejected", "superseded"] as const;
const conflictSeverities = ["information", "warning", "blocking"] as const;
const conflictStates = ["open", "requires_review", "resolved", "superseded"] as const;
const roles = ["owner", "admin", "manager", "member", "viewer"] as const;
const decisionTypes = ["confirmed", "candidate_rejected", "resolution_rejected"] as const;
const propertyStates = ["unverified", "active", "disputed", "archived"] as const;
const relationTypes = ["property_address", "property_geo_reference", "property_parcel", "property_building", "parcel_building"] as const;
const relationDirections = ["directed", "bidirectional"] as const;
const relationStatuses = ["proposed", "confirmed", "rejected", "superseded", "disputed"] as const;
const referenceStatuses = ["observed", "limited", "unverified", "disputed", "superseded", "rejected"] as const;
const evidenceStatuses = ["available", "limited", "unavailable", "unknown", "stale", "conflicting", "user_provided", "unverified"] as const;
const qualityStatuses = ["passed", "limited", "failed", "not_checked"] as const;
const licenseStatuses = ["approved", "owner_review_required", "restricted", "prohibited", "not_applicable", "unknown"] as const;
const casePurposes = ["buy_due_diligence", "development", "brokerage", "valuation_review", "investment_review"] as const;
const caseStatuses = ["open", "in_progress", "on_hold", "closed", "archived"] as const;
const caseIdentityStatuses = ["unverified", "legacy_unverified", "resolving", "confirmed"] as const;
const errorCodes = [
  "authentication_required", "permission_denied", "not_found", "validation_failed", "unsupported_input",
  "version_conflict", "idempotency_conflict", "ambiguous_identity", "stale_evidence", "conflicting_evidence",
  "coverage_unavailable", "provider_unavailable", "duplicate_legacy_import", "rate_limited", "maintenance", "internal_error",
] as const;
const sourceTypes = ["official", "partner", "user", "deterministic", "document", "demo", "test"] as const;
const conflictCategories = ["normalized_identity_disagreement", "identifier_disagreement", "address_parcel_mismatch", "coordinate_parcel_mismatch", "provider_disagreement", "cardinality_disagreement", "temporal_conflict", "coverage_limitation", "existing_property_conflict"] as const;
const attemptErrorCategories = ["provider_unavailable", "timeout", "unsupported_input", "provider_rejected", "invalid_response", "transport_error", "rate_limited", "internal_error", "not_configured"] as const;

export type VNextErrorCode = (typeof errorCodes)[number];

export type SourceDTO = ReturnType<typeof parseSource>;
export type IdentityCandidateDTO = ReturnType<typeof parseCandidate>;
export type IdentityConflictDTO = ReturnType<typeof parseConflict>;
export type IdentityDecisionDTO = ReturnType<typeof parseDecision>;
export type PropertyResolutionDTO = ReturnType<typeof parsePropertyResolution>;
export type PropertyDTO = ReturnType<typeof parseProperty>;
export type PropertyGraphDTO = ReturnType<typeof parsePropertyGraph>;
export type PropertyEvidenceDTO = ReturnType<typeof parsePropertyEvidence>;
export type CaseDTO = ReturnType<typeof parseCase>;
export type CaseAttachmentDTO = ReturnType<typeof parseCaseAttachment>;
export type VNextContextDTO = ReturnType<typeof parseVNextContext>;
export type WorkspaceContextDTO = ReturnType<typeof parseWorkspaceContext>;
export type VNextErrorEnvelope = ReturnType<typeof parseVNextError>;

function parseSource(value: unknown, path: string) {
  const item = objectAt(value, path);
  return {
    source_id: stringAt(item.source_id, `${path}.source_id`, 160),
    source_type: enumAt(item.source_type, `${path}.source_type`, sourceTypes),
    environment: enumAt(item.environment, `${path}.environment`, ["production", "demo", "test"] as const),
    provider_id: nullableStringAt(item.provider_id, `${path}.provider_id`, 160),
    source_record_id: nullableStringAt(item.source_record_id, `${path}.source_record_id`, 320),
    retrieved_at: nullableDateAt(item.retrieved_at, `${path}.retrieved_at`),
  };
}

function parseCandidate(value: unknown, path: string) {
  const item = objectAt(value, path);
  const humanRequired = booleanAt(item.needs_human_confirmation, `${path}.needs_human_confirmation`);
  if (!humanRequired) throw new VNextContractError(`${path}.needs_human_confirmation`);
  return {
    candidate_id: uuidAt(item.candidate_id, `${path}.candidate_id`),
    candidate_type: enumAt(item.candidate_type, `${path}.candidate_type`, candidateTypes),
    normalized_identity: jsonObjectAt(item.normalized_identity, `${path}.normalized_identity`),
    display_identity: stringAt(item.display_identity, `${path}.display_identity`, 512),
    source: parseSource(item.source, `${path}.source`),
    confidence: numberAt(item.confidence, `${path}.confidence`, 0, 1),
    confidence_method: stringAt(item.confidence_method, `${path}.confidence_method`, 160),
    ranking_trace: jsonObjectAt(item.ranking_trace, `${path}.ranking_trace`),
    rank: integerAt(item.rank, `${path}.rank`, 1),
    status: enumAt(item.status, `${path}.status`, candidateStatuses),
    coverage_status: enumAt(item.coverage_status, `${path}.coverage_status`, coverageStatuses),
    coverage: jsonObjectAt(item.coverage, `${path}.coverage`),
    supporting_evidence_ids: arrayAt(item.supporting_evidence_ids, `${path}.supporting_evidence_ids`, uuidAt, 100),
    supporting_identity_reference_ids: arrayAt(item.supporting_identity_reference_ids, `${path}.supporting_identity_reference_ids`, uuidAt, 100),
    possible_existing_property_entity_id: nullableUuidAt(item.possible_existing_property_entity_id, `${path}.possible_existing_property_entity_id`),
    needs_human_confirmation: true as const,
  };
}

function parseConflict(value: unknown, path: string) {
  const item = objectAt(value, path);
  return {
    conflict_id: uuidAt(item.conflict_id, `${path}.conflict_id`),
    left_candidate_id: uuidAt(item.left_candidate_id, `${path}.left_candidate_id`),
    right_candidate_id: nullableUuidAt(item.right_candidate_id, `${path}.right_candidate_id`),
    related_identity_reference_id: nullableUuidAt(item.related_identity_reference_id, `${path}.related_identity_reference_id`),
    related_evidence_id: nullableUuidAt(item.related_evidence_id, `${path}.related_evidence_id`),
    related_property_entity_id: nullableUuidAt(item.related_property_entity_id, `${path}.related_property_entity_id`),
    category: enumAt(item.category, `${path}.category`, conflictCategories),
    severity: enumAt(item.severity, `${path}.severity`, conflictSeverities),
    state: enumAt(item.state, `${path}.state`, conflictStates),
  };
}

function parseDecision(value: unknown, path: string) {
  const item = objectAt(value, path);
  return {
    decision_id: uuidAt(item.decision_id, `${path}.decision_id`),
    decision_type: enumAt(item.decision_type, `${path}.decision_type`, decisionTypes),
    candidate_id: nullableUuidAt(item.candidate_id, `${path}.candidate_id`),
    property_entity_id: nullableUuidAt(item.property_entity_id, `${path}.property_entity_id`),
    reason_code: nullableStringAt(item.reason_code, `${path}.reason_code`, 80),
    resolution_version_observed: integerAt(item.resolution_version_observed, `${path}.resolution_version_observed`, 1),
    decision_version: integerAt(item.decision_version, `${path}.decision_version`, 1),
    actor_user_id: uuidAt(item.actor_user_id, `${path}.actor_user_id`),
    decided_at: dateAt(item.decided_at, `${path}.decided_at`),
  };
}

function parseAttempt(value: unknown, path: string) {
  const item = objectAt(value, path);
  return {
    attempt_id: uuidAt(item.attempt_id, `${path}.attempt_id`),
    order: integerAt(item.order, `${path}.order`, 1),
    strategy_id: stringAt(item.strategy_id, `${path}.strategy_id`, 160),
    source: parseSource(item.source, `${path}.source`),
    status: enumAt(item.status, `${path}.status`, attemptStatuses),
    coverage_status: enumAt(item.coverage_status, `${path}.coverage_status`, coverageStatuses),
    coverage: jsonObjectAt(item.coverage, `${path}.coverage`),
    result_count: integerAt(item.result_count, `${path}.result_count`),
    error_category: item.error_category === null ? null : enumAt(item.error_category, `${path}.error_category`, attemptErrorCategories),
    error_code: nullableStringAt(item.error_code, `${path}.error_code`, 80),
    retryable: item.retryable === null ? null : booleanAt(item.retryable, `${path}.retryable`),
    started_at: dateAt(item.started_at, `${path}.started_at`),
    completed_at: dateAt(item.completed_at, `${path}.completed_at`),
  };
}

export function parsePropertyResolution(value: unknown): {
  resolution_id: string; workspace_id: string; case_id: string | null; state: ResolutionState;
  input: { kind: "address" | "lot_number" | "building_number" | "coordinates" | "map_click"; value: JsonObject };
  normalized_input: JsonObject; normalization_version: string; coverage_status: CoverageStatus; coverage: JsonObject;
  ambiguity: (typeof ambiguityStates)[number]; needs_human_confirmation: boolean; candidates: ReturnType<typeof parseCandidate>[];
  conflicts: ReturnType<typeof parseConflict>[]; provider_attempts: ReturnType<typeof parseAttempt>[]; decisions: ReturnType<typeof parseDecision>[];
  selected_candidate_id: string | null; confirmed_property_entity_id: string | null; version: number;
  created_by: string; created_at: string; updated_at: string;
} {
  const path = "resolution";
  const item = objectAt(value, path);
  const input = objectAt(item.input, `${path}.input`);
  const parsed = {
    resolution_id: uuidAt(item.resolution_id, `${path}.resolution_id`),
    workspace_id: uuidAt(item.workspace_id, `${path}.workspace_id`),
    case_id: nullableUuidAt(item.case_id, `${path}.case_id`),
    state: enumAt(item.state, `${path}.state`, resolutionStates),
    input: {
      kind: enumAt(input.kind, `${path}.input.kind`, ["address", "lot_number", "building_number", "coordinates", "map_click"] as const),
      value: jsonObjectAt(input.value, `${path}.input.value`),
    },
    normalized_input: jsonObjectAt(item.normalized_input, `${path}.normalized_input`),
    normalization_version: stringAt(item.normalization_version, `${path}.normalization_version`, 80),
    coverage_status: enumAt(item.coverage_status, `${path}.coverage_status`, coverageStatuses),
    coverage: jsonObjectAt(item.coverage, `${path}.coverage`),
    ambiguity: enumAt(item.ambiguity, `${path}.ambiguity`, ambiguityStates),
    needs_human_confirmation: booleanAt(item.needs_human_confirmation, `${path}.needs_human_confirmation`),
    candidates: arrayAt(item.candidates, `${path}.candidates`, parseCandidate, 100),
    conflicts: arrayAt(item.conflicts, `${path}.conflicts`, parseConflict, 100),
    provider_attempts: arrayAt(item.provider_attempts, `${path}.provider_attempts`, parseAttempt, 100),
    decisions: arrayAt(item.decisions, `${path}.decisions`, parseDecision, 200),
    selected_candidate_id: nullableUuidAt(item.selected_candidate_id, `${path}.selected_candidate_id`),
    confirmed_property_entity_id: nullableUuidAt(item.confirmed_property_entity_id, `${path}.confirmed_property_entity_id`),
    version: integerAt(item.version, `${path}.version`, 1),
    created_by: uuidAt(item.created_by, `${path}.created_by`),
    created_at: dateAt(item.created_at, `${path}.created_at`),
    updated_at: dateAt(item.updated_at, `${path}.updated_at`),
  };
  if (parsed.state === "confirmed") {
    if (parsed.needs_human_confirmation || !parsed.selected_candidate_id || !parsed.confirmed_property_entity_id) {
      throw new VNextContractError(`${path}.confirmation`);
    }
    const matchingDecision = parsed.decisions.some((decision) => decision.decision_type === "confirmed"
      && decision.candidate_id === parsed.selected_candidate_id
      && decision.property_entity_id === parsed.confirmed_property_entity_id);
    if (!matchingDecision) throw new VNextContractError(`${path}.decisions`);
  } else if (parsed.state === "rejected") {
    if (parsed.needs_human_confirmation || parsed.selected_candidate_id !== null || parsed.confirmed_property_entity_id !== null
      || !parsed.decisions.some((decision) => decision.decision_type === "resolution_rejected")) {
      throw new VNextContractError(`${path}.rejection`);
    }
  } else if (!parsed.needs_human_confirmation || parsed.selected_candidate_id !== null || parsed.confirmed_property_entity_id !== null) {
    throw new VNextContractError(`${path}.human_gate`);
  }
  return parsed;
}

function parseConfirmation(value: unknown, path: string) {
  const item = objectAt(value, path);
  const parsed = {
    available: booleanAt(item.available, `${path}.available`),
    human_confirmed: booleanAt(item.human_confirmed, `${path}.human_confirmed`),
    confirmation_id: nullableUuidAt(item.confirmation_id, `${path}.confirmation_id`),
    confirmed_at: nullableDateAt(item.confirmed_at, `${path}.confirmed_at`),
    confirmed_by: nullableUuidAt(item.confirmed_by, `${path}.confirmed_by`),
    resolution_id: nullableUuidAt(item.resolution_id, `${path}.resolution_id`),
  };
  const references = [parsed.confirmation_id, parsed.confirmed_at, parsed.confirmed_by, parsed.resolution_id];
  const referencesValid = parsed.human_confirmed
    ? references.every((reference) => reference !== null)
    : references.every((reference) => reference === null);
  if (!referencesValid || parsed.available !== parsed.human_confirmed) {
    throw new VNextContractError(path);
  }
  return parsed;
}

export function parseProperty(value: unknown) {
  const path = "property";
  const item = objectAt(value, path);
  return {
    property_entity_id: uuidAt(item.property_entity_id, `${path}.property_entity_id`),
    workspace_id: uuidAt(item.workspace_id, `${path}.workspace_id`),
    lifecycle_state: enumAt(item.lifecycle_state, `${path}.lifecycle_state`, propertyStates),
    display_label: stringAt(item.display_label, `${path}.display_label`, 512),
    confirmation_summary: parseConfirmation(item.confirmation_summary, `${path}.confirmation_summary`),
    version: integerAt(item.version, `${path}.version`, 1),
    created_at: dateAt(item.created_at, `${path}.created_at`),
    updated_at: dateAt(item.updated_at, `${path}.updated_at`),
  };
}

function parseGraphNode(value: unknown, path: string) {
  const item = objectAt(value, path);
  return {
    node_id: uuidAt(item.node_id, `${path}.node_id`), node_type: stringAt(item.node_type, `${path}.node_type`, 80),
    record_id: uuidAt(item.record_id, `${path}.record_id`), display_label: stringAt(item.display_label, `${path}.display_label`, 512),
    status: item.status === null ? null : enumAt(item.status, `${path}.status`, referenceStatuses),
    source: item.source === null ? null : parseSource(item.source, `${path}.source`),
    valid_from: nullableDateAt(item.valid_from, `${path}.valid_from`), valid_to: nullableDateAt(item.valid_to, `${path}.valid_to`),
  };
}

function parseRelation(value: unknown, path: string) {
  const item = objectAt(value, path);
  return {
    relation_id: uuidAt(item.relation_id, `${path}.relation_id`), from_node_id: uuidAt(item.from_node_id, `${path}.from_node_id`),
    to_node_id: uuidAt(item.to_node_id, `${path}.to_node_id`), relation_type: enumAt(item.relation_type, `${path}.relation_type`, relationTypes),
    direction: enumAt(item.direction, `${path}.direction`, relationDirections),
    confidence: item.confidence === null ? null : numberAt(item.confidence, `${path}.confidence`, 0, 1),
    confidence_method: nullableStringAt(item.confidence_method, `${path}.confidence_method`, 160), source: parseSource(item.source, `${path}.source`),
    evidence_id: nullableUuidAt(item.evidence_id, `${path}.evidence_id`), status: enumAt(item.status, `${path}.status`, relationStatuses),
    valid_from: nullableDateAt(item.valid_from, `${path}.valid_from`), valid_to: nullableDateAt(item.valid_to, `${path}.valid_to`),
    supersedes_relation_id: nullableUuidAt(item.supersedes_relation_id, `${path}.supersedes_relation_id`),
    created_at: dateAt(item.created_at, `${path}.created_at`), confirmation_id: nullableUuidAt(item.confirmation_id, `${path}.confirmation_id`),
  };
}

export function parsePropertyGraph(value: unknown) {
  const path = "graph";
  const item = objectAt(value, path);
  return {
    property: parseProperty(item.property), nodes: arrayAt(item.nodes, `${path}.nodes`, parseGraphNode, 500),
    relations: arrayAt(item.relations, `${path}.relations`, parseRelation, 100),
    as_of: nullableDateAt(item.as_of, `${path}.as_of`), next_cursor: nullableStringAt(item.next_cursor, `${path}.next_cursor`, 4096),
  };
}

function parseEvidence(value: unknown, path: string) {
  const item = objectAt(value, path);
  return {
    evidence_id: uuidAt(item.evidence_id, `${path}.evidence_id`), workspace_id: uuidAt(item.workspace_id, `${path}.workspace_id`),
    fact_type: stringAt(item.fact_type, `${path}.fact_type`, 120), value: item.value === null ? null : jsonObjectAt(item.value, `${path}.value`),
    has_private_value_reference: booleanAt(item.has_private_value_reference, `${path}.has_private_value_reference`),
    value_schema: nullableStringAt(item.value_schema, `${path}.value_schema`, 160), source: parseSource(item.source, `${path}.source`),
    effective_from: nullableDateAt(item.effective_from, `${path}.effective_from`), effective_to: nullableDateAt(item.effective_to, `${path}.effective_to`),
    expires_at: nullableDateAt(item.expires_at, `${path}.expires_at`), coverage_status: enumAt(item.coverage_status, `${path}.coverage_status`, coverageStatuses),
    coverage: jsonObjectAt(item.coverage, `${path}.coverage`), status: enumAt(item.status, `${path}.status`, evidenceStatuses),
    quality_confidence: item.quality_confidence === null ? null : numberAt(item.quality_confidence, `${path}.quality_confidence`, 0, 1),
    quality_method: nullableStringAt(item.quality_method, `${path}.quality_method`, 160), quality_status: enumAt(item.quality_status, `${path}.quality_status`, qualityStatuses),
    quality: jsonObjectAt(item.quality, `${path}.quality`), license_status: enumAt(item.license_status, `${path}.license_status`, licenseStatuses),
    license_reference: nullableStringAt(item.license_reference, `${path}.license_reference`, 512), license: jsonObjectAt(item.license, `${path}.license`),
    lineage: jsonObjectAt(item.lineage, `${path}.lineage`), content_hash: stringAt(item.content_hash, `${path}.content_hash`, 128),
    version: integerAt(item.version, `${path}.version`, 1), supersedes_evidence_id: nullableUuidAt(item.supersedes_evidence_id, `${path}.supersedes_evidence_id`),
    created_at: dateAt(item.created_at, `${path}.created_at`),
  };
}

export function parsePropertyEvidence(value: unknown) {
  const path = "evidence";
  const item = objectAt(value, path);
  return {
    property: parseProperty(item.property), evidence: arrayAt(item.evidence, `${path}.evidence`, parseEvidence, 100),
    next_cursor: nullableStringAt(item.next_cursor, `${path}.next_cursor`, 4096),
  };
}

export function parseCase(value: unknown) {
  const path = "case";
  const item = objectAt(value, path);
  return {
    case_id: uuidAt(item.case_id, `${path}.case_id`), workspace_id: uuidAt(item.workspace_id, `${path}.workspace_id`),
    purpose: enumAt(item.purpose, `${path}.purpose`, casePurposes), status: enumAt(item.status, `${path}.status`, caseStatuses),
    title: stringAt(item.title, `${path}.title`, 240), identity_status: enumAt(item.identity_status, `${path}.identity_status`, caseIdentityStatuses),
    assigned_member_id: nullableUuidAt(item.assigned_member_id, `${path}.assigned_member_id`), version: integerAt(item.version, `${path}.version`, 1),
    opened_at: dateAt(item.opened_at, `${path}.opened_at`), updated_at: dateAt(item.updated_at, `${path}.updated_at`),
  };
}

export function parseCaseAttachment(value: unknown) {
  const path = "attachment";
  const item = objectAt(value, path);
  const link = objectAt(item.link, `${path}.link`);
  return {
    case: parseCase(item.case),
    link: {
      case_property_link_id: uuidAt(link.case_property_link_id, `${path}.link.case_property_link_id`),
      case_id: uuidAt(link.case_id, `${path}.link.case_id`), property_entity_id: uuidAt(link.property_entity_id, `${path}.link.property_entity_id`),
      resolution_id: uuidAt(link.resolution_id, `${path}.link.resolution_id`), confirmation_id: uuidAt(link.confirmation_id, `${path}.link.confirmation_id`),
      supersedes_case_property_link_id: nullableUuidAt(link.supersedes_case_property_link_id, `${path}.link.supersedes_case_property_link_id`),
      attached_by: uuidAt(link.attached_by, `${path}.link.attached_by`), attached_at: dateAt(link.attached_at, `${path}.link.attached_at`),
    },
  };
}

export function parseVNextContext(value: unknown) {
  const path = "context";
  const item = objectAt(value, path); const principal = objectAt(item.principal, `${path}.principal`); const features = objectAt(item.features, `${path}.features`);
  if (item.status !== "ok") throw new VNextContractError(`${path}.status`);
  return { status: "ok" as const, principal: { user_id: uuidAt(principal.user_id, `${path}.principal.user_id`) }, features: {
    identity_v1: booleanAt(features.identity_v1, `${path}.features.identity_v1`),
    legacy_case_import_v1: booleanAt(features.legacy_case_import_v1, `${path}.features.legacy_case_import_v1`),
  } };
}

export function parseWorkspaceContext(value: unknown) {
  const path = "workspace"; const item = objectAt(value, path);
  if (item.status !== "ok") throw new VNextContractError(`${path}.status`);
  return { status: "ok" as const, workspace_id: uuidAt(item.workspace_id, `${path}.workspace_id`), user_id: uuidAt(item.user_id, `${path}.user_id`), role: enumAt(item.role, `${path}.role`, roles) };
}

export function parseVNextError(value: unknown) {
  const path = "error"; const root = objectAt(value, path); const item = objectAt(root.error, `${path}.error`);
  return {
    error: {
      code: enumAt(item.code, `${path}.error.code`, errorCodes), message: stringAt(item.message, `${path}.error.message`, 512),
      request_id: stringAt(item.request_id, `${path}.error.request_id`, 128), retryable: booleanAt(item.retryable, `${path}.error.retryable`),
      details: item.details === undefined ? null : jsonObjectAt(item.details, `${path}.error.details`),
    },
  };
}
