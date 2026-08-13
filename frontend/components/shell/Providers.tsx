"use client";

import { IntelligenceProvider } from "@/lib/session";
import type { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  return <IntelligenceProvider>{children}</IntelligenceProvider>;
}
