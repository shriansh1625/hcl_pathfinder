import type { ReactNode } from "react";

type Tone = "surface" | "elevated" | "none";

export function Panel({
  children,
  className = "",
  tone = "surface",
}: {
  children: ReactNode;
  className?: string;
  tone?: Tone;
}) {
  const tones: Record<Tone, string> = {
    none: "",
    surface: "border border-line bg-ink-800/40",
    elevated: "border border-line bg-ink-700 shadow-elevated",
  };
  return <section className={`${tones[tone]} ${className}`}>{children}</section>;
}

export function PanelHeader({
  kicker,
  title,
  action,
}: {
  kicker?: string;
  title: string;
  action?: ReactNode;
}) {
  return (
    <header className="flex items-start justify-between gap-4 border-b border-line px-0 py-4">
      <div>
        {kicker ? (
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-mist">{kicker}</p>
        ) : null}
        <h2 className="mt-1 font-display text-2xl font-medium text-paper">{title}</h2>
      </div>
      {action}
    </header>
  );
}
