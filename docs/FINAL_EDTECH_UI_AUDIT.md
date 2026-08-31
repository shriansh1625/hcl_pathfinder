# PathFinder — Final EdTech UI Audit

**Date:** August 2026  
**Scope:** Full frontend forensic audit before EdTech transformation  
**Method:** Source inspection, production build review, reference comparison

---

## Executive summary (pre-transformation)

PathFinder’s intelligence layer is strong, but the **first visual impression** reads as a technical demo: monospace kickers (KNOW · DIAGNOSE · ADAPT), ontology language above the fold, dark-default theme, and a split onboarding layout that buries the marketing story beside a wizard panel. Judges and students must infer value from engineering vocabulary instead of career outcomes.

**Primary fix:** Recompose `/` as a mature EdTech homepage (light-primary), progressive disclosure of complexity, human copy on every screen, preserved backend semantics.

---

## Screen-by-screen audit

### 01 — Home / Onboarding (`/`)

| Dimension | Finding |
|-----------|---------|
| **Current problem** | No dedicated marketing homepage; hero and 7-step wizard share one viewport; dark atmospheric default. |
| **User confusion** | “Career ontology,” “semantic ML,” “LLM” in hero subcopy before user understands the product. |
| **Visual weakness** | Ambient SVG is decorative, not explanatory; no nav, no sections, no trust bar. |
| **Interaction weakness** | Primary action competes with wizard panel; no “Explore Careers” secondary path. |
| **What should change** | Full hero + journey visual + 7 content sections; wizard in `#get-started`; light default; human headline copy. |

### 02 — Goal intake (step 0)

| Dimension | Finding |
|-----------|---------|
| **Current problem** | Field is good functionally but framed as “resolve goal” not “what do you want to become?” |
| **User confusion** | RESOLVED / AMBIGUOUS / UNSUPPORTED states use system language. |
| **Visual weakness** | Buried in right column on desktop. |
| **Interaction weakness** | Manual career escape is small. |
| **What should change** | Plain prompt: “What are you trying to become?”; friendlier state labels; prominent Build My Path. |

### 03 — Career Explorer

| Dimension | Finding |
|-----------|---------|
| **Current problem** | “Live ontology” framing; cards functional but dense. |
| **User confusion** | Compare feature not obvious from nav. |
| **Visual weakness** | Feels like admin picker, not career discovery. |
| **Interaction weakness** | Search works; preview hierarchy could be clearer. |
| **What should change** | “Explore careers”; what it is / what you learn / gaps preview; professional hierarchy. |

### 04 — Compare (within Career Explorer)

| Dimension | Finding |
|-----------|---------|
| **Current problem** | Embedded only; no top-level discoverability. |
| **User confusion** | Low — works when found. |
| **Visual weakness** | Side-by-side tables adequate but not editorial. |
| **Interaction weakness** | None critical. |
| **What should change** | Clearer section title on homepage careers band. |

### 05 — Profile steps (experience → review)

| Dimension | Finding |
|-----------|---------|
| **Current problem** | Steps are clear; evidence step uses “competency model” language. |
| **User confusion** | Demo evidence toggle purpose unclear to non-technical users. |
| **Visual weakness** | Consistent with panel; acceptable. |
| **Interaction weakness** | Judge demo buried in final step. |
| **What should change** | Softer evidence copy; keep judge demo for evaluators. |

### 06 — Dashboard (Overview)

| Dimension | Finding |
|-----------|---------|
| **Current problem** | “KNOW · Dashboard” reads as analytics admin. |
| **User confusion** | KPI grid competes with narrative. |
| **Visual weakness** | Command-center layout; numbers before story. |
| **Interaction weakness** | IntelligenceExplainer adds tech depth early. |
| **What should change** | “My career journey”; destination → position → next → gaps story. |

### 07 — Blockers

| Dimension | Finding |
|-----------|---------|
| **Current problem** | Not in primary nav; DIAGNOSE kicker. |
| **User confusion** | CONFLICT pills are engineer-facing. |
| **Visual weakness** | Dense lists. |
| **Interaction weakness** | Reachable via flow only. |
| **What should change** | “What’s holding you back”; prerequisite chains in plain language. |

### 08 — My Path

| Dimension | Finding |
|-----------|---------|
| **Current problem** | Strong spine metaphor; still list-like on mobile. |
| **User confusion** | EXECUTABLE / WAITING labels internal. |
| **Visual weakness** | Good route spine; week grouping could feel more journey-like. |
| **Interaction weakness** | WHY drawer works. |
| **What should change** | Journey framing; human status labels where shown. |

### 09 — WHY drawer

| Dimension | Finding |
|-----------|---------|
| **Current problem** | Scoring factors visible immediately — good for judges, heavy for students. |
| **User confusion** | Semantic signal jargon. |
| **Visual weakness** | Drawer layout solid. |
| **Interaction weakness** | None. |
| **What should change** | Lead with Why this / Why now / What it unlocks; progressive disclosure for scores. |

### 10 — Progress actions

| Dimension | Finding |
|-----------|---------|
| **Current problem** | “Submit progress” / “Evidence, not a shortcut” — accurate but cold. |
| **User confusion** | Confidence slider without “how did this feel?” framing. |
| **Visual weakness** | Functional surfaces. |
| **Interaction weakness** | Complete / Struggled / Skip work. |
| **What should change** | “How did this feel?”; keep backend semantics. |

### 11 — Assessment (Prove + Run)

| Dimension | Finding |
|-----------|---------|
| **Current problem** | PROVE kicker; “Skill under evaluation” clinical. |
| **User confusion** | Low during run. |
| **Visual weakness** | Clean enough; not gamified (good). |
| **Interaction weakness** | Loading copy “Updating competency model” is technical. |
| **What should change** | “Skill check”; “Updating your profile…” loading. |

### 12 — Result

| Dimension | Finding |
|-----------|---------|
| **Current problem** | Before → Evidence → After chain is strong. |
| **User confusion** | “Evidence recorded” vs outcome story. |
| **Visual weakness** | Good animation. |
| **Interaction weakness** | CTA clear. |
| **What should change** | “Because your evidence changed, your path can change.” |

### 13–14 — Path V1 / V2 (PathChanged)

| Dimension | Finding |
|-----------|---------|
| **Current problem** | Signature moment exists; cascade uses engineer labels. |
| **User confusion** | PathDiff group names (ADDED/MOVED) raw. |
| **Visual weakness** | FLIP strong; frozen work callout could be louder. |
| **Interaction weakness** | None — keep FLIP. |
| **What should change** | Student sequence: What we knew → New evidence → What changed → New path. |

### 15 — Why changed

| Dimension | Finding |
|-----------|---------|
| **Current problem** | “ADAPT · Causality” — forensic, not friendly. |
| **User confusion** | Grid is detailed. |
| **Visual weakness** | Adequate for judges. |
| **Interaction weakness** | None. |
| **What should change** | “Why your path changed” headline. |

### 16 — History (Timeline)

| Dimension | Finding |
|-----------|---------|
| **Current problem** | Archival tone correct; kicker technical. |
| **User confusion** | Low. |
| **Visual weakness** | Timeline readable. |
| **Interaction weakness** | None. |
| **What should change** | “Your path over time.” |

### 17 — Skill Map

| Dimension | Finding |
|-----------|---------|
| **Current problem** | “What blocks what?” — good; no intro framing. |
| **User confusion** | HARD/SOFT labels. |
| **Visual weakness** | Advanced viz is strong. |
| **Interaction weakness** | Selection works. |
| **What should change** | “See how skills depend on each other.” |

### 18 — Ask PathFinder (AI)

| Dimension | Finding |
|-----------|---------|
| **Current problem** | “Contextual analyst” — better than chatbot but still tech. |
| **User confusion** | Grounded IN panel good for trust. |
| **Visual weakness** | Chip context helpful. |
| **Interaction weakness** | None. |
| **What should change** | “Your learning guide”; facts first. |

### 19 — Judge Mode

| Dimension | Finding |
|-----------|---------|
| **Current problem** | Mission rail is dense on mobile. |
| **User confusion** | Evaluator-only — acceptable. |
| **Visual weakness** | Compact by design. |
| **Interaction weakness** | Jumps work. |
| **What should change** | Minor polish only; preserve for demos. |

---

## System-level findings

| Area | Problem | Change |
|------|---------|--------|
| **Theme default** | Dark first | Light primary; art-directed both |
| **Navigation** | No marketing nav; workspace labels technical | EdTech nav + human labels |
| **Typography** | Mono kickers everywhere | Reserve mono for metadata |
| **Motion** | Good FLIP; some decorative ambient | Keep FLIP; 80–360ms micro-interactions |
| **globals.css** | Mature token system | Extend landing + navy CTA tokens for light |
| **Responsive** | Mobile overflow fixed on path-v2 | Re-test all breakpoints post-redesign |

---

## Post-transformation section

*Updated after implementation — see transformation report at end of this file.*
