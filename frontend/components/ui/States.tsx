import type { ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { Mark } from "@/components/ui/Mark";

export function LoadingState({
  label = "Loading intelligence…",
  detail,
}: {
  label?: string;
  detail?: string;
}) {
  return (
    <div role="status" className="loading-context" aria-live="polite">
      <Mark className="loading-context-mark h-3 w-[18px] text-accent/80" />
      <div>
        <p className="loading-context-label">{label}</p>
        {detail ? <p className="loading-context-detail">{detail}</p> : null}
      </div>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
  context = "The backend did not confirm this action. Nothing was updated locally.",
  title = "Request failed",
}: {
  message: string;
  onRetry?: () => void;
  context?: string;
  title?: string;
}) {
  return (
    <div role="alert" className="error-state">
      <p className="error-state-kicker">What could not load</p>
      <p className="mt-2 text-sm font-medium text-paper">{title}</p>
      <p className="mt-2 text-sm leading-relaxed text-mist">{context}</p>
      <p className="mt-3 font-mono text-xs text-mist/90">{message}</p>
      {onRetry ? (
        <Button variant="secondary" className="mt-4 px-3 py-1.5 text-xs" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <p className="empty-state-kicker">Nothing here yet</p>
      <p className="mt-2 text-sm font-medium text-paper">{title}</p>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-mist">{body}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
