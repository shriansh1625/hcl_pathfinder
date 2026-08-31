type ValueIconProps = {
  name: "evidence" | "everyone" | "private" | "outcome";
  className?: string;
};

export function ValueIcon({ name, className = "" }: ValueIconProps) {
  const common = { className: `home-value-icon ${className}`.trim(), viewBox: "0 0 24 24", fill: "none", "aria-hidden": true as const };

  switch (name) {
    case "evidence":
      return (
        <svg {...common}>
          <path d="M12 3 4 6.5v6.2c0 4.1 3.4 7.9 8 8.3 4.6-.4 8-4.2 8-8.3V6.5L12 3Z" stroke="currentColor" strokeWidth="1.5" />
          <path d="m9.2 12.1 1.9 1.9 4.7-4.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "everyone":
      return (
        <svg {...common}>
          <circle cx="9" cy="8.5" r="2.5" stroke="currentColor" strokeWidth="1.5" />
          <circle cx="16" cy="9.5" r="2" stroke="currentColor" strokeWidth="1.5" />
          <path d="M4.5 18.5c.8-2.4 2.8-3.8 4.5-3.8s3.7 1.4 4.5 3.8M13 18.5c.5-1.6 1.7-2.7 3-2.7 1.4 0 2.5 1.1 3 2.7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "private":
      return (
        <svg {...common}>
          <rect x="5.5" y="10.5" width="13" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
          <path d="M8.5 10.5V8.8a3.5 3.5 0 0 1 7 0v1.7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "outcome":
      return (
        <svg {...common}>
          <path d="M6 17.5 10.5 13l3 3L18 9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M14.5 9.5H18v3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M5 19.5h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
  }
}
