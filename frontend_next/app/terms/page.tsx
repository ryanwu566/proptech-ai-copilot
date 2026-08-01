import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="mx-auto max-w-3xl space-y-5 p-6">
      <header>
        <p className="text-xs font-bold uppercase tracking-widest text-cyan-800">Public policy</p>
        <h1 className="mt-2 text-3xl font-black text-slate-950">Terms and limitations</h1>
        <p className="mt-2 text-sm leading-6 text-slate-700">Reference tools are presented with their operational limits.</p>
      </header>
      <section className="space-y-4 rounded-xl border border-stone-200 bg-white p-5 text-sm leading-7 text-slate-700">
        <p>TaxOracle is a preliminary screening and rule-trace surface. It is not an official tax assessment, legal opinion, appraisal, loan approval, safety guarantee, investment score or purchase recommendation.</p>
        <p>Holding Cost is an illustrative current-input estimate, not an actual bill or quote. Location, terrain, market and financing modules are supporting reference tools and do not replace professional review.</p>
        <p>Missing, stale or unavailable data must be treated as unresolved. Users are responsible for confirming facts with tax professionals, banks, appraisers, lawyers, land agents and government agencies before acting.</p>
      </section>
      <Link className="text-sm font-bold text-cyan-800 underline" href="/">Back to the product</Link>
    </main>
  );
}
