import Link from "next/link";
/** Retired commercial comparison entry; canonical selection lives at /compare. */
export function PropertyCaseComparisonWorkbench() {
  return <section className="ds-panel"><p>比較 2–4 個已儲存案件的證據、假設與限制。</p><Link href="/compare" className="ds-button ds-button--primary">開啟案件證據比較</Link></section>;
}