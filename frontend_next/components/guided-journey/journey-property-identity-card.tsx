import type { JourneyPropertyIdentityAnchorV1 } from "@/lib/journey-property-identity";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { isJourneyAddressAssociated, journeyIdentityCopy, journeyIdentityEvidenceLabel, journeyIdentitySourceLabel } from "@/lib/journey-identity-copy";

export function JourneyPropertyIdentityCard({ anchor }: { anchor: JourneyPropertyIdentityAnchorV1 }) {
  const { locale } = useExperienceLocale();
  const c = journeyIdentityCopy(locale);
  const stale = anchor.revalidation.status === "needs_revalidation";
  const rows = [
    [c.address, anchor.normalized_address || anchor.address_input || c.unavailable],
    [c.location, [anchor.administrative_location.city, anchor.administrative_location.district].filter(Boolean).join(" · ") || c.unavailable],
    [c.village, anchor.administrative_location.village ? `${anchor.administrative_location.village}${anchor.administrative_location.village_code ? ` (${anchor.administrative_location.village_code})` : ""}` : c.unavailable],
    [c.confidence, `${c[anchor.confidence.level]} · ${c.scope}`],
    [c.parcel, journeyIdentityEvidenceLabel(anchor.parcel.status, locale)],
    [c.building, journeyIdentityEvidenceLabel(anchor.building.status, locale)],
  ];
  return <section data-testid="journey-property-identity-card" aria-labelledby="journey-property-identity-heading" className="rounded-xl border border-sky-200 bg-sky-50/60 p-4">
    <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
      <div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-sky-700">{c.kicker}</p><h3 id="journey-property-identity-heading" className="mt-1 text-base font-black text-slate-950">{c.title}</h3></div>
      <span className={`w-fit rounded-full px-2.5 py-1 text-[10px] font-bold ${stale ? "bg-amber-100 text-amber-900" : "bg-sky-100 text-sky-800"}`}>
        {stale ? c.stale : isJourneyAddressAssociated(anchor) ? c.aligned : journeyIdentityEvidenceLabel(anchor.location_status, locale)}
      </span>
    </div>
    <p className="mt-2 text-xs leading-5 text-slate-600">{c.boundary}</p>
    {stale && <p role="alert" className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-950">{c.conflict}</p>}
    <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">{rows.map(([label, value]) => <div key={label}><dt className="font-bold text-slate-500">{label}</dt><dd className="mt-0.5 text-slate-900">{value}</dd></div>)}</dl>
    <p className="mt-3 border-t border-sky-100 pt-3 text-xs leading-5 text-slate-600"><span className="font-bold text-slate-700">{c.sources}:</span> {anchor.evidence.sources.map(source => journeyIdentitySourceLabel(source.source_id, locale)).join(" · ") || c.unavailable}</p>
  </section>;
}
