# Light Theme EdTech Audit — PathFinder

## P0 Problems (before fix)

| Problem | Cause | Fix |
|---------|-------|-----|
| Background too flat/pale | Light tokens used near-white surfaces (`#f8f4e9`) with weak gradient layers | Warmer ivory base (`#e3dac6`→`#ebe4d2`), stronger radial depth on `body` |
| Body text low contrast | `--mist: #6e675a` on cream ≈ 4.2:1 on some surfaces | `--mist: #4f483d`, `--text-secondary: #524c42` for body/lead copy |
| Buttons look like text | `.btn-ghost` had no border/background; secondary was transparent | Light-specific borders, shadows, hover lift on all button variants |
| Primary CTA not obvious | Sage green primary blended with parchment | Navy filled CTA (`--brand-navy`) with elevation shadow |
| Form fields invisible | Goal field border too faint | `1.5px` borders, focus ring, elevated surface |
| Career cards ambiguous | Low border contrast, weak selected state | Strong borders, hover lift, accent selected fill |

## Screens Audited

- Homepage (hero, nav, value strip, onboarding)
- Onboarding wizard (goal, career, profile)
- Career explorer cards
- Workspace nav, dashboard, path, progress, assessment
- Result/adaptation views

## Design Principles Applied (Apna College reference — principles only)

- Strong contrast for readability
- Obvious interactive elements (shape + border + shadow)
- Clear navigation with hover states
- Generous whitespace preserved
- Primary CTA unmistakable (filled navy)
- Secondary CTA clearly bordered

## PathFinder Identity Preserved

- Bodoni Moda editorial serif headlines
- Sage accent for emphasis lines
- Path/route geometry motifs
- Warm parchment palette (not Apna blue/yellow)
- PathFinder journey hero image

## Token Additions

- `--text-primary`, `--text-secondary`, `--text-muted`
- `--brand-navy`, `--brand-navy-hover`
- `--shadow-raised`, `--shadow-elevated`

## Files Changed

- `frontend/app/globals.css` — light tokens + master pass block
- (No backend changes)
