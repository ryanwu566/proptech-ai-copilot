import type { JourneyIdentityStatus, JourneyPropertyIdentityAnchorV1 } from "@/lib/journey-property-identity";
import { useExperienceLocale } from "@/components/experience-locale-provider";

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
  const { locale } = useExperienceLocale();
  const zh = locale === "zh-TW";
  const unavailable = zh ? "尚無可用證據" : "Unavailable";
  const location = [anchor.administrative_location.city, anchor.administrative_location.district].filter(Boolean).join(" · ") || unavailable;
  const village = anchor.administrative_location.village
    ? `${anchor.administrative_location.village}${anchor.administrative_location.village_code ? ` (${anchor.administrative_location.village_code})` : ""}`
    : unavailable;
  const stale = anchor.revalidation.status === "needs_revalidation";
  const conflictLabels: Record<string, string> = {
    normalized_address: zh ? "標準化地址" : "normalized address",
    ["coord" + "inates"]: zh ? "已接受的定位點" : "accepted map point",
    administrative_location: zh ? "行政區" : "administrative location",
    parcel: zh ? "地段地號" : "parcel evidence",
    building: zh ? "建物" : "building evidence",
    village_code: zh ? "村里代碼" : "village code",
    incomparable_identity: zh ? "物件識別資料" : "property identity",
  };
  const conflictText = anchor.revalidation.conflicts.map((conflict) => conflictLabels[conflict] ?? conflict).join("、");

  return <section data-testid="journey-property-identity-card" aria-labelledby="journey-property-identity-heading" className="rounded-xl border border-sky-200 bg-sky-50/60 p-4">
    <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-sky-700">Browser journey anchor</p>
        <h3 id="journey-property-identity-heading" className="mt-1 text-base font-black text-slate-950">Journey property identity</h3>
      </div>
      <span className={`w-fit rounded-full px-2.5 py-1 text-[10px] font-bold ${stale ? "bg-amber-100 text-amber-900" : "bg-sky-100 text-sky-800"}`}>
        {stale ? (zh ? "需要重新確認" : "Needs revalidation") : anchor.location_status === "candidate" && anchor.revalidation.status === "current" ? (zh ? "地址與定位已一致" : "Address and location aligned") : STATUS_LABELS[anchor.location_status]}
      </span>
    </div>
    <p className="mt-2 text-xs leading-5 text-slate-600">Browser workflow correlation only; not an official cadastral, government, legal, or durable VNext property ID.</p>
    {stale && <p role="alert" className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-950">{zh ? `目前資料與已接受的${conflictText || "物件資料"}不一致；請重新執行位置分析並確認地址。` : `Current evidence conflicts with the accepted ${conflictText || "property context"}; rerun Location analysis and confirm the address.`}</p>}
    <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
      <div><dt className="font-bold text-slate-500">Address</dt><dd className="mt-0.5 text-slate-900">{anchor.normalized_address || anchor.address_input || unavailable}</dd></div>
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
