import type { PropertyCaseWorkspace } from "./workspace-model";
/** Shared binding for saved Scenario Lab drafts and read-only evidence consumers. */
export function scenarioContext(workspace: PropertyCaseWorkspace): string {
  return JSON.stringify([workspace.caseId, workspace.revision, workspace.updatedAt, workspace.identity, workspace.assumptions, workspace.finance, workspace.location.routeEvidence]);
}
