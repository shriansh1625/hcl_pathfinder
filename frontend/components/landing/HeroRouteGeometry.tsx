"use client";

/** Abstract route path through the hero — decorative, pointer-responsive via CSS vars. */
export function HeroRouteGeometry() {
  return (
    <svg className="hero-route-geo" viewBox="0 0 1200 600" preserveAspectRatio="xMidYMid slice" aria-hidden>
      <defs>
        <linearGradient id="hero-geo-grad" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="var(--hero-geo-start)" stopOpacity="0.35" />
          <stop offset="50%" stopColor="var(--hero-geo-mid)" stopOpacity="0.25" />
          <stop offset="100%" stopColor="var(--hero-geo-end)" stopOpacity="0.2" />
        </linearGradient>
      </defs>
      <path
        className="hero-route-geo-line"
        d="M 80 520 C 200 440, 280 380, 400 320 S 620 220, 760 180 S 980 120, 1100 80"
        fill="none"
      />
      <circle className="hero-route-node hero-route-node-1" cx="80" cy="520" r="4" />
      <circle className="hero-route-node hero-route-node-2" cx="280" cy="380" r="3.5" />
      <circle className="hero-route-node hero-route-node-3" cx="520" cy="260" r="3" />
      <circle className="hero-route-node hero-route-node-4" cx="760" cy="180" r="3" />
      <circle className="hero-route-node hero-route-node-5" cx="1100" cy="80" r="5" />
    </svg>
  );
}
