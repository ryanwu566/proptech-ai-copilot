export function VisualDataUnavailableState({ message = "資料暫時無法取得，請稍後再試；不以缺少資料推論低風險或零值。" }: { message?: string }) {
  return <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm leading-6 text-amber-900" role="status" aria-live="polite">{message}</div>;
}
