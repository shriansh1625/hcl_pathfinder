"use client";

import { ErrorState } from "@/components/ui/States";
import { Button } from "@/components/ui/Button";

export function OnboardAlert({
  message,
  onDismiss,
  onRetry,
}: {
  message: string;
  onDismiss?: () => void;
  onRetry?: () => void;
}) {
  return (
    <div className="onboard-alert-region" role="region" aria-label="Onboarding error">
      <ErrorState message={message} onRetry={onRetry} />
      {onDismiss ? (
        <Button variant="ghost" className="mt-3 px-0 text-xs" onClick={onDismiss}>
          Dismiss and continue manually
        </Button>
      ) : null}
    </div>
  );
}
