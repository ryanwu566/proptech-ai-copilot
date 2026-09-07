"use client";

import { API_BASE } from "@/lib/api";
import { getVNextAccessToken } from "@/lib/vnext-auth-session";
import {
  VNextContractError,
  parseCase,
  parseCaseAttachment,
  parseProperty,
  parsePropertyEvidence,
  parsePropertyGraph,
  parsePropertyResolution,
  parseVNextContext,
  parseVNextError,
  parseWorkspaceContext,
  type PropertyDTO,
  type PropertyResolutionDTO,
  type VNextContextDTO,
  type VNextErrorCode,
  type WorkspaceContextDTO,
} from "@/lib/vnext-identity-contract";

export type ResolutionInput =
  | { kind: "address"; value: { text: string } }
  | { kind: "lot_number"; value: { jurisdiction: string; section: string; subsection: string | null; lot_number: string } }
  | { kind: "building_number"; value: { jurisdiction: string | null; building_number: string } }
  | { kind: "coordinates"; value: { latitude: number; longitude: number; crs: "EPSG:4326" } }
  | { kind: "map_click"; value: { latitude: number; longitude: number; crs: "EPSG:4326"; map_context: string | null } };

export type CasePurpose = "buy_due_diligence" | "development" | "brokerage" | "valuation_review" | "investment_review";

export class VNextApiError extends Error {
  constructor(
    readonly code: VNextErrorCode,
    readonly status: number,
    readonly requestId: string,
    readonly retryable: boolean,
  ) {
    super(code);
    this.name = "VNextApiError";
  }
}

export class VNextOutcomeUnknownError extends Error {
  constructor() {
    super("command_outcome_unknown");
    this.name = "VNextOutcomeUnknownError";
  }
}

export class VNextSessionError extends Error {
  constructor(readonly reason: "configuration_error" | "missing_session") {
    super(reason);
    this.name = "VNextSessionError";
  }
}

function apiUrl(path: string): string {
  if (!API_BASE) throw new VNextSessionError("configuration_error");
  return `${API_BASE}${path}`;
}

function identifier(value: string): string {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) {
    throw new VNextContractError("request.identifier");
  }
  return value;
}

async function authenticatedHeaders(commandKey?: string): Promise<Headers> {
  const session = await getVNextAccessToken();
  if (session.status !== "authenticated") throw new VNextSessionError(session.status);
  const headers = new Headers({ Authorization: `Bearer ${session.accessToken}`, Accept: "application/json" });
  if (commandKey) {
    if (!/^[A-Za-z0-9._:-]{16,128}$/.test(commandKey)) throw new VNextContractError("request.idempotency_key");
    headers.set("Content-Type", "application/json");
    headers.set("Idempotency-Key", commandKey);
  }
  return headers;
}

async function requestJson<T>(
  path: string,
  parser: (value: unknown) => T,
  options: { method?: "GET" | "POST"; body?: object; commandKey?: string; timeoutMs?: number } = {},
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), options.timeoutMs ?? 15_000);
  try {
    const response = await fetch(apiUrl(path), {
      method: options.method ?? "GET",
      headers: await authenticatedHeaders(options.commandKey),
      body: options.body ? JSON.stringify(options.body) : undefined,
      cache: "no-store",
      signal: controller.signal,
    });
    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      throw new VNextContractError("response.json");
    }
    if (!response.ok) {
      const envelope = parseVNextError(payload);
      throw new VNextApiError(envelope.error.code, response.status, envelope.error.request_id, envelope.error.retryable);
    }
    return parser(payload);
  } catch (error: unknown) {
    if (error instanceof VNextApiError || error instanceof VNextContractError || error instanceof VNextSessionError) throw error;
    throw new VNextOutcomeUnknownError();
  } finally {
    window.clearTimeout(timeout);
  }
}

export function newIdempotencyKey(command: "resolution" | "confirm" | "reject" | "case" | "attach"): string {
  return `${command}:${crypto.randomUUID()}`;
}

function requireMatch(actual: string, expected: string, path: string): void {
  if (actual !== expected) throw new VNextContractError(path);
}

export const vnextIdentityClient = {
  context: (): Promise<VNextContextDTO> => requestJson("/v1", parseVNextContext),
  workspace: async (workspaceId: string): Promise<WorkspaceContextDTO> => {
    const expected = identifier(workspaceId);
    const result = await requestJson(`/v1/workspaces/${expected}/context`, parseWorkspaceContext);
    requireMatch(result.workspace_id, expected, "workspace.workspace_id");
    return result;
  },
  createResolution: async (workspaceId: string, input: ResolutionInput, commandKey: string): Promise<PropertyResolutionDTO> => {
    const expectedWorkspace = identifier(workspaceId);
    const result = await requestJson("/v1/property-resolutions", parsePropertyResolution, {
      method: "POST", commandKey, body: { workspace_id: expectedWorkspace, input, case_id: null },
    });
    requireMatch(result.workspace_id, expectedWorkspace, "resolution.workspace_id");
    return result;
  },
  resolution: async (resolutionId: string): Promise<PropertyResolutionDTO> => {
    const expected = identifier(resolutionId);
    const result = await requestJson(`/v1/property-resolutions/${expected}`, parsePropertyResolution);
    requireMatch(result.resolution_id, expected, "resolution.resolution_id");
    return result;
  },
  confirm: async (resolutionId: string, candidateId: string, version: number, confirmationReason: string, commandKey: string): Promise<PropertyResolutionDTO> => {
    const expectedResolution = identifier(resolutionId);
    const expectedCandidate = identifier(candidateId);
    const result = await requestJson(`/v1/property-resolutions/${expectedResolution}/confirm`, parsePropertyResolution, {
      method: "POST", commandKey, body: { candidate_id: identifier(candidateId), version, confirmation_reason: confirmationReason },
    });
    requireMatch(result.resolution_id, expectedResolution, "resolution.resolution_id");
    if (result.state === "confirmed") requireMatch(result.selected_candidate_id ?? "", expectedCandidate, "resolution.selected_candidate_id");
    return result;
  },
  reject: async (resolutionId: string, candidateId: string | null, version: number, reasonCode: string, commandKey: string): Promise<PropertyResolutionDTO> => {
    const expectedResolution = identifier(resolutionId);
    const result = await requestJson(`/v1/property-resolutions/${expectedResolution}/reject`, parsePropertyResolution, {
      method: "POST", commandKey, body: { candidate_id: candidateId ? identifier(candidateId) : null, version, reason_code: reasonCode },
    });
    requireMatch(result.resolution_id, expectedResolution, "resolution.resolution_id");
    return result;
  },
  property: async (propertyId: string): Promise<PropertyDTO> => {
    const expected = identifier(propertyId);
    const result = await requestJson(`/v1/properties/${expected}`, parseProperty);
    requireMatch(result.property_entity_id, expected, "property.property_entity_id");
    return result;
  },
  graph: async (propertyId: string, cursor?: string) => {
    const expected = identifier(propertyId);
    const query = new URLSearchParams({ limit: "25" });
    if (cursor) query.set("cursor", cursor);
    const result = await requestJson(`/v1/properties/${expected}/graph?${query}`, parsePropertyGraph);
    requireMatch(result.property.property_entity_id, expected, "graph.property.property_entity_id");
    return result;
  },
  evidence: async (propertyId: string, cursor?: string) => {
    const expected = identifier(propertyId);
    const query = new URLSearchParams({ limit: "25" });
    if (cursor) query.set("cursor", cursor);
    const result = await requestJson(`/v1/properties/${expected}/evidence?${query}`, parsePropertyEvidence);
    requireMatch(result.property.property_entity_id, expected, "evidence.property.property_entity_id");
    return result;
  },
  createCase: async (workspaceId: string, purpose: CasePurpose, title: string, commandKey: string) => {
    const expectedWorkspace = identifier(workspaceId);
    const result = await requestJson("/v1/cases", parseCase, { method: "POST", commandKey, body: { workspace_id: expectedWorkspace, purpose, title } });
    requireMatch(result.workspace_id, expectedWorkspace, "case.workspace_id");
    return result;
  },
  attachResolution: async (caseId: string, resolutionId: string, propertyId: string, caseVersion: number, commandKey: string) => {
    const expectedCase = identifier(caseId); const expectedResolution = identifier(resolutionId); const expectedProperty = identifier(propertyId);
    const result = await requestJson(`/v1/cases/${expectedCase}/attach-resolution`, parseCaseAttachment, {
      method: "POST", commandKey, body: { resolution_id: expectedResolution, case_version: caseVersion },
    });
    requireMatch(result.case.case_id, expectedCase, "attachment.case.case_id");
    requireMatch(result.link.case_id, expectedCase, "attachment.link.case_id");
    requireMatch(result.link.resolution_id, expectedResolution, "attachment.link.resolution_id");
    requireMatch(result.link.property_entity_id, expectedProperty, "attachment.link.property_entity_id");
    return result;
  },
};
