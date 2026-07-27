"use client";

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <html lang="zh-Hant">
      <body>
        <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-4 px-6 py-12">
          <div role="alert" className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-950">
            <h1 className="text-xl font-bold">服務暫時無法顯示</h1>
            <p className="mt-2 text-sm leading-6">請重新載入或稍後再試，未完成的資料不會被補成假結果。</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={() => reset()} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white">再試一次</button>
            <a href="/" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700">回到首頁</a>
          </div>
        </main>
      </body>
    </html>
  );
}
