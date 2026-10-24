"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { CommercialButton } from "@/components/design-system/button";
import { createBrowserCaseRepository } from "@/lib/workspace/case-repository";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { StatusLabel } from "@/components/design-system/status-label";
import { resolveCommercialState } from "@/lib/commercial/state";
import { formatExactDate, formatWan } from "@/lib/commercial/formatters";
import type { PropertyCaseWorkspace } from "@/lib/workspace/workspace-model";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { journeyIdentityCopy, journeyIdentityEvidenceLabel } from "@/lib/journey-identity-copy";
import { scenarioEntryCopy } from "@/lib/workspace/scenario-entry-copy";
import { GuidedTourEntry } from "@/components/guided-tour-entry";
import { caseFrameCopy } from "@/lib/workspace/case-frame-copy";

/** Closes an open popover disclosure on an outside press or Escape, returning focus to its summary. */
export function usePopoverDisclosure() {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const close = (event: Event) => {
      const details = ref.current;
      if (!details?.open) return;
      if (event instanceof KeyboardEvent) {
        if (event.key !== "Escape") return;
        details.open = false;
        details.querySelector("summary")?.focus();
      } else if (!details.contains(event.target as Node)) details.open = false;
    };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", close);
    return () => { document.removeEventListener("pointerdown", close); document.removeEventListener("keydown", close); };
  }, []);
  return ref;
}

/** The case bar: identity on the left, save and secondary details on the right, one row on wide screens. */
export function PropertyContextHeader({ workspace, readOnly = false }: { workspace: PropertyCaseWorkspace; readOnly?: boolean }) {
  const { locale, copyFrom } = useExperienceLocale();
  const copy = (key: keyof (typeof caseFrameCopy)["en"]) => copyFrom(caseFrameCopy, key);
  const identityCopy = journeyIdentityCopy(locale);
  const pathname = usePathname();
  const isFinance = pathname.endsWith("/finance");
  const isScenario = pathname.endsWith("/scenarios");
  const repository = useMemo(createBrowserCaseRepository, []);
  const [saveStatus, setSaveStatus] = useState("");
  const more = usePopoverDisclosure();
  useEffect(() => {
    setSaveStatus("");
    if (more.current) more.current.open = false;
  }, [pathname, more]);
  async function saveSnapshot() {
    setSaveStatus("");
    try {
      const result = await repository.saveSnapshot(workspace);
      setSaveStatus(result.status === "saved"
        ? copy("saved")
        : result.reason === "storage_unavailable" ? `${copy("saveFailed")}${result.message}` : result.message);
    } catch {
      setSaveStatus(copy("saveStorageFailed"));
    }
  }
  const identity = resolveCommercialState("identity", workspace.identity.state);
  const activePrice = workspace.assumptions.activePriceWan;
  const anchor = workspace.identity.anchor;
  return <header role="banner" aria-label={copy("current")} className="workspace-property-header" data-testid="case-context-header">
    <div className="workspace-property-header__panel">
      <div className="workspace-property-header__primary">
        <div className="workspace-property-header__title">
          <p className="text-meta">{copy("current")} · {workspace.title}</p>
          <strong>{workspace.displayAddress}</strong>
        </div>
        <StatusLabel semanticRole={identity.role}>{identity.label[locale]}</StatusLabel>
        <div className="workspace-property-header__save">
          <GuidedTourEntry cta="demo" className="ds-button ds-button--tertiary ds-button--compact" />
          {!readOnly && (isScenario ? <span className="text-meta">{copyFrom(scenarioEntryCopy, "readonly")}</span> : isFinance ? <a className="ds-button ds-button--secondary ds-button--compact" href="#finance-save-section">{copy("saveFinance")}</a> : <CommercialButton size="compact" variant="secondary" onClick={saveSnapshot}>{copy("saveSnapshot")}</CommercialButton>)}
          {/* Secondary facts live one layer down: price basis, snapshot time and source boundary. */}
          <DetailsDisclosure ref={more} summary={copy("details")} variant="compact" className="workspace-property-header__more">
            <div className="workspace-property-header__secondary">
              <span><span className="text-meta">{copy(workspace.assumptions.activePriceBasis)}</span> <strong data-numeric>{activePrice ? formatWan(activePrice) : copy("notProvided")}</strong></span>
              <StatusLabel semanticRole="information">{copy("snapshotSaved")}</StatusLabel>
              <span className="text-meta">{copy("lastSaved")}：{formatExactDate(workspace.updatedAt)}</span>
            </div>
            <dl className="workspace-property-header__details text-dense">
              <div><dt>{copy("normalized")}</dt><dd>{anchor?.normalized_address || copy("notYet")}</dd></div>
              <div><dt>{copy("scope")}</dt><dd>{anchor ? copy("scopeAnchor") : copy("scopePending")}</dd></div>
              <div><dt>{identityCopy.parcel}</dt><dd>{journeyIdentityEvidenceLabel(anchor?.parcel.status, locale)}</dd></div>
              <div><dt>{identityCopy.building}</dt><dd>{journeyIdentityEvidenceLabel(anchor?.building.status, locale)}</dd></div>
              <div><dt>{copy("checkedAt")}</dt><dd>{anchor ? formatExactDate(anchor.evidence.checked_at) : copy("notChecked")}</dd></div>
              <div><dt>{copy("boundary")}</dt><dd>{identityCopy.boundary}</dd></div>
            </dl>
          </DetailsDisclosure>
        </div>
      </div>
      {workspace.identity.state === "revalidation_required" && <p className="workspace-property-header__warning">{copy("revalidation")}</p>}
      <div data-testid="context-save-status"><p data-testid="overview-save-status" aria-live="polite" className="workspace-property-header__save-status text-dense">{saveStatus}</p></div>
    </div>
  </header>;
}
