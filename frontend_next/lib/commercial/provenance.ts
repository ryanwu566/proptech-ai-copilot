export type PrimaryProvenance = {
  result: string;
  effectivePeriod?: string;
  limitation?: string;
};

export type EvidenceDetail = {
  agency?: string;
  dataset?: string;
  coverage?: string;
  method?: string;
  sourceVintage?: string;
  retrievedAt?: string;
};

export type DiagnosticDetail = {
  providerId?: string;
  endpoint?: string;
  httpStatus?: number;
  requestId?: string;
  rawCode?: string;
};

export type ProvenanceDisclosure = {
  primary: PrimaryProvenance;
  supportingContext?: string;
  evidenceDetail?: EvidenceDetail;
  diagnostics?: DiagnosticDetail;
};

export function createProvenanceDisclosure(disclosure: ProvenanceDisclosure): ProvenanceDisclosure {
  return {
    primary: { ...disclosure.primary },
    ...(disclosure.supportingContext ? { supportingContext: disclosure.supportingContext } : {}),
    ...(disclosure.evidenceDetail ? { evidenceDetail: { ...disclosure.evidenceDetail } } : {}),
    ...(disclosure.diagnostics ? { diagnostics: { ...disclosure.diagnostics } } : {}),
  };
}
export function serializePrimaryProvenance(disclosure: ProvenanceDisclosure): string {
  return [disclosure.primary.result, disclosure.primary.effectivePeriod, disclosure.primary.limitation].filter(Boolean).join(" · ");
}
