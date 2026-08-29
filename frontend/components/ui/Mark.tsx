import type { CSSProperties, ReactNode } from "react";

export function Mark({
  className = "h-3.5 w-5",
  title,
  style,
}: {
  className?: string;
  title?: string;
  style?: CSSProperties;
}) {
  return (
    <svg
      viewBox="0 0 24 16"
      width="24"
      height="16"
      className={className}
      style={style}
      fill="none"
      aria-hidden={title ? undefined : true}
      role={title ? "img" : "presentation"}
    >
      {title ? <title>{title}</title> : null}
      <path d="M1.5 12.5 H9.5 L15 3.5 H22.5" stroke="currentColor" strokeWidth="1.25" />
      <circle cx="1.5" cy="12.5" r="1.35" fill="currentColor" />
      <circle cx="9.5" cy="12.5" r="1.35" fill="currentColor" />
      <circle cx="15" cy="3.5" r="1.35" fill="currentColor" />
      <circle cx="22.5" cy="3.5" r="1.35" stroke="currentColor" strokeWidth="1.25" />
    </svg>
  );
}

export function Waypoint({
  kind,
  className = "h-3 w-3",
}: {
  kind: "filled" | "open" | "blocked" | "path";
  className?: string;
}) {
  if (kind === "path") return <Mark className={className} />;
  if (kind === "blocked") {
    return (
      <svg viewBox="0 0 12 12" className={className} fill="none" aria-hidden>
        <rect x="2.75" y="2.75" width="6.5" height="6.5" stroke="currentColor" strokeWidth="1.25" />
      </svg>
    );
  }
  if (kind === "open") {
    return (
      <svg viewBox="0 0 12 12" className={className} fill="none" aria-hidden>
        <circle cx="6" cy="6" r="3.4" stroke="currentColor" strokeWidth="1.25" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 12 12" className={className} aria-hidden>
      <circle cx="6" cy="6" r="3.1" fill="currentColor" />
    </svg>
  );
}

export function ScreenKicker({
  verb,
  children,
}: {
  verb: "KNOW" | "DIAGNOSE" | "PROVE" | "ADAPT" | "PATH";
  children?: ReactNode;
}) {
  return (
    <p className="type-section flex items-center gap-2">
      <Mark className="h-3 w-[18px] shrink-0 text-paper/70" />
      <span>{verb}</span>
      {children ? <span className="font-normal tracking-[0.14em] text-mist/70">· {children}</span> : null}
    </p>
  );
}

/** Vertical route connector between path items */
export function RouteConnector({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block w-px bg-gradient-to-b from-transparent via-paper/15 to-transparent ${className}`}
      aria-hidden
    />
  );
}
