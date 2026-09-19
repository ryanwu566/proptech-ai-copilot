"use client";

import { useEffect, useState } from "react";
import { VNextApiError, VNextSessionError, vnextIdentityClient } from "@/lib/vnext-identity-client";
import { VNextContractError, type PropertyDTO, type PropertyEvidenceDTO, type PropertyGraphDTO, type WorkspaceContextDTO } from "@/lib/vnext-identity-contract";
import styles from "./professional-workspace-shell.module.css";

export type WorkspaceContextInputState = "missing" | "invalid" | "provided";
type Readiness = "AVAILABLE" | "PARTIAL" | "NOT_AVAILABLE";
type ModuleId = "identity" | "parcel" | "building" | "planning" | "market" | "listings" | "documents" | "crm" | "decision";

type LoadedContext = {
  workspace: WorkspaceContextDTO;
  property: PropertyDTO;
  graph: PropertyGraphDTO;
  evidence: PropertyEvidenceDTO;
};

type LoadState =
  | { kind: "idle" | "loading" | "denied" | "error" | "configuration_error" | "session_error" }
  | { kind: "ready"; data: LoadedContext };

const MODULES: ReadonlyArray<{ id: ModuleId; label: string; description: string }> = [
  { id: "identity", label: "Identity", description: "Existing PropertyEntity, graph, and confirmation metadata from approved VNext reads." },
  { id: "parcel", label: "Parcel/GIS", description: "No approved professional parcel geometry or durable GIS case-set read is available in this shell." },
  { id: "building", label: "Building", description: "No approved building-candidate or building-fact read is available in this shell." },
  { id: "planning", label: "Planning", description: "No planning, zoning, or redevelopment backend contract is available." },
  { id: "market", label: "Market", description: "Historical market services are not connected to a confirmed professional case read in this slice." },
  { id: "listings", label: "Listings", description: "No licensed active-listing provider or professional listing read is available." },
  { id: "documents", label: "Title/Documents", description: "No title or private document-vault workflow is available." },
  { id: "crm", label: "CRM", description: "No contact, assignment, follow-up, or professional CRM contract is available." },
  { id: "decision", label: "Decision", description: "No durable professional decision, review, or approval record is available." },
];

function ReadinessBadge({ value }: { value: Readiness }) {
  return <span className={`${styles.badge} ${styles[`badge_${value.toLowerCase()}`]}`} aria-label={`Readiness: ${value}`}>{value}</span>;
}

function moduleReadiness(moduleId: ModuleId, state: LoadState): Readiness {
  if (moduleId !== "identity") return "NOT_AVAILABLE";
  if (state.kind === "ready") return "AVAILABLE";
  return state.kind === "loading" ? "PARTIAL" : "NOT_AVAILABLE";
}

function loadMessage(contextState: WorkspaceContextInputState, state: LoadState): string {
  if (contextState === "missing") return "Workspace and PropertyEntity context were not supplied. Both identifiers are required before approved reads can run.";
  if (contextState === "invalid") return "Workspace and PropertyEntity context must both be supplied as valid UUIDs. No backend read was attempted.";
  if (state.kind === "loading") return "Loading approved workspace, PropertyEntity, graph, and evidence reads…";
  if (state.kind === "denied") return "The requested workspace or PropertyEntity was not found or is not available to this account.";
  if (state.kind === "configuration_error") return "Professional backend configuration is unavailable. No read or fallback data was used.";
  if (state.kind === "session_error") return "The existing VNext session is no longer available. Authentication must be restored before approved reads can run.";
  if (state.kind === "error") return "Approved workspace context could not be loaded. No fallback or demo data was used.";
  return "Approved workspace context is loaded.";
}

export function ProfessionalWorkspaceShell({
  caseId,
  contextState,
  workspaceId,
  propertyId,
}: {
  caseId: string;
  contextState: WorkspaceContextInputState;
  workspaceId: string | null;
  propertyId: string | null;
}) {
  const [state, setState] = useState<LoadState>({ kind: contextState === "provided" ? "loading" : "idle" });
  const [selectedModule, setSelectedModule] = useState<ModuleId>("identity");

  useEffect(() => {
    let active = true;
    if (contextState !== "provided" || !workspaceId || !propertyId) {
      setState({ kind: "idle" });
      return () => { active = false; };
    }

    async function loadApprovedContext() {
      setState({ kind: "loading" });
      try {
        const workspace = await vnextIdentityClient.workspace(workspaceId as string);
        const property = await vnextIdentityClient.property(propertyId as string);
        if (property.workspace_id !== workspace.workspace_id) throw new VNextContractError("workspace.property_binding");
        const [graph, evidence] = await Promise.all([
          vnextIdentityClient.graph(property.property_entity_id),
          vnextIdentityClient.evidence(property.property_entity_id),
        ]);
        if (graph.property.workspace_id !== workspace.workspace_id || evidence.property.workspace_id !== workspace.workspace_id) {
          throw new VNextContractError("workspace.read_binding");
        }
        if (active) setState({ kind: "ready", data: { workspace, property, graph, evidence } });
      } catch (error: unknown) {
        if (!active) return;
        if (error instanceof VNextSessionError) {
          setState({ kind: error.reason === "configuration_error" ? "configuration_error" : "session_error" });
          return;
        }
        const denied = error instanceof VNextApiError
          && (error.status === 403 || error.status === 404 || error.code === "permission_denied" || error.code === "not_found");
        setState({ kind: denied ? "denied" : "error" });
      }
    }

    void loadApprovedContext();
    return () => { active = false; };
  }, [contextState, propertyId, workspaceId]);

  const loaded = state.kind === "ready" ? state.data : null;
  const evidenceReadiness: Readiness = state.kind === "ready" ? "AVAILABLE"
    : state.kind === "loading" || contextState === "missing" ? "PARTIAL" : "NOT_AVAILABLE";
  const activeModule = MODULES.find((item) => item.id === selectedModule) ?? MODULES[0];
  const activeModuleReadiness = moduleReadiness(activeModule.id, state);

  return (
    <div className={styles.page}>
      <header className={styles.contextHeader} role="banner" aria-label="Workspace context">
        <div className={styles.contextTitle}>
          <div>
            <p className={styles.eyebrow}>CASE-CENTERED INVESTIGATION SHELL</p>
            <h1>Professional Workspace</h1>
          </div>
          <ReadinessBadge value={loaded ? "PARTIAL" : "NOT_AVAILABLE"} />
        </div>
        <dl className={styles.contextFacts}>
          <div><dt>Route case reference</dt><dd>{caseId}</dd></div>
          <div><dt>Case details</dt><dd>Case details are not available from an approved read contract.</dd></div>
          <div><dt>Workspace</dt><dd>{loaded ? `${loaded.workspace.workspace_id} · ${loaded.workspace.role}` : "Not loaded"}</dd></div>
          <div><dt>PropertyEntity</dt><dd>{loaded ? `${loaded.property.display_label} · ${loaded.property.property_entity_id}` : "Not loaded"}</dd></div>
        </dl>
        <p className={styles.contextNotice} role={contextState === "invalid" || ["denied", "error", "configuration_error", "session_error"].includes(state.kind) ? "alert" : "status"}>
          {loadMessage(contextState, state)}
        </p>
      </header>

      <main className={styles.workspaceGrid}>
        <nav className={styles.moduleNavigation} aria-label="Workspace modules">
          <div className={styles.panelHeading}><div><p className={styles.kicker}>NAVIGATION</p><h2>Modules</h2></div></div>
          <div className={styles.moduleList}>
            {MODULES.map((module) => {
              const readiness = moduleReadiness(module.id, state);
              return <button
                type="button"
                key={module.id}
                className={`${styles.moduleButton} ${selectedModule === module.id ? styles.moduleButtonActive : ""}`}
                aria-pressed={selectedModule === module.id}
                onClick={() => setSelectedModule(module.id)}
              >
                <span>{module.label}</span><ReadinessBadge value={readiness} />
              </button>;
            })}
          </div>
        </nav>

        <section className={`${styles.panel} ${styles.mapCanvas}`} aria-labelledby="map-canvas-heading">
          <div className={styles.panelHeading}>
            <div><p className={styles.kicker}>CENTRAL WORKSPACE</p><h2 id="map-canvas-heading">Map Canvas</h2></div>
            <ReadinessBadge value="NOT_AVAILABLE" />
          </div>
          <div className={styles.mapEmpty}>
            <div className={styles.mapMarker} aria-hidden="true"><span /></div>
            <p>No supported professional geometry is available.</p>
            <span>Cadastral parcels, buildings, planning layers, title overlays, and listing markers are not rendered in this foundation shell.</span>
          </div>
        </section>

        <aside className={`${styles.panel} ${styles.evidenceRail}`} aria-labelledby="evidence-rail-heading">
          <div className={styles.panelHeading}>
            <div><p className={styles.kicker}>TRACEABILITY</p><h2 id="evidence-rail-heading">Evidence Rail</h2></div>
            <ReadinessBadge value={evidenceReadiness} />
          </div>
          {state.kind === "loading" && <p className={styles.muted} role="status">Loading the approved evidence ledger…</p>}
          {state.kind === "ready" && state.data.evidence.evidence.length === 0 && <p className={styles.emptyState}>No evidence items were returned by the approved evidence interface.</p>}
          {state.kind === "ready" && state.data.evidence.evidence.length > 0 && <ol className={styles.evidenceList}>
            {state.data.evidence.evidence.map((item) => <li key={item.evidence_id} className={styles.evidenceItem}>
              <div><strong>{item.fact_type}</strong><span className={styles.evidenceStatus}>{item.status}</span></div>
              <dl>
                <div><dt>Source</dt><dd>{item.source.source_id} · {item.source.environment}</dd></div>
                <div><dt>Coverage</dt><dd>{item.coverage_status}</dd></div>
                <div><dt>Quality</dt><dd>{item.quality_status}</dd></div>
                <div><dt>Retrieved</dt><dd>{item.source.retrieved_at ?? "Unknown"}</dd></div>
              </dl>
            </li>)}
          </ol>}
          {state.kind !== "ready" && state.kind !== "loading" && <p className={styles.emptyState}>Evidence requires validated workspace and PropertyEntity context. No evidence was inferred.</p>}
        </aside>

        <section className={`${styles.panel} ${styles.taskPanel}`} aria-labelledby="task-panel-heading">
          <div className={styles.panelHeading}>
            <div><p className={styles.kicker}>INVESTIGATION</p><h2 id="task-panel-heading">Task Panel</h2></div>
            <ReadinessBadge value="NOT_AVAILABLE" />
          </div>
          <p className={styles.emptyState}>No durable professional task or assignment backend is available. Browser-local pseudo tasks are not created.</p>
        </section>

        <section className={`${styles.panel} ${styles.moduleDetail}`} aria-labelledby="module-detail-heading">
          <div className={styles.panelHeading}>
            <div><p className={styles.kicker}>SELECTED MODULE</p><h2 id="module-detail-heading">Module Detail</h2></div>
            <ReadinessBadge value={activeModuleReadiness} />
          </div>
          <div className={styles.moduleDetailTitle}><h3>{activeModule.label}</h3><p>{activeModule.description}</p></div>
          <dl className={styles.moduleContext} aria-label={`${activeModule.label} active context`}>
            <div><dt>Workspace</dt><dd>{loaded ? loaded.workspace.workspace_id : "NOT_AVAILABLE — verified workspace context is not loaded."}</dd></div>
            <div><dt>Property</dt><dd>{loaded ? `${loaded.property.display_label} · ${loaded.property.property_entity_id}` : "NOT_AVAILABLE — verified PropertyEntity context is not loaded."}</dd></div>
            <div><dt>Case</dt><dd>{caseId} · route reference only; case details are NOT_AVAILABLE.</dd></div>
            <div><dt>Evidence freshness</dt><dd>NOT_AVAILABLE — approved interfaces do not provide a module-specific freshness summary.</dd></div>
            <div><dt>Next investigation step</dt><dd>NOT_AVAILABLE — no durable professional task or next-step contract exists.</dd></div>
          </dl>
          {activeModule.id === "identity" && loaded ? <div className={styles.identityDetail}>
            <dl>
              <div><dt>Lifecycle</dt><dd>{loaded.property.lifecycle_state}</dd></div>
              <div><dt>Property version</dt><dd>{loaded.property.version}</dd></div>
              <div><dt>Human confirmed</dt><dd>{loaded.property.confirmation_summary.human_confirmed ? "Yes" : "No"}</dd></div>
              <div><dt>Graph records</dt><dd>{loaded.graph.nodes.length} nodes · {loaded.graph.relations.length} relations</dd></div>
            </dl>
            {loaded.graph.relations.length === 0 ? <p className={styles.emptyState}>The approved graph interface returned no relations.</p> : <ol className={styles.relationList}>
              {loaded.graph.relations.map((relation) => <li key={relation.relation_id}>
                <strong>{relation.relation_type}</strong><span>{relation.status} · {relation.source.source_id}</span>
              </li>)}
            </ol>}
          </div> : <p className={styles.emptyState}>{activeModule.id === "identity" ? loadMessage(contextState, state) : activeModule.description}</p>}
        </section>

        <section className={`${styles.panel} ${styles.copilot}`} aria-labelledby="copilot-heading">
          <div className={styles.panelHeading}>
            <div><p className={styles.kicker}>SYNTHESIS</p><h2 id="copilot-heading">Copilot</h2></div>
            <ReadinessBadge value="NOT_AVAILABLE" />
          </div>
          <p className={styles.emptyState}>Evidence-grounded professional AI is not available. No chat, recommendation, or generated case claim is provided.</p>
        </section>

        <section className={`${styles.panel} ${styles.activityTimeline}`} aria-labelledby="activity-timeline-heading">
          <div className={styles.panelHeading}>
            <div><p className={styles.kicker}>DURABLE HISTORY</p><h2 id="activity-timeline-heading">Activity Timeline</h2></div>
            <ReadinessBadge value="NOT_AVAILABLE" />
          </div>
          <p className={styles.emptyState}>No durable activity read contract is available. Page loads and browser events are not presented as case history.</p>
        </section>
      </main>
    </div>
  );
}
