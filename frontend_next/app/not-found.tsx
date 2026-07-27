export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-[60vh] max-w-xl flex-col justify-center gap-4 px-6 py-12">
      <div role="alert" className="rounded-2xl border border-slate-200 bg-white p-6 text-slate-900">
        <h1 className="text-xl font-bold">找不到這個頁面</h1>
        <p className="mt-2 text-sm leading-6">請回到首頁繼續查詢物件資料。</p>
      </div>
      <a href="/" className="w-fit rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white">回到首頁</a>
    </main>
  );
}
