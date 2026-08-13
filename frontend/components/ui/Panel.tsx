import type { ReactNode } from "react";

export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-xl border border-line bg-ink-800/80 shadow-panel ${className}`}>
      {children}
    </section>
  );
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
    <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
      <div>
        {kicker ? (
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-accent">{kicker}</p>
        ) : null}
        <h2 className="mt-1 text-lg font-medium text-paper">{title}</h2>
      </div>
      {action}
    </header>
  );
}
