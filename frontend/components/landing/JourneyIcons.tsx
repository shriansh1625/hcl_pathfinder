type JourneyIconProps = { className?: string };

export function JourneyCompassIcon({ className = "" }: JourneyIconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.5" />
      <path d="M12 8v4l2.5 2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="m12 4 .8 2.2L12 8l-1.2-.8L12 4Z" fill="currentColor" />
    </svg>
  );
}

export function JourneyEvidenceIcon({ className = "" }: JourneyIconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="5" y="4" width="11" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M9 8h5M9 11h5M9 14h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="17.5" cy="16.5" r="3.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="m19.5 18.5 2 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function JourneyDiagnosisIcon({ className = "" }: JourneyIconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M8 8.5 11 11.5 16 6.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M6 14.5h4.5l2-2 2 2H18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

export function JourneyPathIcon({ className = "" }: JourneyIconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M6 6.5h11a2 2 0 0 1 2 2v9.5H8a2 2 0 0 1-2-2V6.5Z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M6 10.5h13" stroke="currentColor" strokeWidth="1.5" />
      <path d="M9 14.5h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function JourneyDestinationIcon({ className = "" }: JourneyIconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M6 19.5V8.5l6-3.5 6 3.5v11" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M10.5 12.5h3v7h-3z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M12 5v2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M12 5 14.5 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
