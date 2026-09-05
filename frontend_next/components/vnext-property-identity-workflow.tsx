"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import {
  VNextApiError,
  VNextOutcomeUnknownError,
  VNextSessionError,
  newIdempotencyKey,
  vnextIdentityClient,
  type CasePurpose,
  type ResolutionInput,
} from "@/lib/vnext-identity-client";
import {
  VNextContractError,
  type CaseDTO,
  type IdentityCandidateDTO,
  type PropertyDTO,
  type PropertyEvidenceDTO,
  type PropertyGraphDTO,
  type PropertyResolutionDTO,
  type WorkspaceContextDTO,
} from "@/lib/vnext-identity-contract";
import { getIdentityCopy } from "@/lib/vnext-identity-copy";
import styles from "./vnext-property-identity-workflow.module.css";

type InputKind = ResolutionInput["kind"];
type Attempt = { fingerprint: string; key: string };
type CreatedCaseReplay = { key: string; workspaceId: string; purpose: CasePurpose; title: string };

const inputKinds: InputKind[] = ["address", "lot_number", "building_number", "coordinates", "map_click"];
const casePurposes: CasePurpose[] = ["buy_due_diligence", "development", "brokerage", "valuation_review", "investment_review"];

function isInputKind(value: string): value is InputKind {
  return inputKinds.some((kind) => kind === value);
}

function isCasePurpose(value: string): value is CasePurpose {
  return casePurposes.some((purpose) => purpose === value);
}

function displayToken(value: string): string {
  return value.replaceAll("_", " ");
}

function compactJson(value: object): string {
  const rendered = JSON.stringify(value);
  return rendered.length > 800 ? `${rendered.slice(0, 797)}...` : rendered;
}

function candidateConflicts(resolution: PropertyResolutionDTO, candidate: IdentityCandidateDTO) {
  return resolution.conflicts.filter((conflict) => conflict.left_candidate_id === candidate.candidate_id || conflict.right_candidate_id === candidate.candidate_id);
}

function retryMustReuseKey(caught: unknown): boolean {
  return caught instanceof VNextOutcomeUnknownError || caught instanceof VNextContractError;
}

export function VNextPropertyIdentityWorkflow() {
  const { locale, setLocale, formatDate, formatPercent } = useExperienceLocale();
  const copy = getIdentityCopy(locale);
  const errorRef = useRef<HTMLDivElement>(null);
  const pendingRef = useRef<string | null>(null);

  const [bootstrap, setBootstrap] = useState<"loading" | "ready" | "disabled" | "auth" | "config" | "error">("loading");
  const [workspaceId, setWorkspaceId] = useState("");
  const [workspace, setWorkspace] = useState<WorkspaceContextDTO | null>(null);
  const [resolutionIdInput, setResolutionIdInput] = useState("");
  const [resolution, setResolution] = useState<PropertyResolutionDTO | null>(null);
  const [property, setProperty] = useState<PropertyDTO | null>(null);
  const [graphPages, setGraphPages] = useState<PropertyGraphDTO[]>([]);
  const [evidencePages, setEvidencePages] = useState<PropertyEvidenceDTO[]>([]);
  const [graphCursor, setGraphCursor] = useState<string | null>(null);
  const [evidenceCursor, setEvidenceCursor] = useState<string | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [confirmIntent, setConfirmIntent] = useState(false);
  const [confirmationReason, setConfirmationReason] = useState("");
  const [rejectEntire, setRejectEntire] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("not_same_property");
  const [inputKind, setInputKind] = useState<InputKind>("address");
  const [address, setAddress] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [section, setSection] = useState("");
  const [subsection, setSubsection] = useState("");
  const [lotNumber, setLotNumber] = useState("");
  const [buildingNumber, setBuildingNumber] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [mapContext, setMapContext] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [resolutionAttempt, setResolutionAttempt] = useState<Attempt | null>(null);
  const [confirmAttempt, setConfirmAttempt] = useState<Attempt | null>(null);
  const [rejectAttempt, setRejectAttempt] = useState<Attempt | null>(null);
  const [caseAttempt, setCaseAttempt] = useState<Attempt | null>(null);
  const [attachAttempt, setAttachAttempt] = useState<Attempt | null>(null);
  const [createdCaseReplay, setCreatedCaseReplay] = useState<CreatedCaseReplay | null>(null);
  const [caseTitle, setCaseTitle] = useState("");
  const [casePurpose, setCasePurpose] = useState<CasePurpose>("buy_due_diligence");
  const [currentCase, setCurrentCase] = useState<CaseDTO | null>(null);
  const [caseAttached, setCaseAttached] = useState(false);

  useEffect(() => {
    let active = true;
    vnextIdentityClient.context().then((context) => {
      if (!active) return;
      setBootstrap(context.features.identity_v1 ? "ready" : "disabled");
    }).catch((caught: unknown) => {
      if (!active) return;
      if (caught instanceof VNextSessionError) setBootstrap(caught.reason === "missing_session" ? "auth" : "config");
      else setBootstrap("error");
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (error) errorRef.current?.focus();
  }, [error]);

  function begin(label: string): boolean {
    if (pendingRef.current) return false;
    pendingRef.current = label;
    setPending(label);
    setError(null);
    setNotice(null);
    return true;
  }

  function finish() {
    pendingRef.current = null;
    setPending(null);
  }

  function clearLoadedIdentity() {
    setResolution(null); setProperty(null); setSelectedCandidateId(null); setReviewed(false); setConfirmIntent(false); setConfirmationReason(""); setRejectEntire(false);
    setGraphPages([]); setEvidencePages([]); setGraphCursor(null); setEvidenceCursor(null);
    setCurrentCase(null); setCaseAttached(false); setCreatedCaseReplay(null);
    setResolutionAttempt(null); setConfirmAttempt(null); setRejectAttempt(null); setCaseAttempt(null); setAttachAttempt(null);
  }

  function errorMessage(caught: unknown): string {
    if (caught instanceof VNextOutcomeUnknownError) return copy.retrySafe;
    if (caught instanceof VNextContractError) return caught.path.startsWith("request.") ? copy.invalidInput : copy.invalidResponse;
    if (caught instanceof VNextSessionError) return caught.reason === "missing_session" ? copy.authMissing : copy.authConfig;
    if (caught instanceof VNextApiError) {
      if (caught.code === "not_found") return copy.notFound;
      const labels: Partial<Record<VNextApiError["code"], string>> = {
        authentication_required: copy.authMissing,
        permission_denied: copy.permissionDenied,
        validation_failed: copy.invalidInput,
        unsupported_input: copy.invalidInput,
        version_conflict: copy.caseConflict,
        idempotency_conflict: copy.idempotencyConflict,
        ambiguous_identity: copy.ambiguity,
        stale_evidence: copy.staleEvidence,
        conflicting_evidence: copy.conflictingEvidence,
        coverage_unavailable: copy.coverageUnavailable,
        provider_unavailable: copy.providerUnavailable,
        maintenance: copy.maintenance,
        internal_error: copy.genericError,
      };
      return `${labels[caught.code] ?? copy.genericError} Reference: ${caught.requestId}`;
    }
    return copy.genericError;
  }

  async function loadWorkspace(event: FormEvent) {
    event.preventDefault();
    if (!begin("workspace")) return;
    try {
      const loaded = await vnextIdentityClient.workspace(workspaceId.trim());
      if (resolution && resolution.workspace_id !== loaded.workspace_id) clearLoadedIdentity();
      setWorkspace(loaded);
      setWorkspaceId(loaded.workspace_id);
    } catch (caught: unknown) {
      setWorkspace(null);
      setError(errorMessage(caught));
    } finally { finish(); }
  }

  function makeInput(): ResolutionInput | null {
    if (inputKind === "address") return address.trim() ? { kind: "address", value: { text: address.trim() } } : null;
    if (inputKind === "lot_number") return jurisdiction.trim() && section.trim() && lotNumber.trim() ? {
      kind: "lot_number", value: { jurisdiction: jurisdiction.trim(), section: section.trim(), subsection: subsection.trim() || null, lot_number: lotNumber.trim() },
    } : null;
    if (inputKind === "building_number") return buildingNumber.trim() ? {
      kind: "building_number", value: { jurisdiction: jurisdiction.trim() || null, building_number: buildingNumber.trim() },
    } : null;
    const lat = Number(latitude); const lng = Number(longitude);
    if (!Number.isFinite(lat) || lat < -90 || lat > 90 || !Number.isFinite(lng) || lng < -180 || lng > 180 || !latitude.trim() || !longitude.trim()) return null;
    if (inputKind === "coordinates") return { kind: "coordinates", value: { latitude: lat, longitude: lng, crs: "EPSG:4326" } };
    return { kind: "map_click", value: { latitude: lat, longitude: lng, crs: "EPSG:4326", map_context: mapContext.trim() || null } };
  }

  function resetReview(loaded: PropertyResolutionDTO) {
    clearLoadedIdentity();
    setResolution(loaded);
  }

  async function createResolution(event?: FormEvent) {
    event?.preventDefault();
    if (!workspace || workspace.workspace_id !== workspaceId.trim()) { setError(copy.loadWorkspaceFirst); return; }
    const input = makeInput();
    if (!input) { setError(copy.invalidObservation); return; }
    const fingerprint = JSON.stringify({ workspace: workspace.workspace_id, input });
    const attempt = resolutionAttempt?.fingerprint === fingerprint ? resolutionAttempt : { fingerprint, key: newIdempotencyKey("resolution") };
    setResolutionAttempt(attempt);
    if (!begin("resolution")) return;
    try {
      const loaded = await vnextIdentityClient.createResolution(workspace.workspace_id, input, attempt.key);
      setResolutionAttempt(null);
      resetReview(loaded);
      setResolutionIdInput(loaded.resolution_id);
    } catch (caught: unknown) {
      if (!retryMustReuseKey(caught)) setResolutionAttempt(null);
      setError(errorMessage(caught));
    } finally { finish(); }
  }

  async function refreshResolution(resolutionId: string, resetSelection = false) {
    const loaded = await vnextIdentityClient.resolution(resolutionId);
    setResolution(loaded);
    if (resetSelection) { setSelectedCandidateId(null); setReviewed(false); setConfirmIntent(false); }
    if (loaded.confirmed_property_entity_id) {
      setProperty(null);
      const loadedProperty = await vnextIdentityClient.property(loaded.confirmed_property_entity_id);
      if (loadedProperty.workspace_id !== loaded.workspace_id) throw new VNextContractError("property.workspace_id");
      if (!loadedProperty.confirmation_summary.human_confirmed || loadedProperty.confirmation_summary.resolution_id !== loaded.resolution_id) {
        throw new VNextContractError("property.confirmation_summary");
      }
      setProperty(loadedProperty);
    } else setProperty(null);
    return loaded;
  }

  async function openResolution(event: FormEvent) {
    event.preventDefault();
    if (!begin("open-resolution")) return;
    setWorkspace(null);
    clearLoadedIdentity();
    try {
      const loaded = await refreshResolution(resolutionIdInput.trim(), true);
      setWorkspaceId(loaded.workspace_id);
      const loadedWorkspace = await vnextIdentityClient.workspace(loaded.workspace_id);
      setWorkspace(loadedWorkspace);
      setGraphPages([]); setEvidencePages([]); setGraphCursor(null); setEvidenceCursor(null);
      setCurrentCase(null); setCaseAttached(false); setCreatedCaseReplay(null);
    } catch (caught: unknown) { setError(errorMessage(caught)); }
    finally { finish(); }
  }

  const activeConflicts = resolution?.conflicts.filter((item) => item.state === "open" || item.state === "requires_review") ?? [];
  const hasBlockingConflict = activeConflicts.some((item) => item.severity === "blocking");
  const canConfirm = workspace?.role === "owner" || workspace?.role === "admin";
  const canCreate = workspace ? ["owner", "admin", "manager", "member"].includes(workspace.role) : false;
  const providerUnavailable = resolution?.provider_attempts.some((item) => item.status === "unavailable" || item.status === "timeout" || item.error_category === "provider_unavailable") ?? false;
  const confirmedCandidate = resolution?.selected_candidate_id ? resolution.candidates.find((candidate) => candidate.candidate_id === resolution.selected_candidate_id) ?? null : null;

  async function confirmCandidate() {
    if (!resolution || !selectedCandidateId || !reviewed || !confirmIntent || confirmationReason.trim().length < 8 || confirmationReason.trim().length > 1000 || hasBlockingConflict || !canConfirm) return;
    const reason = confirmationReason.trim();
    const fingerprint = JSON.stringify({ resolution: resolution.resolution_id, candidate: selectedCandidateId, version: resolution.version, reason });
    const attempt = confirmAttempt?.fingerprint === fingerprint ? confirmAttempt : { fingerprint, key: newIdempotencyKey("confirm") };
    setConfirmAttempt(attempt);
    if (!begin("confirm")) return;
    try {
      const saved = await vnextIdentityClient.confirm(resolution.resolution_id, selectedCandidateId, resolution.version, reason, attempt.key);
      setConfirmAttempt(null);
      setResolution(saved);
      try { await refreshResolution(resolution.resolution_id); }
      catch { setError(copy.commandSavedRefreshFailed); return; }
      setNotice(copy.confirmationSaved);
    } catch (caught: unknown) {
      if (!retryMustReuseKey(caught)) setConfirmAttempt(null);
      if (caught instanceof VNextApiError && caught.code === "version_conflict") {
        try {
          await refreshResolution(resolution.resolution_id, true);
          setError(copy.resolutionConflict);
        } catch (refreshError: unknown) { setError(errorMessage(refreshError)); }
      } else setError(errorMessage(caught));
    } finally { finish(); }
  }

  async function rejectResolution() {
    if (!resolution || (!rejectEntire && !selectedCandidateId)) return;
    const candidateId = rejectEntire ? null : selectedCandidateId;
    const fingerprint = JSON.stringify({ resolution: resolution.resolution_id, candidateId, version: resolution.version, reason: rejectionReason });
    const attempt = rejectAttempt?.fingerprint === fingerprint ? rejectAttempt : { fingerprint, key: newIdempotencyKey("reject") };
    setRejectAttempt(attempt);
    if (!begin("reject")) return;
    try {
      const saved = await vnextIdentityClient.reject(resolution.resolution_id, candidateId, resolution.version, rejectionReason, attempt.key);
      setRejectAttempt(null);
      setResolution(saved);
      try { await refreshResolution(resolution.resolution_id, true); }
      catch { setError(copy.commandSavedRefreshFailed); return; }
      setNotice(copy.rejectionSaved);
    } catch (caught: unknown) {
      if (!retryMustReuseKey(caught)) setRejectAttempt(null);
      if (caught instanceof VNextApiError && caught.code === "version_conflict") {
        try {
          await refreshResolution(resolution.resolution_id, true);
          setError(copy.rejectionConflict);
        } catch (refreshError: unknown) { setError(errorMessage(refreshError)); }
      } else setError(errorMessage(caught));
    } finally { finish(); }
  }

  async function loadGraph(cursor?: string) {
    if (!property || !begin("graph")) return;
    try {
      const page = await vnextIdentityClient.graph(property.property_entity_id, cursor);
      if (page.property.workspace_id !== property.workspace_id) throw new VNextContractError("graph.property.workspace_id");
      setGraphPages((current) => cursor ? [...current, page] : [page]);
      setGraphCursor(page.next_cursor);
    } catch (caught: unknown) { setError(errorMessage(caught)); }
    finally { finish(); }
  }

  async function loadEvidence(cursor?: string) {
    if (!property || !begin("evidence")) return;
    try {
      const page = await vnextIdentityClient.evidence(property.property_entity_id, cursor);
      if (page.property.workspace_id !== property.workspace_id) throw new VNextContractError("evidence.property.workspace_id");
      setEvidencePages((current) => cursor ? [...current, page] : [page]);
      setEvidenceCursor(page.next_cursor);
    } catch (caught: unknown) { setError(errorMessage(caught)); }
    finally { finish(); }
  }

  async function createCase(event: FormEvent) {
    event.preventDefault();
    if (!workspace || !canCreate || !caseTitle.trim() || caseTitle.trim().length > 240) return;
    const title = caseTitle.trim();
    const fingerprint = JSON.stringify({ workspace: workspace.workspace_id, purpose: casePurpose, title });
    const attempt = caseAttempt?.fingerprint === fingerprint ? caseAttempt : { fingerprint, key: newIdempotencyKey("case") };
    setCaseAttempt(attempt);
    if (!begin("case")) return;
    try {
      const loaded = await vnextIdentityClient.createCase(workspace.workspace_id, casePurpose, title, attempt.key);
      setCaseAttempt(null);
      setCurrentCase(loaded);
      setCreatedCaseReplay({ key: attempt.key, workspaceId: workspace.workspace_id, purpose: casePurpose, title });
      setCaseAttached(false);
      setNotice(copy.caseCreated);
    } catch (caught: unknown) {
      if (!retryMustReuseKey(caught)) setCaseAttempt(null);
      setError(errorMessage(caught));
    } finally { finish(); }
  }

  async function attachCase() {
    if (!resolution?.confirmed_property_entity_id || !property || !currentCase || !canConfirm) return;
    const fingerprint = JSON.stringify({ caseId: currentCase.case_id, resolutionId: resolution.resolution_id, version: currentCase.version });
    const attempt = attachAttempt?.fingerprint === fingerprint ? attachAttempt : { fingerprint, key: newIdempotencyKey("attach") };
    setAttachAttempt(attempt);
    if (!begin("attach")) return;
    try {
      const attached = await vnextIdentityClient.attachResolution(currentCase.case_id, resolution.resolution_id, resolution.confirmed_property_entity_id, currentCase.version, attempt.key);
      if (attached.case.workspace_id !== resolution.workspace_id || attached.case.identity_status !== "confirmed"
        || attached.link.confirmation_id !== property.confirmation_summary.confirmation_id) {
        throw new VNextContractError("attachment.confirmation_binding");
      }
      setAttachAttempt(null);
      setCurrentCase(attached.case);
      setCaseAttached(true);
      setNotice(copy.caseAttached);
    } catch (caught: unknown) {
      if (caught instanceof VNextApiError && caught.code === "version_conflict" && createdCaseReplay) {
        setAttachAttempt(null);
        try {
          const refreshed = await vnextIdentityClient.createCase(createdCaseReplay.workspaceId, createdCaseReplay.purpose, createdCaseReplay.title, createdCaseReplay.key);
          setCurrentCase(refreshed);
          setError(copy.caseConflict);
        } catch (refreshError: unknown) { setError(errorMessage(refreshError)); }
      } else {
        if (!retryMustReuseKey(caught)) setAttachAttempt(null);
        setError(errorMessage(caught));
      }
    } finally { finish(); }
  }

  const inputLabel = (kind: InputKind) => ({ address: copy.address, lot_number: copy.lot, building_number: copy.building, coordinates: copy.coordinates, map_click: copy.mapClick })[kind];

  if (bootstrap !== "ready") {
    const message = bootstrap === "loading" ? "Loading authenticated feature state…" : bootstrap === "disabled" ? copy.featureOff : bootstrap === "auth" ? copy.authMissing : bootstrap === "config" ? copy.authConfig : copy.genericError;
    return <main className={styles.page}><section className={styles.hero}><p className={styles.eyebrow}>PROPERTY IDENTITY · HUMAN REVIEW</p><h1>{copy.title}</h1><div className={styles.state} role="status" aria-live="polite">{message}</div></section></main>;
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <div className={styles.heroTop}><p className={styles.eyebrow}>PROPERTY IDENTITY · HUMAN REVIEW</p><label>Language<select value={locale} onChange={(event) => setLocale(event.target.value)} aria-label="Language"><option value="zh-TW">繁體中文</option><option value="en">English</option><option value="ja">日本語</option><option value="ko">한국어</option></select></label></div>
        <h1>{copy.title}</h1><p>{copy.intro}</p>
      </section>

      {error && <div className={styles.error} role="alert" tabIndex={-1} ref={errorRef}>{error}{(resolutionAttempt || confirmAttempt || rejectAttempt || caseAttempt || attachAttempt) && <span> {copy.retry}</span>}</div>}
      {notice && <div className={styles.notice} role="status" aria-live="polite">{notice}</div>}

      <section className={styles.panel} aria-labelledby="workspace-heading">
        <h2 id="workspace-heading">{copy.workspace}</h2>
        <form className={styles.inlineForm} onSubmit={loadWorkspace}>
          <label>Workspace UUID<input value={workspaceId} onChange={(event) => { setWorkspaceId(event.target.value); setWorkspace(null); }} required autoComplete="off" /></label>
          <button type="submit" data-testid="load-workspace" disabled={pending !== null}>{copy.loadWorkspace}</button>
        </form>
        {workspace && <p className={styles.state} data-testid="workspace-role">{displayToken(workspace.role)} · {copy.roleNote}</p>}
      </section>

      <section className={styles.panel} aria-labelledby="existing-heading">
        <h2 id="existing-heading">{copy.openResolution}</h2>
        <form className={styles.inlineForm} onSubmit={openResolution}>
          <label>{copy.resolutionId}<input value={resolutionIdInput} onChange={(event) => setResolutionIdInput(event.target.value)} required autoComplete="off" /></label>
          <button type="submit" data-testid="open-resolution" disabled={pending !== null}>{copy.openResolution}</button>
        </form>
      </section>

      <section className={styles.panel} aria-labelledby="input-heading">
        <h2 id="input-heading">{copy.inputHeading}</h2>
        <form onSubmit={createResolution}>
          <label>{copy.inputKind}<select value={inputKind} onChange={(event) => { if (isInputKind(event.target.value)) setInputKind(event.target.value); }}>{inputKinds.map((kind) => <option key={kind} value={kind}>{inputLabel(kind)}</option>)}</select></label>
          <div className={styles.inputGrid}>
            {inputKind === "address" && <label>{copy.address}<input value={address} maxLength={512} onChange={(event) => setAddress(event.target.value)} required /></label>}
            {(inputKind === "lot_number" || inputKind === "building_number") && <label>Jurisdiction<input value={jurisdiction} maxLength={160} onChange={(event) => setJurisdiction(event.target.value)} required={inputKind === "lot_number"} /></label>}
            {inputKind === "lot_number" && <><label>Section<input value={section} maxLength={160} onChange={(event) => setSection(event.target.value)} required /></label><label>Subsection<input value={subsection} maxLength={160} onChange={(event) => setSubsection(event.target.value)} /></label><label>Lot number<input value={lotNumber} maxLength={120} onChange={(event) => setLotNumber(event.target.value)} required /></label></>}
            {inputKind === "building_number" && <label>Building number<input value={buildingNumber} maxLength={160} onChange={(event) => setBuildingNumber(event.target.value)} required /></label>}
            {(inputKind === "coordinates" || inputKind === "map_click") && <><label>Latitude<input type="number" min="-90" max="90" step="any" value={latitude} onChange={(event) => setLatitude(event.target.value)} required /></label><label>Longitude<input type="number" min="-180" max="180" step="any" value={longitude} onChange={(event) => setLongitude(event.target.value)} required /></label><label>CRS<input value="EPSG:4326" readOnly /></label></>}
            {inputKind === "map_click" && <label>Map context<input value={mapContext} maxLength={160} onChange={(event) => setMapContext(event.target.value)} /></label>}
          </div>
          <p className={styles.caution}>{copy.intro}</p>
          <button type="submit" data-testid="create-resolution" disabled={pending !== null || !canCreate}>{copy.submitResolution}</button>
        </form>
      </section>

      {resolution && <section className={styles.panel} aria-labelledby="candidate-heading">
        <div className={styles.sectionTitle}><div><h2 id="candidate-heading">{copy.candidates}</h2><p>{copy.noPreselect}</p></div><span className={`${styles.status} ${styles[`status_${resolution.coverage_status}`]}`}>{displayToken(resolution.state)} · {displayToken(resolution.coverage_status)}</span></div>
        <p><strong>Resolution:</strong> {resolution.resolution_id} · version {resolution.version}</p>
        <details><summary>{copy.normalized}</summary><code>{compactJson(resolution.normalized_input)}</code></details>
        {(resolution.ambiguity !== "none" || resolution.state === "ambiguous") && <div className={styles.warning} role="status">{copy.ambiguity} ({displayToken(resolution.ambiguity)})</div>}
        {providerUnavailable && <div className={styles.unavailable} role="status" data-testid="provider-unavailable">{copy.providerUnavailable}</div>}
        {hasBlockingConflict && <div className={styles.blocking} role="alert">{copy.blocking}</div>}
        <details><summary>Source attempts and coverage</summary><ul>{resolution.provider_attempts.map((attempt) => <li key={attempt.attempt_id}><strong>{attempt.source.source_id}</strong>: {displayToken(attempt.status)} · coverage {displayToken(attempt.coverage_status)} · results {attempt.result_count}{attempt.error_code ? ` · ${displayToken(attempt.error_code)}` : ""}</li>)}</ul></details>
        <fieldset className={styles.candidateList}><legend className={styles.srOnly}>{copy.candidates}</legend>{resolution.candidates.map((candidate) => {
          const conflicts = candidateConflicts(resolution, candidate);
          return <article className={`${styles.candidate} ${selectedCandidateId === candidate.candidate_id ? styles.selected : ""}`} key={candidate.candidate_id}>
            <label className={styles.candidateHeader}><input type="radio" name="candidate" value={candidate.candidate_id} checked={selectedCandidateId === candidate.candidate_id} onChange={() => { setSelectedCandidateId(candidate.candidate_id); setReviewed(false); setConfirmIntent(false); }} /><strong>{candidate.display_identity}</strong><span>Rank {candidate.rank}</span></label>
            <span>{displayToken(candidate.candidate_type)} · {displayToken(candidate.status)} · {candidate.source.source_id} ({candidate.source.environment})</span>
            <span className={styles.secondary}>{copy.confidence}: {formatPercent(candidate.confidence * 100)} · {candidate.confidence_method}</span>
            <span className={`${styles.status} ${styles[`status_${candidate.coverage_status}`]}`}>{copy.coverage}: {displayToken(candidate.coverage_status)}</span>
            <span>{copy.evidence}: {candidate.supporting_evidence_ids.length} · {copy.references}: {candidate.supporting_identity_reference_ids.length}</span>
            <span><strong>{copy.humanRequired}</strong></span>
            <details><summary>{copy.limitations}</summary><code>{compactJson(candidate.coverage)}</code></details>
            {conflicts.length > 0 && <ul aria-label={copy.conflicts}>{conflicts.map((conflict) => <li key={conflict.conflict_id}><strong>{displayToken(conflict.severity)}</strong>: {displayToken(conflict.category)} · {displayToken(conflict.state)}</li>)}</ul>}
          </article>;
        })}</fieldset>

        {canConfirm ? <div className={styles.commandBox}>
          <label className={styles.checkbox}><input type="checkbox" checked={reviewed} onChange={(event) => setReviewed(event.target.checked)} />{copy.reviewed}</label>
          <label className={styles.checkbox}><input type="checkbox" checked={confirmIntent} onChange={(event) => setConfirmIntent(event.target.checked)} />{copy.intent}</label>
          <label>{copy.reason}<textarea value={confirmationReason} minLength={8} maxLength={1000} onChange={(event) => setConfirmationReason(event.target.value)} /></label>
          <button type="button" data-testid="confirm-resolution" onClick={confirmCandidate} disabled={pending !== null || !selectedCandidateId || !reviewed || !confirmIntent || confirmationReason.trim().length < 8 || hasBlockingConflict || resolution.state === "confirmed" || resolution.state === "rejected"}>{copy.confirm}</button>
        </div> : <p className={styles.caution}>{copy.roleRestricted}</p>}

        {canConfirm && <div className={styles.rejectBox}>
          <label className={styles.checkbox}><input type="checkbox" checked={rejectEntire} onChange={(event) => setRejectEntire(event.target.checked)} />{copy.rejectAll}</label>
          <label>Reason code<select value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value)}><option value="not_same_property">not same property</option><option value="insufficient_evidence">insufficient evidence</option><option value="provider_conflict">provider conflict</option></select></label>
          <button type="button" data-testid="reject-resolution" className={styles.secondaryButton} onClick={rejectResolution} disabled={pending !== null || (!rejectEntire && !selectedCandidateId) || resolution.state === "confirmed" || resolution.state === "rejected"}>{rejectEntire ? copy.rejectAll : copy.rejectCandidate}</button>
        </div>}

        {resolution.decisions.length > 0 && <div><h3>{copy.history}</h3><ol>{resolution.decisions.map((decision) => <li key={decision.decision_id}>{displayToken(decision.decision_type)} · {formatDate(decision.decided_at)} · actor {decision.actor_user_id}{decision.reason_code ? ` · ${displayToken(decision.reason_code)}` : ""}</li>)}</ol></div>}
      </section>}

      {property && resolution && <section className={styles.panel} aria-labelledby="property-heading">
        <h2 id="property-heading">{copy.property}</h2><div className={styles.confirmed}><strong>{property.display_label}</strong><span>{copy.selectedCandidate}: {confirmedCandidate?.display_identity ?? resolution.selected_candidate_id ?? "unknown"}</span><span>{displayToken(property.lifecycle_state)} · version {property.version}</span><span>PropertyEntity: {property.property_entity_id}</span><span>Human confirmed: {property.confirmation_summary.human_confirmed ? "yes" : "no"}</span><span>Confirmed at: {property.confirmation_summary.confirmed_at ? formatDate(property.confirmation_summary.confirmed_at) : "unknown"}</span><span>Confirmed by: {property.confirmation_summary.confirmed_by ?? "unknown"}</span><span>Resolution: {property.confirmation_summary.resolution_id ?? "unknown"}</span></div>
        <p className={styles.caution}>{copy.confirmedCaution}</p>
        <div className={styles.buttonRow}><button type="button" onClick={() => loadGraph()} disabled={pending !== null}>{copy.graphLoad}</button><button type="button" onClick={() => loadEvidence()} disabled={pending !== null}>{copy.evidenceLoad}</button></div>
        {graphPages.length > 0 && <div><h3>{copy.graph}</h3>{graphPages.flatMap((page) => page.relations).map((relation) => <article className={styles.ledgerRow} key={relation.relation_id}><strong>{displayToken(relation.relation_type)}</strong><span>{displayToken(relation.direction)} · {displayToken(relation.status)}</span><span>{relation.from_node_id} → {relation.to_node_id}</span><span>Source: {relation.source.source_id} ({relation.source.environment})</span><span>Valid: {relation.valid_from ? formatDate(relation.valid_from) : "unknown"} → {relation.valid_to ? formatDate(relation.valid_to) : "open/unknown"}</span><span>Confirmation binding: {relation.confirmation_id ?? "none"}</span></article>)}{graphCursor && <button type="button" onClick={() => loadGraph(graphCursor)} disabled={pending !== null}>{copy.loadMore}</button>}</div>}
        {evidencePages.length > 0 && <div><h3>{copy.evidence}</h3>{evidencePages.flatMap((page) => page.evidence).map((item) => <article className={styles.ledgerRow} key={item.evidence_id}><strong>{displayToken(item.fact_type)}</strong><span>{displayToken(item.status)} · {copy.coverage}: {displayToken(item.coverage_status)}</span><span>Source: {item.source.source_id} ({item.source.environment})</span><span>Retrieved: {item.source.retrieved_at ? formatDate(item.source.retrieved_at) : "unknown"}</span><span>Effective: {item.effective_from ? formatDate(item.effective_from) : "unknown"}</span><span>Quality: {displayToken(item.quality_status)}{item.quality_method ? ` · ${item.quality_method}` : ""}</span><span>Private value present: {item.has_private_value_reference ? "yes (reference not exposed)" : "no"}</span><details><summary>{copy.limitations}</summary><code>{compactJson(item.coverage)}</code></details></article>)}{evidenceCursor && <button type="button" onClick={() => loadEvidence(evidenceCursor)} disabled={pending !== null}>{copy.loadMore}</button>}</div>}
      </section>}

      {property && resolution?.confirmed_property_entity_id === property.property_entity_id && <section className={styles.panel} aria-labelledby="case-heading">
        <h2 id="case-heading">{copy.caseHeading}</h2><p>{copy.caseSeparate}</p>
        {!currentCase && <form onSubmit={createCase} className={styles.inlineForm}><label>{copy.caseTitle}<input value={caseTitle} maxLength={240} onChange={(event) => setCaseTitle(event.target.value)} required /></label><label>Purpose<select value={casePurpose} onChange={(event) => { if (isCasePurpose(event.target.value)) setCasePurpose(event.target.value); }}>{casePurposes.map((purpose) => <option key={purpose} value={purpose}>{displayToken(purpose)}</option>)}</select></label><button type="submit" data-testid="create-case" disabled={pending !== null || !canCreate}>{copy.createCase}</button></form>}
        {currentCase && <div className={styles.caseCard}><strong>{currentCase.title}</strong><span>Case: {currentCase.case_id}</span><span>Status: {displayToken(currentCase.status)}</span><span>Identity: {displayToken(currentCase.identity_status)}</span><span>Version: {currentCase.version}</span>{canConfirm && !caseAttached && <button type="button" data-testid="attach-case" onClick={attachCase} disabled={pending !== null}>{copy.attachCase}</button>}{caseAttached && <span className={styles.success} data-testid="case-attached">{copy.caseAttached}</span>}</div>}
      </section>}
      <div className={styles.live} aria-live="polite">{pending ? `${copy.working}: ${pending}` : ""}</div>
    </main>
  );
}
