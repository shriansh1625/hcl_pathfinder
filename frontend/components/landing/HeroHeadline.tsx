const LINES = [
  { text: "Build the path to the", className: "hero-line-strong" },
  { text: "career you", className: "hero-line-soft" },
  { text: "actually want.", className: "hero-line-accent" },
] as const;

export function HeroHeadline() {
  return (
    <h1 className="home-headline">
      {LINES.map((line, index) => (
        <span key={line.text} className="hero-line-wrap" style={{ ["--line-i" as string]: index }}>
          <span className={`hero-line ${line.className}`}>{line.text}</span>
        </span>
      ))}
    </h1>
  );
}
