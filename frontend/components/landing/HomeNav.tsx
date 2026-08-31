"use client";

import Link from "next/link";
import { Mark } from "@/components/ui/Mark";
import { ThemeSwitch } from "@/components/shell/ThemeSwitch";
import { Button } from "@/components/ui/Button";

type HomeNavProps = {
  onBuildPath?: () => void;
};

const LINKS = [
  { href: "#careers", label: "Explore Careers" },
  { href: "#how-it-works", label: "How It Works" },
  { href: "#get-started", label: "My Path" },
  { href: "#resources", label: "Resources" },
] as const;

export function HomeNav({ onBuildPath }: HomeNavProps) {
  return (
    <header className="home-nav">
      <div className="home-nav-inner">
        <div className="home-nav-start">
          <Link href="/" className="home-nav-brand">
            <Mark className="home-logo-mark h-4 w-6 text-accent" title="PathFinder" />
            <span className="home-nav-wordmark">PathFinder</span>
          </Link>
        </div>

        <nav className="home-nav-center hidden lg:flex" aria-label="Main">
          {LINKS.map((link) => (
            <a key={link.href} href={link.href} className="home-nav-link">
              {link.label}
            </a>
          ))}
        </nav>

        <div className="home-nav-end">
          <ThemeSwitch />
          <Button className="home-cta-primary home-cta-nav hidden sm:inline-flex" showMark onClick={onBuildPath}>
            Build My Path
          </Button>
        </div>
      </div>
    </header>
  );
}
