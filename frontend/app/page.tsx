"use client";

import { Onboarding } from "@/components/onboarding/Onboarding";
import { ThemeSwitch } from "@/components/shell/ThemeSwitch";

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <div className="fixed right-6 top-5 z-30">
        <ThemeSwitch />
      </div>
      <Onboarding />
    </div>
  );
}
