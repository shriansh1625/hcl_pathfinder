"use client";

import { IntelligenceProvider } from "@/lib/session";
import { ThemeProvider } from "@/lib/theme";
import { PointerField } from "@/components/shell/PointerField";
import type { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <IntelligenceProvider>
        <PointerField />
        {children}
      </IntelligenceProvider>
    </ThemeProvider>
  );
}
