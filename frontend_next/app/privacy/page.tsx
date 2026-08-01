import Link from "next/link";

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl space-y-5 p-6">
      <header>
        <p className="text-xs font-bold uppercase tracking-widest text-cyan-800">Public policy</p>
        <h1 className="mt-2 text-3xl font-black text-slate-950">Privacy policy</h1>
        <p className="mt-2 text-sm leading-6 text-slate-700">Current storage and browser behavior, stated without promises beyond the product.</p>
      </header>
      <section className="space-y-4 rounded-xl border border-stone-200 bg-white p-5 text-sm leading-7 text-slate-700">
        <p>Property Cases contain user-entered case facts and selected analysis outputs. Browser-only interaction such as speech recognition uses the browser-native capability; audio is not sent by this product to an external speech provider.</p>
        <p>Runtime provider responses, raw coordinates and raw provider payloads are not intentionally stored as a public case record. Saved case behavior is limited by the current browser storage implementation; users should remove saved cases from the product when available.</p>
        <p>No contact or deletion channel is configured in this release. Do not enter secrets or information you are not authorized to process. Provider availability and retention behavior can change.</p>
      </section>
      <Link className="text-sm font-bold text-cyan-800 underline" href="/">Back to the product</Link>
    </main>
  );
}
