# PathFinder — Interaction audit

Manual interaction against production (`next start` :3002, API :8000) plus Playwright capture in `artifacts/ui-grok-final/`. Intelligence backends were not modified.

| FEATURE | EXPECTED INTERACTION | ACTUAL INTERACTION | QUALITY /10 | FIX |
|---|---|---|---|---|
| Goal input | Focus glow, real resolve, destination card | Focus + sage CTA; resolve produced AI/ML Engineer | 8 | Keep; disabled until 3+ chars (correct) |
| Career search | Filter roles | Search field present; cards remain | 7 | Unselected cards still share one template |
| Career selection | Destination + skill signature | Selected AI/ML gets sage inset + PYTHON · SQL · GIT | 8 | Peek route is a 3-dot bar, not a preview graph |
| Career comparison | Two-role columns | Compare opens Role A/B selects; Role B loads Backend | 7 | Still two selects, not a dual route |
| Profile | Recap then launch | Path configuration grid + Judge demo | 8 | Form language remains |
| Dashboard | Destination-first, next action | AI/ML hero, 1/6, Verify docker, amber meters | 8 | Competency still stacked meters |
| Blockers | Causal cards | Docker No evidence / WAITING FOR VERIFICATION | 8 | Backend explanations leaked UNKNOWN in captured build; display now humanized |
| Path item | Waypoint + Why | Spine + week markers; Why opens drawer | 7 | Progress buttons make rows list-like |
| Why drawer | Forensic fields | Score breakdown + causality | 8 | Overlay Close vs dismiss already distinct |
| Progress | COMPLETE / STRUGGLED / SKIP | Buttons on executable items | 7 | Native slider still thin |
| Assessment answer | Selected waypoint fills | Hairline answers, sage Next | 8 | Question-first holds |
| Assessment submit | Result hero | Playwright timed out on `result-hero` (120s) | 5 | Same gap as prior QA; not recaptured |
| Result | BEFORE → evidence → AFTER | Not captured this pass | — | Needs live submit |
| V1 → V2 | Cascade + FLIP | Not captured this pass | — | Blocked by result timeout |
| Timeline | Version focus | V1/V2 archive spine + inspect | 8 | Continue now routes to Skill Map |
| Skill map | Neighborhood plot | HARD red / SOFT dashed SVG; selected sage node | 8 | Typographic edge list hidden on desktop |
| Ask PathFinder | Analyst, not chat | Chips + input under path | 7 | Chip palette still prompt-like |
| Judge Mode | Where / learned / changed / next | Compact rail on desktop; 2 fields hidden on 390 | 7 | Tall on mobile even after compact CSS |
| History Continue | Advance off History | Source: `nextFlowView("history")` → `map` | 8 | Production capture did not click it this loop |
| Reset | Return to landing | Header Reset present | 8 | Not failure-tested this loop |
