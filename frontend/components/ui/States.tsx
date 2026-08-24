export function LoadingState({ label = "Loading intelligence…" }: { label?: string }) {
  return (
    <div role="status" className="py-8 text-sm text-mist">
      {label}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
  context = "The backend did not confirm this action. Nothing was updated locally.",
}: {
  message: string;
  onRetry?: () => void;
  context?: string;
}) {
  return (
    <div role="alert" className="border border-rose-400/25 px-5 py-6">
      <p className="text-sm font-medium text-rose-100">Request failed</p>
      <p className="mt-2 text-sm text-rose-100/80">{context}</p>
      <p className="mt-2 font-mono text-xs text-rose-100/70">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="btn-press mt-4 border border-rose-200/30 px-3 py-1.5 text-sm text-rose-50"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="py-8">
      <p className="text-sm font-medium text-paper">{title}</p>
      <p className="mt-2 text-sm text-mist">{body}</p>
    </div>
  );
}
