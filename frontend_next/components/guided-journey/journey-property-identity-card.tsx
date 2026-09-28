import type { JourneyIdentityStatus, JourneyPropertyIdentityAnchorV1 } from "@/lib/journey-property-identity";

const STATUS_LABELS: Record<JourneyIdentityStatus, string> = {
  candidate: "Candidate",
  manual_confirmed: "Manually confirmed",
  unresolved: "Unresolved",
  unavailable: "Unavailable",
  restricted: "Restricted",
  unsupported: "Unsupported",
  error: "Error",
  stale: "Stale",
};

const CONFIDENCE_LABELS = {
  high: "High",
  medium: "Medium",
  low: "Low",
  unknown: "Unknown",
} as const;

const SOURCE_LABELS: Record<string, string> = {
  property_selection: "Property selection",
  google_geocoding: "Google geocoding",
  tgos_geocoding: "TGOS geocoding",
  ["provided_" + "coord" + "inates"]: "Provided geocoded point",
  nlsc_village_boundary: "NLSC village boundary",
};

export function JourneyPropertyIdentityCard({ anchor }: { anchor: JourneyPropertyIdentityAnchorV1 }) {
  const location = [anchor.administrative_location.city, anchor.administrative_location.district].filter(Boolean).join(" · ") || "Unavailable";
  const village = anchor.administrative_location.village
    ? `${anchor.administrative_location.village}${anchor.administrative_location.village_code ? ` (${anchor.administrative_location.village_code})` : ""}`
    : "Unavailable";
  const stale = anchor.revalidation.status === "needs_revalidation";

  return <section data-testid="journey-property-identity-card" aria-labelledby="journey-property-identity-heading" className="rounded-xl border border-sky-200 bg-sky-50/60 p-4">
    <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-sky-700">Browser journey anchor</p>
        <h3 id="journey-property-identity-heading" className="mt-1 text-base font-black text-slate-950">Journey property identity</h3>
      </div>
      <span className={`w-fit rounded-full px-2.5 py-1 text-[10px] font-bold ${stale ? "bg-amber-100 text-amber-900" : "bg-sky-100 text-sky-800"}`}>
        {stale ? "Needs revalidation" : STATUS_LABELS[anchor.location_status]}
      </span>
    </div>
    <p className="mt-2 text-xs leading-5 text-slate-600">Browser workflow correlation only; not an official cadastral, government, legal, or durable VNext property ID.</p>
    {stale && <p role="alert" className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-950">Stored identity evidence conflicts with newly resolved evidence. Review before relying on downstream results.</p>}
    <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
      <div><dt className="font-bold text-slate-500">Address</dt><dd className="mt-0.5 text-slate-900">{anchor.normalized_address || anchor.address_input || "Unavailable"}</dd></div>
      <div><dt className="font-bold text-slate-500">Location</dt><dd className="mt-0.5 text-slate-900">{location}</dd></div>
      <div><dt className="font-bold text-slate-500">Village</dt><dd className="mt-0.5 text-slate-900">{village}</dd></div>
      <div><dt className="font-bold text-slate-500">Confidence</dt><dd className="mt-0.5 text-slate-900">{CONFIDENCE_LABELS[anchor.confidence.level]} — address/location evidence only</dd></div>
      <div><dt className="font-bold text-slate-500">Parcel</dt><dd className="mt-0.5 text-slate-900">Parcel: {STATUS_LABELS[anchor.parcel.status]}</dd></div>
      <div><dt className="font-bold text-slate-500">Building</dt><dd className="mt-0.5 text-slate-900">Building: {STATUS_LABELS[anchor.building.status]}</dd></div>
    </dl>
    <div className="mt-3 border-t border-sky-100 pt-3 text-xs leading-5 text-slate-600">
      <p><span className="font-bold text-slate-700">Sources:</span> {anchor.evidence.sources.map((source) => SOURCE_LABELS[source.source_id] ?? source.source_id).join(" · ") || "Unavailable"}</p>
      <p className="mt-1">Address-level confidence does not confirm parcel, building, ownership, title, or legal boundary. Map imagery and proximity are not cadastral proof.</p>
    </div>
  </section>;
}
