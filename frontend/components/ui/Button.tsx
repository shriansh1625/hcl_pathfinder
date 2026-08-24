import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Mark } from "@/components/ui/Mark";

type Variant = "primary" | "secondary" | "ghost" | "danger";

export function Button({
  children,
  variant = "primary",
  className = "",
  showMark = false,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
  showMark?: boolean;
}) {
  const styles: Record<Variant, string> = {
    primary: "btn-primary",
    secondary: "btn-secondary",
    ghost: "btn-ghost",
    danger: "btn-danger",
  };
  return (
    <button
      type={props.type ?? "button"}
      className={`btn-press inline-flex items-center justify-center gap-2 rounded-sm px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-45 ${styles[variant]} ${className}`}
      {...props}
    >
      {showMark && variant === "primary" ? (
        <Mark className="btn-mark h-2.5 w-4 shrink-0" />
      ) : null}
      {children}
    </button>
  );
}
