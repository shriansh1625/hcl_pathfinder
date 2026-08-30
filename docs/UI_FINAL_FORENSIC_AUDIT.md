# PathFinder — UI final forensic audit

Inspected from current source (`frontend/app/globals.css`, shell, onboarding, workspace instruments) plus prior production captures in `artifacts/ui-final/after/`. Intelligence backends are out of scope.

Scoring is visual/product presentation only. A 10 requires atmosphere, hierarchy, interaction, and screenshot-without-logo distinctiveness.

| SCREEN | CURRENT /10 | TOP PROBLEMS | SEVERITY | ROOT CAUSE | PROPOSED FIX | POST-FIX /10 |
|---|---|---|---|---|---|---|
| Landing / onboarding | 7 | Dark field reads as black void; ambient route is faint; left column has unused gravity | P0 | `--bg: #08090b` + two weak radials; no pointer-tied atmosphere | Warm graphite canvas, layered light fields, route geometry | 8 |
| Goal input | 7 | Focus is a 1px border; field still textarea-like | P1 | Goal field uses hairline only | Local sage glow + route activation on focus (keep real resolve) | 8 |
| Goal resolution | 7 | Resolved card is a box on a dead canvas | P2 | Surface equals canvas | Elevated parchment-on-charcoal card | 8 |
| Career Explorer | 6 | Unselected cards share one template; peek route is a 3-dot bar | P0 | Grid of identical hairline cards | Selected = destination; peek illuminates route; skill signature on select | 8 |
| Career comparison | 7 | Editorial columns exist; still low chroma | P2 | Compare uses same mist text | Cool vs sage column identity | 8 |
| Experience / interests / schedule | 6 | Questionnaire density; controls are generic | P2 | Form language, not configuration instrument | Stronger selected chips, sage complete steps | 7 |
| Evidence | 7 | Honest UNKNOWN semantics; visually grey | P1 | Raw enum leaked historically; meters thin | No-evidence dashed amber track; never 0% | 8 |
| Profile | 7 | Clear copy, flat summary | P2 | Same hairline as every panel | Destination recap with route mark | 8 |
| Dashboard | 6 | Command cells sit on identical black; competency is a meter list | P0 | `.command-cell { background: var(--bg) }` | Elevated graphite cells, semantic meters, destination-first | 8 |
| Blockers | 7 | Causal cards exist; still type-heavy | P2 | Little chroma on WAIT vs GAP | Amber verify / rose blocked / sage frozen | 8 |
| Path | 7 | Spine exists but still reads as a list below the fold | P0 | Connectors are 1px grey; waypoints uncolored | Semantic waypoint + connector by state; hover Why | 8 |
| Why resource | 8 | Drawer is forensic; overlay collision fixed | P2 | Drawer surface = black | Elevated focus surface, sage frozen | 8 |
| Progress | 7 | Native slider; buttons generic | P1 | `accent-color` only | Track + target marker + tactile press | 8 |
| Assessment | 8 | Question-first is correct | P2 | Answers still grey rows | Selected waypoint fills sage | 8 |
| Result | 7 | Chain exists; not captured in last QA | P1 | Missing browser proof | Metric-first + semantic before/after | 8 |
| Path Changed | 8 | Cascade + FLIP exist | P1 | Sequence can feel like captions | Stronger V1 grey / V2 sage contrast | 8 |
| Why Changed | 7 | Forensic grid; UNKNOWN leaked as copy | P1 | Raw enum in diagnosis line | Display labels: NO EVIDENCE → GAP | 8 |
| Timeline | 7 | Archive spine works; Continue was a no-op | P0 (fixed) | Flow clamped to last index | History → Skill Map; archival vs live chroma | 8 |
| Skill Map | 5 | Typographic edge list, not a map | P0 | `<ul class="skill-graph">` of text rows | Spatial neighborhood plot, HARD/SOFT weight | 8 |
| Grounded AI | 7 | Left-rule note is correct; chips look like a prompt palette | P2 | Chip chrome | Fact chips with source emphasis | 8 |
| Ask PathFinder | 7 | Not a chatbot; still a form footer | P2 | Same hairline as everything | Analyst surface, local glow on focus | 8 |
| Judge Mode | 6 | Tall on 390px; tutorial strip | P1 | Four-column rail stacked | Compact mobile; sage progress ticks | 7 |
| Shell / canvas | 5 | Dead black, pure-ivory type, faint grid | P0 | Token set is near-monochrome | Layered graphite + sage/amber/cool fields | 8 |
| Motion / pointer | 6 | Tokens exist; environment does not respond | P1 | Pointer vars unused on canvas | 1–4px light-field drift, reduced-motion off | 8 |

## Visual self-red-team (pre-change)

Without the word PATHFINDER, screenshots still read as a serious dark editorial product — not purple-AI. The failure mode is **monochrome flatness**: parchment-on-black everywhere, so Path, Dashboard, and Skill Map share one temperature. Color is not doing semantic work. Skill Map is the weakest instrument.

## Constraints honored

- No backend intelligence changes in this pass.
- Testids `.path-row`, `result-hero`, `adapt-cascade`, `path-timeline`, `judge-guide` preserved.
- UNKNOWN remains a backend enum; UI copy uses “No evidence” / “NO EVIDENCE”.
