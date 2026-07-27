export function VisualDataUnavailableState({ message = "目前沒有足夠的資料可安全呈現圖表。" }: { message?: string }) {
  return <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm leading-6 text-amber-900" role="status">{message}</div>;
}
