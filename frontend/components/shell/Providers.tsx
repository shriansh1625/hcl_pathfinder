"use client";

import { IntelligenceProvider } from "@/lib/session";
import { PointerField } from "@/components/shell/PointerField";
import type { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <IntelligenceProvider>
      <PointerField />
      {children}
    </IntelligenceProvider>
  );
}
