"use client";

import { ErrorState } from "@/components/ui/States";
import { Button } from "@/components/ui/Button";

export function OnboardAlert({
  message,
  onDismiss,
  onRetry,
  onManual,
}: {
  message: string;
  onDismiss?: () => void;
  onRetry?: () => void;
  onManual?: () => void;
}) {
  return (
    <div className="onboard-alert-region" role="region" aria-label="Onboarding error">
      <ErrorState message={message} onRetry={onRetry} />
      <div className="mt-3 flex flex-wrap gap-2">
        {onManual ? (
          <Button variant="secondary" className="px-3 py-1.5 text-xs" onClick={onManual}>
            Pick career manually
          </Button>
        ) : null}
        {onDismiss ? (
          <Button variant="ghost" className="px-0 text-xs" onClick={onDismiss}>
            Dismiss
          </Button>
        ) : null}
      </div>
    </div>
  );
}
