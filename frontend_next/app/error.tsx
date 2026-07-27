"use client";

import { useEffect } from "react";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  useEffect(() => undefined, []);
  return (
    <main className="mx-auto flex min-h-[60vh] max-w-xl flex-col justify-center gap-4 px-6 py-12">
      <div role="alert" className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-950">
        <h1 className="text-xl font-bold">這個頁面暫時無法載入</h1>
        <p className="mt-2 text-sm leading-6">目前沒有可安全顯示的資料，請稍後重試。</p>
      </div>
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={() => reset()} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white">再試一次</button>
        <a href="/" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700">回到首頁</a>
      </div>
    </main>
  );
}
