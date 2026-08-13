import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

export function Button({
  children,
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; children: ReactNode }) {
  const styles: Record<Variant, string> = {
    primary:
      "bg-accent text-ink-950 hover:bg-accent-dim disabled:opacity-50",
    secondary:
      "border border-line bg-ink-700 text-paper hover:border-accent/40 disabled:opacity-50",
    ghost: "text-mist hover:text-paper disabled:opacity-50",
  };
  return (
    <button
      type={props.type ?? "button"}
      className={`inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
