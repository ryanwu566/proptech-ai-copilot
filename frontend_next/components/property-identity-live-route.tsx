"use client";

import { useEffect, useState } from "react";
import { PropertyIdentityReview } from "@/components/property-identity-review";
import { VNextApiError, VNextSessionError, vnextIdentityClient } from "@/lib/vnext-identity-client";
import type { PropertyDTO, WorkspaceContextDTO } from "@/lib/vnext-identity-contract";

type State =
  | { kind: "loading" | "disabled" | "denied" | "error" }
  | { kind: "ready"; property: PropertyDTO; workspace: WorkspaceContextDTO };

export function PropertyIdentityLiveRoute({ workspaceId, propertyId }: { workspaceId: string; propertyId: string }) {
  const [state, setState] = useState<State>({ kind: "loading" });
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const context = await vnextIdentityClient.context();
        if (!context.features.identity_v1) { if (active) setState({ kind: "disabled" }); return; }
        const workspace = await vnextIdentityClient.workspace(workspaceId);
        if (workspace.user_id !== context.principal.user_id) throw new Error("workspace principal mismatch");
        const property = await vnextIdentityClient.property(propertyId);
        if (property.workspace_id !== workspace.workspace_id) throw new Error("property workspace mismatch");
        if (active) setState({ kind: "ready", workspace, property });
      } catch (error) {
        if (!active || error instanceof VNextSessionError) return;
        if (error instanceof VNextApiError && (error.status === 403 || error.status === 404 || error.code === "permission_denied")) {
          setState({ kind: "denied" });
        } else setState({ kind: "error" });
      }
    }
    setState({ kind: "loading" });
    void load();
    return () => { active = false; };
  }, [workspaceId, propertyId]);

  if (state.kind === "ready") return <PropertyIdentityReview property={state.property} role={state.workspace.role} api={vnextIdentityClient} />;
  const message = state.kind === "loading" ? "正在載入房產與工作空間…"
    : state.kind === "disabled" ? "房產識別功能目前尚未開放。"
      : state.kind === "denied" ? "無法查看這個工作空間或房產。" : "房產資料暫時無法載入，請稍後再試。";
  return <main style={{ maxWidth: 800, margin: "48px auto", padding: "0 20px" }}>
    <h1>房產識別審閱</h1><p role={state.kind === "loading" ? "status" : "alert"}>{message}</p>
  </main>;
}
