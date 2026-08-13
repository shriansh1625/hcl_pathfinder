export function LoadingState({ label = "Loading intelligence…" }: { label?: string }) {
  return (
    <div role="status" className="rounded-xl border border-line bg-ink-800 px-5 py-8 text-sm text-mist">
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-xl border border-rose-400/30 bg-rose-400/10 px-5 py-6">
      <p className="text-sm font-medium text-rose-100">Something failed</p>
      <p className="mt-2 text-sm text-rose-100/80">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-md border border-rose-200/30 px-3 py-1.5 text-sm text-rose-50"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-dashed border-line px-5 py-8">
      <p className="text-sm font-medium text-paper">{title}</p>
      <p className="mt-2 text-sm text-mist">{body}</p>
    </div>
  );
}
